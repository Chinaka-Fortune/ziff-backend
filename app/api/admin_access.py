from flask import Blueprint, request, jsonify
from app.models.user import User
from app.models.enrollment import Enrollment
from app.extensions import db
from app.utils.decorators import requires_roles
from flask_jwt_extended import get_jwt_identity
from datetime import datetime, timezone

admin_access_bp = Blueprint('admin_access', __name__)

@admin_access_bp.route('/enrollment/<int:enrollment_id>/override', methods=['PATCH'])
@requires_roles('admin', 'super_admin', 'director', 'manager', 'admin_staff')
def override_enrollment_access(enrollment_id):
    """
    Allow admins to grant Executive Access or Restrict specific students per-course.
    """
    data = request.get_json()
    enrollment = db.session.get(Enrollment, enrollment_id)
    if not enrollment:
        return jsonify(message="Enrollment not found"), 404
        
    if 'is_executive' in data:
        enrollment.is_executive = bool(data['is_executive'])
    if 'is_restricted' in data:
        enrollment.is_restricted = bool(data['is_restricted'])
    if 'payment_status' in data:
        enrollment.payment_status = data['payment_status'] # e.g. 'Paid', 'Pending'
        
    db.session.commit()
    return jsonify(message="Access override updated successfully", enrollment=enrollment.to_dict()), 200

@admin_access_bp.route('/user/<int:user_id>/global-restriction', methods=['PATCH'])
@requires_roles('super_admin')
def toggle_global_restriction(user_id):
    """
    Only Super Admins can globally restrict a user from all academic content.
    """
    data = request.get_json()
    user = db.session.get(User, user_id)
    if not user:
        return jsonify(message="User not found"), 404
        
    if 'is_globally_restricted' in data:
        user.is_globally_restricted = bool(data['is_globally_restricted'])
        
    db.session.commit()
    status = "restricted" if user.is_globally_restricted else "unrestricted"
    return jsonify(message=f"User {user.name} is now globally {status}."), 200

@admin_access_bp.route('/enrollment/<int:enrollment_id>/mark-paid', methods=['POST'])
@requires_roles('admin', 'super_admin', 'director', 'manager', 'admin_staff')
def mark_enrollment_paid(enrollment_id):
    """
    Allow admins to manually confirm payment (e.g. for Bank Transfers or Cash).
    """
    enrollment = db.session.get(Enrollment, enrollment_id)
    if not enrollment:
        return jsonify(message="Enrollment not found"), 404
        
    enrollment.payment_status = 'Paid'
    
    # Create a record of this manual payment
    from app.models.payment import Payment
    payment = Payment(
        user_id=enrollment.user_id,
        enrollment_id=enrollment.id,
        amount=enrollment.course.price,
        currency='Manual',
        gateway='Admin_Manual',
        status='successful',
        transaction_id=f"MANUAL-{enrollment_id}-{int(datetime.now(timezone.utc).timestamp())}"
    )
    db.session.add(payment)
    db.session.commit()
    
    return jsonify(message=f"Enrollment for {enrollment.course.title} marked as PAID manually."), 200
