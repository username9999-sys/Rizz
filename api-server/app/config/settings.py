"""
Application Settings
Configuration for different environments
"""

import os
from typing import Any, ClassVar, List, Optional


class Config:
    """Base configuration."""

    SECRET_KEY: ClassVar[Optional[str]] = os.environ.get(
        "SECRET_KEY", "dev-secret-key-change-in-production"
    )
    JWT_SECRET_KEY: ClassVar[Optional[str]] = os.environ.get(
        "JWT_SECRET_KEY", "jwt-secret-change-in-production"
    )

    # Database
    DATABASE_URL: ClassVar[str] = os.environ.get("DATABASE_URL", "sqlite:///rizz_api.db")
    REDIS_URL: ClassVar[str] = os.environ.get("REDIS_URL", "redis://localhost:6379/0")

    # Rate limiting
    RATELIMIT_DEFAULT: ClassVar[str] = "100 per hour"
    RATELIMIT_STORAGE_URL: ClassVar[str] = REDIS_URL

    # Upload
    MAX_CONTENT_LENGTH: ClassVar[int] = 16 * 1024 * 1024  # 16MB

    # CORS — comma-separated env var, no wildcard fallback
    _cors_env: ClassVar[str] = os.environ.get("CORS_ORIGINS", "")
    CORS_ORIGINS: ClassVar[List[str]] = (
        [o.strip() for o in _cors_env.split(",") if o.strip()]
        or ["http://localhost:3000", "http://localhost:5000"]
    )

    # Security headers
    CSP_POLICY: ClassVar[str] = os.environ.get(
        "CSP_POLICY",
        "default-src 'self'; frame-ancestors 'none'; base-uri 'self'",
    )
    ENFORCE_HTTPS: ClassVar[bool] = os.environ.get("ENFORCE_HTTPS", "false").lower() == "true"

    @staticmethod
    def init_app(app: Any) -> None:
        pass


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG: ClassVar[bool] = True
    TESTING: ClassVar[bool] = False
    PRODUCTION: ClassVar[bool] = False

    DATABASE_URL: ClassVar[str] = os.environ.get("DATABASE_URL", "sqlite:///rizz_api_dev.db")


class ProductionConfig(Config):
    """Production configuration. Fails closed on missing secrets or wildcard CORS."""

    DEBUG: ClassVar[bool] = False
    TESTING: ClassVar[bool] = False
    PRODUCTION: ClassVar[bool] = True

    SECRET_KEY: ClassVar[Optional[str]] = os.environ.get("SECRET_KEY")
    JWT_SECRET_KEY: ClassVar[Optional[str]] = os.environ.get("JWT_SECRET_KEY")

    @classmethod
    def init_app(cls, app: Any) -> None:
        Config.init_app(app)

        missing: List[str] = [
            k for k in ("SECRET_KEY", "JWT_SECRET_KEY") if not app.config.get(k)
        ]
        if missing:
            raise RuntimeError(
                f"Missing required production env vars: {', '.join(missing)}"
            )

        if "*" in app.config.get("CORS_ORIGINS", []):
            raise RuntimeError("CORS_ORIGINS cannot include '*' in production")

        import logging
        from logging import StreamHandler
        app.logger.addHandler(StreamHandler())
        app.logger.setLevel(logging.INFO)


class TestingConfig(Config):
    """Testing configuration."""

    TESTING: ClassVar[bool] = True
    DEBUG: ClassVar[bool] = True
    PRODUCTION: ClassVar[bool] = False

    DATABASE_URL: ClassVar[str] = "sqlite:///:memory:"
    RATELIMIT_ENABLED: ClassVar[bool] = False
    CORS_ORIGINS: ClassVar[List[str]] = ["http://localhost", "http://test"]


config: dict = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
    "default": DevelopmentConfig,
}
