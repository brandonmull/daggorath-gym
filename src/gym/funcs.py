import socket

def open_socket():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('127.0.0.1', 8080))
    server_socket.listen(1)
    return server_socket

def close_socket(server_socket):
    server_socket.close()

def send_message(server_socket, message):
    server_socket.sendall(message.encode())