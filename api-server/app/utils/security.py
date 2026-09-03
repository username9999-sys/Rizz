"""
Security Utilities
Reusable decorators and helpers for input validation, content-type enforcement,
and CORS hardening. Reuses validate_* from utils.validators.

This module deliberately avoids importing the `app` package so it can be
unit-tested without pulling in prometheus, opentelemetry, sqlalchemy, etc.
"""

import os
import sys

from functools import wraps
from flask import request, jsonify, current_app

# Import validators directly without going through app/__init__.py,
# which has heavy third-party imports.
_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
try:
    from validators import (  # type: ignore
        validate_email,
        validate_username,
        validate_password,
        validate_post_title,
        validate_post_content,
        validate_comment_content,
        validate_tag_name,
        sanitize_html,
    )
except ImportError:
    # Fallback to relative import for when called as part of the app package
    from .validators import (
        validate_email,
        validate_username,
        validate_password,
        validate_post_title,
        validate_post_content,
        validate_comment_content,
        validate_tag_name,
        sanitize_html,
    )

ALLOWED_CONTENT_TYPES = {"application/json"}

# Map field name -> validator function. Use "validate_<name>" by convention.
_VALIDATORS = {
    "email": validate_email,
    "username": validate_username,
    "password": validate_password,
    "title": validate_post_title,
    "content": validate_post_content,
    "comment": validate_comment_content,
    "tag": validate_tag_name,
}

# Fields that must be HTML-sanitized before storage.
_SANITIZE_FIELDS = {"title", "content", "comment"}


def _to_bool(value, default=False):
    if value is None:
        return default
    return str(value).lower() in {"1", "true", "yes", "on"}


def _parse_json_body():
    """Return parsed JSON or (None, error_response)."""
    if not request.is_json:
        if request.content_length and request.content_length > 0:
            return None, (jsonify({
                "error": "Content-Type must be application/json"
            }), 415)
        return None, (jsonify({"error": "Request body required"}), 400)
    try:
        data = request.get_json(force=False, silent=False)
    except Exception:
        return None, (jsonify({"error": "Malformed JSON"}), 400)
    if data is None:
        return None, (jsonify({"error": "Empty JSON body"}), 400)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "JSON body must be an object"}), 400)
    return data, None


def validate_json(required_fields=None, allowed_fields=None, strict=True):
    """
    Decorator: enforce JSON content-type, parse body, validate required fields,
    optionally reject unknown fields, and run type-specific validators.

    Args:
        required_fields: list of field names that must be present
        allowed_fields: list of allowed field names (None = allow all)
        strict: if True and allowed_fields given, reject unknown fields

    Returns:
        Decorated view with `g.validated_data` available (sanitized dict).
    """
    required_fields = set(required_fields or [])
    allowed_fields = set(allowed_fields) if allowed_fields else None

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            data, error = _parse_json_body()
            if error:
                return error

            # Reject unknown fields when allowlist is enforced
            if allowed_fields is not None and strict:
                unknown = set(data.keys()) - allowed_fields - required_fields
                if unknown:
                    return jsonify({
                        "error": "Unknown fields not allowed",
                        "fields": sorted(unknown)
                    }), 400

            missing = [f for f in required_fields if f not in data or data[f] in (None, "")]
            if missing:
                return jsonify({
                    "error": "Missing required fields",
                    "fields": missing
                }), 400

            # Run type-specific validators
            errors = {}
            sanitized = {}
            for field, value in data.items():
                validator = _VALIDATORS.get(field)
                if validator and isinstance(value, str):
                    if not validator(value):
                        errors[field] = f"Invalid value for '{field}'"
                        continue
                if field in _SANITIZE_FIELDS and isinstance(value, str):
                    value = sanitize_html(value)
                sanitized[field] = value

            if errors:
                return jsonify({"error": "Validation failed", "details": errors}), 400

            from flask import g
            g.validated_data = sanitized
            return view(*args, **kwargs)

        return wrapper

    return decorator


def require_content_type(allowed=None):
    """
    Decorator: enforce that the request has one of the allowed Content-Type
    values. Useful for endpoints that don't go through validate_json.
    """
    allowed = set(allowed or ALLOWED_CONTENT_TYPES)

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            ctype = (request.content_type or "").split(";")[0].strip().lower()
            if ctype and ctype not in allowed:
                return jsonify({
                    "error": f"Content-Type must be one of: {sorted(allowed)}"
                }), 415
            return view(*args, **kwargs)

        return wrapper

    return decorator


def is_production():
    """True when running under ProductionConfig."""
    return _to_bool(current_app.config.get("PRODUCTION")), _to_bool


# Eager import to surface helper availability
__all__ = [
    "validate_json",
    "require_content_type",
    "ALLOWED_CONTENT_TYPES",
    "sanitize_html",
]
