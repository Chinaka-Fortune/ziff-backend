from app.extensions import db
from datetime import datetime, timezone

class Certificate(db.Model):
    __tablename__ = 'certificates'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('courses.id'), nullable=False)
    issue_date = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    certificate_url = db.Column(db.String(256), nullable=False)
    grade = db.Column(db.String(10), nullable=True)

    user = db.relationship('User', back_populates='certificates')
    course = db.relationship('Course', backref='certificates')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'course_title': self.course.title if self.course else 'N/A',
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'certificate_url': self.certificate_url,
            'grade': self.grade
        }
