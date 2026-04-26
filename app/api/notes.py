from flask import Blueprint, jsonify, request
from app.models.course_note import CourseNote
from app.models.course import Course
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity

notes_bp = Blueprint('notes', __name__)

@notes_bp.route('/', methods=['GET'])
@jwt_required()
def get_notes():
    user_id = int(get_jwt_identity())
    notes = db.session.scalars(db.select(CourseNote).filter_by(user_id=user_id)).all()
    return jsonify([note.to_dict() for note in notes]), 200

@notes_bp.route('/', methods=['POST'])
@jwt_required()
def create_note():
    data = request.get_json()
    if not data or not data.get('content') or not data.get('course_id'):
        return jsonify({'message': 'Content and Course ID are required'}), 400
        
    user_id = int(get_jwt_identity())
    
    new_note = CourseNote(
        user_id=user_id,
        course_id=data['course_id'],
        lesson_id=data.get('lesson_id'),
        timestamp_in_video=data.get('timestamp_in_video'),
        content=data['content']
    )
    db.session.add(new_note)
    db.session.commit()
    
    return jsonify({'message': 'Note created successfully', 'note': new_note.to_dict()}), 201

@notes_bp.route('/<int:note_id>', methods=['PUT', 'PATCH'])
@jwt_required()
def update_note(note_id):
    user_id = int(get_jwt_identity())
    note = db.session.get(CourseNote, note_id)
    
    if not note:
        return jsonify({'message': 'Note not found'}), 404
    if note.user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    data = request.get_json()
    if data.get('content'):
        note.content = data['content']
    if 'lesson_id' in data:
        note.lesson_id = data['lesson_id']
    if 'timestamp_in_video' in data:
        note.timestamp_in_video = data['timestamp_in_video']
        
    db.session.commit()
    return jsonify({'message': 'Note updated successfully', 'note': note.to_dict()}), 200

@notes_bp.route('/<int:note_id>', methods=['DELETE'])
@jwt_required()
def delete_note(note_id):
    user_id = int(get_jwt_identity())
    note = db.session.get(CourseNote, note_id)
    
    if not note:
        return jsonify({'message': 'Note not found'}), 404
    if note.user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    db.session.delete(note)
    db.session.commit()
    return jsonify({'message': 'Note deleted successfully'}), 200
