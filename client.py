import socket
import sys
import os
import json
import ffmpeg
import re

class UserInterface:
    def input_file_path(self):
        valid_extensions = ('.mp4', '.avi')
        while True:
            file_path = input("ファイルパスを入力してください（mp4、aviのいずれかの拡張子）: ")
            if file_path.endswith(valid_extensions):
                print(f"有効なファイルパスが入力されました: {file_path}")
                return file_path
            else:
                print("無効なファイル拡張子です。もう一度試してください。")

    def input_operation(self):
        while True:
            print("1: 動画の圧縮, 2: 動画の解像度の変更, 3: 動画のアスペクト比の変更, 4: 動画を音声に変換, 5: 指定した時間範囲でGIFの作成")
            try:
                operation = int(input("オペレーションを入力してください(1-5): "))
                if operation in range(1, 6):
                    print(f"選択されたオペレーション: {operation}")
                    return operation
                else:
                    print("無効な選択です。1から5の数字を入力してください。")
            except ValueError:
                print("無効な入力です。数字を入力してください。")

    def input_operation_details(self, operation, json_file, file_path):
        if operation == 2:
            json_file = self.select_resolution(json_file)
        elif operation == 3:
            json_file = self.select_aspect_ratio(json_file)
        elif operation == 5:
            json_file = self.select_gif_range(json_file, file_path)
        return json_file

    def select_resolution(self, json_file):
        resolutions = {"1": "1920:1080", "2": "1280:720", "3": "720:480"}
        while True:
            print("1: フルHD(1920:1080), 2: HD(1280:720), 3: SD(720:480)")
            selection = input("希望する解像度の番号を入力してください。: ")
            if selection in resolutions:
                json_file['resolution'] = resolutions[selection]
                break
            else:
                print("無効な選択です。もう一度入力してください。")
        return json_file

    def select_aspect_ratio(self, json_file):
        ratios = {"1": "16/9", "2": "4/3", "3": "1/1"}
        while True:
            print("1: (16:9), 2: (4:3), 3: (1:1)")
            selection = input("希望するアスペクト比の番号を入力してください。: ")
            if selection in ratios:
                json_file['aspect_ratio'] = ratios[selection]
                break
            else:
                print("無効な選択です。もう一度入力してください。")
        return json_file

    def select_gif_range(self, json_file, file_path):
        duration = self.get_video_duration(file_path)
        HH, MM, SS = int(duration // 3600), int((duration % 3600) // 60), int(duration % 60)

        while True:
            print(f"動画の長さは{HH:02}:{MM:02}:{SS:02}です。")
            start_time = input("開始時間を入力してください（例: 00:00:10）: ")
            if re.match(r'^\d{2}:\d{2}:\d{2}$', start_time):
                st_HH, st_MM, st_SS = map(int, start_time.split(":"))
                start_sec = st_HH * 3600 + st_MM * 60 + st_SS
                if start_sec < duration:
                    json_file['start_time'] = start_sec
                    break
                else:
                    print(f"動画の長さ{HH:02}:{MM:02}:{SS:02}未満にしてください。")
            else:
                print("無効な時間形式です。もう一度入力してください。")

        while True:
            dur_input = input("再生時間を秒単位で入力してください（例: 10）: ")
            if dur_input.isdigit():
                dur = float(dur_input)
                if 0 < dur <= duration - json_file['start_time']:
                    json_file['duration'] = dur
                    break
                else:
                    print("再生時間が不正です。もう一度入力してください。")
            else:
                print("無効な再生時間です。数字を入力してください。")
        return json_file

    def get_video_duration(self, file_path):
        probe = ffmpeg.probe(file_path)
        return float(probe['format']['duration'])


class TCPClient:
    def __init__(self, server_address, server_port):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = server_address
        self.server_port = server_port
        self.chunk_size = 1400
        self.dpath = 'recieve'
        self.ui = UserInterface()
        os.makedirs(self.dpath, exist_ok=True)

    def start(self):
        try:
            self.sock.connect((self.server_address, self.server_port))
        except socket.error as err:
            print(err)
            sys.exit(1)
        self.upload_file()

    def upload_file(self):
        try:
            file_path = self.ui.input_file_path()
            media_type_bytes, media_type_bytes_length = self.get_media_type(file_path)

            with open(file_path, 'rb') as f:
                file_size, file_name = self.get_file_info(f)
                operation = self.ui.input_operation()

                json_file = {
                    'file_name': file_name,
                    'operation': operation
                }

                json_file = self.ui.input_operation_details(operation, json_file, file_path)
                json_string_bytes = json.dumps(json_file).encode('utf-8')
                json_string_bytes_length = len(json_string_bytes)

                header = self.protocol_header(json_string_bytes_length, media_type_bytes_length, file_size)
                self.sock.sendall(header)
                self.sock.sendall(json_string_bytes + media_type_bytes)
                self.send_file_data(f, file_size)

                self.handle_upload_response()
                self.recieve_file()

        except Exception as e:
            print(f"エラーが発生しました: {e}")

        finally:
            print('closing socket')
            self.sock.close()

    def get_media_type(self, file_path):
        _, media_type = os.path.splitext(file_path)
        media_type_bytes = media_type.encode('utf-8')
        return media_type_bytes, len(media_type_bytes)

    def get_file_info(self, file):
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        return file_size, os.path.basename(file.name)

    def send_file_data(self, file, file_size):
        data = file.read(self.chunk_size)
        while data:
            print("Sending...")
            self.sock.send(data)
            data = file.read(self.chunk_size)

    def handle_upload_response(self):
        response_bytes = self.sock.recv(16)
        response = int.from_bytes(response_bytes, "big")
        if response == 0x00:
            print("アップロードに成功しました")
        elif response == 0x01:
            print("アップロードに失敗しました")
            sys.exit(1)
        else:
            print("エラーが発生しました")
            sys.exit(1)

    def protocol_header(self, json_length, media_type_length, payload_length):
        return json_length.to_bytes(2, "big") + media_type_length.to_bytes(1, "big") + payload_length.to_bytes(5, "big")

    def recieve_file(self):
        header = self.sock.recv(8)
        json_length = int.from_bytes(header[0:2], "big")
        media_type_length = int.from_bytes(header[2:3], "big")
        file_size = int.from_bytes(header[3:8], "big")

        body = self.sock.recv(json_length + media_type_length)
        json_file = json.loads(body[:json_length].decode("utf-8"))
        media_type = body[json_length:].decode("utf-8")

        if json_file['error']:
            print("エラーが発生しました")
            print(json_file['error_message'])
            sys.exit(1)

        output_file_path = os.path.join(self.dpath, json_file['file_name'])
        print(output_file_path)

        try:
            with open(output_file_path, 'wb+') as f:
                while file_size > 0:
                    data = self.sock.recv(min(file_size, self.chunk_size))
                    f.write(data)
                    print('recieved {} bytes'.format(len(data)))
                    file_size -= len(data)
            print("ダウンロードに成功しました")
        except Exception as e:
            print('Error:', e)
            print("ダウンロードに失敗しました")


if __name__ == "__main__":
    server_address = '0.0.0.0'
    tcp_server_port = 9001
    tcp_client = TCPClient(server_address, tcp_server_port)
    tcp_client.start()
