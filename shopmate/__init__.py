from flask import Flask, request, jsonify
from werkzeug.security import check_password_hash,generate_password_hash
from flask import request, jsonify
import random
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS,cross_origin
import os
from flask import session
from config import Config
from flask_login import LoginManager,login_required
from flask_session import Session
import secrets
from flask_mail import Mail, Message


load_dotenv()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy()

db.init_app(app)
allowed_url="https://virtual-assistant-frontend-3sbii3l0f.vercel.app"
CORS(app,
     origins=["http://localhost:5173", "http://127.0.0.1:5173",allowed_url],
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"])




app.config.from_object(Config) 



login_manager=LoginManager(app)
login_manager.login_view='signin'
login_manager.login_message_category='sucess'
otp_storage = {}

upload_folder = os.path.join(os.getcwd(), 'uploads')
if not os.path.exists(upload_folder):
    os.makedirs(upload_folder)

app.config['SESSION_TYPE'] = 'filesystem'
app.config['SESSION_COOKIE_SAMESITE'] = 'None'
app.config['SESSION_COOKIE_SECURE'] = True 
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_USE_SIGNER'] = True
app.config['SECRET_KEY'] = os.getenv("SECRET_KEY", "supersecret")

Session(app)



app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
app.config['UPLOAD_FOLDER'] = upload_folder  
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx', 'jpg', 'png'}

# Flask-Mail Configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_ID')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_APP_PASSWORD')
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True

from shopmate.models import User,Conversation,Message,userpreference,reminder
from shopmate.routes import signin,signup,verifyotp,conversation,message,recommend,analyze_reviews,forgot_password,get_price,price_history
from shopmate.utils import reminder_worker