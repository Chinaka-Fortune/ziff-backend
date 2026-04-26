from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.communication import SupportThread, SupportMessage
from app.models.user import User
from app.extensions import db
from app.services.notification_engine import notification_engine

governance_bp = Blueprint('governance', __name__)

# Map roles to hierarchy levels
ROLE_RANKS = {
    'student': -1,
    'customer': -1,
    'staff': 0,
    'team_lead': 0,
    'manager': 1,
    'admin': 1,
    'director': 2,
    'super_admin': 2,
    'admin_staff': 1
}

@governance_bp.route('/support/threads', methods=['POST'])
@jwt_required()
def create_support_thread():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    
    if not data or not data.get('subject') or not data.get('body') or not data.get('department'):
        return jsonify({'message': 'Subject, body, and department are required'}), 400
        
    new_thread = SupportThread(
        student_id=user_id,
        department=data['department'],
        subject=data['subject'],
        status='Open'
    )
    db.session.add(new_thread)
    db.session.flush() # Get thread ID
    
    first_msg = SupportMessage(
        thread_id=new_thread.id,
        sender_id=user_id,
        body=data['body']
    )
    db.session.add(first_msg)
    db.session.commit()
    
    # Notify department staff (Mock logic: Send to all with matching role)
    # real notification logic would fetch emails of everyone in that department
    
    return jsonify({'message': 'Support request submitted', 'thread': new_thread.to_dict()}), 201

@governance_bp.route('/support/threads', methods=['GET'])
@jwt_required()
def get_user_threads():
    user_id = int(get_jwt_identity())
    user = db.get_or_404(User, user_id)
    
    if user.role == 'student':
        # Student sees their own threads
        threads = db.session.execute(db.select(SupportThread).filter_by(student_id=user_id).order_by(SupportThread.created_at.desc())).scalars().all()
    else:
        # Staff see threads they have access to
        current_rank = ROLE_RANKS.get(user.role, 0)
        
        # Staff can see threads: 1) Unassigned 2) Assigned to them 
        # 3) Assigned to someone ELSE BUT with access_level <= their rank
        # 4) Their "original" threads once resolved
        
        query = db.select(SupportThread).filter(
            (SupportThread.access_level <= current_rank) | 
            (SupportThread.original_staff_id == user_id) & (SupportThread.status == 'Resolved')
        )
        
        # Additional hierarchical check: 
        # A 'staff' (rank 0) should NOT see threads assigned to a 'manager' (rank 1)
        # Even if it's in their department. 
        # So we filter out specific assignments to higher ranks.
        
        threads = db.session.execute(query.order_by(SupportThread.created_at.desc())).scalars().all()
        
        # Further manual filter to ensure hierarchy: 
        # if assigned_staff_id exists, check that staff's role rank.
        final_threads = []
        for t in threads:
            if t.assigned_staff_id:
                assignee = db.session.get(User, t.assigned_staff_id)
                if assignee and ROLE_RANKS.get(assignee.role, 0) > current_rank:
                    continue # Hide if assigned to higher rank
            final_threads.append(t)
        return jsonify([t.to_dict() for t in final_threads]), 200

    return jsonify([t.to_dict() for t in threads]), 200

@governance_bp.route('/support/threads/<int:thread_id>/reply', methods=['POST'])
@jwt_required()
def reply_to_thread(thread_id):
    user_id = int(get_jwt_identity())
    user = db.get_or_404(User, user_id)
    thread = db.get_or_404(SupportThread, thread_id)
    data = request.get_json()
    
    # Permission Check
    if user.role != 'student':
        current_rank = ROLE_RANKS.get(user.role, 0)
        if thread.access_level > current_rank:
            return jsonify({'message': 'Access denied: Escalated to higher management'}), 403
            
        # "Claim" logic: First staff to reply is assigned
        if not thread.assigned_staff_id:
            thread.assigned_staff_id = user_id
            thread.status = 'Staff Replied'
    
    new_msg = SupportMessage(
        thread_id=thread_id,
        sender_id=user_id,
        body=data['body']
    )
    db.session.add(new_msg)
    db.session.commit()
    
    # Notify student if staff replies
    if user.role != 'student':
        student = db.get_or_404(User, thread.student_id)
        if student.notify_email:
            notification_engine.send_email(
                student.email,
                f"New reply to your support request: {thread.subject}",
                f"Hi {student.name},\n\n Counseler {user.name} responded to your support request:\n\n{data['body']}\n\nView it on your dashboard."
            )
            
    return jsonify({'message': 'Reply sent', 'thread': thread.to_dict()}), 201

@governance_bp.route('/support/threads/<int:thread_id>/escalate', methods=['PATCH'])
@jwt_required()
def escalate_thread(thread_id):
    user_id = int(get_jwt_identity())
    user = db.get_or_404(User, user_id)
    thread = db.get_or_404(SupportThread, thread_id)
    
    if user.role == 'student':
        return jsonify({'message': 'Students cannot escalate threads'}), 403
        
    # Set original staff and increase access level
    thread.original_staff_id = user_id
    thread.assigned_staff_id = None # Clear assignment for managers to pick up
    thread.access_level = ROLE_RANKS.get(user.role, 0) + 1
    thread.status = 'Escalated'
    
    db.session.commit()
    return jsonify({'message': 'Thread escalated to management', 'thread': thread.to_dict()}), 200

@governance_bp.route('/support/threads/<int:thread_id>/resolve', methods=['PATCH'])
@jwt_required()
def resolve_thread(thread_id):
    user_id = int(get_jwt_identity())
    user = db.get_or_404(User, user_id)
    thread = db.get_or_404(SupportThread, thread_id)
    
    if user.role == 'student':
        return jsonify({'message': 'Action restricted to staff'}), 403
        
    thread.status = 'Resolved'
    db.session.commit()
    
    # Notify student
    student = db.get_or_404(User, thread.student_id)
    notification_engine.send_email(
        student.email,
        "Your Ziffcode support request has been resolved",
        f"Hi {student.name},\n\nWe've marked your support request '{thread.subject}' as resolved. Feel free to open a new ticket if you need more help!"
    )
    
    # Notify original staff if it was escalated
    if thread.original_staff_id:
        original = db.get_or_404(User, thread.original_staff_id)
        notification_engine.send_email(
            original.email,
            "An escalated thread has been resolved",
            f"Counseler {user.name} resolved the thread '{thread.subject}' that you escalated. You now have view-only access to see the resolution."
        )

    return jsonify({'message': 'Thread resolved', 'thread': thread.to_dict()}), 200
