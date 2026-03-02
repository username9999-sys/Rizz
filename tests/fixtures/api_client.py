"""
Test Fixtures - API Client
"""

import pytest
import sys
import os

# Import the actual app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'api-server'))

@pytest.fixture
def app():
    """Create test application"""
    from app import create_app
    app = create_app('testing')
    app.config['TESTING'] = True
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()

@pytest.fixture
def auth_header():
    """Return authentication header"""
    return {'Authorization': 'Bearer test_token_123'}
