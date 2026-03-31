import os
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'default_secret_key')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'default_jwt_secret_key')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Cloudinary Configuration
import os
from dotenv import load_dotenv
load_dotenv()


class Config:
    MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/virtualshop")
    SECRET_KEY = os.getenv("SECRET_KEY", "supersecret")
    JWT_SECRET = os.getenv("JWT_SECRET", "jwtsecret")
    SERPAPI_KEY = os.getenv("SERPAPI_KEY", "")
    OPENAI_KEY = os.getenv("OPENAI_KEY", "")
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
