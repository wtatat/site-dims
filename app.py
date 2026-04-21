from flask import Flask, render_template

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/reg')
def register():
    return render_template('register.html')

app.run(port=8080)