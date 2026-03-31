from medjobhub import db

class UserProfile(db.Model):
    __tablename__ = 'user_profiles'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)

    first_name = db.Column(db.String(80), nullable=False)
    last_name = db.Column(db.String(80), nullable=False)
    phone = db.Column(db.String(15), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    age = db.Column(db.Integer, nullable=True)
    address = db.Column(db.String(200), nullable=True)
    profile_pic_url = db.Column(db.String(255), nullable=True)
    linkedin = db.Column(db.String(255), nullable=True)
    github = db.Column(db.String(255), nullable=True)
    twitter = db.Column(db.String(255), nullable=True)
    portfolio_website = db.Column(db.String(255), nullable=True)

    medical_license_number = db.Column(db.String(100), nullable=True) 
    specialization = db.Column(db.String(255), nullable=True)
    certifications = db.Column(db.Text, nullable=True) 
    skills = db.Column(db.Text, nullable=True) 
    education = db.Column(db.Text, nullable=True)
    work_experience = db.Column(db.Text, nullable=True) 
    publications = db.Column(db.Text, nullable=True) 
    availability = db.Column(db.String(50), nullable=True) 

    resume_url = db.Column(db.String(255), nullable=True)
    resume_generated = db.Column(db.Boolean, default=False)

    education_file = db.Column(db.String(255), nullable=True)
    education_filename = db.Column(db.String(255), nullable=True)

    company_name = db.Column(db.String(255), nullable=True)
    company_website = db.Column(db.String(255), nullable=True)
    company_description = db.Column(db.Text, nullable=True)
    industry = db.Column(db.String(100), nullable=True)
    company_size = db.Column(db.String(50), nullable=True)
    founded_year = db.Column(db.Integer, nullable=True) 
    headquarters_location = db.Column(db.String(255), nullable=True)
    company_logo = db.Column(db.String(255), nullable=True) 
