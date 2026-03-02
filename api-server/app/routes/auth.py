"""
Authentication Routes
Login, register, and user management
"""

from flask import Blueprint, request, jsonify, current_app
from app.auth.jwt_handler import create_token, token_required
import hashlib

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


@bp.route('/register', methods=['POST'])
def register():
    """Register new user"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    
    if not all([username, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400
    
    if len(password) < 6:
        return jsonify({'error': 'Password must be at least 6 characters'}), 400
    
    # Hash password
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    # TODO: Save to database
    # For now, just return success
    return jsonify({
        'message': 'User registered successfully',
        'username': username
    }), 201


@bp.route('/login', methods=['POST'])
def login():
    """Login user"""
    data = request.get_json()
    
    if not data:
        return jsonify({'error': 'No data provided'}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not all([username, password]):
        return jsonify({'error': 'Missing credentials'}), 400
    
    # TODO: Verify with database
    # For demo, accept admin/admin123
    if username == 'admin' and password == 'admin123':
        token = create_token(user_id=1, username=username)
        return jsonify({
            'message': 'Login successful',
            'token': token,
            'user': {
                'id': 1,
                'username': username,
                'email': 'admin@rizz.dev'
            }
        })
    
    return jsonify({'error': 'Invalid credentials'}), 401


@bp.route('/me', methods=['GET'])
@token_required
def get_current_user():
    """Get current user info"""
    return jsonify({
        'user': {
            'id': g.current_user,
            'username': g.current_username
        }
    })
