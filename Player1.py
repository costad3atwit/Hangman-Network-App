import socketio

# Connect to the server
sio = socketio.Client()

class Player1:
    def __init__(self):
        self=self

@sio.event
def connect():
    print("Connected to a game")

@sio.event
def disconnect():
    print("Disconnected from game")

@sio.event
def message(data):
    print(f"Message from server: {data}")

if __name__ == '__main__':
    sio.connect('http://127.0.0.1:5000')
    sio.wait()
