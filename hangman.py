from flask import Flask
from flask import render_template
from flask import request 
#pip install flask-socketio
#to install line 5 copy the above command into the terminal
from flask_socketio import SocketIO

# Create a Flask app instance
app = Flask(__name__)

app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)
# Define a route for the root URL ('/')

@app.route('/')
def hello_world():
    message = "Hangman App! :P"
    
    return render_template('index.html',  
                           message=message) 

#The below code block is a listener from the client
#to await a role selection. There are two buttons
#shown in index.html which send this information to the server.
@socketio.on('role selection')
def handle_role_selection(data):
    role = data['role']
    print(f'User selected role: {role}')

    # Handle role logic here
    if role == 'host':
        #below not executing even though role should be established correctly
        print(f'Role is host, emitting showHostPage to ' + request.sid)
        socketio.emit('showHostPage', room=request.sid)
    elif role == 'player':
        socketio.emit('show player page', room=request.sid)


# Run the app when this file is executed
if __name__ == '__main__':
    socketio.run(app)