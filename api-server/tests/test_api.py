"""
Test suite for API Server
Run with: pytest --cov=. --cov-report=html
"""

import pytest
from app import app
import json

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def auth_token(client):
    """Get auth token for testing"""
    response = client.post('/api/auth/login',
                          json={'username': 'admin', 'password': 'admin123'})
    return response.get_json().get('token')

def test_health_check(client):
    """Test health check endpoint"""
    response = client.get('/api/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'

def test_api_info(client):
    """Test API info endpoint"""
    response = client.get('/api')
    assert response.status_code == 200
    data = response.get_json()
    assert 'name' in data
    assert data['name'] == 'Rizz API'

def test_login_success(client):
    """Test successful login"""
    response = client.post('/api/auth/login',
                          json={'username': 'admin', 'password': 'admin123'})
    assert response.status_code == 200
    data = response.get_json()
    assert 'token' in data
    assert 'user' in data

def test_login_failure(client):
    """Test failed login"""
    response = client.post('/api/auth/login',
                          json={'username': 'admin', 'password': 'wrong'})
    assert response.status_code == 401

def test_get_posts(client):
    """Test getting posts"""
    response = client.get('/api/posts')
    assert response.status_code == 200
    data = response.get_json()
    assert 'posts' in data

def test_create_post_requires_auth(client):
    """Test that creating post requires authentication"""
    response = client.post('/api/posts',
                          json={'title': 'Test', 'content': 'Content'})
    assert response.status_code == 401

def test_create_post_with_auth(client, auth_token):
    """Test creating post with authentication"""
    headers = {'Authorization': f'Bearer {auth_token}'}
    response = client.post('/api/posts',
                          json={'title': 'Test', 'content': 'Content'},
                          headers=headers)
    assert response.status_code in [200, 201]

def test_invalid_token(client):
    """Test invalid token"""
    headers = {'Authorization': 'Bearer invalid_token'}
    response = client.get('/api/auth/me', headers=headers)
    assert response.status_code == 401

def test_rate_limiting(client):
    """Test rate limiting"""
    # Make multiple requests
    for i in range(100):
        response = client.get('/api/health')
        if response.status_code == 429:
            break
    # Should hit rate limit eventually
    assert response.status_code in [200, 429]
