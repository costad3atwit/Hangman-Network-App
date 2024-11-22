from flask import Flask
from flask import render_template
from flask import request 
#pip install flask-socketio
#to install line 6 copy the above command into the terminal
from flask_socketio import SocketIO, send, join_room, emit
from Player1 import Player1
from Player2 import Player2
import queue


# Bool flag to "remember" when we have both types of players
player_connections = {}
host_rooms = {}
hostQueue = queue.Queue()
playerQueue = queue.Queue()
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

@socketio.on('roleSelection')
def handle_role_selection(data):
    global player_connections, hostQueue, playerQueue
    sid = request.sid  # Current session ID
    role = data['role']  # Role selected by the client
    player = player_connections.get(sid, f"Player_{sid[:6]}")  # Default player name if not set
    print(f'{player} selected role: {role}')

    if role == 'host':
        hostQueue.put(sid)
        player_connections[sid] = "Host"

        room_name = f"room_{sid}"
        rooms[sid] = room_name


        join_room(room_name)
        print("Host joined, room created:", room_name)

        # Notify the host
        socketio.emit('showHostPage', room=sid)
        send("Host joined", broadcast=True)

        if(not playerQueue.empty()):
            currentPlayer = playerQueue.get()
            join_room(room_name, sid=currentPlayer)
            print(f"Player {currentPlayer} joined the host's room: {room_name}")
            socketio.emit('showPlayerPage', {'room': room_name}, room=currentPlayer)

    elif role == 'player':
        playerQueue.put(sid)
        player_connections[sid] = "Player"

        if(not hostQueue.empty()):
            #ADD PLAYER TO OLDEST HOSTS ROOM
            currentHost = hostQueue.get()
            join_room(rooms[currentHost])
            print(f"player {sid} joined host's room: {rooms[currentHost]}")
            socketio.emit('showHostPage', room=currentHost)
            socketio.emit('showPlayerPage', room=sid)
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
        hangman_stage = room_data['hangman_stage']
        incorrect_letters = set(room_data['incorrect_letters'])

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
                letter if letter in guessed_letters else '*' for letter in secret_word
            ]
            room_data['revealed_word'] = revealed_word

            # Broadcast the updated revealed word
            print(f"emitting correctGuess to client with following info: \n Revealed Word: {revealed_word} \n Letter Guessed: {guess} \n Guessed Letters: {', '.join(room_data['guessed_letters'])}")
            socketio.emit('correctGuess', {'revealed_word': ''.join(revealed_word), 'letter': guess, 'guessedLetters': room_data['guessed_letters']}, room=room_name)

            # Check if the word is fully guessed
            if '*' not in revealed_word:
                room_data['game_over'] = True
                socketio.emit('gameOver', {'message': 'Congratulations! You guessed the word!' + secret_word, 'win':True}, room=room_name)
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



def startGame (secretWord, room_name):
    host_sid = next(iter(player_connections))  # Get the first host's SID
    room_name = rooms[host_sid]  # Get the host's room name
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
    socketio.run(app, host='0.0.0.0',port=5000)