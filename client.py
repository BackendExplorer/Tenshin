import socket
import threading

SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 49152
CLIENT_ADDRESS = 'localhost'

# クライアントのポート番号をユーザーに入力させる
while True:
    CLIENT_PORT = int(input("Enter a port number for the client (1024-65535): "))
    if 1024 <= CLIENT_PORT <= 65535:
        break

# クライアントのユーザー名をユーザーに入力させる
while True:
    username = input("Enter a username: ")
    if len(username.encode('utf-8')) > 255:
        print("The username is too long. (Enter a username within 255 bytes)")
    else:
        break

# メッセージパケットを作成する
def build_packet(username_bits, message_bits):
    username_length = len(username_bits)
    header = username_length.to_bytes(1, 'big')
    return header + username_bits + message_bits

# サーバからのメッセージを受信して表示する
def recv_data(sock):
    while True:
        data, address = sock.recvfrom(1024)
        data = data.decode("utf-8")
        print(f'\n{data}')

print("Starting the chat. Type '/quit' to exit.")

# UDPソケットを作成し、指定したクライアントのポートでバインドする
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind((CLIENT_ADDRESS, CLIENT_PORT))

    # サーバからのメッセージ受信を別スレッドで処理
    threading.Thread(target=recv_data, args=(sock,), daemon=True).start()

    # ユーザー入力のループ
    while True:
        message = input('Enter a message (or "quit" to exit): ')
        if message == "quit":  # '/quit'を入力するとチャットを終了
            break

        # 入力されたメッセージをUTF-8でエンコード
        username_bits = username.encode('utf-8')
        message_bits = message.encode('utf-8')

        # メッセージが4096バイトを超えているか確認
        packet = build_packet(username_bits, message_bits)
        if len(packet) > 4096:
            print("Error: Message is too long. Maximum size is 4096 bytes.")
            continue

        # サーバにメッセージを送信
        sock.sendto(packet, (SERVER_ADDRESS, SERVER_PORT))

print("Disconnected from the server.")
