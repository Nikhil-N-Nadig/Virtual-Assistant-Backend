from medjobhub import db,datetime


class JobApplication(db.Model):
    __tablename__ = 'job_applications'
    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)  
    applicant_name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    resume_link = db.Column(db.String(500), nullable=False)
    cover_letter = db.Column(db.Text, nullable=True)
    applied_on = db.Column(db.DateTime, default=datetime.utcnow)

    qualifications = db.Column(db.String(500), nullable=True)  
    experience = db.Column(db.String(50), nullable=True)
    preferred_shift = db.Column(db.String(100), nullable=True)
    expected_salary = db.Column(db.Float, nullable=True)
    application_status = db.Column(db.String(50), nullable=False, default="Pending")  

    job = db.relationship('Job', back_populates='applications', lazy=True)
    applicant = db.relationship('User', back_populates='applications', lazy=True)

    def to_dict(self):
        return {
            "id": self.id,
            "job_id": self.job_id,
            "user_id": self.user_id,
            "applicant_name": self.applicant_name,
            "email": self.email,
            "phone": self.phone,
            "resume_link": self.resume_link,
            "cover_letter": self.cover_letter,
            "applied_on": self.applied_on.isoformat() if self.applied_on else None,
            "qualifications": self.qualifications,
            "experience": self.experience,
            "preferred_shift": self.preferred_shift,
            "expected_salary": self.expected_salary,
            "application_status": self.application_status,
            
            "job": self.job.to_dict() if self.job else None,
    
            "applicant": {
                "id": self.applicant.id,
                "username": self.applicant.username,
                "email": self.applicant.email
            } if self.applicant else None
        }