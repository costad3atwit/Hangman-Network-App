from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, join_room, emit
from Player1 import Player1
from Player2 import Player2
import queue

# Global Variables
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
    socketio.emit('showHostPage', room=sid)
    send("Host joined", broadcast=True)

    if not playerQueue.empty():
        currentPlayer = playerQueue.get()
        join_room(room_name, sid=currentPlayer)
        print(f"Player {currentPlayer} joined the host's room: {room_name}")
        socketio.emit('showPlayerPage', {'room': room_name}, room=currentPlayer)

def handle_player_role(sid):
    """Handle player role selection."""
    playerQueue.put(sid)
    player_connections[sid] = "Player"

    if not hostQueue.empty():
        currentHost = hostQueue.get()
        join_room(rooms[currentHost])
        print(f"Player {sid} joined host's room: {rooms[currentHost]}")
        socketio.emit('showHostPage', room=currentHost)
        socketio.emit('showPlayerPage', room=sid)
    else:
        socketio.emit('showWaitingPage', {'message': "Waiting for a host to join"}, room=sid)

@socketio.on('hostSecretWord')
def secret_word_setup(data):
    """Handle secret word setup by the host."""
    if 'word' in data and isinstance(data['word'], str):
        secret = data['word']
        if secret.isalpha():
            setup_game(secret)
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

    if '*' not in revealed_word:
        room_data['game_over'] = True
        socketio.emit('gameOver', {
            'message': f"Congratulations! You guessed the word: {room_data['secret_word']}",
            'win': True
        }, room=room_name)

def handle_incorrect_guess(room_name, room_data, guess):
    """Handle an incorrect guess."""
    hangman_stage = room_data['hangman_stage']
    incorrect_letters = set(room_data['incorrect_letters'])
    incorrect_letters.add(guess)
    room_data['incorrect_letters'] = list(incorrect_letters)

    room_data['hangman_stage'] += 1

    socketio.emit('incorrectGuess', {
        'incorrect_letters': room_data['incorrect_letters'],
        'letter': guess,
        'remaining_attempts': len(hangman_stages) - room_data['hangman_stage'],
        'stage': room_data['hangman_stage']
    }, room=room_name)

    if room_data['hangman_stage'] == len(hangman_stages):
        room_data['game_over'] = True
        socketio.emit('gameOver', {
            'message': f"Game Over! The correct word was {room_data['secret_word']}",
            'win': False
        }, room=room_name)

def start_game(secret_word, room_name):
    """Start the game."""
    print(f"Starting game in room: {room_name}")
    game_data = {
        'room': room_name,
        'secretWord': secret_word,
        'incorrectGuesses': 0,
        'lettersGuessed': []
    }
    socketio.emit('startGame', game_data, room=room_name)

# Run the app
if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
