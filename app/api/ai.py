from flask import Blueprint, request, jsonify, Response
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.project import Project
from app.models.course_note import CourseNote
from app.models.activity_log import ActivityLog
from app.models.user import User
from app.models.enrollment import Enrollment
from app.extensions import db
from openai import OpenAI
import os
import json
from datetime import datetime

ai_bp = Blueprint('ai', __name__)

def log_ai_error(error_type, message):
    """Telemetry redirected to console for cloud compatibility"""
    print(f"ZIFFIE AI SYNC ERROR [{error_type}]: {message}")

@ai_bp.route('/ask', methods=['POST'])
@jwt_required()
def ask_ziffie():
    data = request.get_json()
    if not data or not data.get('prompt'):
        return jsonify({'message': 'A prompt is required'}), 400
        
    user_id = get_jwt_identity()
    user_prompt = data['prompt']
    
    # --- Context Restoration Layer ---
    # Fetch data while the request context is active
    try:
        uid = int(user_id) if str(user_id).isdigit() else user_id
        # 1. Fetch Core User Identity
        user = db.session.get(User, uid)
        user_role = user.role if user else "student"
        is_restricted = user.is_globally_restricted if user else False
        
        # 2. Fetch Personal Context
        user_projects = db.session.execute(db.select(Project).filter_by(user_id=uid)).scalars().all()
        user_notes = db.session.execute(db.select(CourseNote).filter_by(user_id=uid)).scalars().all()
        user_logs = db.session.execute(db.select(ActivityLog).filter_by(user_id=uid).order_by(ActivityLog.timestamp.desc()).limit(10)).scalars().all()
        user_enrollments = db.session.execute(db.select(Enrollment).filter_by(user_id=uid)).scalars().all()
        
        projects_ctx = "\n".join([f"- {p.title} (Status: {p.status})" for p in user_projects])
        notes_ctx = "\n".join([f"- {n.content[:100]}..." for n in user_notes])
        logs_ctx = "\n".join([f"- {l.description} (+{l.points_earned} pts)" for l in user_logs])
        
        enrollments_ctx = "\n".join([
            f"- {enr.course.title} | Status: {enr.payment_status} | Enrollment Status: {enr.status} | "
            f"Override Table: [Executive: {enr.is_executive}, Restricted: {enr.is_restricted}]"
            for enr in user_enrollments if enr.course
        ])
        
        print(f"Ziffie: Intelligence sync for {user.name} ({user_role})")
    except Exception as e:
        log_ai_error("ContextSyncError", str(e))
        return jsonify({'message': 'Synchronization failure while fetching context.'}), 500
    # --------------------------------

    def generate():
        try:
            # 1. Fresh Client Initialization
            print(f"Ziffie: Synchronization pulse initiated for user {user_id}")
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                yield f"data: {json.dumps({'error': 'Intelligence credentials missing from environment.'})}\n\n"
                return

            client = OpenAI(api_key=api_key)

            system_prompt = f"""
            You are Ziffie, the Lead Technical Mentor and Platform Expert at Ziffcode Technologies Limited. 
            Mission: "Coding today, Empowering tomorrow."
            Expertise: Fullstack Development, architectural design, and empowerment.

            ZIFFCODE PLATFORM GOVERNANCE:
            - Access Rule: Registration -> Payment -> Automated Access.
            - Executive Roles: manager, director, admin, super_admin, admin_staff (Bypass all restrictions).
            - Student Restrictions: Can be globally restricted (all access blocked) or per-course restricted by an admin.
            - Executive Overrides: Admins can toggle 'is_executive' per enrollment to bypass payment requirements.

            CURRENT USER STANDING:
            Name: {user.name}
            Role: {user_role}
            Global Platform Status: {'RESTRICTED' if is_restricted else 'ACTIVE'}
            
            USER ENROLLMENTS & PAYMENT STATUS:
            {enrollments_ctx if enrollments_ctx else "No current enrollments."}

            STUDENT PORTFOLIO DATA:
            Projects: {projects_ctx if projects_ctx else "None."}
            Recent Notes: {notes_ctx if notes_ctx else "None."}
            Recent Achievements: {logs_ctx if logs_ctx else "None."}

            INSTRUCTIONS:
            - Role-Based Advice: If the user is a Student, encourage payment for pending courses. If Admin, remind them they can manage restrictions.
            - Access Guidance: If a student asks about blocked lessons, check their ENROLLMENT and PAYMENT STATUS provided above and advice accordingly.
            - Motivation: Celebrate points earned and projects built.
            - Style: Professional, concise, tech-aligned (tactical elite aesthetic). Use Markdown.
            """

            # 2. Streamed Completion Transmission
            stream = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=800,
                stream=True
            )

            for chunk in stream:
                if chunk.choices[0].delta.content:
                    payload = {
                        "chunk": chunk.choices[0].delta.content,
                        "sender": "Ziffie AI"
                    }
                    yield f"data: {json.dumps(payload)}\n\n"

        except Exception as e:
            log_ai_error(type(e), str(e))
            print(f"Ziff-Critical Streaming Error: {e}")
            error_payload = {
                "error": True,
                "reply": "I'm experiencing a momentary synchronization bottleneck with the Ziff-Mainframe. Please use the Tactical Retry button."
            }
            yield f"data: {json.dumps(error_payload)}\n\n"

    return Response(generate(), mimetype='text/event-stream')
