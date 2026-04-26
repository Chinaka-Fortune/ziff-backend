from flask import jsonify
from app.models.user import User
from app.models.enrollment import Enrollment
from app.models.course import Course
from app.extensions import db

def check_course_access(user_id, course_id):
    """
    Central logic to verify if a user has access to a course's lessons or live classes.
    Returns (bool, str, int) -> (success, message, status_code)
    """
    user = db.session.get(User, user_id)
    if not user:
        return False, "User not found", 404
        
    # 1. Global Restriction check (Super Admin Level)
    if user.is_globally_restricted:
        return False, "Your account has been restricted from all academic content by the Super Admin.", 403

    # 2. Executive Role check (Role-based Executive Access)
    # Based on user request: manager, director, admin, super admin
    executive_roles = ['manager', 'director', 'admin', 'super_admin', 'admin_staff']
    if user.role in executive_roles:
        return True, "Executive access granted by role.", 200

    # 3. Enrollment check
    enrollment = db.session.execute(
        db.select(Enrollment).filter_by(user_id=user_id, course_id=course_id)
    ).scalar_one_or_none()
    
    if not enrollment:
        return False, "You are not enrolled in this program.", 403

    # 4. Manual Overrides (Per-course)
    if enrollment.is_restricted:
        return False, "Access to this specific program has been restricted for your account.", 403
        
    if enrollment.is_executive:
        return True, "Executive access granted for this program.", 200

    # 5. Payment check
    course = db.session.get(Course, course_id)
    if not course:
        return False, "Course not found", 404

    # A course is free if price is 0 or None
    is_free = course.price is None or float(course.price) <= 0
    
    if not is_free and enrollment.payment_status != 'Paid':
        return False, "Payment required to access this training program.", 402

    return True, "Access granted.", 200
