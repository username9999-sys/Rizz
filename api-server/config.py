"""
API Server Configuration
Environment-based configuration for development, testing, and production
"""

import os
from pathlib import Path

class Config:
    """Base configuration - subclasses should override with environment-specific values"""
    # Secrets must be provided via environment variables; no defaults
    JWT_ACCESS_TOKEN_EXPIRES = 3600  # 1 hour
    JWT_REFRESH_TOKEN_EXPIRES = 604800  # 7 days

    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///rizz_api.db')

    # Security
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    # Content Security Policy (CSP)
    CSP_POLICY = "default-src 'self'"
    # Secure cookie settings (for session cookies if used)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = True
    ENFORCE_HTTPS = True

    # CORS
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',')

    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FILE = os.environ.get('LOG_FILE', 'logs/api.log')

    @staticmethod
    def init_app(app):
        # Enforce required secrets based on environment
        env = os.environ.get('FLASK_ENV', 'development')
        if env == 'production':
            if not os.environ.get('SECRET_KEY'):
                raise ValueError("SECRET_KEY must be set in production environment")
            if not os.environ.get('JWT_SECRET_KEY'):
                raise ValueError("JWT_SECRET_KEY must be set in production environment")


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    LOG_LEVEL = 'DEBUG'


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    DATABASE_URL = 'sqlite:///:memory:'
    JWT_SECRET_KEY = 'test-secret-key'
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    LOG_LEVEL = 'WARNING'

    # Require environment variables in production
    def __init__(self):
        if not os.environ.get('SECRET_KEY'):
            raise ValueError("SECRET_KEY must be set in production")
        if not os.environ.get('JWT_SECRET_KEY'):
            raise ValueError("JWT_SECRET_KEY must be set in production")


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
