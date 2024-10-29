import socket
import threading

player_count = 0

def handle_client(client_socket, client_address):
    global player_count
    player_count += 1
    player_id = player_count
    
    if player_id == 1:
        print("Player 1 joined.")
    elif player_id == 2:
        print("Player 2 joined.")
    
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if not message:
                break
            print(f"Received from {client_address}: {message}")
        except:
            break
    client_socket.close()
    print(f"Connection from {client_address} has been closed.")

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind(("0.0.0.0", 9999))
    server.listen(2)
    print("Game started, waiting for players.")

    while True:
        client_socket, client_address = server.accept()
        client_handler = threading.Thread(target=handle_client, args=(client_socket, client_address))
        client_handler.start()

if __name__ == "__main__":
    start_server()
