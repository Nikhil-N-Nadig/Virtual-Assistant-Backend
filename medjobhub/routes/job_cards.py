from medjobhub import app, db, session, jsonify, request, datetime,cross_origin,allowed_url
from medjobhub.models import User, Job, JobApplication

#Add Job
@app.route("/add_job", methods=["POST"])
def add_job():
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Please sign in to access this page"})
    
    if session['role'] != 'employer':
        return jsonify({"success": False, "message": "You don't have permission to access this page"})
    
    user = User.query.get(session['user_id'])
    
    if not user or user.role != "employer":
        return jsonify({"success": False, "message": "Only employers can post jobs."})
    
    job_data = request.get_json()
    
    try:
        new_job = Job(
            title=job_data.get('title'),
            company=job_data.get('company') or user.company_name,
            location=job_data.get('location'),
            description=job_data.get('description'),
            salary=float(job_data.get('salary', 0)),
            posted_by=user.id,
            posted_on=datetime.utcnow(),
            employment_type=job_data.get('employment_type', 'Full-time'),
            specialization=job_data.get('specialization'),
            required_experience=job_data.get('required_experience'),
            required_qualifications=job_data.get('required_qualifications'),
            shift_timing=job_data.get('shift_timing'),
            job_type=job_data.get('job_type', 'Hospital'),
            application_deadline=datetime.strptime(job_data.get('application_deadline'), '%Y-%m-%d') if job_data.get('application_deadline') else None,
            benefits=job_data.get('benefits'),
            contact_email=job_data.get('contact_email') or user.email,
            contact_phone=job_data.get('contact_phone') or user.phone
        )
        db.session.add(new_job)
        db.session.commit()
        return jsonify({"success": True, "message": "Job posted successfully!"})
    except Exception as e:
        return jsonify({"success": False, "message": "Error posting job."})


#Employer_Jobs
@app.route('/your_jobs', methods=['GET'])
@cross_origin(origin=allowed_url, supports_credentials=True)
def your_jobs():
    if 'user_id' not in session or session['role'] != 'employer':
        return jsonify({"success": False, "message": "Unauthorized access"})
    
    user_id = session['user_id']
    jobs = Job.query.filter_by(posted_by=user_id).all()
    return jsonify({"success": True, "jobs": [job.to_dict() for job in jobs]})


#Available_Jobs
@app.route('/available_jobs', methods=['GET'])
@cross_origin(origin=allowed_url, supports_credentials=True)
def available_jobs():
    if 'user_id' not in session or session['role'] == 'employer':
        return jsonify({"success": False, "message": "Unauthorized access"})
    
    jobs = Job.query.all()
    return jsonify({"success": True, "jobs": [job.to_dict() for job in jobs]})


#Delete_Jobs
@app.route('/delete_job/<int:job_id>', methods=['POST'])
def delete_job(job_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Please sign in to continue"})
    
    job = Job.query.get(job_id)
    if not job:
        return jsonify({"success": False, "message": "Job not found"})
    
    if job.posted_by != session['user_id']:
        return jsonify({"success": False, "message": "Unauthorized"})
    
    JobApplication.query.filter_by(job_id=job.id).delete()
    db.session.delete(job)
    db.session.commit()
    return jsonify({"success": True, "message": "Job deleted successfully"})


#Job_Details
@app.route('/job_details/<int:job_id>', methods=['GET'])
@cross_origin(origin=allowed_url, supports_credentials=True)

def job_details(job_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "message": "Please sign in to continue"})
    
    job = Job.query.get(job_id)
    if not job:
        return jsonify({"success": False, "message": "Job not found"})
    
    return jsonify({"success": True, "job": job.to_dict()})