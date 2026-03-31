from medjobhub import db,datetime


class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    company = db.Column(db.String(255), nullable=False)  
    location = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    salary = db.Column(db.Float, nullable=False)
    posted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  
    posted_on = db.Column(db.DateTime, default=datetime.utcnow)

    employment_type = db.Column(db.String(50), nullable=False, default="Full-time")  
    specialization = db.Column(db.String(255), nullable=True)
    required_experience = db.Column(db.String(50), nullable=True)
    required_qualifications = db.Column(db.Text, nullable=True)
    shift_timing = db.Column(db.String(100), nullable=True)
    job_type = db.Column(db.String(50), nullable=False, default="Hospital")
    application_deadline = db.Column(db.DateTime, nullable=True)
    benefits = db.Column(db.Text, nullable=True)
    contact_email = db.Column(db.String(255), nullable=True)
    contact_phone = db.Column(db.String(20), nullable=True)

    employer = db.relationship('User', back_populates='jobs_posted', lazy=True)

    applications = db.relationship('JobApplication', back_populates='job', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "salary": self.salary,
            "posted_on": self.posted_on.isoformat() if self.posted_on else None,
            "description": self.description,
            "employment_type": self.employment_type,
            "specialization": self.specialization,
            "required_experience": self.required_experience,
            "required_qualifications": self.required_qualifications,
            "shift_timing": self.shift_timing,
            "job_type": self.job_type,
            "application_deadline": self.application_deadline.isoformat() if self.application_deadline else None,
            "benefits": self.benefits,
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "posted_by": self.posted_by,  
            "employer": {
                "id": self.employer.id,
                "username": self.employer.username
            } if self.employer else None,  
        }