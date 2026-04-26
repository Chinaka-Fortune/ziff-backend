from app.extensions import db
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
from app.models.activity_log import ActivityLog

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(50), default='student') # student, customer, staff, team_lead, manager, director, admin_staff, super_admin
    reset_token = db.Column(db.String(100), nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Elite Dashboard Fields
    bio = db.Column(db.Text, nullable=True)
    avatar_url = db.Column(db.String(256), nullable=True)
    points = db.Column(db.Integer, default=0)
    public_profile = db.Column(db.Boolean, default=False)
    
    # Social Branding Fields
    linkedin_url = db.Column(db.String(256), nullable=True)
    github_url = db.Column(db.String(256), nullable=True)
    twitter_url = db.Column(db.String(256), nullable=True)
    whatsapp_number = db.Column(db.String(50), nullable=True)
    instagram_url = db.Column(db.String(256), nullable=True)

    # Notification Preferences
    notify_email = db.Column(db.Boolean, default=True)
    notify_whatsapp = db.Column(db.Boolean, default=False)

    # Universal Skill/Metric Proficiency (JSON for role flexibility)
    skills = db.Column(db.JSON, nullable=True)

    # Super Admin Security Controls
    is_globally_restricted = db.Column(db.Boolean, default=False)

    enrollments = db.relationship('Enrollment', back_populates='user', lazy='dynamic')
    certificates = db.relationship('Certificate', back_populates='user', lazy='dynamic')
    activity_logs = db.relationship('ActivityLog', back_populates='user', lazy='dynamic')
    notes = db.relationship('CourseNote', back_populates='user', lazy='dynamic')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'role': self.role,
            'bio': self.bio,
            'avatar_url': self.avatar_url,
            'points': self.points,
            'public_profile': self.public_profile,
            'socials': {
                'linkedin': self.linkedin_url,
                'github': self.github_url,
                'twitter': self.twitter_url,
                'whatsapp': self.whatsapp_number,
                'instagram': self.instagram_url
            },
            'notifications': {
                'email': self.notify_email,
                'whatsapp': self.notify_whatsapp
            },
            'skills': self.skills or {},
            'is_globally_restricted': self.is_globally_restricted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'certificates': [c.to_dict() for c in self.certificates.all()],
            'activity_logs': [a.to_dict() for a in self.activity_logs.order_by(ActivityLog.timestamp.desc()).limit(100).all()]
        }
