# app.py
from flask import Flask
from config import Config
from models import db

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    db.init_app(app)
    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True)