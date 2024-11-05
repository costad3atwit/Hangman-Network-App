from flask import Flask
from flask import render_template
from flask import request 
#pip install flask-socketio
#to install line 6 copy the above command into the terminal
from flask_socketio import SocketIO, send
from Player1 import Player1
from Player2 import Player2

# Bool flag to "remember" when we have both types of players
hasHost = False
hasPlayer = False
secretWord = ""

# Create a Flask app instance
app = Flask(__name__)
app.config['SECRET_KEY'] = "secret!"

socketio = SocketIO(app)
# Define a route for the root URL ('/')

player_connections = {}

@app.route('/')
def hello_world():
    message = "Hangman App! :P"
    
    return render_template('index.html',  
                           message=message) 

@socketio.on('connect')
def handle_connect():
    global player_connections
    sid = request.sid

    if len(player_connections) ==0:
        player_connections[sid] = "Player 1"
        print("Player 1 joined")
        send("Player 1 joined", broadcast=True)
        player1=Player1()
    elif len(player_connections) ==1:
        player_connections[sid] = "Player 2"
        print("Player 2 joined")
        send("Player 2 joined", broadcast=True)
        player2=Player2()
        
        
#The below code block is a listener from the client
#to await a role selection. There are two buttons
#shown in index.html which send this information to the server.
@socketio.on('roleSelection')
def handle_role_selection(data):
    global hasHost,hasPlayer
    role = data['role']
    player = player_connections[request.sid]
    print(f'{player} selected role: {role}')

    # Handle role logic here
    if role == 'host':
        hasHost = True
        socketio.emit('showHostPage', room=request.sid)
    elif role == 'player':
        hasPlayer = True
        socketio.emit('showWaitingPage', room=request.sid)
        

@socketio.on('hostSecretWord')
def secretWordSetup(data):
    if 'word' in data and isinstance(data['word'], str):
        secret = data['word']
        
        if secret.isalpha():
            print("Secret Word received and validated:" + secret)
            if hasPlayer:
                print("Starting game with secret word" + secret)
                startGame(secret)
        else:
            print("Invalid secret word format, only alphabetic characters allowed.")
    else:
        print(f"Unexpected data format received: {data}")

def startGame (secretWord):
    socketio.emit('startGame', {'secretWord': secretWord})

# Run the app when this file is executed
if __name__ == '__main__':
    socketio.run(app)