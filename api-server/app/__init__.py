"""
Rizz API Server - Application Factory
Enterprise-grade Flask application with proper initialization
"""

from flask import Flask, jsonify
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from prometheus_client import make_wsgi_app, Counter, Histogram, generate_latest
from werkzeug.middleware.dispatcher import DispatcherMiddleware
import logging
import json

from .config import config
from .models import db, User, Role, Post
from .routes import auth_bp, posts_bp


# Metrics for monitoring
REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'HTTP request latency', ['method', 'endpoint'])


def create_app(config_name=None):
    """Application factory"""
    if config_name is None:
        config_name = 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Setup logging
    setup_logging(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        create_default_roles()
        create_admin_user()
    
    # Register error handlers
    register_error_handlers(app)
    
    # Health check endpoint
    @app.route('/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'healthy',
            'service': 'rizz-api',
            'version': '2.0.0'
        })
    
    # Metrics endpoint
    @app.route('/metrics', methods=['GET'])
    def metrics():
        return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    # API info endpoint
    @app.route('/api', methods=['GET'])
    def api_info():
        return jsonify({
            'name': 'Rizz API',
            'version': '2.0.0',
            'author': 'username9999',
            'description': 'Enterprise-grade REST API with authentication',
            'endpoints': {
                'auth': {
                    'POST /api/auth/register': 'Register new user',
                    'POST /api/auth/login': 'Login user',
                    'POST /api/auth/refresh': 'Refresh access token',
                    'POST /api/auth/logout': 'Logout user',
                    'POST /api/auth/logout-all': 'Logout from all devices',
                    'GET /api/auth/me': 'Get current user info',
                    'PUT /api/auth/me': 'Update current user profile'
                },
                'posts': {
                    'GET /api/posts': 'Get all posts (with pagination & filtering)',
                    'GET /api/posts/<id>': 'Get single post by ID',
                    'GET /api/posts/slug/<slug>': 'Get single post by slug',
                    'POST /api/posts': 'Create new post (auth required)',
                    'PUT /api/posts/<id>': 'Update post (auth required)',
                    'DELETE /api/posts/<id>': 'Delete post (auth required)',
                    'POST /api/posts/<id>/like': 'Like a post (auth required)',
                    'POST /api/posts/<id>/comments': 'Add comment to post (auth required)'
                },
                'system': {
                    'GET /health': 'Health check',
                    'GET /metrics': 'Prometheus metrics'
                }
            },
            'documentation': 'https://github.com/username9999-sys/Rizz'
        })
    
    return app


def init_extensions(app):
    """Initialize Flask extensions"""
    # Database
    db.init_app(app)
    
    # CORS
    CORS(app, origins=app.config['CORS_ORIGINS'])
    
    # Rate limiting
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[app.config['RATELIMIT_DEFAULT']],
        storage_uri=app.config['RATELIMIT_STORAGE_URL']
    )
    
    # Store limiter for use in routes
    app.extensions['limiter'] = limiter


def register_blueprints(app):
    """Register Flask blueprints"""
    app.register_blueprint(auth_bp)
    app.register_blueprint(posts_bp)


def setup_logging(app):
    """Setup application logging"""
    log_level = getattr(logging, app.config['LOG_LEVEL'])
    
    # Create formatter
    formatter = logging.Formatter(app.config['LOG_FORMAT'])
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    
    # File handler (in production)
    if app.config['FLASK_ENV'] == 'production':
        file_handler = logging.FileHandler('/var/log/rizz-api/api.log')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        app.logger.addHandler(file_handler)
    
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)


def create_default_roles():
    """Create default roles if they don't exist"""
    roles = [
        {'name': 'admin', 'description': 'Administrator with full access', 
         'permissions': ['all']},
        {'name': 'user', 'description': 'Regular user', 
         'permissions': ['read:posts', 'create:posts', 'edit:own_posts', 'delete:own_posts', 'create:comments']},
        {'name': 'moderator', 'description': 'Moderator with content management', 
         'permissions': ['read:posts', 'create:posts', 'edit:any_posts', 'delete:any_posts', 'moderate:comments']}
    ]
    
    for role_data in roles:
        role = Role.query.filter_by(name=role_data['name']).first()
        if not role:
            role = Role(
                name=role_data['name'],
                description=role_data['description'],
                permissions=role_data['permissions']
            )
            db.session.add(role)
    
    db.session.commit()


def create_admin_user():
    """Create default admin user if not exists"""
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@rizz.dev',
            is_active=True,
            is_verified=True
        )
        admin.set_password('admin123')
        
        # Assign admin role
        admin_role = Role.query.filter_by(name='admin').first()
        if admin_role:
            admin.roles.append(admin_role)
        
        db.session.add(admin)
        db.session.commit()


def register_error_handlers(app):
    """Register error handlers"""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({'error': 'Bad request', 'code': 'BAD_REQUEST'}), 400
    
    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({'error': 'Unauthorized', 'code': 'UNAUTHORIZED'}), 401
    
    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({'error': 'Forbidden', 'code': 'FORBIDDEN'}), 403
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Not found', 'code': 'NOT_FOUND'}), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({'error': 'Method not allowed', 'code': 'METHOD_NOT_ALLOWED'}), 405
    
    @app.errorhandler(429)
    def rate_limit_exceeded(error):
        return jsonify({'error': 'Rate limit exceeded', 'code': 'RATE_LIMITED'}), 429
    
    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Internal error: {error}')
        return jsonify({'error': 'Internal server error', 'code': 'INTERNAL_ERROR'}), 500
    
    @app.errorhandler(503)
    def service_unavailable(error):
        return jsonify({'error': 'Service unavailable', 'code': 'SERVICE_UNAVAILABLE'}), 503
