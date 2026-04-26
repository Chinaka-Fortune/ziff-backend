from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.models.communication import HubPost, HubComment
from app.models.user import User
from app.extensions import db
from app.services.notification_engine import notification_engine

interaction_bp = Blueprint('interaction', __name__)

@interaction_bp.route('/hub/posts', methods=['GET'])
def get_hub_posts():
    # Guests can see public posts, students/staff see all they have access to
    is_public_only = request.args.get('public_only', 'false').lower() == 'true'
    
    query = db.select(HubPost)
    if is_public_only:
        query = query.filter_by(is_public=True)
        
    posts = db.session.execute(query.order_by(HubPost.created_at.desc())).scalars().all()
    return jsonify([p.to_dict() for p in posts]), 200

@interaction_bp.route('/hub/posts', methods=['POST'])
@jwt_required()
def create_hub_post():
    user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or not data.get('title') or not data.get('content'):
        return jsonify({'message': 'Title and content are required'}), 400
        
    new_post = HubPost(
        author_id=user_id,
        title=data['title'],
        content=data['content'],
        category=data.get('category', 'Discussion'),
        is_public=data.get('is_public', False)
    )
    db.session.add(new_post)
    db.session.commit()
    
    return jsonify({'message': 'Post created', 'post': new_post.to_dict()}), 201

@interaction_bp.route('/hub/posts/<int:post_id>/comments', methods=['GET'])
def get_post_comments(post_id):
    post = db.get_or_404(HubPost, post_id)
    comments = post.comments.order_by(HubPost.created_at.asc()).all()
    return jsonify([c.to_dict() for c in comments]), 200

@interaction_bp.route('/hub/posts/<int:post_id>/comments', methods=['POST'])
@jwt_required()
def add_hub_comment(post_id):
    user_id = get_jwt_identity()
    user = db.get_or_404(User, user_id)
    post = db.get_or_404(HubPost, post_id)
    data = request.get_json()
    
    if not data or not data.get('content'):
        return jsonify({'message': 'Content is required'}), 400
        
    new_comment = HubComment(
        post_id=post_id,
        author_id=user_id,
        content=data['content']
    )
    db.session.add(new_comment)
    db.session.commit()
    
    # Notify post author if it's not their own comment
    if post.author_id != user_id:
        author = db.get_or_404(User, post.author_id)
        if author.notify_email:
            notification_engine.send_email(
                author.email,
                f"New comment on your Ziffcode Hub post",
                f"Hi {author.name},\n\n{user.name} just commented on your post '{post.title}':\n\n{data['content']}\n\nKeep the conversation going!"
            )

    return jsonify({'message': 'Comment added', 'comment': new_comment.to_dict()}), 201
