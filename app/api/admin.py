from flask import Blueprint, jsonify
from app.models.user import User
from app.models.course import Course
from app.models.enrollment import Enrollment
from app.extensions import db
from app.utils.decorators import admin_required, requires_roles

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/stats', methods=['GET'])
@requires_roles('admin', 'super_admin', 'director', 'manager', 'admin_staff', 'team_lead', 'staff')
def get_stats():
    total_users = db.session.execute(db.select(db.func.count(User.id))).scalar()
    total_courses = db.session.execute(db.select(db.func.count(Course.id))).scalar()
    total_enrollments = db.session.execute(db.select(db.func.count(Enrollment.id))).scalar()
    
    return jsonify({
        'total_users': total_users,
        'total_courses': total_courses,
        'total_enrollments': total_enrollments
    }), 200
