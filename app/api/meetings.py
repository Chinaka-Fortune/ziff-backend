from flask import Blueprint, jsonify, request
from app.models.live_class import LiveClass
from app.models.enrollment import Enrollment
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.utils.access_control import check_course_access
import jwt
import os
import time

meetings_bp = Blueprint('meetings', __name__)

JITSI_APP_ID = os.environ.get('JITSI_APP_ID', 'vpaas-magic-cookie-example')
JITSI_API_KEY = os.environ.get('JITSI_API_KEY', 'default_secret')

@meetings_bp.route('/<room_name>/token', methods=['GET'])
@jwt_required()
def generate_jitsi_token(room_name):
    # Retrieve user and meeting logic
    user_id = int(get_jwt_identity())
    
    live_class = db.session.execute(db.select(LiveClass).filter_by(room_name=room_name)).scalar_one_or_none()
    if not live_class:
        return jsonify({'message': 'Meeting room not found'}), 404
        
    # Check enrollment and payment access centrally
    success, message, status_code = check_course_access(user_id, live_class.course_id)
    
    if not success:
        return jsonify({'message': message}), status_code

    from app.models.user import User
    user = db.session.get(User, user_id)

    # Generate JWT for Jitsi Meet secure access
    payload = {
        "context": {
            "user": {
                "id": str(user.id),
                "name": user.name,
                "email": user.email
            }
        },
        "aud": "jitsi",
        "iss": JITSI_APP_ID,
        "sub": "*", # tenant
        "room": room_name,
        "nbf": int(time.time()),
        "exp": int(time.time() + 7200) # Valid for 2 hours
    }

    token = jwt.encode(payload, JITSI_API_KEY, algorithm='HS256')
    
    return jsonify({
        'token': token,
        'room': room_name,
        'app_id': JITSI_APP_ID
    }), 200
