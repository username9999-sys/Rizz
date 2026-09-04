"""
Common encoding helpers used by TOTP, sessions, and tests.

Extracted to avoid the same base64url encode/decode helper being
duplicated across modules. Pure stdlib, zero external dependencies.
"""

import base64
from typing import Any, Dict, Optional, Tuple

from flask import jsonify, Response


def b64url_encode(data: bytes) -> str:
    """Base64-URL encode without padding (RFC 4648 §5)."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def b64url_decode(data: str) -> bytes:
    """Base64-URL decode, tolerating un-padded input."""
    s = data.strip().replace(" ", "")
    pad = "=" * (-len(s) % 8)
    return base64.urlsafe_b64decode(s + pad)


# ---------- Error response builders ----------

def error_response(message: str, status: int, **extra: Any) -> Tuple[Response, int]:
    """Build a structured JSON error response.

    Usage:
        return error_response("missing fields", 400, fields=["username"])
    """
    body: Dict[str, Any] = {"error": message}
    body.update(extra)
    return jsonify(body), status


def ok_response(data: Any, status: int = 200) -> Tuple[Response, int]:
    """Build a successful JSON response."""
    return jsonify(data), status
