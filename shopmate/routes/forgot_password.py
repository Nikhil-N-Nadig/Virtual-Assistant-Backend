from flask import request, jsonify
from shopmate import app, db, User, Mail
from flask_mail import Message as MailMessage
from datetime import datetime, timedelta
import random
from werkzeug.security import check_password_hash

mail = Mail(app)

@app.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')

    if not email:
        return jsonify({'error': 'Email is required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'No account found with that email.'}), 404

    # Generate OTP and expiry
    otp = str(random.randint(100000, 999999))
    user.otp_code = otp
    user.otp_expiry = datetime.utcnow() + timedelta(minutes=10)
    db.session.commit()

    try:
        msg = MailMessage(
            'Password Reset OTP',
            sender=app.config['MAIL_USERNAME'],
            recipients=[email]
        )
        msg.body = f"Your password reset OTP is {otp}. It expires in 10 minutes."
        mail.send(msg)
    except Exception as e:
        return jsonify({'error': 'Failed to send email', 'details': str(e)}), 500

    return jsonify({'message': 'OTP sent to your email successfully.'}), 200


@app.route('/verify-reset-otp', methods=['POST'])
def verify_reset_otp():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')

    if not email or not otp:
        return jsonify({'error': 'Email and OTP are required'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.otp_code != otp:
        return jsonify({'error': 'Invalid OTP'}), 400

    if datetime.utcnow() > user.otp_expiry:
        return jsonify({'error': 'OTP expired'}), 400

    user.otp_verified_for_reset = True  # add this dynamically, not persisted
    db.session.commit()

    return jsonify({'message': 'OTP verified successfully. You can reset your password now.'}), 200


from werkzeug.security import generate_password_hash

@app.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    otp = data.get('otp')
    new_password = data.get('new_password')

    if not all([email, otp, new_password]):
        return jsonify({'error': 'Email, OTP, and new password are required.'}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.otp_code != otp:
        return jsonify({'error': 'Invalid OTP'}), 400

    if datetime.utcnow() > user.otp_expiry:
        return jsonify({'error': 'OTP expired'}), 400
    

    if check_password_hash(user.password, new_password):
        return jsonify({'error': 'New password cannot be same as old password.', 'same_password': True}), 400


    # ✅ Update password
    user.password = generate_password_hash(new_password)
    user.otp_code = None
    user.otp_expiry = None
    db.session.commit()

    return jsonify({'message': 'Password reset successful! Please sign in with your new password.'}), 200
