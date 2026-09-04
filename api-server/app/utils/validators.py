"""
Validation Utilities
Enterprise-grade input validation
"""

import re
from typing import Optional


def validate_email(email: Optional[str]) -> bool:
    """Validate email format."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, email) is not None


def validate_username(username: Optional[str]) -> bool:
    """Validate username format (3-30 chars, must start with letter)."""
    if not username:
        return False
    if len(username) < 3 or len(username) > 30:
        return False
    pattern = r"^[a-zA-Z][a-zA-Z0-9_]*$"
    return re.match(pattern, username) is not None


def validate_password(password: Optional[str]) -> bool:
    """Validate password strength: 8+ chars, must have letter and digit."""
    if not password:
        return False
    if len(password) < 8:
        return False
    has_letter: bool = bool(re.search(r"[a-zA-Z]", password))
    has_number: bool = bool(re.search(r"\d", password))
    return has_letter and has_number


def validate_post_title(title: Optional[str]) -> bool:
    """Validate post title: 1-200 chars."""
    if not title:
        return False
    return 1 <= len(title) <= 200


def validate_post_content(content: Optional[str]) -> bool:
    """Validate post content: at least 10 chars."""
    if not content:
        return False
    return len(content) >= 10


def validate_comment_content(content: Optional[str]) -> bool:
    """Validate comment content: 1-5000 chars."""
    if not content:
        return False
    return 1 <= len(content) <= 5000


def validate_tag_name(name: Optional[str]) -> bool:
    """Validate tag name: 1-50 chars, alphanumeric + spaces + hyphens."""
    if not name:
        return False
    if len(name) > 50:
        return False
    pattern = r"^[a-zA-Z0-9\s-]+$"
    return re.match(pattern, name) is not None


def sanitize_html(text: Optional[str]) -> Optional[str]:
    """Strip dangerous HTML tags (script, iframe, object, embed).

    NOTE: use the bleach library for production-grade sanitization.
    This is a basic regex-based filter good enough for defense in depth
    but does not handle every XSS vector.
    """
    if not text:
        return text
    text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<(iframe|object|embed)[^>]*>.*?</\1>", "", text, flags=re.IGNORECASE | re.DOTALL)
    return text
