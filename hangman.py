from flask import Flask
from flask import render_template 

# Create a Flask app instance
app = Flask(__name__)

# Define a route for the root URL ('/')
@app.route('/')
def hello_world():
    message = "Hangman App! :P"
    
    return render_template('index.html',  
                           message=message) 

# Run the app when this file is executed
if __name__ == '__main__':
    app.run(threaded=True, debug=True)