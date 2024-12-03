from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, join_room, emit
from Player1 import Player1
from Player2 import Player2
import queue

# Bool flag to "remember" when we have both types of players
player_connections = {}
host_rooms = {}
hostQueue = queue.Queue()
playerQueue = queue.Queue()
rooms = {}

# Hangman ASCII Art
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

# Flask and Socket.IO Setup
app = Flask(__name__)
app.config['SECRET_KEY'] = "secret!"
socketio = SocketIO(app)  # No need for async_mode argument here

# Routes
@app.route('/')
def home():
    """Render the home page."""
    return render_template('index.html', message="Hangman App! :P")

# Socket.IO Events
@socketio.on('roleSelection')
def handle_role_selection(data):
    """Handle role selection: host or player."""
    global player_connections, hostQueue, playerQueue

    sid = request.sid
    role = data.get('role')
    player = player_connections.get(sid, f"Player_{sid[:6]}")
    print(f"{player} selected role: {role}")

    if role == 'host':
        handle_host_role(sid)
    elif role == 'player':
        handle_player_role(sid)
    else:
        print(f"Unknown role selected: {role}")

    # Debugging state
    print(f"Current player connections: {player_connections}")
    print(f"Current host rooms: {rooms}")

def handle_host_role(sid):
    """Handle host role selection."""
    hostQueue.put(sid)
    player_connections[sid] = "Host"

        room_name = f"room_{sid}"
        rooms[sid] = room_name


        join_room(room_name)
        print("Host joined, room created:", room_name)

        # Notify the host
        socketio.emit('showWaitingPage', {'message': 'Waiting for player to join'}, room = sid)
        send("Host joined", broadcast=True)

        if(not playerQueue.empty()):
            print('playerQueue recognized as non-empty')
            socketio.emit('showHostPage', room=sid)
            currentPlayer = playerQueue.queue[0]
            print(f'currentPlayer = playerQueue.queue[0] returns: {currentPlayer}')
            hostQueue.get() # Remove host from queue, player has filled their room
            join_room(room_name, sid=currentPlayer)
            print(f"Player {currentPlayer} joined the host's room: {room_name}")
            socketio.emit('showWaitingPage', {'message': "Waiting for host to enter a secret word"}, room=currentPlayer) #THIS REPLACES THE LINE BELOW

def handle_player_role(sid):
    """Handle player role selection."""
    playerQueue.put(sid)
    player_connections[sid] = "Player"

        if(not hostQueue.empty()):
            print('hostQueue recognized as non-empty')
            #ADD PLAYER TO OLDEST HOSTS ROOM
            currentHost = hostQueue.get()
            playerQueue.queue[0] #May need to replace to get()
            join_room(rooms[currentHost])
            print(f"player {sid} joined host's room: {rooms[currentHost]}")
            socketio.emit('showHostPage', room=currentHost)
            socketio.emit('showWaitingPage', {'message': 'Waiting for host to select a secret'}, room=sid)
        else:
            # No host available
            socketio.emit('showWaitingPage', {'message': "Waiting for a host to join"}, room=sid)

    else:
        socketio.emit('showWaitingPage', {'message': "Waiting for a host to join"}, room=sid)

@socketio.on('hostSecretWord')
def secret_word_setup(data):
    """Handle secret word setup by the host."""
    if 'word' in data and isinstance(data['word'], str):
        secret = data['word']
        if secret.isalpha():
            sid = request.sid
            print(f'sid: {sid} (this should match the room name below)')
            room_name = rooms.get(sid)  # Retrieve the host's room name
            print(f'room_name: {room_name} ')
            # Create and store room data if room_name is valid
            if room_name:
                rooms[room_name] = {
                    "secret_word": secret.lower(),  # Store secret word in lowercase for consistent validation
                    "guessed_letters": [],
                    "hangman_stage": 0,
                    "incorrect_letters": [],
                    "game_over": False,  # Initially set game over to False
                    "revealed_word": ["*"] * len(secret)  # Initialize the revealed word with asterisks
                }
                print(f"Secret Word '{secret}' received and validated for room: '{room_name}' ")
                
                  # Check if the word is already "guessed" (if all letters are revealed)
                revealed_word = rooms[room_name]["revealed_word"]
                if '*' not in revealed_word:  # If there are no underscores, the word is already guessed
                    rooms[room_name['game_over']] = True
                    socketio.emit('gameOver', {'message': 'You won! Congratulations!','win': True}, room=room_name)
                    print("The word was already guessed. Game Over!")
             
                # Notify players in the room to start the game
                startGame(secret, room_name)
            else:
                print("Error: Room not found for host.")
        else:
            print("Invalid secret word format. Only alphabetic characters are allowed.")
    else:
        print(f"Unexpected data format received: {data}")

def setup_game(secret):
    """Initialize the game with the secret word."""
    sid = request.sid
    room_name = rooms.get(sid)

    if not room_name:
        print("Error: Room not found for host.")
        return

    rooms[room_name] = {
        "secret_word": secret.lower(),
        "guessed_letters": [],
        "hangman_stage": 0,
        "incorrect_letters": [],
        "game_over": False,
        "revealed_word": ["*"] * len(secret),
    }
    print(f"Secret Word '{secret}' received and validated for room: '{room_name}'")
    start_game(secret, room_name)

@socketio.on('playerGuess')
def handle_player_guess(data):
    """Handle player's guess."""
    room_name = data.get('room')
    guess = data.get('guess', '').lower().strip()

    if not guess.isalpha() or len(guess) != 1:
        socketio.emit('invalidGuess', {'message': 'Please guess one alphabetic letter at a time.'}, room=room_name)
        return

    if room_name and room_name in rooms:
        process_guess(room_name, guess)
    else:
        print(f"Room {room_name} does not exist. Ignoring guess.")

def process_guess(room_name, guess):
    """Process the player's guess."""
    room_data = rooms[room_name]
    secret_word = room_data['secret_word']
    guessed_letters = set(room_data['guessed_letters'])
    hangman_stage = room_data['hangman_stage']
    incorrect_letters = set(room_data['incorrect_letters'])

    if guess in guessed_letters or guess in incorrect_letters:
        socketio.emit('repeatedGuess', {'message': f"You've already guessed '{guess}'."}, room=room_name)
    elif guess in secret_word:
        handle_correct_guess(room_name, room_data, guess)
    else:
        handle_incorrect_guess(room_name, room_data, guess)

def handle_correct_guess(room_name, room_data, guess):
    """Handle a correct guess."""
    guessed_letters = set(room_data['guessed_letters'])
    guessed_letters.add(guess)
    room_data['guessed_letters'] = list(guessed_letters)

    revealed_word = [
        letter if letter in guessed_letters else '*' for letter in room_data['secret_word']
    ]
    room_data['revealed_word'] = revealed_word

    socketio.emit('correctGuess', {
        'revealed_word': ''.join(revealed_word),
        'letter': guess,
        'guessedLetters': room_data['guessed_letters']
    }, room=room_name)

            # Check if the word is fully guessed
            if '*' not in revealed_word:
                room_data['game_over'] = True
                socketio.emit('gameOver', {'message': 'Congratulations! You guessed the word! - ' + secret_word, 'win':True}, room=room_name)
                rooms[room_name] = {
                    "secret_word": "",  # Store secret word in lowercase for consistent validation
                    "guessed_letters": [],
                    "hangman_stage": 0,
                    "incorrect_letters": [],
                    "game_over": False,  # Initially set game over to False
                    "revealed_word": ["*"]  # Initialize the revealed word with asterisks
                }

        else:
            # Incorrect guess
            print("player made an incorrect guess, adding to list")
            hangman_stage += 1
            room_data['hangman_stage'] = hangman_stage
            incorrect_letters.add(guess)
            room_data['incorrect_letters'] = list(incorrect_letters)
             # Check if max incorrect guesses reached
            if len(hangman_stages) - hangman_stage - 1 == 0:
                i = len(hangman_stages) - hangman_stage -1
                print(f"len(hangman_stages) - hangman_stage -1 results in {i}")
                print(f"secret word is {secret_word}")
                room_data['game_over'] = True
                socketio.emit('gameOver', {
                    'message': "Game Over! You ran out of guesses. The correct word was "+ secret_word, 'win': False
                }, room=room_name)
                rooms[room_name] = {
                    "secret_word": "",  # Store secret word in lowercase for consistent validation
                    "guessed_letters": [],
                    "hangman_stage": 0,
                    "incorrect_letters": [],
                    "game_over": False,  # Initially set game over to False
                    "revealed_word": ["*"]  # Initialize the revealed word with asterisks
                }

            # Notify players of incorrect guess and hangman stage
            else:
                socketio.emit('incorrectGuess', {
                    'incorrect_letters': room_data['incorrect_letters'],
                    'letter': guess,
                    'remaining_attempts': len(hangman_stages) - hangman_stage - 1,
                    'stage': hangman_stage
                }, room=room_name)
                
           
    else:
        print(f"Room {room_name} does not exist. Ignoring guess.")

@socketio.on('leave_room')
def on_leave(data):
    print(f'attempting to have user leave room {data['room']}')
    leave_room(data['room'])


def startGame (secretWord, room_name):
    
    print(f"starting game in room {room_name}")
    # Ensure room_name exists
    if room_name not in rooms:
        print(f"Error: Room {room_name} does not exist.")
        return

    print("pre currentPlayer establish")
    currentPlayer = playerQueue.get()
    print(f"attempting to show player page with {currentPlayer}")
    socketio.emit('showPlayerPage', {'room': room_name}, room=currentPlayer)
   
    room_data = rooms[room_name]
    gameData = {
        'room' : room_name,
        'secretWord': secretWord,
        'incorrectGuesses': 0,  # Initial count
        'lettersGuessed': []    # Initial empty list
    }
    if room_data['game_over'] == True:
        print("THIS GAME HAS ALREADY BEEN FINISHED")
    else:
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
    socketio.run(app, host='0.0.0.0', port=5000)
