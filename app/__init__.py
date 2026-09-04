import os
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from app.config import config_by_name
from app.extensions import db, login_manager, migrate, csrf


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')

    app = Flask(__name__)
    app.config.from_object(config_by_name.get(config_name, config_by_name['default']))

    # Initialize Extensions
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    csrf.init_app(app)

    # Ensure upload and QR code directories exist
    upload_dir = Path(app.config['UPLOAD_FOLDER'])
    qr_dir = Path(app.config['QR_FOLDER'])
    upload_dir.mkdir(parents=True, exist_ok=True)
    qr_dir.mkdir(parents=True, exist_ok=True)

    # Register Blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.admin import admin_bp
    from app.blueprints.student import student_bp
    from app.blueprints.employer import employer_bp
    from app.blueprints.verify import verify_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(employer_bp)
    app.register_blueprint(verify_bp)

    # Context processors
    @app.context_processor
    def inject_global_context():
        return {
            'app_name': 'BlockCert',
            'now_year': 2025
        }

    # Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Forbidden: You do not have permission to access this resource.'}), 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Resource not found.'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.is_json or request.path.startswith('/api/'):
            return jsonify({'success': False, 'error': 'Internal server error.'}), 500
        return render_template('errors/500.html'), 500

    # Auto-create tables in development mode if not using alembic immediately
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            app.logger.warning(f"Could not automatically run db.create_all(): {e}")

    return app
