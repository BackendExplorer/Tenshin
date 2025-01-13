import socket
import os
import time
import threading

SERVER_ADDRESS = "127.0.0.1"
SERVER_PORT = 49152

clients = {}
last_active_map = {}
TIMEOUT_SECONDS = 60

# 指定された送信者以外の全クライアントにメッセージをブロードキャストする
def broadcast_message(sender_addr, message_data, sock):
    for client_addr in clients.keys():
        if client_addr != sender_addr:
            sock.sendto(message_data.encode('utf-8'), client_addr)

# 最終アクティブ時間を監視し、非アクティブなクライアントを削除する
def remove_inactive_clients():
    while True:
        now = time.time()
        for caddr in list(clients):
            last_active_time = last_active_map.get(caddr, 0)
            if now - last_active_time > TIMEOUT_SECONDS:
                print(f"Client {caddr} timed out and removed.")
                clients.pop(caddr, None)
                last_active_map.pop(caddr, None)
        time.sleep(5)

# データを解析し、ユーザー名とメッセージに分割する
def parse_data(data):
    username_len = data[0]
    username_bytes = data[1:1 + username_len]
    message_bytes = data[1 + username_len:]

    username = username_bytes.decode('utf-8')
    message = message_bytes.decode('utf-8')

    return username, message

# メッセージをリレーし、必要に応じて新しいクライアントを登録する
def relay_message(address, username, message, sock):
    if address not in clients:
        print("New client joined: {} (username: '{}')".format(address, username))
        clients[address] = username
        last_active_map[address] = time.time()

    add, port = address
    senderkey = f'{add}:{port}'
    recvmsg = f'{senderkey}> {username}:{message}'

    if len(recvmsg.encode('utf-8')) > 4096:
        print("Relay message too long, not sending.")
        return

    print(recvmsg)

    broadcast_message(address, recvmsg, sock)

# サーバがクライアントからのメッセージを受信し、処理する
def recv_data(sock):
    while True:
        data, address = sock.recvfrom(4096)
        username, message = parse_data(data)
        relay_message(address, username, message, sock)

print('Server started and listening for incoming connections...')

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
    sock.bind((SERVER_ADDRESS, SERVER_PORT))
    threading.Thread(target=recv_data, args=(sock,), daemon=True).start()
    threading.Thread(target=remove_inactive_clients, daemon=True).start()

    while True:
        message = input("Enter 'quit' to stop the server: ").strip()
        if message == "quit":
            print("Stopping the server...")
            break

    print("Server socket closed.")
