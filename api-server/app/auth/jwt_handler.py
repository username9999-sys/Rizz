"""
JWT Token Handler
Handles token creation and verification
"""

import jwt
import uuid
import datetime
from functools import wraps
from flask import request, jsonify, current_app, g


def create_token(user_id: int, username: str, expires_days: int = 7) -> str:
    """Create an access JWT token with a unique JTI for revocation."""
    jti = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "username": username,
        "jti": jti,
        "type": "access",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=expires_days),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")
    """Create JWT token"""
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=expires_days),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def verify_token(token: str) -> dict | None:
    """Verify an access token and return its payload or None if invalid/expired."""
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        # Ensure token is of type access
        if payload.get("type") != "access":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, current_app.config['SECRET_KEY'], algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def token_required(f):
    """Decorator to require valid token"""
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            if auth_header.startswith('Bearer '):
                token = auth_header.split(' ')[1]
        
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401

        # Check token blacklist (revoked tokens) using JTI
        redis_client = current_app.extensions.get('redis')
        if redis_client and payload.get('jti'):
            blacklist_key = f'jwt_blacklist:{payload["jti"]}'
            if redis_client.exists(blacklist_key):
                return jsonify({'error': 'Token has been revoked'}), 401

        g.current_user = payload['user_id']
        g.current_username = payload['username']

        return f(*args, **kwargs)
    
    return decorated

# ---------------------------------------------------------------------------
# Refresh token handling
# ---------------------------------------------------------------------------

def create_refresh_token(user_id: int, username: str, expires_days: int = 30) -> str:
    """Create a refresh JWT token.
    Includes a unique ``jti`` to allow revocation and a ``type`` claim set to ``refresh``.
    """
    jti = str(uuid.uuid4())
    payload = {
        "user_id": user_id,
        "username": username,
        "jti": jti,
        "type": "refresh",
        "exp": datetime.datetime.utcnow() + datetime.timedelta(days=expires_days),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, current_app.config["SECRET_KEY"], algorithm="HS256")


def verify_refresh_token(token: str) -> dict | None:
    """Verify a refresh token and return its payload.
    Returns ``None`` if token is invalid, expired, or not a refresh token.
    """
    try:
        payload = jwt.decode(token, current_app.config["SECRET_KEY"], algorithms=["HS256"])
        if payload.get("type") != "refresh":
            return None
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def revoke_token(jti: str, ttl: int | None = None) -> None:
    """Add a token's JTI to the Redis blacklist.
    If ``ttl`` is provided, the blacklist entry expires after that many seconds.
    """
    redis_client = current_app.extensions.get("redis")
    if not redis_client:
        return
    key = f"jwt_blacklist:{jti}"
    if ttl:
        redis_client.set(key, "revoked", ex=ttl)
    else:
        redis_client.set(key, "revoked")
