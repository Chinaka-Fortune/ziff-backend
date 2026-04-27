from flask import Flask, send_from_directory
import os
from app.config import config
from app.extensions import db, migrate, jwt, cors

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app)

    # Register blueprints
    from app.api.auth import auth_bp
    from app.api.courses import courses_bp
    from app.api.enrollments import enrollments_bp
    from app.api.admin import admin_bp
    from app.api.blog import blog_bp
    from app.api.contact import contact_bp
    from app.api.payments import payments_bp
    from app.api.meetings import meetings_bp
    from app.api.ai import ai_bp
    from app.api.notes import notes_bp
    from app.api.projects import projects_bp
    from app.api.interaction_api import interaction_bp
    from app.api.governance_api import governance_bp
    from app.api.admin_access import admin_access_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(courses_bp, url_prefix='/api/courses')
    app.register_blueprint(enrollments_bp, url_prefix='/api/enrollments')
    app.register_blueprint(admin_bp, url_prefix='/api/admin')
    app.register_blueprint(blog_bp, url_prefix='/api/blog')
    app.register_blueprint(contact_bp, url_prefix='/api/contact')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    app.register_blueprint(meetings_bp, url_prefix='/api/meetings')
    app.register_blueprint(ai_bp, url_prefix='/api/ai')
    app.register_blueprint(notes_bp, url_prefix='/api/notes')
    app.register_blueprint(projects_bp, url_prefix='/api/projects')
    app.register_blueprint(interaction_bp, url_prefix='/api/interaction')
    app.register_blueprint(governance_bp, url_prefix='/api/governance')
    app.register_blueprint(admin_access_bp, url_prefix='/api/admin-access')

    # Ensure the upload directory exists (handle read-only filesystem on Vercel)
    try:
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
            os.makedirs(os.path.join(app.config['UPLOAD_FOLDER'], 'profile_pics'), exist_ok=True)
    except OSError:
        pass # Vercel read-only filesystem

    # Route to serve uploaded files
    @app.route('/uploads/<path:filename>')
    def uploaded_file(filename):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

    # Simple health check route
    @app.route('/health')
    def health_check():
        return {'status': 'ok', 'message': 'Ziffcode API is running'}

    return app
