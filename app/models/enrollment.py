from app.extensions import db
from datetime import datetime, timezone

class Enrollment(db.Model):
    __tablename__ = 'enrollments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    status = db.Column(db.String(50), default='Registered') # e.g., 'Registered', 'Completed'
    payment_status = db.Column(db.String(50), default='Pending') # e.g., 'Pending', 'Paid'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Elite Dashboard Fields
    progress = db.Column(db.Float, default=0.0) # Percentage 0.0 to 100.0
    last_lesson_id = db.Column(db.Integer, nullable=True)
    streak = db.Column(db.Integer, default=0)
    last_active = db.Column(db.DateTime, nullable=True)

    # Manual Access Control
    is_executive = db.Column(db.Boolean, default=False)
    is_restricted = db.Column(db.Boolean, default=False)

    user = db.relationship('User', back_populates='enrollments')
    course = db.relationship('Course', back_populates='enrollments')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_id': self.course_id,
            'course_title': self.course.title if self.course else 'Untitled Course',
            'course_slug': self.course.slug if self.course else 'general-class',
            'status': self.status,
            'payment_status': self.payment_status,
            'progress': self.progress,
            'last_lesson_id': self.last_lesson_id,
            'streak': self.streak,
            'last_active': self.last_active.isoformat() if self.last_active else None,
            'is_executive': self.is_executive,
            'is_restricted': self.is_restricted,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

    def __repr__(self):
        return f'<Enrollment {self.user_id} -> {self.course_id} | Executive: {self.is_executive} | Restricted: {self.is_restricted}>'
