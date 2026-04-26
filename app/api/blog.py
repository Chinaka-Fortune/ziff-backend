from flask import Blueprint, jsonify, request
from app.models.blog import Post
from app.extensions import db
from app.utils.decorators import admin_required
import re

blog_bp = Blueprint('blog', __name__)

def slugify(text):
    return re.sub(r'[\W_]+', '-', text.lower()).strip('-')

@blog_bp.route('/', methods=['GET'])
def get_posts():
    posts = db.session.scalars(db.select(Post).order_by(Post.created_at.desc())).all()
    return jsonify([post.to_dict() for post in posts]), 200

@blog_bp.route('/<slug>', methods=['GET'])
def get_post(slug):
    post = db.session.execute(db.select(Post).filter_by(slug=slug)).scalar_one_or_none()
    if not post:
        return jsonify({'message': 'Post not found'}), 404
    return jsonify(post.to_dict()), 200

@blog_bp.route('/', methods=['POST'])
@admin_required()
def create_post():
    data = request.get_json()
    if not data or not data.get('title') or not data.get('content'):
        return jsonify({'message': 'Title and content required'}), 400

    new_post = Post(
        title=data['title'],
        slug=slugify(data['title']),
        content=data['content'],
        featured_image=data.get('featured_image')
    )
    db.session.add(new_post)
    db.session.commit()
    return jsonify({'message': 'Post created', 'post': new_post.to_dict()}), 201

@blog_bp.route('/<slug>', methods=['PUT'])
@admin_required()
def update_post(slug):
    post = db.session.execute(db.select(Post).filter_by(slug=slug)).scalar_one_or_none()
    if not post:
        return jsonify({'message': 'Post not found'}), 404
        
    data = request.get_json()
    if 'title' in data:
        post.title = data['title']
        post.slug = slugify(data['title'])
    if 'content' in data:
        post.content = data['content']
    if 'featured_image' in data:
        post.featured_image = data['featured_image']

    db.session.commit()
    return jsonify({'message': 'Post updated', 'post': post.to_dict()}), 200

@blog_bp.route('/<slug>', methods=['DELETE'])
@admin_required()
def delete_post(slug):
    post = db.session.execute(db.select(Post).filter_by(slug=slug)).scalar_one_or_none()
    if not post:
        return jsonify({'message': 'Post not found'}), 404
        
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Post deleted'}), 200
