from app.extensions import db
from datetime import datetime, timezone

class LiveClass(db.Model):
    __tablename__ = 'live_classes'

    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    title = db.Column(db.String(250), nullable=False)
    agenda = db.Column(db.Text)
    room_name = db.Column(db.String(250), unique=True, index=True, nullable=False)
    scheduled_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, default=60)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    course = db.relationship('Course', backref=db.backref('live_classes', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'title': self.title,
            'agenda': self.agenda,
            'room_name': self.room_name,
            'scheduled_time': self.scheduled_time.isoformat(),
            'duration_minutes': self.duration_minutes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
