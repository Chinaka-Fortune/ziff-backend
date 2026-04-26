from flask import Blueprint, jsonify, request
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.models.project import Project
from app.models.course_note import CourseNote
from app.models.certificate import Certificate
from app.models.user import User

enrollments_bp = Blueprint('enrollments', __name__)

@enrollments_bp.route('/', methods=['GET'])
@enrollments_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def my_enrollments():
    user_id = int(get_jwt_identity())
    user = db.session.get(User, user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    enrollments = db.session.scalars(db.select(Enrollment).filter_by(user_id=user_id)).all()
    notes = db.session.scalars(db.select(CourseNote).filter_by(user_id=user_id)).all()
    projects = db.session.scalars(db.select(Project).filter_by(user_id=user_id)).all()
    certificates = db.session.scalars(db.select(Certificate).filter_by(user_id=user_id)).all()
    
    return jsonify({
        'user': user.to_dict(),
        'enrollments': [enr.to_dict() for enr in enrollments],
        'notes': [note.to_dict() for note in notes],
        'projects': [p.to_dict() for p in projects],
        'certificates': [c.to_dict() for c in certificates]
    }), 200

@enrollments_bp.route('/', methods=['POST'])
@jwt_required()
def enroll():
    data = request.get_json()
    if not data or not data.get('course_id'):
        return jsonify({'message': 'Course ID is required'}), 400
        
    user_id = int(get_jwt_identity())
    course_id = data['course_id']
    
    course = db.session.get(Course, course_id)
    if not course:
        return jsonify({'message': 'Course not found'}), 404
        
    existing = db.session.execute(
        db.select(Enrollment).filter_by(user_id=user_id, course_id=course_id)
    ).scalar_one_or_none()
    
    if existing:
        return jsonify({'message': 'Already enrolled in this course'}), 400
        
    new_enrollment = Enrollment(
        user_id=user_id,
        course_id=course_id
    )
    db.session.add(new_enrollment)
    db.session.commit()
    
    return jsonify({'message': 'Enrollment successful', 'enrollment': new_enrollment.to_dict()}), 201

@enrollments_bp.route('/<int:enrollment_id>', methods=['DELETE'])
@jwt_required()
def delete_enrollment(enrollment_id):
    user_id = int(get_jwt_identity())
    enrollment = db.session.get(Enrollment, enrollment_id)
    
    if not enrollment:
        return jsonify({'message': 'Enrollment not found'}), 404
        
    # Only allow owners or admins to delete
    # (Assuming admin check logic for 'role' if needed, but for now simple owner check)
    if enrollment.user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    db.session.delete(enrollment)
    db.session.commit()
    
    return jsonify({'message': 'Successfully unenrolled'}), 200
