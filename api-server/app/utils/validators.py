"""
Validation Utilities
Enterprise-grade input validation
"""

import re


def validate_email(email):
    """Validate email format"""
    if not email:
        return False
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_username(username):
    """Validate username format"""
    if not username:
        return False
    if len(username) < 3 or len(username) > 30:
        return False
    pattern = r'^[a-zA-Z][a-zA-Z0-9_]*$'
    return re.match(pattern, username) is not None


def validate_password(password):
    """Validate password strength"""
    if not password:
        return False
    if len(password) < 8:
        return False
    # Must contain at least one letter and one number
    has_letter = bool(re.search(r'[a-zA-Z]', password))
    has_number = bool(re.search(r'\d', password))
    return has_letter and has_number


def validate_post_title(title):
    """Validate post title"""
    if not title:
        return False
    return 1 <= len(title) <= 200


def validate_post_content(content):
    """Validate post content"""
    if not content:
        return False
    return len(content) >= 10


def validate_comment_content(content):
    """Validate comment content"""
    if not content:
        return False
    return 1 <= len(content) <= 5000


def validate_tag_name(name):
    """Validate tag name"""
    if not name:
        return False
    if len(name) > 50:
        return False
    pattern = r'^[a-zA-Z0-9\s-]+$'
    return re.match(pattern, name) is not None


def sanitize_html(text):
    """Basic HTML sanitization (use bleach library for production)"""
    if not text:
        return text
    # Remove script tags
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.IGNORECASE | re.DOTALL)
    # Remove other potentially dangerous tags
    text = re.sub(r'<(iframe|object|embed)[^>]*>.*?</\1>', '', text, flags=re.IGNORECASE | re.DOTALL)
    return text
