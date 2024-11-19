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

    # if len(player_connections) ==0:
    #     player_connections[sid] = "Host"
    #     room_name = f"room_{sid}"  # Create a unique room for the host
    #     host_rooms[sid] = room_name
    #     join_room(room_name)
    #     print("Host joined, room created:", room_name)
    #     send("Host joined", broadcast=True)
    # elif len(player_connections) ==1:
    #     player_connections[sid] = "Player"
    #     # Find the first host's room
    #     host_sid = next(iter(player_connections))  # Get the first host's SID
    #     room_name = host_rooms[host_sid]  # Get the host's room name
    #     join_room(room_name)
    #     print("Player joined host's room:", room_name)
    #     send("Player joined the room", room=room_name)
    # else:
    #     print("Connection limit reached.")
    #     send("Connection limit reached.", room=sid)

@socketio.on('roleSelection')
def handle_role_selection(data):
    global player_connections, hasHost, hasPlayer
    sid = request.sid  # Current session ID
    role = data['role']  # Role selected by the client
    player = player_connections.get(sid, f"Player_{sid[:6]}")  # Default player name if not set
    print(f'{player} selected role: {role}')

    if role == 'host':
        # Mark host as present
        hasHost = True
        player_connections[sid] = "Host"

        # Create a unique room for the host


        #HERE MAYBE??
        room_name = f"room_{sid}"
        rooms[sid] = room_name


        join_room(room_name)
        print("Host joined, room created:", room_name)

        # Notify the host
        socketio.emit('showHostPage', room=sid)
        send("Host joined", broadcast=True)

        # Connect an existing player (if any) to this new room
        for player_sid, player_role in player_connections.items():
            if player_role == "Player" and player_sid not in rooms.values():
                # Assign the player to the current host's room
                player_connections[player_sid] = room_name
                join_room(room_name, sid=player_sid)
                socketio.emit('showPlayerPage', {'room': room_name}, room=player_sid)
                print(f"Player joined host's room: {room_name}")
                break

    elif role == 'player':
        # Mark player as present
        hasPlayer = True
        player_connections[sid] = "Player"

        if hasHost:
            # Attempt to connect the player to the oldest available room
            for host_sid, room_name in rooms.items():
                if not any(player == room_name for player in player_connections.values()):  # Check for unoccupied room
                    player_connections[sid] = room_name
                    join_room(room_name, sid=sid)
                    socketio.emit('showPlayerPage', {'room': room_name}, room=sid)
                    print(f"Player joined host's room: {room_name}")
                    return  

            # If no available room, show waiting page
            data = {'message': "Waiting for a host to pick the secret word"}
            socketio.emit('showWaitingPage', data, room=sid)
        else:
            # No host available
            data = {'message': "Waiting for a host to join"}
            socketio.emit('showWaitingPage', data, room=sid)

    else:
        print(f"Unknown role selected: {role}")

    # Debugging state
    print(f"Current player connections: {player_connections}")
    print(f"Current host rooms: {rooms}")        

@socketio.on('hostSecretWord')
def secretWordSetup(data):
    if 'word' in data and isinstance(data['word'], str):
        secret = data['word']
        
        if secret.isalpha():
            sid = request.sid
            room_name = rooms.get(sid)  # Retrieve the host's room name
            
            # Create and store room data if room_name is valid
            if room_name:
                rooms[room_name] = {
                    "secret_word": secret.lower(),  # Store secret word in lowercase for consistent validation
                    "guessed_letters": [],
                    "incorrect_guesses": 0,
                    "game_over": False,  # Initially set game over to False
                    "revealed_word": ["_"] * len(secret)  # Initialize the revealed word with underscores
                }
                print(f"Secret Word '{secret}' received and validated for room: '{room_name}' ")
                
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

    room_name = data.get('room')
    print(f"Room name = data.get('room') assigns: {room_name}")
    guess = data.get('guess', '').lower().strip()  # Sanitize input
    
    if not guess.isalpha() or len(guess) != 1:
        # Invalid guess: send error message
        socketio.emit('invalidGuess', {'message': 'Please guess one alphabetic letter at a time.'}, room=room_name)
        return


    # HERE PLEASEEEE
    if room_name:
        print(f"room_name valid: {room_name}, checking guess against secret word")
        room_data = rooms[room_name]
        secret_word = room_data['secret_word']
        guessed_letters = set(room_data['guessed_letters'])
        incorrect_guesses = room_data['incorrect_guesses']

        if guess in guessed_letters:
            # Repeated guess: notify the player
            socketio.emit('repeatedGuess', {'message': f"You've already guessed '{guess}'."}, room=room_name)
        elif guess in secret_word:
            # Correct guess
            print("player made a correct guess, adding to list")
            guessed_letters.add(guess)
            room_data['guessed_letters'] = list(guessed_letters)

            # Update revealed word
            revealed_word = [
                letter if letter in guessed_letters else '_' for letter in secret_word
            ]
            room_data['revealed_word'] = revealed_word

            # Broadcast the updated revealed word
            print(f"emitting correctGuess to client with following info: \n Revealed Word: {revealed_word} \n Letter Guessed: {guess} \n Guessed Letters: {', '.join(room_data['guessed_letters'])}")
            socketio.emit('correctGuess', {'revealed_word': ''.join(revealed_word), 'letter': guess, 'guessedLetters': room_data['guessed_letters']}, room=room_name)

            # Check if the word is fully guessed
            if '_' not in revealed_word:
                room_data['game_over'] = True
                socketio.emit('gameOver', {'message': 'Congratulations! You guessed the word!'}, room=room_name)
        else:
            # Incorrect guess
            incorrect_guesses += 1
            room_data['incorrect_guesses'] = incorrect_guesses

            # Notify players of incorrect guess and hangman stage
            socketio.emit('incorrectGuess', {
                'letter': guess,
                'remaining_attempts': len(hangman_stages) - incorrect_guesses - 1,
                'hangman_stage': hangman_stages[incorrect_guesses]
            }, room=room_name)

            # Check if max incorrect guesses reached
            if incorrect_guesses == len(hangman_stages) - 1:
                room_data['game_over'] = True
                socketio.emit('gameOver', {
                    'message': f"Game over! The word was '{secret_word}'."
                }, room=room_name)
    else:
        print(f"Room {room_name} does not exist. Ignoring guess.")



def startGame (secretWord, room_name):
    host_sid = next(iter(player_connections))  # Get the first host's SID
    room_name = rooms[host_sid]  # Get the host's room name
    gameData = {
        'room' : room_name,
        'secretWord': secretWord,
        'incorrectGuesses': 0,  # Initial count
        'lettersGuessed': []    # Initial empty list
    }
    print('Starting game in room: ' + gameData['room'])
    socketio.emit('startGame', gameData, room=room_name)

  

def check_win_condition(room_name, secret_word, guessed_letters):
    # Check if all letters of the secret word have been guessed
    if all(letter in guessed_letters for letter in secret_word):
        # If all letters are guessed, it's a win
        rooms[room_name]['game_over'] = True  # Mark the game as over
        socketio.emit('gameWon', {'message': 'You won! Congratulations!'}, room=room_name)
        print(f"Game Over! {room_name} has won the game!")

# Run the app when this file is executed
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0',port=5000)