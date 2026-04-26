from app.extensions import db
from datetime import datetime, timezone

class Lesson(db.Model):
    __tablename__ = 'lessons'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    duration = db.Column(db.String(50))
    description = db.Column(db.Text)
    video_url = db.Column(db.String(500))
    order = db.Column(db.Integer, default=0) # To sort the syllabus
    is_completed = db.Column(db.Boolean, default=False)
    
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    course = db.relationship('Course', back_populates='lessons')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'duration': self.duration,
            'description': self.description,
            'video_url': self.video_url,
            'order': self.order,
            'is_completed': self.is_completed,
            'course_id': self.course_id
        }
