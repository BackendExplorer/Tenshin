import socket
import os
import json
import ffmpeg
from pathlib import Path

class MediaProcessor:
    # 初期化処理。指定されたディレクトリ(dpath)を作成する。
    def __init__(self, dpath='processed'):
        self.dpath = dpath
        os.makedirs(self.dpath, exist_ok=True)

    # 操作番号(operation)に基づき、適切なメディア処理メソッドを呼び出す。
    def process(self, json_file, input_file_path, file_name):
        operation = json_file['operation']
        match operation:
            case 1:
                return self.compress_video(input_file_path, file_name)
            case 2:
                return self.change_resolution(input_file_path, file_name, json_file['resolution'])
            case 3:
                return self.change_aspect_ratio(input_file_path, file_name, json_file['aspect_ratio'])
            case 4:
                return self.convert_to_audio(input_file_path, file_name)
            case 5:
                return self.create_gif(input_file_path, file_name, json_file['start_time'], json_file['duration'])

    # ビデオファイルを指定されたビットレートで圧縮する。
    def compress_video(self, input_file_path, file_name, bitrate='1M'):
        return self._ffmpeg_process(input_file_path, file_name, 'compressed_', b=bitrate)

    # ビデオファイルの解像度を変更する。
    def change_resolution(self, input_file_path, file_name, resolution):
        return self._ffmpeg_process(input_file_path, file_name, 'changed_resolution_', vf=f"scale={resolution}")

    # ビデオファイルのアスペクト比を変更する。
    def change_aspect_ratio(self, input_file_path, file_name, aspect_ratio):
        return self._ffmpeg_process(input_file_path, file_name, 'changed_aspect_ratio_', vf=f"setdar={aspect_ratio}")

    # ビデオファイルから音声を抽出し、音声ファイルに変換する。
    def convert_to_audio(self, input_file_path, file_name):
        base_name = os.path.splitext(file_name)[0]
        return self._ffmpeg_process(input_file_path, base_name + '.mp3', 'converted_to_audio_', acodec='mp3')

    # ビデオファイルの指定箇所からGIFアニメーションを生成する。
    def create_gif(self, input_file_path, file_name, start_time, duration, fps=10):
        base_name = os.path.splitext(file_name)[0]
        return self._ffmpeg_process(
            input_file_path, base_name + '.gif', 'created_gif_',
            ss=start_time, t=duration, vf=f"fps={fps}", pix_fmt='rgb24'
        )

    # ffmpegを使用してメディア処理を実行し、出力ファイルを生成する（内部処理メソッド）。
    def _ffmpeg_process(self, input_file_path, output_file_name, prefix, **kwargs):
        output_file_path = os.path.join(self.dpath, prefix + output_file_name)
        if os.path.exists(output_file_path):
            os.remove(output_file_path)
        ffmpeg.input(input_file_path).output(output_file_path, **kwargs).run()
        os.remove(input_file_path)
        return output_file_path


class TCPServer:
    # TCPサーバーの初期化。ソケットの設定、バインド、リッスンの開始、およびMediaProcessorのインスタンス生成を行う。
    def __init__(self, server_address, server_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = server_address
        self.server_port = server_port
        self.chunk_size = 1400
        self.processor = MediaProcessor()

        print('Starting up on {}'.format((server_address, server_port)))

        try:
            os.unlink(server_address)
        except FileNotFoundError:
            pass

        self.sock.bind((server_address, server_port))
        self.sock.listen()

    # クライアントからの接続を待ち、接続があれば各クライアントの処理を開始する。
    def start(self):
        while True:
            connection, client_address = self.sock.accept()
            try:
                print('Connection from', client_address)
                self.handle_client(connection)
            except Exception as e:
                print('Error:', e)
                self.send_error_response(connection, str(e))
            finally:
                print("Closing current connection")
                connection.close()

    # クライアントとの通信を処理し、メタデータ受信、ファイル受信、メディア変換、ファイル送信を行う。
    def handle_client(self, connection):
        header, file_size = self.receive_header(connection)
        if file_size == 0:
            raise Exception('No data to read from client.')

        json_file, media_type = self.receive_metadata(connection, header)
        input_file_path = self.receive_file(connection, json_file['file_name'], file_size)

        connection.send(bytes([0x00]))  # success

        output_file_path = self.processor.process(json_file, input_file_path, json_file['file_name'])
        self.send_file(connection, output_file_path)

    # クライアントから送信されたヘッダー部を受信し、JSONの長さ、メディアタイプの長さ、およびファイルサイズを抽出する。
    def receive_header(self, connection):
        header = connection.recv(8)
        json_length = int.from_bytes(header[0:2], "big")
        media_type_length = int.from_bytes(header[2:3], "big")
        file_size = int.from_bytes(header[3:8], "big")
        return (json_length, media_type_length), file_size

    # ヘッダー情報に基づいて、メタデータ部分（JSONデータおよびメディアタイプ）を受信・解析する。
    def receive_metadata(self, connection, header):
        json_length, media_type_length = header
        body = connection.recv(json_length + media_type_length)
        json_file = json.loads(body[:json_length].decode("utf-8"))
        media_type = body[json_length:].decode("utf-8")
        return json_file, media_type

    # クライアントからファイルデータをチャンク単位で受信し、指定されたパスに保存する。
    def receive_file(self, connection, file_name, file_size):
        input_file_path = os.path.join(self.processor.dpath, file_name)
        with open(input_file_path, 'wb+') as f:
            while file_size > 0:
                data = connection.recv(min(file_size, self.chunk_size))
                f.write(data)
                print('Received {} bytes'.format(len(data)))
                file_size -= len(data)
        print('Finished downloading the file from client.')
        return input_file_path

    # クライアントに対してエラーメッセージをJSON形式で送信する。
    def send_error_response(self, connection, error_message):
        json_file = {
            'error': True,
            'error_message': error_message
        }
        json_bytes = json.dumps(json_file).encode('utf-8')
        header = self.protocol_header(len(json_bytes), 0, 0)
        connection.sendall(header)
        connection.sendall(json_bytes)

    # 変換済みファイルをクライアントに送信するために、ファイル情報とファイル本体を順次送信する。
    def send_file(self, connection, output_file_path):
        media_type = os.path.splitext(output_file_path)[1]
        media_type_bytes = media_type.encode('utf-8')
        file_size = os.path.getsize(output_file_path)
        file_name = os.path.basename(output_file_path)

        json_file = {
            'file_name': file_name,
            'error': False,
            'error_message': None
        }
        json_bytes = json.dumps(json_file).encode('utf-8')
        header = self.protocol_header(len(json_bytes), len(media_type_bytes), file_size)
        connection.sendall(header)
        connection.sendall(json_bytes + media_type_bytes)

        with open(output_file_path, 'rb') as f:
            while data := f.read(self.chunk_size):
                print("Sending...")
                connection.send(data)

    # プロトコル仕様に沿ったヘッダー部を生成する。
    def protocol_header(self, json_length, media_type_length, payload_length):
        return json_length.to_bytes(2, "big") + media_type_length.to_bytes(1, "big") + payload_length.to_bytes(5, "big")


if __name__ == "__main__":
    server_address = '0.0.0.0'
    tcp_server_port = 9001
    server = TCPServer(server_address, tcp_server_port)
    server.start()
