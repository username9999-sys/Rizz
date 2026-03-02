"""
Test Fixtures - Authentication
"""

import pytest
import jwt
import datetime

@pytest.fixture
def auth_token():
    """Generate valid JWT token for testing"""
    payload = {
        'user_id': 1,
        'username': 'testuser',
        'exp': datetime.datetime.utcnow() + datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, 'test-secret-key', algorithm='HS256')

@pytest.fixture
def expired_token():
    """Generate expired JWT token"""
    payload = {
        'user_id': 1,
        'username': 'testuser',
        'exp': datetime.datetime.utcnow() - datetime.timedelta(hours=1)
    }
    return jwt.encode(payload, 'test-secret-key', algorithm='HS256')
