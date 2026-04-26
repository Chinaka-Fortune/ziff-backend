from flask import Blueprint, jsonify, request
from app.models.project import Project
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity

projects_bp = Blueprint('projects', __name__)

@projects_bp.route('/', methods=['GET'])
@jwt_required()
def get_projects():
    user_id = int(get_jwt_identity())
    projects = db.session.scalars(db.select(Project).filter_by(user_id=user_id)).all()
    return jsonify([p.to_dict() for p in projects]), 200

@projects_bp.route('/', methods=['POST'])
@jwt_required()
def create_project():
    data = request.get_json()
    if not data or not data.get('title'):
        return jsonify({'message': 'Title is required'}), 400
        
    user_id = int(get_jwt_identity())
    
    new_project = Project(
        user_id=user_id,
        title=data['title'],
        description=data.get('description'),
        status=data.get('status', 'to_do')
    )
    db.session.add(new_project)
    db.session.commit()
    
    return jsonify({'message': 'Project created successfully', 'project': new_project.to_dict()}), 201

@projects_bp.route('/<int:project_id>', methods=['PUT', 'PATCH'])
@jwt_required()
def update_project(project_id):
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    
    if not project:
        return jsonify({'message': 'Project not found'}), 404
    if project.user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    data = request.get_json()
    if 'title' in data:
        project.title = data['title']
    if 'description' in data:
        project.description = data['description']
    if 'status' in data:
        project.status = data['status']
        
    db.session.commit()
    return jsonify({'message': 'Project updated successfully', 'project': project.to_dict()}), 200

@projects_bp.route('/<int:project_id>', methods=['DELETE'])
@jwt_required()
def delete_project(project_id):
    user_id = int(get_jwt_identity())
    project = db.session.get(Project, project_id)
    
    if not project:
        return jsonify({'message': 'Project not found'}), 404
    if project.user_id != user_id:
        return jsonify({'message': 'Unauthorized'}), 403
        
    db.session.delete(project)
    db.session.commit()
    return jsonify({'message': 'Project deleted successfully'}), 200
