from flask import Blueprint, jsonify, request
from app.models.contact import Inquiry
from app.models.activity_log import ActivityLog
from app.extensions import db
from app.utils.decorators import admin_required, requires_roles
from flask_jwt_extended import get_jwt_identity

contact_bp = Blueprint('contact', __name__)

@contact_bp.route('/', methods=['POST'])
def submit_inquiry():
    data = request.get_json()
    if not data or not data.get('name') or not data.get('email') or not data.get('message'):
        return jsonify({'message': 'Name, email, and message are required'}), 400
        
    new_inquiry = Inquiry(
        name=data['name'],
        email=data['email'],
        message=data['message']
    )
    db.session.add(new_inquiry)
    db.session.commit()
    
    return jsonify({'message': 'Inquiry submitted successfully'}), 201

@contact_bp.route('/', methods=['GET'])
@requires_roles('admin', 'super_admin', 'director', 'manager', 'admin_staff', 'team_lead', 'staff')
def get_inquiries():
    inquiries = db.session.scalars(db.select(Inquiry).order_by(Inquiry.created_at.desc())).all()
    return jsonify([inq.to_dict() for inq in inquiries]), 200

@contact_bp.route('/<int:id>', methods=['PUT'])
@requires_roles('admin', 'super_admin', 'director', 'manager', 'admin_staff', 'team_lead', 'staff')
def update_inquiry_status(id):
    inquiry = db.session.get(Inquiry, id)
    if not inquiry:
        return jsonify({'message': 'Inquiry not found'}), 404
        
    data = request.get_json()
    if 'status' in data:
        inquiry.status = data['status']
        
        # Log Activity
        admin_id = int(get_jwt_identity())
        db.session.add(ActivityLog(
            user_id=admin_id,
            activity_type='inquiry_resolved' if data['status'] == 'Resolved' else 'inquiry_updated',
            description=f"Operational Oversight: Inquiry from {inquiry.name} marked as {data['status']}."
        ))
        
        db.session.commit()
        
    return jsonify({'message': 'Inquiry updated', 'inquiry': inquiry.to_dict()}), 200

@contact_bp.route('/<int:id>', methods=['DELETE'])
@requires_roles('admin', 'super_admin', 'director', 'manager', 'team_lead')
def delete_inquiry(id):
    inquiry = db.session.get(Inquiry, id)
    if not inquiry:
        return jsonify({'message': 'Inquiry not found'}), 404
        
    db.session.delete(inquiry)
    db.session.commit()
    return jsonify({'message': 'Inquiry deleted successfully'}), 200
