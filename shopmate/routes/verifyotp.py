from shopmate import app,request,jsonify,random,datetime,timedelta,User,db,Mail
from flask_mail import Message as MailMessage

mail = Mail(app)

@app.route('/verify-otp', methods=['POST'])
def verify_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')


    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.is_verified:
        return jsonify({'message': 'User already verified'}), 200

    # Check OTP validity
    if user.otp_code != otp:
        return jsonify({'error': 'Invalid OTP'}), 400

    if datetime.utcnow() > user.otp_expiry:
        return jsonify({'error': 'OTP expired'}), 400

    # Mark as verified
    user.is_verified = True
    user.otp_code = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({
        'message': 'Email verified successfully!',
        'user': {
            'id': user.id,
            'name': user.name,
            'email': user.email,
            'username': user.username
        },
        'token': user.auth_token
    }), 200



@app.route('/resend-otp', methods=['POST'])
def resend_otp():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    # Fetch user
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    # If already verified, no need to resend
    if user.is_verified:
        return jsonify({'message': 'User already verified.'}), 200

    # Optional cooldown (avoid spamming resend)
    if user.otp_expiry and (datetime.utcnow() < user.otp_expiry - timedelta(minutes=9)):
        return jsonify({
            'error': 'OTP was already sent recently. Please wait a minute before requesting again.'
        }), 429  # Too Many Requests

    # Generate new OTP and expiry
    otp = str(random.randint(100000, 999999))
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()

    # Send email
    try:
        msg = MailMessage(
            'Resend Email Verification OTP',
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Your new OTP code is {otp}. It will expire in 10 minutes."
        mail.send(msg)
    except Exception as mail_error:
        return jsonify({
            'error': 'Failed to send OTP email.',
            'details': str(mail_error)
        }), 500

    return jsonify({
        'message': 'A new OTP has been sent to your email.',
        'email': email,
        'otp_expiry': user.otp_expiry.isoformat()
    }), 200
