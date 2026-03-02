"""Routes Package"""
from .auth import auth_bp
from .posts import posts_bp

__all__ = ['auth_bp', 'posts_bp']
