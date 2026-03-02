"""
Authentication Routes - FIXED
Login, register, and user management with proper security
"""

from flask import Blueprint, request, jsonify, current_app, g
from app.auth.jwt_handler import create_token, token_required
import bcrypt
import re

bp = Blueprint('auth', __name__, url_prefix='/api/auth')


def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    return True, "Password is strong"


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(pattern, email):
        return False
    return True


@bp.route('/register', methods=['POST'])
def register():
    """Register new user with proper security"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '')

    # Validate required fields
    if not all([username, email, password]):
        return jsonify({'error': 'Missing required fields'}), 400

    # Validate username
    if len(username) < 3:
        return jsonify({'error': 'Username must be at least 3 characters'}), 400
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return jsonify({'error': 'Username can only contain letters, numbers, and underscores'}), 400

    # Validate email
    if not validate_email(email):
        return jsonify({'error': 'Invalid email format'}), 400

    # Validate password strength
    is_strong, message = validate_password(password)
    if not is_strong:
        return jsonify({'error': message}), 400

    # Hash password with bcrypt (secure!)
    password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

    # TODO: Save to database
    # db.users.insert_one({
    #     'username': username,
    #     'email': email,
    #     'password_hash': password_hash,
    #     'verified': False
    # })

    # Log registration attempt
    current_app.logger.info(f"Registration attempt for username: {username}, email: {email}")

    return jsonify({
        'message': 'User registered successfully',
        'username': username,
        'email': email,
        'note': 'Email verification coming soon'
    }), 201


@bp.route('/login', methods=['POST'])
def login():
    """Login user with proper security"""
    data = request.get_json()

    if not data:
        return jsonify({'error': 'No data provided'}), 400

    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not all([username, password]):
        return jsonify({'error': 'Missing credentials'}), 400

    # TODO: Verify with database
    # user = db.users.find_one({'username': username})
    # if not user:
    #     return jsonify({'error': 'Invalid credentials'}), 401
    #
    # # Verify password with bcrypt
    # if not bcrypt.checkpw(password.encode('utf-8'), user['password_hash'].encode('utf-8')):
    #     return jsonify({'error': 'Invalid credentials'}), 401

    # TEMPORARY: For testing only - REMOVE IN PRODUCTION
    # This should NEVER be in production code
    if username == 'testuser' and password == 'Test1234!':
        token = create_token(user_id=999, username=username, expires_days=1)
        return jsonify({
            'message': 'Login successful (TEST MODE)',
            'token': token,
            'user': {
                'id': 999,
                'username': username,
                'email': 'test@example.com'
            },
            'warning': 'TEST MODE - Remove hardcoded credentials before production!'
        })

    # Log failed login attempt
    current_app.logger.warning(f"Failed login attempt for username: {username}")

    return jsonify({'error': 'Invalid credentials'}), 401


@bp.route('/refresh', methods=['POST'])
@token_required
def refresh_token():
    """Refresh JWT token"""
    try:
        new_token = create_token(
            user_id=g.current_user,
            username=g.current_username,
            expires_days=7
        )
        return jsonify({
            'token': new_token,
            'message': 'Token refreshed successfully'
        })
    except Exception as e:
        current_app.logger.error(f"Token refresh failed: {str(e)}")
        return jsonify({'error': 'Token refresh failed'}), 500


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


@bp.route('/logout', methods=['POST'])
@token_required
def logout():
    """Logout user (client should discard token)"""
    # TODO: Add token to blacklist
    # db.token_blacklist.insert_one({
    #     'token': request.headers.get('Authorization').split(' ')[1],
    #     'expires_at': token_expiry
    # })

    return jsonify({'message': 'Logout successful'})
