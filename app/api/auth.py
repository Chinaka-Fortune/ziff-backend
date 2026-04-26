from flask import Blueprint, request, jsonify, current_app
from app.models.user import User
from app.models.enrollment import Enrollment
from app.extensions import db
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import secrets
from datetime import datetime, timezone, timedelta
import os
from werkzeug.utils import secure_filename

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    if not data or not data.get('email'):
        return jsonify({'message': 'Email is required'}), 400

    user = db.session.execute(db.select(User).filter_by(email=data['email'])).scalar_one_or_none()
    
    if not user:
        return jsonify({'message': f"No account found with the email {data['email']}"}), 404

    success_msg = {'message': f"A reset link has been successfully sent to {data['email']}"}

    token = secrets.token_urlsafe(32)
    user.reset_token = token
    user.reset_token_expiry = datetime.now(timezone.utc) + timedelta(hours=1)
    db.session.commit()

    # SIMULATION: Log reset link
    reset_link = f"http://localhost:3000/reset-password?token={token}"
    with open('backend.log', 'a') as f:
        f.write(f"\n[{datetime.now()}] PASSWORD RESET LINK: {reset_link}\n")

    return jsonify(success_msg), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    token = data.get('token')
    email = data.get('email')
    new_password = data.get('password')

    if not token or not new_password or not email:
        return jsonify({'message': 'Missing token, email, or password'}), 400

    user = db.session.execute(
        db.select(User).filter(
            User.reset_token == token,
            User.email == email,
            User.reset_token_expiry > datetime.now(timezone.utc)
        )
    ).scalar_one_or_none()

    if not user:
        return jsonify({'message': 'Invalid or expired token'}), 400

    user.set_password(new_password)
    user.reset_token = None
    user.reset_token_expiry = None
    db.session.commit()

    return jsonify({'message': 'Password reset successfully'}), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password') or not data.get('name'):
        return jsonify({'message': 'Missing required fields'}), 400

    existing_user = db.session.execute(db.select(User).filter_by(email=data['email'])).scalar_one_or_none()
    if existing_user:
        return jsonify({'message': 'Email already registered'}), 400

    new_user = User(
        email=data['email'],
        name=data['name'],
        role=data.get('role', 'student') 
    )
    new_user.set_password(data['password'])

    db.session.add(new_user)
    db.session.flush() # Ensure new_user.id is available

    # Linking the student to the desired program/course
    course_id = data.get('course_id')
    if course_id:
        enrollment = Enrollment(
            user_id=new_user.id,
            course_id=int(course_id),
            status='Registered',
            payment_status='Pending'
        )
        db.session.add(enrollment)

    db.session.commit()

    return jsonify({'message': 'User registered successfully', 'user': new_user.to_dict()}), 201

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'message': 'Missing email or password'}), 400

    user = db.session.execute(db.select(User).filter_by(email=data['email'])).scalar_one_or_none()
    if not user or not user.check_password(data['password']):
        return jsonify({'message': 'Invalid credentials'}), 401

    access_token = create_access_token(identity=str(user.id), expires_delta=timedelta(days=1))
    return jsonify({
        'message': 'Login successful',
        'access_token': access_token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/me', methods=['GET', 'PATCH'])
@jwt_required()
def me():
    current_user_id = int(get_jwt_identity())
    user = db.session.get(User, current_user_id)
    if not user:
        return jsonify({'message': 'User not found'}), 404
        
    if request.method == 'GET':
        # Provide default skills based on role if none exist yet
        if not user.skills:
            defaults = {
                'student': {'HTML/CSS': 80, 'JavaScript': 75, 'Python': 50, 'React': 65, 'Database': 40, 'DevOps': 30},
                'staff': {'Comms': 90, 'Support': 85, 'Resolution': 75, 'Efficiency': 80, 'Feedback': 70},
                'admin': {'SysHealth': 95, 'UserGrowth': 80, 'Security': 90, 'Quality': 85, 'Revenue': 70}
            }
            # Fallback for complex roles based on root keywords
            role_type = user.role.lower()
            if 'admin' in role_type or 'manager' in role_type:
                user.skills = defaults['admin']
            elif 'staff' in role_type or 'lead' in role_type:
                user.skills = defaults['staff']
            else:
                user.skills = defaults['student']
            db.session.commit()
            
        return jsonify(user.to_dict()), 200
        
    if request.method == 'PATCH':
        data = request.get_json()
        if 'name' in data: user.name = data['name']
        if 'bio' in data: user.bio = data['bio']
        if 'avatar_url' in data: user.avatar_url = data['avatar_url']
        if 'public_profile' in data: user.public_profile = data['public_profile']
        
        # Handle Socials
        if 'socials' in data:
            s = data['socials']
            user.linkedin_url = s.get('linkedin', user.linkedin_url)
            user.github_url = s.get('github', user.github_url)
            user.twitter_url = s.get('twitter', user.twitter_url)
            user.whatsapp_number = s.get('whatsapp', user.whatsapp_number)
            user.instagram_url = s.get('instagram', user.instagram_url)
            
        # Handle Notifications
        if 'notifications' in data:
            n = data['notifications']
            user.notify_email = n.get('email', user.notify_email)
            user.notify_whatsapp = n.get('whatsapp', user.notify_whatsapp)

        if 'email' in data:
            existing = db.session.execute(db.select(User).filter(User.email == data['email'], User.id != current_user_id)).scalar_one_or_none()
            if existing: return jsonify({'message': 'Email already in use'}), 400
            user.email = data['email']
            
        # Handle Skill Proficiency Updates
        if 'skills' in data:
            user.skills = data['skills']
            
        # Create Activity Log for context acknowledgment
        from app.models.activity_log import ActivityLog
        log = ActivityLog(
            user_id=user.id,
            activity_type='profile_updated',
            description=f"User {user.name} updated their professional profile and settings."
        )
        db.session.add(log)
        
        db.session.commit()
        return jsonify({'message': 'Profile updated', 'user': user.to_dict()}), 200

@auth_bp.route('/upload-avatar', methods=['POST'])
@jwt_required()
def upload_avatar():
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if file:
        filename = secure_filename(file.filename)
        # Add timestamp to filename to avoid duplicate conflicts
        filename = f"{int(datetime.now().timestamp())}_{filename}"
        
        save_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'profile_pics', filename)
        
        # Ensure directory exists again just in case
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        file.save(save_path)
        
        # Return the public URL
        # We return the path relative to the root so the frontend can prepend the API base if needed
        # Or better: return the path that our app route /uploads/<path:filename> handles
        avatar_url = f"/uploads/profile_pics/{filename}"
        
        return jsonify({'message': 'Upload successful', 'avatar_url': avatar_url}), 200

    return jsonify({'message': 'Upload failed'}), 400

@auth_bp.route('/public-portfolio/<int:user_id>', methods=['GET'])
def get_public_portfolio(user_id):
    user = db.session.get(User, user_id)
    if not user or not user.public_profile:
        return jsonify({'message': 'Portfolio not found or private', 'public_profile': False}), 404
        
    # Return ONLY job-relevant data as requested by the user
    # Exclude internal points, streaks, etc.
    return jsonify({
        'name': user.name,
        'bio': user.bio,
        'public_profile': user.public_profile,
        'socials': {
            'linkedin': user.linkedin_url,
            'github': user.github_url,
            'twitter': user.twitter_url,
            'instagram': user.instagram_url
        },
        'skills': user.to_dict().get('skills', {}), # Fallback if skills not yet aggregated
        'certificates': user.to_dict().get('certificates', []),
        'projects': [p.to_dict() for p in user.projects.filter_by(status='production_ready').all()]
    }), 200
