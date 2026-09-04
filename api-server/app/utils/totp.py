"""
TOTP (RFC 6238) — Time-based One-Time Password.

Zero external dependencies. Implements:
  - HOTP (RFC 4226) counter-based
  - TOTP (RFC 6238) time-based
  - Base32 secret generation
  - otpauth:// URI for QR code enrollment
  - Constant-time comparison
  - Configurable digits (6 default), period (30s default), window (+/- 1)

This module deliberately does NOT depend on the broken app/__init__.py
so it can be unit-tested in isolation.

Typical enrollment flow:
    secret = totp.new_secret()
    uri = totp.provisioning_uri(secret, "alice@example.com", "Rizz")
    # Show QR code of `uri` to user
    # User scans with Google Authenticator / 1Password / etc.
    # Verify by storing `secret` server-side and checking user-entered code
    is_valid = totp.verify(secret, code_from_user)
"""

import base64
import hashlib
import hmac
import os
import struct
import time
import urllib.parse


DEFAULT_DIGITS = 6
DEFAULT_PERIOD = 30
DEFAULT_ALGORITHM = "sha1"
DEFAULT_WINDOW = 1  # accept +/- 1 step (i.e. 90s total)


def _b32encode(raw: bytes) -> str:
    """Base32-encode without padding (RFC 4648 base32, no '=' chars).

    This is the format expected by authenticator apps.
    """
    return base64.b32encode(raw).rstrip(b"=").decode("ascii")


def _b32decode(s: str) -> bytes:
    """Base32-decode with optional padding (handles un-padded input)."""
    s = s.strip().replace(" ", "").upper()
    pad = (-len(s)) % 8
    return base64.b32decode(s + ("=" * pad))


def new_secret(length: int = 20) -> str:
    """Generate a new random base32-encoded secret.

    20 bytes (160 bits) is the RFC 4226 recommended length. The base32
    representation is 32 chars.
    """
    if length < 16:
        raise ValueError("secret must be at least 16 bytes (128 bits)")
    return _b32encode(os.urandom(length))


def _hotp(secret_b: bytes, counter: int, digits: int = DEFAULT_DIGITS,
          algorithm: str = DEFAULT_ALGORITHM) -> str:
    """HOTP per RFC 4226."""
    counter_bytes = struct.pack(">Q", counter)
    h = hmac.new(secret_b, counter_bytes, algorithm).digest()
    # Dynamic truncation (RFC 4226 sec 5.3)
    offset = h[-1] & 0x0F
    code_int = (
        ((h[offset] & 0x7F) << 24)
        | ((h[offset + 1] & 0xFF) << 16)
        | ((h[offset + 2] & 0xFF) << 8)
        | (h[offset + 3] & 0xFF)
    )
    return str(code_int % (10 ** digits)).zfill(digits)


def totp(secret: str, timestamp: float = None, digits: int = DEFAULT_DIGITS,
         period: int = DEFAULT_PERIOD, algorithm: str = DEFAULT_ALGORITHM) -> str:
    """Generate the TOTP code for the given timestamp.

    Defaults to current time. Returns a zero-padded string of `digits`.
    """
    if timestamp is None:
        timestamp = time.time()
    counter = int(timestamp) // period
    return _hotp(_b32decode(secret), counter, digits, algorithm)


def verify(secret: str, code: str, timestamp: float = None,
           digits: int = DEFAULT_DIGITS, period: int = DEFAULT_PERIOD,
           window: int = DEFAULT_WINDOW, algorithm: str = DEFAULT_ALGORITHM) -> bool:
    """Verify a user-entered TOTP code.

    Accepts codes from `window` steps before/after the current step.
    Returns True if any window slot matches. Uses constant-time
    comparison for the final equality check.

    `code` is normalized: whitespace stripped, must be all digits.
    """
    if not isinstance(code, str) or not code.isdigit():
        return False
    if len(code) != digits:
        return False
    if timestamp is None:
        timestamp = time.time()
    try:
        secret_b = _b32decode(secret)
    except Exception:
        return False
    current_counter = int(timestamp) // period
    expected = [
        _hotp(secret_b, current_counter + offset, digits, algorithm)
        for offset in range(-window, window + 1)
    ]
    # Constant-time comparison across all candidates
    return any(hmac.compare_digest(code, e) for e in expected)


def provisioning_uri(secret: str, account_name: str, issuer: str = "Rizz",
                     digits: int = DEFAULT_DIGITS, period: int = DEFAULT_PERIOD,
                     algorithm: str = DEFAULT_ALGORITHM) -> str:
    """Build an otpauth:// URI for QR-code enrollment.

    The account_name is typically the user's email. Issuer names the
    application so the authenticator app shows it correctly.
    """
    label = urllib.parse.quote(f"{issuer}:{account_name}", safe="")
    params = urllib.parse.urlencode({
        "secret": secret,
        "issuer": issuer,
        "algorithm": algorithm.upper(),
        "digits": digits,
        "period": period,
    })
    return f"otpauth://totp/{label}?{params}"


# Self-check: if executed directly, show current code
if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m app.utils.totp <base32-secret>")
        sys.exit(1)
    s = sys.argv[1]
    print(f"Current TOTP: {totp(s)}")
    print(f"Verify '123456' (example): {verify(s, '123456')}")
