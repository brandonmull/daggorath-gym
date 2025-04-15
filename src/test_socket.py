import socket
import json

def start_server():
    # Server setup
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('localhost', 8000))
    server_socket.listen(5)  # Allow up to 5 pending connections
    print('Server listening on localhost:8000')
    
    try:
        while True:  # Continuous operation
            client_socket, addr = server_socket.accept()
            print(f'Connection from {addr}')
            
            try:
                # Receive data from the client
                data = client_socket.recv(1024)
                if not data:
                    break
                    
                data_dict = json.loads(data.decode())
                print(f'Received: {data_dict}')
                
                # Send response
                response_dict = {'message': 'Hello, client!'}
                response_data = json.dumps(response_dict).encode()
                client_socket.sendall(response_data)
                
            finally:
                client_socket.close()
                
    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        server_socket.close()

def start_client():
    # Client setup
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(('localhost', 8000))
    
    try:
        # Send data to the server
        data_dict = {'name': 'LabEx', 'message': 'Hello, server!'}
        data = json.dumps(data_dict).encode()
        client_socket.sendall(data)
        
        # Receive response
        response_data = client_socket.recv(1024)
        response_dict = json.loads(response_data.decode())
        print(f'Received: {response_dict}')
        
    finally:
        client_socket.close()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) != 2 or sys.argv[1] not in ['server', 'client']:
        print("Usage: python script_name.py <server|client>")
        sys.exit(1)
    
    if sys.argv[1] == 'server':
        start_server()
    else:
        start_client()