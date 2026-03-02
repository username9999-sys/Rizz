"""
JWT Token Handler
Handles token creation and verification
"""

import jwt
import datetime
from functools import wraps
from flask import request, jsonify, current_app, g


def create_token(user_id, username, expires_days=7):
    """Create JWT token"""
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': datetime.datetime.utcnow() + datetime.timedelta(days=expires_days),
        'iat': datetime.datetime.utcnow()
    }
    return jwt.encode(payload, current_app.config['SECRET_KEY'], algorithm='HS256')


def verify_token(token):
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
        
        g.current_user = payload['user_id']
        g.current_username = payload['username']
        
        return f(*args, **kwargs)
    
    return decorated
