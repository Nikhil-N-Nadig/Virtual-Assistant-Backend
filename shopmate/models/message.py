from shopmate import db, datetime
from sqlalchemy.dialects.postgresql import JSON

class Message(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    conversation_id = db.Column(db.Integer, db.ForeignKey('conversation.id'), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    content = db.Column(db.Text, nullable=False)

    # STORE ALL TOOL OUTPUTS
    products = db.Column(JSON, nullable=True)
    price_history = db.Column(JSON, nullable=True)
    price_prediction = db.Column(JSON, nullable=True)
    reviews = db.Column(JSON, nullable=True)

    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

