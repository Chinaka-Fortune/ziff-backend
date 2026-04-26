from app.extensions import db
from datetime import datetime, timezone

class SupportThread(db.Model):
    __tablename__ = 'support_threads'

    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    original_staff_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    department = db.Column(db.String(50), nullable=False) # 'Tech Support', 'Administration', 'Leadership'
    subject = db.Column(db.String(256), nullable=False)
    status = db.Column(db.String(50), default='Open') # 'Open', 'Staff Replied', 'Escalated', 'Resolved'
    access_level = db.Column(db.Integer, default=0) # 0: Staff+, 1: Manager+, 2: Director+
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    messages = db.relationship('SupportMessage', backref='thread', lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'assigned_staff_id': self.assigned_staff_id,
            'original_staff_id': self.original_staff_id,
            'department': self.department,
            'subject': self.subject,
            'status': self.status,
            'access_level': self.access_level,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'messages': [m.to_dict() for m in self.messages.order_by(SupportMessage.created_at.asc()).all()]
        }

class SupportMessage(db.Model):
    __tablename__ = 'support_messages'

    id = db.Column(db.Integer, primary_key=True)
    thread_id = db.Column(db.Integer, db.ForeignKey('support_threads.id'), nullable=False)
    sender_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'thread_id': self.thread_id,
            'sender_id': self.sender_id,
            'body': self.body,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class HubPost(db.Model):
    __tablename__ = 'hub_posts'

    id = db.Column(db.Integer, primary_key=True)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(256), nullable=False)
    content = db.Column(db.Text, nullable=False)
    category = db.Column(db.String(50), default='Discussion') # 'Feedback', 'Announcement', 'Discussion'
    is_public = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    comments = db.relationship('HubComment', backref='post', lazy='dynamic', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'author_id': self.author_id,
            'title': self.title,
            'content': self.content,
            'category': self.category,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'comments_count': self.comments.count()
        }

class HubComment(db.Model):
    __tablename__ = 'hub_comments'

    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('hub_posts.id'), nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    def to_dict(self):
        return {
            'id': self.id,
            'post_id': self.post_id,
            'author_id': self.author_id,
            'content': self.content,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
