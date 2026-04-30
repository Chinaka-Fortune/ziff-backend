from flask import Blueprint, jsonify, request
from app.extensions import db
from flask_jwt_extended import jwt_required, get_jwt_identity
import jwt
import os
import time
import uuid

from app.models.user import User
from app.models.meeting import Meeting, MeetingParticipant

meetings_bp = Blueprint('meetings', __name__)

JITSI_APP_ID = os.environ.get('JITSI_APP_ID', 'vpaas-magic-cookie-example')
JITSI_API_KEY = os.environ.get('JITSI_API_KEY', 'default_secret')

ROLE_HIERARCHY = {
    'super_admin': 100,
    'director': 90,
    'manager': 80,
    'team_lead': 70,
    'admin_staff': 60,
    'staff': 50,
    'student': 10,
    'customer': 10
}

@meetings_bp.route('/', methods=['POST'])
@jwt_required()
def create_meeting():
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    
    if not user or ROLE_HIERARCHY.get(user.role, 0) < 50:
        return jsonify({'message': 'Unauthorized. Only staff and managerial members can create meetings.'}), 403

    data = request.get_json()
    title = data.get('title', f"{user.name}'s Meeting")
    
    room_name = str(uuid.uuid4())
    
    meeting = Meeting(
        room_name=room_name,
        title=title,
        creator_id=user.id
    )
    db.session.add(meeting)
    db.session.commit()
    
    return jsonify({'message': 'Meeting created', 'meeting': meeting.to_dict()}), 201

@meetings_bp.route('/my_meetings', methods=['GET'])
@jwt_required()
def get_my_meetings():
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Fetch meetings created by this user
    created_meetings = Meeting.query.filter_by(creator_id=user.id, status='active').all()
    created_list = [m.to_dict() for m in created_meetings]

    # Fetch meetings user was invited to
    invitations = MeetingParticipant.query.filter_by(user_id=user.id).all()
    invited_list = [inv.meeting.to_dict() for inv in invitations if inv.meeting.status == 'active']

    # Also fetch meetings where the creator is LOWER in rank than the current user
    # Because higher-ranked staff can ALWAYS join.
    user_rank = ROLE_HIERARCHY.get(user.role, 0)
    hierarchical_list = []
    
    if user_rank >= 50:
        all_active = Meeting.query.filter_by(status='active').all()
        for m in all_active:
            if m.creator_id != user.id:
                creator = db.session.get(User, m.creator_id)
                if creator and ROLE_HIERARCHY.get(creator.role, 0) < user_rank:
                    # Avoid duplicates if they were explicitly invited
                    if not any(x['id'] == m.id for x in invited_list):
                        hierarchical_list.append(m.to_dict())

    return jsonify({
        'created_meetings': created_list,
        'invited_meetings': invited_list,
        'hierarchical_meetings': hierarchical_list
    }), 200

@meetings_bp.route('/<int:meeting_id>/invite', methods=['POST'])
@jwt_required()
def invite_user(meeting_id):
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    
    meeting = db.session.get(Meeting, meeting_id)
    if not meeting:
        return jsonify({'message': 'Meeting not found'}), 404
        
    if meeting.creator_id != user.id and ROLE_HIERARCHY.get(user.role, 0) < 80:
        return jsonify({'message': 'Only the creator or high-level managers can invite users to this meeting.'}), 403

    data = request.get_json()
    email_to_invite = data.get('email')
    
    user_to_invite = User.query.filter_by(email=email_to_invite).first()
    if not user_to_invite:
        return jsonify({'message': 'User not found with that email address.'}), 404
        
    existing = MeetingParticipant.query.filter_by(meeting_id=meeting.id, user_id=user_to_invite.id).first()
    if existing:
        return jsonify({'message': 'User is already invited.'}), 400
        
    participant = MeetingParticipant(meeting_id=meeting.id, user_id=user_to_invite.id)
    db.session.add(participant)
    db.session.commit()
    
    return jsonify({'message': f'Successfully invited {user_to_invite.name}', 'participant': participant.to_dict()}), 200

@meetings_bp.route('/join/<string:room_name>', methods=['GET'])
@jwt_required()
def authorize_join(room_name):
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    
    if not user:
        return jsonify({'authorized': False, 'message': 'User not found'}), 404
        
    if room_name == 'ziffcode-global':
        if ROLE_HIERARCHY.get(user.role, 0) >= 50:
            return jsonify({'authorized': True, 'message': 'Global room access granted.'}), 200
        return jsonify({'authorized': False, 'message': 'Only staff can access the global room.'}), 403

    meeting = Meeting.query.filter_by(room_name=room_name).first()
    if not meeting:
        return jsonify({'authorized': False, 'message': 'Meeting not found or has ended.'}), 404
        
    if meeting.status != 'active':
        return jsonify({'authorized': False, 'message': 'This meeting has ended.'}), 403

    authorized = False
    if meeting.creator_id == user.id:
        authorized = True
    else:
        creator = db.session.get(User, meeting.creator_id)
        if creator and ROLE_HIERARCHY.get(user.role, 0) > ROLE_HIERARCHY.get(creator.role, 0):
            authorized = True
        else:
            is_invited = MeetingParticipant.query.filter_by(meeting_id=meeting.id, user_id=user.id).first()
            if is_invited:
                authorized = True
                
    if not authorized:
        return jsonify({'authorized': False, 'message': 'You do not have permission to join this meeting.'}), 403

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
        "sub": "*",
        "room": room_name,
        "nbf": int(time.time()),
        "exp": int(time.time() + 7200)
    }

    token = jwt.encode(payload, JITSI_API_KEY, algorithm='HS256')
    
    return jsonify({
        'authorized': True,
        'meeting': meeting.to_dict(),
        'token': token,
        'app_id': JITSI_APP_ID
    }), 200
