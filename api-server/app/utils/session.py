"""
Session management — JWT with refresh token rotation and revocation.

Pattern:
  - Access token: short-lived (15 min default), stateless JWT
  - Refresh token: longer-lived (7 days default), but tracked server-side
    for revocation. Refresh tokens are single-use: each use issues a new
    pair AND revokes the old refresh token (rotation).

  - Revocation list: in-memory store keyed by jti. For production,
    swap with Redis (the `store` parameter accepts a dict-like).

  - `is_revoked` check is called on every request that uses a refresh
    token. For access tokens (stateless), revocation is best-effort via
    short expiry; if you need immediate revocation, store access-token
    jti in the same store and check there.

Zero external dependencies. Does not import app/__init__.py.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
import uuid
from typing import Optional, Callable, Dict, Any, Tuple

# Import codec helpers with fallback for standalone test loading.
# When the test loader uses importlib.util.spec_from_file_location, the
# relative import "from .codec" would fail because there's no package
# context. Fall back to a path-based load in that case.
try:
    from .codec import b64url_encode as _b64u, b64url_decode as _b64u_dec
except (ImportError, ValueError):
    import importlib.util as _ilu
    import os as _os
    _codec_path = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "codec.py")
    _spec = _ilu.spec_from_file_location("_session_codec", _codec_path)
    _codec_mod = _ilu.module_from_spec(_spec)
    _spec.loader.exec_module(_codec_mod)
    _b64u = _codec_mod.b64url_encode
    _b64u_dec = _codec_mod.b64url_decode


DEFAULT_ACCESS_TTL = 15 * 60            # 15 minutes
DEFAULT_REFRESH_TTL = 7 * 24 * 60 * 60 # 7 days
DEFAULT_ALGO = "HS256"


class SessionError(Exception):
    """Base for session-related errors."""


class TokenExpired(SessionError):
    pass


class TokenRevoked(SessionError):
    pass


class TokenInvalid(SessionError):
    pass


class SessionManager:
    """JWT-based session manager with refresh-token rotation.

    Args:
        secret: HMAC signing key (use a strong random value in production).
        access_ttl: access-token lifetime in seconds.
        refresh_ttl: refresh-token lifetime in seconds.
        store: dict-like for revocation tracking. Default is in-memory.
        clock: callable returning current time (for tests).
    """

    def __init__(
        self,
        secret: bytes,
        access_ttl: int = DEFAULT_ACCESS_TTL,
        refresh_ttl: int = DEFAULT_REFRESH_TTL,
        store: Optional[Dict[str, Any]] = None,
        clock: Callable[[], float] = time.time,
    ):
        if not isinstance(secret, (bytes, bytearray)) or len(secret) < 16:
            raise ValueError("secret must be at least 16 random bytes")
        self.secret = bytes(secret)
        self.access_ttl = access_ttl
        self.refresh_ttl = refresh_ttl
        self._store = store if store is not None else {}
        self._clock = clock
        # RLock because rotate_refresh -> issue_pair acquires the same lock.
        # Same thread can re-enter; different threads serialize.
        self._lock = threading.RLock()

    # ---------- Token issuance ----------

    def issue_pair(self, user_id: Any, username: str,
                   extra_claims: Optional[dict] = None) -> dict:
        """Issue a fresh (access, refresh) token pair.

        Returns a dict with keys: access_token, refresh_token, jti,
        access_exp, refresh_exp.
        """
        now = int(self._clock())
        access_jti = uuid.uuid4().hex
        refresh_jti = uuid.uuid4().hex

        access_payload = {
            "sub": str(user_id),
            "usr": username,
            "jti": access_jti,
            "type": "access",
            "iat": now,
            "exp": now + self.access_ttl,
        }
        if extra_claims:
            access_payload.update(extra_claims)

        refresh_payload = {
            "sub": str(user_id),
            "jti": refresh_jti,
            "type": "refresh",
            "iat": now,
            "exp": now + self.refresh_ttl,
        }

        access_token = self._sign(access_payload)
        refresh_token = self._sign(refresh_payload)

        # Track refresh token in the revocation store
        with self._lock:
            self._store[refresh_jti] = {
                "user_id": str(user_id),
                "username": username,
                "issued_at": now,
                "expires_at": now + self.refresh_ttl,
                "rotated_to": None,   # set when this token is exchanged
                "used_at": None,
            }

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "jti": access_jti,
            "access_exp": now + self.access_ttl,
            "refresh_exp": now + self.refresh_ttl,
        }

    # ---------- Token verification ----------

    def verify_access(self, token: str) -> dict:
        """Verify an access token. Returns the claims dict.

        Raises TokenExpired / TokenInvalid / TokenRevoked.
        """
        claims = self._decode(token)
        if claims.get("type") != "access":
            raise TokenInvalid("not an access token")
        return claims

    def rotate_refresh(self, refresh_token: str) -> dict:
        """Exchange a refresh token for a new pair.

        Implements single-use refresh tokens: the presented token is
        immediately revoked. If the same refresh token is presented
        twice, the entire user session family is revoked (defense
        against token theft).

        Returns the same shape as issue_pair().
        """
        claims = self._decode(refresh_token)
        if claims.get("type") != "refresh":
            raise TokenInvalid("not a refresh token")

        jti = claims["jti"]
        sub = claims["sub"]
        with self._lock:
            entry = self._store.get(jti)
            if not entry:
                # Unknown jti
                raise TokenRevoked("refresh token not recognized")
            if entry.get("rotated_to"):
                # REPLAY DETECTED — revoke the entire family for this user
                self._revoke_user(sub, reason="refresh_token_replay")
                raise TokenRevoked("refresh token reuse detected; all sessions revoked")
            if entry["expires_at"] < int(self._clock()):
                raise TokenExpired("refresh token expired")

            # Mark old token as rotated (cannot be used again)
            new_pair = self.issue_pair(sub, entry["username"])
            entry["rotated_to"] = new_pair["jti"]
            entry["used_at"] = int(self._clock())

        return new_pair

    # ---------- Revocation ----------

    def revoke_refresh(self, refresh_token: str) -> None:
        """Revoke a specific refresh token (e.g. on logout)."""
        claims = self._decode(refresh_token, ignore_expiry=True)
        jti = claims.get("jti")
        if jti:
            with self._lock:
                self._store.pop(jti, None)

    def revoke_user(self, user_id: Any) -> int:
        """Revoke ALL refresh tokens for a user (e.g. password change).
        Returns the number of tokens revoked."""
        with self._lock:
            return self._revoke_user(str(user_id), reason="admin_action")

    def is_revoked(self, jti: str) -> bool:
        return jti not in self._store

    # ---------- Internals ----------

    def _revoke_user(self, user_id: str, reason: str = "admin") -> int:
        """Internal: revoke every refresh token whose entry.user_id matches.
        Caller must hold self._lock."""
        to_delete = [
            jti for jti, entry in self._store.items()
            if entry.get("user_id") == user_id
        ]
        for jti in to_delete:
            del self._store[jti]
        return len(to_delete)

    def _sign(self, payload: dict) -> str:
        header = _b64u(json.dumps({"alg": DEFAULT_ALGO, "typ": "JWT"},
                                  separators=(",", ":")).encode())
        body = _b64u(json.dumps(payload, separators=(",", ":")).encode())
        signing_input = f"{header}.{body}".encode()
        sig = hmac.new(self.secret, signing_input, hashlib.sha256).digest()
        return f"{header}.{body}.{_b64u(sig)}"

    def _decode(self, token: str, ignore_expiry: bool = False) -> dict:
        if not isinstance(token, str) or token.count(".") != 2:
            raise TokenInvalid("malformed token")
        try:
            header_b, body_b, sig_b = token.split(".")
            signing_input = f"{header_b}.{body_b}".encode()
            expected = hmac.new(self.secret, signing_input,
                                hashlib.sha256).digest()
            if not hmac.compare_digest(_b64u(expected), sig_b):
                raise TokenInvalid("bad signature")
            claims = json.loads(_b64u_dec(body_b))
        except TokenInvalid:
            raise
        except Exception as e:
            raise TokenInvalid(f"decode error: {e}")

        now = int(self._clock())
        if not ignore_expiry and claims.get("exp", 0) < now:
            raise TokenExpired("token expired")

        # Check revocation for refresh tokens
        if claims.get("type") == "refresh":
            with self._lock:
                entry = self._store.get(claims.get("jti"))
                if not entry:
                    raise TokenRevoked("refresh token revoked or unknown")

        return claims


def new_secret(nbytes: int = 32) -> bytes:
    """Generate a new random secret suitable for SessionManager."""
    return secrets.token_bytes(nbytes)
