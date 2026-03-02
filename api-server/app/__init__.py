"""
Rizz API Server - Application Factory
Enterprise-grade Flask application with comprehensive features
Enhanced with: Caching, Rate Limiting, Tracing, Versioning, API Documentation
"""

from flask import Flask, jsonify, request, g
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_migrate import Migrate
from prometheus_client import make_wsgi_app, Counter, Histogram, generate_latest
from werkzeug.middleware.dispatcher import DispatcherMiddleware
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
import logging
import json
import time
from datetime import datetime
from functools import wraps

from .config import config
from .models import db, User, Role, Post, AuditLog
from .routes import auth_bp, posts_bp
from .utils.audit import log_action

# ===== Metrics for Monitoring =====
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status', 'service']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint', 'service'],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)
)

REQUEST_IN_PROGRESS = Gauge(
    'http_requests_in_progress',
    'HTTP requests in progress',
    ['method', 'endpoint', 'service']
)

# ===== OpenTelemetry Tracing =====
def setup_tracing(app):
    """Setup distributed tracing with Jaeger"""
    tracer_provider = TracerProvider()
    trace.set_tracer_provider(tracer_provider)
    
    jaeger_exporter = JaegerExporter(
        agent_host_name='jaeger',
        agent_port=6831,
    )
    
    span_processor = BatchSpanProcessor(jaeger_exporter)
    tracer_provider.add_span_processor(span_processor)
    
    FlaskInstrumentor().instrument_app(app)
    
    return trace.get_tracer(__name__)


# ===== Request Timing & Monitoring =====
@app.before_request
def before_request():
    """Track request timing and metrics"""
    g.start_time = time.time()
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    
    # Track in-progress requests
    endpoint = request.endpoint or 'unknown'
    REQUEST_IN_PROGRESS.labels(
        method=request.method,
        endpoint=endpoint,
        service='api'
    ).inc()


@app.after_request
def after_request(response):
    """Log request and update metrics"""
    if hasattr(g, 'start_time'):
        elapsed = time.time() - g.start_time
        endpoint = request.endpoint or 'unknown'
        status = response.status_code
        
        # Update metrics
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=endpoint,
            status=status,
            service='api'
        ).inc()
        
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=endpoint,
            service='api'
        ).observe(elapsed)
        
        REQUEST_IN_PROGRESS.labels(
            method=request.method,
            endpoint=endpoint,
            service='api'
        ).dec()
        
        # Add headers
        response.headers['X-Request-ID'] = g.request_id
        response.headers['X-Response-Time'] = f'{elapsed*1000:.2f}ms'
        
        # Log request
        app.logger.info(f'{request.method} {request.path} {status} {elapsed*1000:.2f}ms')
    
    return response


def create_app(config_name=None):
    """Application factory with enhanced features"""
    if config_name is None:
        config_name = 'default'
    
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    init_extensions(app)
    
    # Setup tracing
    if app.config.get('ENABLE_TRACING', False):
        setup_tracing(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Setup logging
    setup_logging(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Create database tables
    with app.app_context():
        db.create_all()
        create_default_roles()
        create_admin_user()
        run_startup_checks(app)
    
    # ===== Health & Status Endpoints =====
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Enhanced health check with dependency status"""
        health_status = {
            'status': 'healthy',
            'service': 'rizz-api',
            'version': '2.0.0',
            'timestamp': datetime.utcnow().isoformat(),
            'uptime': time.time() - app.config.get('START_TIME', time.time()),
            'checks': {}
        }
        
        # Check database
        try:
            db.session.execute('SELECT 1')
            health_status['checks']['database'] = 'healthy'
        except Exception as e:
            health_status['checks']['database'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Check Redis
        try:
            redis_client = app.extensions.get('redis')
            if redis_client:
                redis_client.ping()
                health_status['checks']['redis'] = 'healthy'
        except Exception as e:
            health_status['checks']['redis'] = f'unhealthy: {str(e)}'
            health_status['status'] = 'degraded'
        
        # Check Elasticsearch
        try:
            es_client = app.extensions.get('elasticsearch')
            if es_client:
                es_client.cluster.health()
                health_status['checks']['elasticsearch'] = 'healthy'
        except Exception as e:
            health_status['checks']['elasticsearch'] = f'unhealthy: {str(e)}'
        
        status_code = 200 if health_status['status'] == 'healthy' else 503
        return jsonify(health_status), status_code
    
    @app.route('/ready', methods=['GET'])
    def readiness_check():
        """Kubernetes readiness probe"""
        try:
            db.session.execute('SELECT 1')
            return jsonify({'status': 'ready'}), 200
        except Exception as e:
            return jsonify({'status': 'not ready', 'error': str(e)}), 503
    
    @app.route('/live', methods=['GET'])
    def liveness_check():
        """Kubernetes liveness probe"""
        return jsonify({'status': 'alive'}), 200
    
    @app.route('/metrics', methods=['GET'])
    def metrics():
        """Prometheus metrics endpoint"""
        return generate_latest(), 200, {'Content-Type': 'text/plain; charset=utf-8'}
    
    @app.route('/api/v2', methods=['GET'])
    def api_info_v2():
        """Enhanced API info with versioning"""
        return jsonify({
            'name': 'Rizz API',
            'version': '2.0.0',
            'api_version': 'v2',
            'author': 'username9999',
            'description': 'Enterprise-grade REST API with comprehensive features',
            'features': [
                'JWT Authentication with refresh tokens',
                'Role-Based Access Control (RBAC)',
                'Rate Limiting',
                'Request Tracing',
                'Prometheus Metrics',
                'Audit Logging',
                'API Versioning',
                'Health Checks',
                'Distributed Tracing'
            ],
            'endpoints': {
                'auth': {
                    'POST /api/v2/auth/register': 'Register new user',
                    'POST /api/v2/auth/login': 'Login user',
                    'POST /api/v2/auth/refresh': 'Refresh access token',
                    'POST /api/v2/auth/logout': 'Logout user',
                    'POST /api/v2/auth/logout-all': 'Logout from all devices',
                    'GET /api/v2/auth/me': 'Get current user info',
                    'PUT /api/v2/auth/me': 'Update current user profile'
                },
                'posts': {
                    'GET /api/v2/posts': 'List posts (paginated, filtered)',
                    'GET /api/v2/posts/<id>': 'Get single post',
                    'GET /api/v2/posts/slug/<slug>': 'Get post by slug',
                    'POST /api/v2/posts': 'Create new post',
                    'PUT /api/v2/posts/<id>': 'Update post',
                    'DELETE /api/v2/posts/<id>': 'Delete post',
                    'POST /api/v2/posts/<id>/like': 'Like post',
                    'POST /api/v2/posts/<id>/comments': 'Add comment'
                },
                'system': {
                    'GET /health': 'Health check with dependency status',
                    'GET /ready': 'Readiness probe',
                    'GET /live': 'Liveness probe',
                    'GET /metrics': 'Prometheus metrics',
                    'GET /api/v2': 'This API info'
                }
            },
            'documentation': 'https://github.com/username9999-sys/Rizz',
            'support': 'contact@rizz.dev'
        })
    
    @app.route('/api/v2/stats', methods=['GET'])
    @token_required
    def get_platform_stats():
        """Get platform statistics"""
        stats = {
            'users': User.query.count(),
            'posts': Post.query.count(),
            'active_users': User.query.filter_by(is_active=True).count(),
            'verified_users': User.query.filter_by(is_verified=True).count(),
            'posts_today': Post.query.filter(
                Post.created_at >= datetime.utcnow().date()
            ).count(),
            'posts_this_week': Post.query.filter(
                Post.created_at >= datetime.utcnow() - timedelta(days=7)
            ).count(),
        }
        
        # Get audit log count
        stats['audit_logs'] = AuditLog.query.count()
        
        return jsonify({
            'statistics': stats,
            'timestamp': datetime.utcnow().isoformat()
        })
    
    # Store startup time
    app.config['START_TIME'] = time.time()
    
    return app


def init_extensions(app):
    """Initialize Flask extensions with enhanced configuration"""
    # Database
    db.init_app(app)
    migrate = Migrate(app, db)
    
    # CORS
    CORS(app, 
         origins=app.config.get('CORS_ORIGINS', '*'),
         supports_credentials=True,
         allow_headers=['Content-Type', 'Authorization', 'X-Request-ID'],
         methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'])
    
    # Rate Limiting
    limiter = Limiter(
        key_func=get_remote_address,
        app=app,
        default_limits=[app.config.get('RATELIMIT_DEFAULT', '100 per hour')],
        storage_uri=app.config.get('RATELIMIT_STORAGE_URL', 'redis://redis:6379/0'),
        strategy="fixed-window"
    )
    
    # Redis (for caching)
    if app.config.get('REDIS_URL'):
        import redis
        redis_client = redis.from_url(app.config['REDIS_URL'])
        app.extensions['redis'] = redis_client
    
    # Elasticsearch (for search)
    if app.config.get('ELASTICSEARCH_URL'):
        from elasticsearch import Elasticsearch
        es_client = Elasticsearch([app.config['ELASTICSEARCH_URL']])
        app.extensions['elasticsearch'] = es_client


def register_blueprints(app):
    """Register Flask blueprints with versioning"""
    # Version 2 endpoints
    app.register_blueprint(auth_bp, url_prefix='/api/v2/auth')
    app.register_blueprint(posts_bp, url_prefix='/api/v2/posts')
    
    # Legacy v1 endpoints (redirect to v2)
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(posts_bp, url_prefix='/api/posts')


def setup_logging(app):
    """Setup enhanced structured logging"""
    log_level = getattr(logging, app.config.get('LOG_LEVEL', 'INFO'))
    
    # JSON formatter for structured logging
    class JSONFormatter(logging.Formatter):
        def format(self, record):
            log_data = {
                'timestamp': datetime.utcnow().isoformat(),
                'level': record.levelname,
                'logger': record.name,
                'message': record.getMessage(),
                'module': record.module,
                'function': record.funcName,
                'line': record.lineno
            }
            
            if hasattr(record, 'request_id'):
                log_data['request_id'] = record.request_id
            
            if record.exc_info:
                log_data['exception'] = self.formatException(record.exc_info)
            
            return json.dumps(log_data)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(JSONFormatter())
    
    # File handler (production)
    if app.config.get('FLASK_ENV') == 'production':
        file_handler = logging.FileHandler('/var/log/rizz-api/api.log')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(JSONFormatter())
        app.logger.addHandler(file_handler)
    
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)
    app.logger.propagate = False


def run_startup_checks(app):
    """Run startup health checks"""
    app.logger.info('Running startup checks...')
    
    # Check database connection
    try:
        db.session.execute('SELECT 1')
        app.logger.info('✓ Database connection OK')
    except Exception as e:
        app.logger.error(f'✗ Database connection failed: {e}')
    
    # Check Redis connection
    try:
        redis_client = app.extensions.get('redis')
        if redis_client:
            redis_client.ping()
            app.logger.info('✓ Redis connection OK')
    except Exception as e:
        app.logger.warning(f'⚠ Redis connection failed: {e}')
    
    app.logger.info('Startup checks completed')
