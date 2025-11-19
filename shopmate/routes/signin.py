
from shopmate import app,db,User,check_password_hash,jsonify,request,random,datetime,timedelta,Mail
from flask_mail import Message as MailMessage

mail = Mail(app)

@app.route('/signin', methods=['POST'])
def signin():
    data = request.get_json()

    # Validate input
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({'error': 'Email and password are required'}), 400

    # Find the user by email
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'Invalid email or password'}), 401

    # Check the password
    if not check_password_hash(user.password, password):
        return jsonify({'error': 'Invalid email or password'}), 401


    # # Optionally, you could check if user.is_verified here
    if not user.is_verified:
        otp = str(random.randint(100000, 999999))
        user.otp_code = otp
        user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        db.session.commit()
        try:
            msg = MailMessage(
                'Email Verification OTP',
                sender=app.config['MAIL_USERNAME'],
                recipients=[email]
            )
            msg.body = f"Your OTP code is {otp}. It will expire in 10 minutes."
            mail.send(msg)
        except Exception as mail_error:
            return jsonify({
                'error': 'Failed to resend OTP email.',
                'details': str(mail_error)
            }), 500
        # Return this so frontend can move user to verify page
        return jsonify({
            'message': 'Account not verified. OTP resent to your email.',
            'email': email,
            'requires_verification': True
        }), 403

    return jsonify({
        'message': 'Sign-in successful',
        'user': {
            'id': user.id,
            'username': user.username,
            'name': user.name,
            'email': user.email,
            'auth_token': user.auth_token
        }
    }), 200
