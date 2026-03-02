"""
Comprehensive Test Suite for Rizz API Server
Coverage: Unit, Integration, E2E
"""

import pytest
import json
from datetime import datetime
from app import create_app
from app.models import db, User, Role, Post
from config.settings import TestingConfig


@pytest.fixture
def app():
    """Create test application"""
    app = create_app('testing')
    
    with app.app_context():
        db.create_all()
        
        # Create test data
        user_role = Role(name='user', description='Test user')
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
    """Create authenticated client"""
    # Register test user
    client.post('/api/v2/auth/register', json={
        'username': 'testuser',
        'email': 'test@example.com',
        'password': 'TestPass123!'
    })
    
    # Login
    response = client.post('/api/v2/auth/login', json={
        'username': 'testuser',
        'password': 'TestPass123!'
    })
    
    token = response.get_json()['access_token']
    client.environ_base['HTTP_AUTHORIZATION'] = f'Bearer {token}'
    
    return client


class TestHealth:
    """Health check tests"""
    
    def test_health_endpoint(self, client):
        """Test health check returns healthy status"""
        response = client.get('/health')
        data = response.get_json()
        
        assert response.status_code == 200
        assert data['status'] == 'healthy'
        assert 'version' in data
        assert 'timestamp' in data


class TestAuthentication:
    """Authentication tests"""
    
    def test_register_success(self, client):
        """Test successful registration"""
        response = client.post('/api/v2/auth/register', json={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'SecurePass123!'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'access_token' in data
        assert data['user']['username'] == 'newuser'
    
    def test_register_duplicate_username(self, client):
        """Test registration with existing username"""
        # Create user
        client.post('/api/v2/auth/register', json={
            'username': 'existing',
            'email': 'existing@example.com',
            'password': 'Pass123!'
        })
        
        # Try duplicate
        response = client.post('/api/v2/auth/register', json={
            'username': 'existing',
            'email': 'another@example.com',
            'password': 'Pass123!'
        })
        
        assert response.status_code == 409
    
    def test_register_duplicate_email(self, client):
        """Test registration with existing email"""
        client.post('/api/v2/auth/register', json={
            'username': 'user1',
            'email': 'duplicate@example.com',
            'password': 'Pass123!'
        })
        
        response = client.post('/api/v2/auth/register', json={
            'username': 'user2',
            'email': 'duplicate@example.com',
            'password': 'Pass123!'
        })
        
        assert response.status_code == 409
    
    def test_register_invalid_email(self, client):
        """Test registration with invalid email"""
        response = client.post('/api/v2/auth/register', json={
            'username': 'testuser',
            'email': 'invalid-email',
            'password': 'Pass123!'
        })
        
        assert response.status_code == 400
    
    def test_register_weak_password(self, client):
        """Test registration with weak password"""
        response = client.post('/api/v2/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '123'
        })
        
        assert response.status_code == 400
    
    def test_login_success(self, client):
        """Test successful login"""
        # Register first
        client.post('/api/v2/auth/register', json={
            'username': 'logintest',
            'email': 'login@example.com',
            'password': 'Pass123!'
        })
        
        # Login
        response = client.post('/api/v2/auth/login', json={
            'username': 'logintest',
            'password': 'Pass123!'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
    
    def test_login_invalid_credentials(self, client):
        """Test login with invalid credentials"""
        response = client.post('/api/v2/auth/login', json={
            'username': 'nonexistent',
            'password': 'wrongpass'
        })
        
        assert response.status_code == 401
    
    def test_get_current_user(self, auth_client):
        """Test getting current user info"""
        response = auth_client.get('/api/v2/auth/me')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'user' in data


class TestPosts:
    """Post CRUD tests"""
    
    def test_create_post(self, auth_client):
        """Test creating a new post"""
        response = auth_client.post('/api/v2/posts', json={
            'title': 'Test Post',
            'content': 'This is test content',
            'tags': ['test', 'python']
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'post' in data
        assert data['post']['title'] == 'Test Post'
    
    def test_create_post_missing_title(self, auth_client):
        """Test creating post without title"""
        response = auth_client.post('/api/v2/posts', json={
            'content': 'Content only'
        })
        
        assert response.status_code == 400
    
    def test_get_posts(self, client, auth_client):
        """Test getting all posts"""
        # Create a post first
        auth_client.post('/api/v2/posts', json={
            'title': 'Post 1',
            'content': 'Content 1'
        })
        
        response = client.get('/api/v2/posts')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'posts' in data
        assert len(data['posts']) >= 1
    
    def test_get_single_post(self, client, auth_client):
        """Test getting a single post"""
        # Create post
        create_response = auth_client.post('/api/v2/posts', json={
            'title': 'Single Post',
            'content': 'Single content'
        })
        post_id = create_response.get_json()['post']['id']
        
        response = client.get(f'/api/v2/posts/{post_id}')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'post' in data
        assert data['post']['id'] == post_id
    
    def test_update_post(self, auth_client):
        """Test updating a post"""
        # Create post
        create_response = auth_client.post('/api/v2/posts', json={
            'title': 'Original Title',
            'content': 'Original content'
        })
        post_id = create_response.get_json()['post']['id']
        
        # Update
        response = auth_client.put(f'/api/v2/posts/{post_id}', json={
            'title': 'Updated Title',
            'content': 'Updated content'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['post']['title'] == 'Updated Title'
    
    def test_delete_post(self, auth_client):
        """Test deleting a post"""
        # Create post
        create_response = auth_client.post('/api/v2/posts', json={
            'title': 'Delete Me',
            'content': 'Content to delete'
        })
        post_id = create_response.get_json()['post']['id']
        
        # Delete
        response = auth_client.delete(f'/api/v2/posts/{post_id}')
        
        assert response.status_code == 200
        
        # Verify deleted
        get_response = auth_client.get(f'/api/v2/posts/{post_id}')
        assert get_response.status_code == 404
    
    def test_unauthorized_create_post(self, client):
        """Test creating post without authentication"""
        response = client.post('/api/v2/posts', json={
            'title': 'Unauthorized',
            'content': 'No auth'
        })
        
        assert response.status_code == 401


class TestValidation:
    """Input validation tests"""
    
    def test_username_length(self, client):
        """Test username minimum length"""
        response = client.post('/api/v2/auth/register', json={
            'username': 'ab',  # Too short
            'email': 'test@example.com',
            'password': 'Pass123!'
        })
        
        assert response.status_code == 400
    
    def test_password_complexity(self, client):
        """Test password complexity requirements"""
        response = client.post('/api/v2/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'simple'  # No numbers
        })
        
        assert response.status_code == 400


class TestRateLimiting:
    """Rate limiting tests"""
    
    def test_rate_limit_auth(self, client):
        """Test rate limiting on auth endpoints"""
        # Make multiple requests
        for i in range(15):
            response = client.post('/api/v2/auth/login', json={
                'username': f'user{i}',
                'password': 'wrong'
            })
        
        # Should be rate limited
        assert response.status_code == 429


class TestPagination:
    """Pagination tests"""
    
    def test_posts_pagination(self, client, auth_client):
        """Test posts pagination"""
        # Create multiple posts
        for i in range(25):
            auth_client.post('/api/v2/posts', json={
                'title': f'Post {i}',
                'content': f'Content {i}'
            })
        
        response = client.get('/api/v2/posts?page=1&per_page=10')
        
        assert response.status_code == 200
        data = response.get_json()
        assert len(data['posts']) == 10
        assert 'pagination' in data
        assert data['pagination']['total_items'] == 25


if __name__ == '__main__':
    pytest.main(['-v', '--cov=app', '--cov-report=html', '--cov-report=term-missing'])
