from shopmate import db,datetime
from sqlalchemy.dialects.postgresql import JSON


class Reminder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    products = db.Column(JSON, nullable=False)        # list of product cards / minimal product objects
    send_time = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default="pending")  # pending, sent, cancelled, failed
    note = db.Column(db.String(255), nullable=True)