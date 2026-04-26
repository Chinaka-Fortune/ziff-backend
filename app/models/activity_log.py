from app.extensions import db
from datetime import datetime, timezone

class ActivityLog(db.Model):
    __tablename__ = 'activity_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    activity_type = db.Column(db.String(100), nullable=False) # e.g., 'lesson_completed', 'quiz_passed', 'login'
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    points_earned = db.Column(db.Integer, default=0)
    description = db.Column(db.String(256), nullable=True)

    user = db.relationship('User', back_populates='activity_logs')

    def to_dict(self):
        return {
            'id': self.id,
            'activity_type': self.activity_type,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'points_earned': self.points_earned,
            'description': self.description
        }
