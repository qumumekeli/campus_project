# config.py
import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'campus-recommend-secret-key-2024')
    SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(BASE_DIR, 'campus.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JSON_AS_ASCII = False