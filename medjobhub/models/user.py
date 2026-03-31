from medjobhub import db,secrets

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    phone = db.Column(db.String(15))
    gender = db.Column(db.String(10))
    age = db.Column(db.Integer)
    address = db.Column(db.String(200))
    password = db.Column(db.String(200), nullable=False)
    is_verified = db.Column(db.Boolean, default=False)

    auth_token = db.Column(db.String(32), unique=True, nullable=True, default=lambda: secrets.token_hex(16))
    role = db.Column(db.String(20), nullable=False)  # "employer" or "job_seeker"
    company_name = db.Column(db.String(255), nullable=True)  # Only for employers
    resume = db.Column(db.String(255), nullable=True)  # Only for job seekers

    profile = db.relationship('UserProfile', backref='profile_user', uselist=False)

    applications = db.relationship('JobApplication', back_populates='applicant', lazy=True)

    jobs_posted = db.relationship('Job', back_populates='employer', lazy=True)
