from medjobhub import app,Message,Mail,request,check_password_hash,random,session,jsonify,db,secrets,cross_origin,allowed_url
from medjobhub.models import User


otp_storage = {} 
mail=Mail(app)

#Email for Otp
def send_email(recipient_email, otp, username):
    with app.app_context():
        msg = Message(
            'Your OTP for MedJobHub',
            sender="MedJobHub <medjobhub>",
            recipients=[recipient_email]
        )
        msg.body = f"""
Hello {username},
Thank you for using our services. Your One-Time Password (OTP) is: {otp}
This OTP is valid for 10 minutes. Please do not share this code.
Best regards, MedJobHub Team
"""
        try:
            mail.send(msg)
            print("Email sent successfully!")
            return True
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
        


#SignIn
@app.route('/signin', methods=['POST'])
@cross_origin(origin=allowed_url, supports_credentials=True)
def signin():
    session.clear()  
    data = request.json  
    username = data.get('username')
    password = data.get('password')

    user = User.query.filter_by(username=username).first()

    if user:
        if check_password_hash(user.password, password):
            if not user.is_verified:
                otp = random.randint(100000, 999999)
                session[f"otp_{username}"] = otp
                print(f"Generated OTP for {username}: {otp}")  
                print("sessions",session.items())

                if send_email(user.email, otp, username):
                    return jsonify({
                        "success": True,
                        "message": "OTP sent to your email.",
                        "username": username,
                        "otp_required": True,
                        "resume":user.resume
                    })
                else:
                    return jsonify({"success": False, "message": "Error sending OTP. Try again later."})
            else:
                session["user_id"] = user.id
                session["role"] = user.role
                session.permanent = True 

                auth_token = secrets.token_hex(16) 
                user.auth_token = auth_token 
                user.is_verified = True 
                db.session.commit()

                return jsonify({
                    "success": True,
                    "message": "Login successful.",
                    "user": {
                        "id": user.id, 
                        "username": user.username, 
                        "role": user.role, 
                        "auth_token": auth_token
                    },
                    "otp_required": False,
                    "resume":user.resume
                })
        else:
            return jsonify({"success": False, "message": "Incorrect password."})
    else:
        return jsonify({"success": False, "message": "Username not found."})


#Get LoggedIn userId
@app.route('/get_session', methods=['GET'])
def get_session():
    if 'user_id' in session:
        return jsonify({
            "success": True,
            "user": {
                "id": session.get('user_id'),
                "role": session.get('role')
            }
        }), 200
    return jsonify({"success": False, "message": "No active session"})


#Verify_User_Token
@app.route('/verify-token', methods=['POST'])
@cross_origin(origin=allowed_url, supports_credentials=True)
def verify_token():
    try:
        data = request.json
        auth_token = data.get("auth_token")

        if not auth_token:
            return jsonify({"success": False, "message": "Token is required."}), 400

        user = User.query.filter_by(auth_token=auth_token).first()

        if not user:
            return jsonify({"success": False, "message": "Invalid or expired token."}), 401

        session["user_id"] = user.id
        session["role"] = user.role
        session.permanent = True  

        return jsonify({
            "success": True,
            "message": "Token verified successfully.",
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "auth_token": user.auth_token,
                "resume":user.resume
            }
        }), 200

    except Exception as e:
        return jsonify({"success": False, "message": f"Token verification failed: {str(e)}"}), 500
