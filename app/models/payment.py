from app.extensions import db
from datetime import datetime, timezone

class Payment(db.Model):
    __tablename__ = 'payments'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    enrollment_id = db.Column(db.Integer, db.ForeignKey('enrollments.id'), nullable=True)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(10), default='USD')
    gateway = db.Column(db.String(50)) # 'stripe', 'paystack', 'flutterwave'
    transaction_id = db.Column(db.String(250), unique=True, index=True)
    status = db.Column(db.String(50), default='pending') # 'pending', 'successful', 'failed'
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    user = db.relationship('User', backref=db.backref('payments', lazy='dynamic'))
    enrollment = db.relationship('Enrollment', backref=db.backref('payment_records', lazy='dynamic'))

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'enrollment_id': self.enrollment_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'gateway': self.gateway,
            'transaction_id': self.transaction_id,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
