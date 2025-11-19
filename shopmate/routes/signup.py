from shopmate import app, request, jsonify, datetime, timedelta, random, User, db, Mail
from flask_mail import Message as MailMessage
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

mail = Mail(app)

@app.route('/signup', methods=['POST'])
def signup():
    try:
        data = request.get_json()

        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        username = data.get('username')  # Optional, depending on your model

        # --- 1️⃣ Validate input ---
        if not name or not email or not password:
            return jsonify({'error': 'Name, email, and password are required.'}), 400

        # --- 2️⃣ Check for duplicates ---
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered.'}), 400
        if username and User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists.'}), 400

        # --- 3️⃣ Hash password securely ---
        hashed_password = generate_password_hash(password)

        # --- 4️⃣ Generate OTP and expiry ---
        otp = str(random.randint(100000, 999999))
        otp_expiry = datetime.utcnow() + timedelta(minutes=10)
        # --- 5️⃣ Create new user (unverified initially) ---
        new_user = User(
            name=name,
            email=email,
            username=username if username else email.split('@')[0],
            password=hashed_password,
            is_verified=False,
            otp_code=otp,
            otp_expiry=otp_expiry
        )
        
        db.session.add(new_user)
        db.session.commit()


        # --- 6️⃣ Send OTP Email ---
        try:
            msg = MailMessage(
                'Email Verification OTP',
                sender=app.config['MAIL_USERNAME'],
                recipients=[email]
            )
            msg.body = f"Your OTP code is {otp}. It will expire in 10 minutes."
            mail.send(msg)
        except Exception as mail_error:
            # If email fails, rollback user and report
            db.session.delete(new_user)
            db.session.commit()
            return jsonify({'error': 'Failed to send verification email.', 'details': str(mail_error)}), 500

        return jsonify({'message': 'User created. Please verify your email with the OTP sent.'}), 201

    # --- 7️⃣ Handle SQLAlchemy integrity errors (duplicate constraints, etc.) ---
    except IntegrityError as e:
        db.session.rollback()
        return jsonify({'error': 'Username or email already exists.', 'details': str(e)}), 400

    # --- 8️⃣ Generic error fallback ---
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'An unexpected error occurred.', 'details': str(e)}), 500
