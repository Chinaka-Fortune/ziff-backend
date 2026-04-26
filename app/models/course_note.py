from app.extensions import db
from datetime import datetime, timezone

class CourseNote(db.Model):
    __tablename__ = 'course_notes'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    lesson_id = db.Column(db.Integer, nullable=True)
    timestamp_in_video = db.Column(db.Integer, nullable=True) # Seconds into the video
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', back_populates='notes')
    course = db.relationship('Course', backref='notes')

    def to_dict(self):
        return {
            'id': self.id,
            'course_title': self.course.title if self.course else 'N/A',
            'lesson_id': self.lesson_id,
            'timestamp_in_video': self.timestamp_in_video,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
