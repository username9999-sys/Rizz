"""
Test Suite - Authentication
Enterprise-grade testing with pytest
"""

import pytest
import json
from datetime import datetime
from app import create_app
from app.models import db, User, Role


@pytest.fixture
def app():
    """Create application for testing"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Create default role
        user_role = Role(name='user', description='Regular user', permissions=['read:posts'])
        db.session.add(user_role)
        db.session.commit()
        
        yield app
        
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Create client with authentication"""
    # Register and login to get token
    client.post('/api/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'testpass123'
    })
    
    response = client.post('/api/auth/login', json={
        'username': 'testuser',
        'password': 'testpass123'
    })
    
    token = response.get_json()['tokens']['access_token']
    client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    
    return client


class TestAuth:
    """Authentication tests"""
    
    def test_register_success(self, client):
        """Test successful registration"""
        response = client.post('/api/auth/register', json={
            'username': 'newuser',
            'email': 'newuser@example.com',
            'password': 'securepass123'
        })
        
        data = response.get_json()
        assert response.status_code == 201
        assert 'message' in data
        assert 'user' in data
        assert 'tokens' in data
        assert data['user']['username'] == 'newuser'
    
    def test_register_duplicate_username(self, client, app):
        """Test registration with existing username"""
        # Create user
        user = User(username='existing', email='existing@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        # Try to register with same username
        response = client.post('/api/auth/register', json={
            'username': 'existing',
            'email': 'another@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 409
    
    def test_register_duplicate_email(self, client, app):
        """Test registration with existing email"""
        user = User(username='user1', email='duplicate@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        response = client.post('/api/auth/register', json={
            'username': 'user2',
            'email': 'duplicate@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 409
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'password123'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'errors' in data
        assert 'email' in data['errors']
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'errors' in data
        assert 'password' in data['errors']
    
    def test_login_success(self, client, app):
        """Test successful login"""
        # Create user
        user = User(username='logintest', email='login@example.com')
        user.set_password('password123')
        db.session.add(user)
        db.session.commit()
        
        response = client.post('/api/auth/login', json={
            'username': 'logintest',
            'password': 'password123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'tokens' in data
        assert 'access_token' in data['tokens']
        assert 'refresh_token' in data['tokens']
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 401
    
    def test_token_refresh(self, client):
        """Test token refresh"""
        # Register
        client.post('/api/auth/register', json={
            'username': 'refreshtest',
            'email': 'refresh@example.com',
            'password': 'password123'
        })
        
        # Login
        login_response = client.post('/api/auth/login', json={
            'username': 'refreshtest',
            'password': 'password123'
        })
        
        refresh_token = login_response.get_json()['tokens']['refresh_token']
        
        # Refresh
        refresh_response = client.post('/api/auth/refresh', json={
            'refresh_token': refresh_token
        })
        
        assert refresh_response.status_code == 200
        data = refresh_response.get_json()
        assert 'tokens' in data
        assert 'access_token' in data['tokens']
    
    def test_get_current_user(self, auth_client):
        """Test getting current user info"""
        response = auth_client.get('/api/auth/me')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'user' in data
        assert 'username' in data['user']
    
    def test_unauthorized_access(self, client):
        """Test accessing protected endpoint without auth"""
        response = client.get('/api/auth/me')
        
        assert response.status_code == 401
    
    def test_logout(self, auth_client):
        """Test logout"""
        response = auth_client.post('/api/auth/logout')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data


class TestValidation:
    """Input validation tests"""
    
    def test_register_missing_fields(self, client):
        """Test registration with missing required fields"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser'
            # Missing email and password
        })
        
        assert response.status_code == 400
    
    def test_login_missing_fields(self, client):
        """Test login with missing fields"""
        response = client.post('/api/auth/login', json={
            'username': 'testuser'
            # Missing password
        })
        
        assert response.status_code == 400
    
    def test_username_format(self, client):
        """Test username format validation"""
        # Invalid: starts with number
        response = client.post('/api/auth/register', json={
            'username': '123user',
            'email': 'test@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 400
        
        # Invalid: too short
        response = client.post('/api/auth/register', json={
            'username': 'ab',
            'email': 'test2@example.com',
            'password': 'password123'
        })
        
        assert response.status_code == 400
