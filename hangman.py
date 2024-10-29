from flask import Flask
from flask import render_template
from flask import request 
#pip install flask-socketio
#to install line 5 copy the above command into the terminal
from flask_socketio import SocketIO, send

# Create a Flask app instance
app = Flask(__name__)
app.config['SECRET_WORD'] = "secret!"

socketio = SocketIO(app)
# Define a route for the root URL ('/')

player_count=0

@app.route('/')
def hello_world():
    message = "Hangman App! :P"
    
    return render_template('index.html',  
                           message=message) 

@socketio.on('connect')
def handle_connect():
    global player_count
    player_count += 1

    if player_count == 1:
        print("Player 1 joined")
        send("Player 1 joined", broadcast=True)
    elif player_count == 2:
        print("Player 2 joined")
        send("Player 2 joined", broadcast=True)
        
#The below code block is a listener from the client
#to await a role selection. There are two buttons
#shown in index.html which send this information to the server.
@socketio.on('roleSelection')
def handle_role_selection(data):
    role = data['role']
    print(f'User selected role: {role}')

    # Handle role logic here
    if role == 'host':
        socketio.emit('showHostPage', room=request.sid)
    elif role == 'player':
        socketio.emit('showPlayerPage', room=request.sid)

@socketio.on('hostSecretWord')
def secretWordSetup(data):
    if 'word' in data and isinstance(data['word'], str):
        secret = data['word']
        #SECRET WORD RECEPTION VERIFICATION HERE
        #VAR secret UNUSED OTHERWISE. NEEDS TO BE STORED FOR PROCESSING
        #ALSO NEEDS TO BE CHECKED FOR ONLY a-z CHARACTERS
        print("Secret word reached server as: " + secret)
    else:
        print(f"Unexpected data format received: {data}")
# Run the app when this file is executed
if __name__ == '__main__':
    socketio.run(app)