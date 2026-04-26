from app.extensions import db
from datetime import datetime, timezone

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    slug = db.Column(db.String(250), unique=True, nullable=False, index=True)
    description = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(100))
    level = db.Column(db.String(50))
    duration = db.Column(db.String(100))
    price = db.Column(db.Numeric(10, 2))
    instructor_bio = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    enrollments = db.relationship('Enrollment', back_populates='course', lazy='dynamic')
    lessons = db.relationship('Lesson', back_populates='course', order_by='Lesson.order', cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'slug': self.slug,
            'description': self.description,
            'category': self.category,
            'level': self.level,
            'duration': self.duration,
            'price': float(self.price) if self.price else None,
            'instructor_bio': self.instructor_bio,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'lessons': [l.to_dict() for l in self.lessons]
        }
