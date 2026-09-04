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
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Union

from flask import request, jsonify, current_app, Response

# Import validators directly without going through app/__init__.py,
# which has heavy third-party imports.
_HERE: str = os.path.dirname(os.path.abspath(__file__))
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

ALLOWED_CONTENT_TYPES: Set[str] = {"application/json"}

# Map field name -> validator function. Use "validate_<name>" by convention.
_VALIDATORS: Dict[str, Callable[[str], bool]] = {
    "email": validate_email,
    "username": validate_username,
    "password": validate_password,
    "title": validate_post_title,
    "content": validate_post_content,
    "comment": validate_comment_content,
    "tag": validate_tag_name,
}

# Fields that must be HTML-sanitized before storage.
_SANITIZE_FIELDS: Set[str] = {"title", "content", "comment"}


def _to_bool(value: Any, default: bool = False) -> bool:
    if value is None:
        return default
    return str(value).lower() in {"1", "true", "yes", "on"}


def _parse_json_body() -> Tuple[Optional[Dict[str, Any]], Optional[Tuple[Response, int]]]:
    """Return parsed JSON or (None, error_response)."""
    if not request.is_json:
        if request.content_length and request.content_length > 0:
            return None, (jsonify({
                "error": "Content-Type must be application/json"
            }), 415)
        return None, (jsonify({"error": "Request body required"}), 400)
    try:
        data: Optional[Dict[str, Any]] = request.get_json(force=False, silent=False)
    except Exception:
        return None, (jsonify({"error": "Malformed JSON"}), 400)
    if data is None:
        return None, (jsonify({"error": "Empty JSON body"}), 400)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "JSON body must be an object"}), 400)
    return data, None


def validate_json(
    required_fields: Optional[List[str]] = None,
    allowed_fields: Optional[List[str]] = None,
    strict: bool = True,
) -> Callable:
    """Decorator: enforce JSON content-type, parse body, validate required fields,
    optionally reject unknown fields, and run type-specific validators.

    Args:
        required_fields: list of field names that must be present.
        allowed_fields: list of allowed field names (None = allow all).
        strict: if True and allowed_fields given, reject unknown fields.

    Returns:
        Decorated view with `g.validated_data` available (sanitized dict).
    """
    required: Set[str] = set(required_fields or [])
    allowed: Optional[Set[str]] = set(allowed_fields) if allowed_fields else None

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            data, error = _parse_json_body()
            if error:
                return error

            if allowed is not None and strict:
                unknown: Set[str] = set(data.keys()) - allowed - required
                if unknown:
                    return jsonify({
                        "error": "Unknown fields not allowed",
                        "fields": sorted(unknown)
                    }), 400

            missing: List[str] = [
                f for f in required if f not in data or data[f] in (None, "")
            ]
            if missing:
                return jsonify({
                    "error": "Missing required fields",
                    "fields": missing
                }), 400

            errors: Dict[str, str] = {}
            sanitized: Dict[str, Any] = {}
            for field, value in data.items():
                validator: Optional[Callable[[str], bool]] = _VALIDATORS.get(field)
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


def require_content_type(allowed: Optional[List[str]] = None) -> Callable:
    """Decorator: enforce that the request has one of the allowed Content-Type
    values. Useful for endpoints that don't go through validate_json.
    """
    allowed_set: Set[str] = set(allowed or ALLOWED_CONTENT_TYPES)

    def decorator(view: Callable) -> Callable:
        @wraps(view)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            ctype: str = (request.content_type or "").split(";")[0].strip().lower()
            if ctype and ctype not in allowed_set:
                return jsonify({
                    "error": f"Content-Type must be one of: {sorted(allowed_set)}"
                }), 415
            return view(*args, **kwargs)

        return wrapper

    return decorator


def is_production() -> Tuple[bool, Callable]:
    """True when running under ProductionConfig.

    Returns a tuple (is_production_flag, _to_bool_helper) for compatibility
    with the legacy caller signature.
    """
    return _to_bool(current_app.config.get("PRODUCTION")), _to_bool


__all__ = [
    "validate_json",
    "require_content_type",
    "ALLOWED_CONTENT_TYPES",
    "sanitize_html",
]
