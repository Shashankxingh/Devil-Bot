from flask import Flask

app = Flask(__name__)

@app.route('/')
def index():
    return "Userbot is alive!"

def run():
    app.run(host='0.0.0.0', port=10000)
