from flask import Flask

# Create a Flask app instance
app = Flask(__name__)

# Define a route for the root URL ('/')
@app.route('/')
def hello_world():
    return '<h1>Hello, World!<h1>'

# Run the app when this file is executed
if __name__ == '__main__':
    app.run(debug=True)