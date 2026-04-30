from app.extensions import db
from datetime import datetime, timezone

class Meeting(db.Model):
    __tablename__ = 'meetings'

    id = db.Column(db.Integer, primary_key=True)
    room_name = db.Column(db.String(255), unique=True, nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.String(50), default='active') # 'active', 'ended'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    creator = db.relationship('User', backref=db.backref('created_meetings', lazy='dynamic'))
    participants = db.relationship('MeetingParticipant', back_populates='meeting', cascade="all, delete-orphan")

    def to_dict(self):
        return {
            'id': self.id,
            'room_name': self.room_name,
            'title': self.title,
            'creator_id': self.creator_id,
            'creator_name': self.creator.name if self.creator else None,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'invited_count': len(self.participants)
        }

class MeetingParticipant(db.Model):
    __tablename__ = 'meeting_participants'

    id = db.Column(db.Integer, primary_key=True)
    meeting_id = db.Column(db.Integer, db.ForeignKey('meetings.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    invited_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    meeting = db.relationship('Meeting', back_populates='participants')
    user = db.relationship('User', backref=db.backref('meeting_invitations', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'meeting_id': self.meeting_id,
            'user_id': self.user_id,
            'user_name': self.user.name if self.user else None,
            'user_email': self.user.email if self.user else None,
            'invited_at': self.invited_at.isoformat() if self.invited_at else None
        }
