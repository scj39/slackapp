import os

from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()


class Config:
    CLIENT_ID = os.getenv("CLIENT_ID")
    CLIENT_SECRET = os.getenv("CLIENT_SECRET")
    OAUTH_REDIRECT_URI = os.getenv(
        "OAUTH_REDIRECT_URI", "http://localhost:5000/oauth/callback"
    )
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY")
    SQLALCHEMY_DATABASE_URI = os.getenv("SQLALCHEMY_DATABASE_URI")
    ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY", Fernet.generate_key())
