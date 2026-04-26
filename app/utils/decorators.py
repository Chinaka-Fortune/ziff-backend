from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models.user import User
from app.extensions import db

def admin_required():
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            user_id = int(get_jwt_identity())
            user = db.session.get(User, user_id)
            if not user or user.role not in ['admin', 'super_admin']:
                return jsonify(message="Admins only!"), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper

def requires_roles(*allowed_roles):
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            verify_jwt_in_request()
            user_id = int(get_jwt_identity())
            user = db.session.get(User, user_id)
            if not user or user.role not in allowed_roles:
                return jsonify(message="Access forbidden: insufficient role!"), 403
            return fn(*args, **kwargs)
        return decorator
    return wrapper
