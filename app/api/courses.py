from flask import Blueprint, jsonify, request
from app.models.course import Course
from app.models.activity_log import ActivityLog
from app.extensions import db
from app.utils.decorators import admin_required, requires_roles
from flask_jwt_extended import jwt_required, get_jwt_identity, verify_jwt_in_request
from app.utils.access_control import check_course_access
import re

courses_bp = Blueprint('courses', __name__)

def slugify(text):
    return re.sub(r'[\W_]+', '-', text.lower()).strip('-')

@courses_bp.route('/', methods=['GET'])
def get_courses():
    category = request.args.get('category')
    level = request.args.get('level')
    query = db.select(Course)
    if category:
        query = query.filter_by(category=category)
    if level:
        query = query.filter_by(level=level)
    
    courses = db.session.scalars(query).all()
    # Return simplified list for overview
    return jsonify([course.to_dict() for course in courses]), 200

@courses_bp.route('/<slug>', methods=['GET'])
def get_course(slug):
    course = db.session.execute(db.select(Course).filter_by(slug=slug)).scalar_one_or_none()
    if not course:
        return jsonify({'message': 'Course not found'}), 404
    
    # Check for authentication to determine if we show full content
    has_access = False
    access_message = "Public preview"
    try:
        verify_jwt_in_request(optional=True)
        user_id = get_jwt_identity()
        if user_id:
            success, msg, status = check_course_access(int(user_id), course.id)
            has_access = success
            access_message = msg
    except Exception:
        pass

    course_data = course.to_dict()
    
    if not has_access:
        # Hide sensitive lesson content like video URLs
        if 'lessons' in course_data:
            for lesson in course_data['lessons']:
                lesson['video_url'] = None
                lesson['description'] = "Enroll and complete payment to unlock this lesson."
        course_data['has_access'] = False
        course_data['access_message'] = access_message
    else:
        course_data['has_access'] = True

    return jsonify(course_data), 200

@courses_bp.route('/', methods=['POST'])
@requires_roles('admin', 'super_admin', 'director', 'manager', 'staff', 'admin_staff')
def create_course():
    data = request.get_json()
    if not data or not data.get('title') or not data.get('description'):
        return jsonify({'message': 'Title and description required'}), 400

    new_course = Course(
        title=data['title'],
        slug=slugify(data['title']),
        description=data['description'],
        category=data.get('category'),
        level=data.get('level'),
        duration=data.get('duration'),
        price=data.get('price'),
        instructor_bio=data.get('instructor_bio')
    )
    db.session.add(new_course)
    
    # Log Activity
    admin_id = int(get_jwt_identity())
    db.session.add(ActivityLog(
        user_id=admin_id,
        activity_type='course_created',
        description=f"Strategic Initiative: Created course '{new_course.title}'"
    ))
    
    db.session.commit()
    return jsonify({'message': 'Course created', 'course': new_course.to_dict()}), 201

@courses_bp.route('/<slug>', methods=['PUT'])
@requires_roles('admin', 'super_admin', 'director', 'manager', 'staff', 'admin_staff')
def update_course(slug):
    course = db.session.execute(db.select(Course).filter_by(slug=slug)).scalar_one_or_none()
    if not course:
        return jsonify({'message': 'Course not found'}), 404
        
    data = request.get_json()
    if 'title' in data:
        course.title = data['title']
        course.slug = slugify(data['title'])
    if 'description' in data:
        course.description = data['description']
    if 'category' in data:
        course.category = data['category']
    if 'level' in data:
        course.level = data['level']
    if 'duration' in data:
        course.duration = data['duration']
    if 'price' in data:
        course.price = data['price']
    if 'instructor_bio' in data:
        course.instructor_bio = data['instructor_bio']

    db.session.commit()
    return jsonify({'message': 'Course updated', 'course': course.to_dict()}), 200

@courses_bp.route('/<slug>', methods=['DELETE'])
@requires_roles('admin', 'super_admin', 'director', 'manager', 'staff', 'admin_staff')
def delete_course(slug):
    course = db.session.execute(db.select(Course).filter_by(slug=slug)).scalar_one_or_none()
    if not course:
        return jsonify({'message': 'Course not found'}), 404
        
    course_title = course.title
    db.session.delete(course)
    
    # Log Activity
    admin_id = int(get_jwt_identity())
    db.session.add(ActivityLog(
        user_id=admin_id,
        activity_type='course_deleted',
        description=f"Course '{course_title}' deleted from academic catalog."
    ))
    
    db.session.commit()
    return jsonify({'message': 'Course deleted'}), 200
