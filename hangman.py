from flask import Flask
from flask import render_template
from flask import request 
#pip install flask-socketio
#to install line 6 copy the above command into the terminal
from flask_socketio import SocketIO, send, join_room, emit
from Player1 import Player1
from Player2 import Player2

# Bool flag to "remember" when we have both types of players
player_connections = {}
host_rooms = {}
hasHost = False
hasPlayer = False
secretWord = ""
rooms = {}

# Hangman ASCII art
hangman_stages = [
    r"""
   -----
   |   |
       |
       |
       |
       |
=========
    """,
    r"""
   -----
   |   |
   O   |
       |
       |
       |
=========
    """,
    r"""
   -----
   |   |
   O   |
   |   |
       |
       |
=========
    """,
    r"""
   -----
   |   |
   O   |
  /|   |
       |
       |
=========
    """,
    r"""
   -----
   |   |
   O   |
  /|\  |
       |
       |
=========
    """,
    r"""
   -----
   |   |
   O   |
  /|\  |
  /    |
       |
=========
    """,
    r"""
   -----
   |   |
   O   |
  /|\  |
  / \  |
       |
=========
    """
]

# Create a Flask app instance
app = Flask(__name__)
app.config['SECRET_KEY'] = "secret!"

socketio = SocketIO(app)
# Define a route for the root URL ('/')

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
        player_connections[sid] = "Host"
        room_name = f"room_{sid}"  # Create a unique room for the host
        host_rooms[sid] = room_name
        join_room(room_name)
        print("Host joined, room created:", room_name)
        send("Host joined", broadcast=True)
    elif len(player_connections) ==1:
        player_connections[sid] = "Player"
        # Find the first host's room
        host_sid = next(iter(player_connections))  # Get the first host's SID
        room_name = host_rooms[host_sid]  # Get the host's room name
        join_room(room_name)
        print("Player joined host's room:", room_name)
        send("Player joined the room", room=room_name)
    else:
        print("Connection limit reached.")
        send("Connection limit reached.", room=sid)

@socketio.on('roleSelection')
def handle_role_selection(data):
    global player_connections
    global hasHost, hasPlayer
    sid = request.sid
    role = data['role']
    player = player_connections[sid]
    print(f'{player} selected role: {role}')

    # Handle role logic here
    if role == 'host':
        hasHost = True
        socketio.emit('showHostPage', room=request.sid)
        #If has a player already, add them to the room and update their screen

        player_connections[sid] = "Host"
        room_name = f"room_{sid}"  # Create a unique room for the host
        host_rooms[sid] = room_name
        join_room(room_name)
        print("Host joined, room created:", room_name)
        send("Host joined", broadcast=True)

        if player_connections:
            #connect player to oldest open room
            print("Connect player to oldest open room")     
    elif role == 'player':
        hasPlayer = True
        if hasHost:
            data = {'message': "Waiting for the host to pick the secret word"}
            socketio.emit('showWaitingPage',data, room=request.sid)
        else:
            data = {'message': "Waiting for a host to join"}
            socketio.emit('showWaitingPage',data, room=request.sid)
        

@socketio.on('hostSecretWord')
def secretWordSetup(data):
    if 'word' in data and isinstance(data['word'], str):
        secret = data['word']
        
        if secret.isalpha():
            sid = request.sid
            room_name = host_rooms.get(sid)  # Retrieve the host's room name
            
            # Create and store room data if room_name is valid
            if room_name:
                rooms[room_name] = {
                    "secret_word": secret.lower(),  # Store secret word in lowercase for consistent validation
                    "guessed_letters": [],
                    "incorrect_guesses": 0,
                    "game_over": False,  # Initially set game over to False
                    "revealed_word": ["_"] * len(secret)  # Initialize the revealed word with underscores
                }
                print(f"Secret Word '{secret}' received and validated for room:", room_name)
                
                  # Check if the word is already "guessed" (if all letters are revealed)
                revealed_word = rooms[room_name]["revealed_word"]
                if '_' not in revealed_word:  # If there are no underscores, the word is already guessed
                    rooms[room_name]['game_over'] = True
                    socketio.emit('gameOver', {'message': 'You won! Congratulations!'}, room=room_name)
                    print("The word was already guessed. Game Over!")
             
                # Notify players in the room to start the game
                startGame(secret, room_name)
            else:
                print("Error: Room not found for host.")
        else:
            print("Invalid secret word format, only alphabetic characters allowed.")

    else:
        print(f"Unexpected data format received: {data}")

@socketio.on('playerGuess')
def handle_player_guess(data):
    
    room_name = data['room']
    guess = data['guess']

    if room_name in rooms:
        room_data = rooms[room_name]
        secret_word = room_data['secret_word']
        guessed_letters = room_data.get('guessed_letters', set())
        incorrect_guesses = room_data.get('incorrect_guesses', 0)
        
        if guess in secret_word and guess not in guessed_letters:
            # Correct guess: add the letter to guessed letters
            guessed_letters.add(guess)
            room_data['guessed_letters'] = guessed_letters  # Update room data
            
            # Broadcast the correct guess
            socketio.emit('correctGuess', {'letter': guess}, room=room_name)
        else:
            # Incorrect guess: increment the count and update the room data
            room_data['incorrect_guesses'] = incorrect_guesses + 1
            socketio.emit('incorrectGuess', {'letter': guess}, room=room_name)
        
        # Send updated game status to both host and player
        socketio.emit('updateGameStatus', {
            'guessed_letters': list(guessed_letters),
            'incorrect_guesses': room_data['incorrect_guesses']
        }, room=room_name)

    

    else:
        print(f"Room {room_name} does not exist. Ignoring guess.")



def startGame (secretWord, room_name):
    host_sid = next(iter(player_connections))  # Get the first host's SID
    room_name = host_rooms[host_sid]  # Get the host's room name
    gameData = {
        'secretWord': secretWord,
        'incorrectGuesses': 0,  # Initial count
        'lettersGuessed': []    # Initial empty list
    }
    socketio.emit('startGame', gameData, room=room_name)

# Run the app when this file is executed
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0',port=5000)