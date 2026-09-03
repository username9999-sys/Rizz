"""
Application Settings
Configuration for different environments
"""

import os
from pathlib import Path


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', 'jwt-secret-change-in-production')

    # Database
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///rizz_api.db')
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')

    # Rate limiting
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_STORAGE_URL = REDIS_URL

    # Upload
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    # CORS — comma-separated env var, no wildcard fallback
    _cors_env = os.environ.get('CORS_ORIGINS', '')
    CORS_ORIGINS = [o.strip() for o in _cors_env.split(',') if o.strip()] or [
        "http://localhost:3000", "http://localhost:5000"
    ]

    # Security headers
    CSP_POLICY = os.environ.get(
        'CSP_POLICY',
        "default-src 'self'; frame-ancestors 'none'; base-uri 'self'"
    )
    ENFORCE_HTTPS = os.environ.get('ENFORCE_HTTPS', 'false').lower() == 'true'

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    PRODUCTION = False

    # Use SQLite for development
    DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///rizz_api_dev.db')


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    PRODUCTION = True

    # Require environment variables in production
    SECRET_KEY = os.environ.get('SECRET_KEY')
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY')

    @classmethod
    def init_app(cls, app):
        Config.init_app(app)

        # Fail-closed on missing secrets
        missing = [k for k in ('SECRET_KEY', 'JWT_SECRET_KEY') if not app.config.get(k)]
        if missing:
            raise RuntimeError(
                f"Missing required production env vars: {', '.join(missing)}"
            )

        # In production, refuse wildcard CORS
        if '*' in app.config.get('CORS_ORIGINS', []):
            raise RuntimeError("CORS_ORIGINS cannot include '*' in production")

        # Log to stderr
        import logging
        from logging import StreamHandler
        app.logger.addHandler(StreamHandler())
        app.logger.setLevel(logging.INFO)


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    PRODUCTION = False

    # Use in-memory SQLite for tests
    DATABASE_URL = 'sqlite:///:memory:'

    # Disable rate limiting for tests
    RATELIMIT_ENABLED = False

    # Permissive CORS for test client
    CORS_ORIGINS = ["http://localhost", "http://test"]


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
