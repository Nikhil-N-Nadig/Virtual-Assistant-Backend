from shopmate import db,datetime

class UserPreference(db.Model):
    __tablename__ = 'user_preferences'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    category = db.Column(db.String(100))
    keyword = db.Column(db.String(255))
    last_searched = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Preference {self.keyword}>"
