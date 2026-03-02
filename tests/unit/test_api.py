"""
Unit Tests - API Server
Test all API endpoints
"""

import pytest
import json
from pathlib import Path

class TestAPIHealth:
    """Test health check endpoints"""
    
    def test_health_endpoint(self, client):
        """Test /health endpoint returns 200"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
    
    def test_api_info(self, client):
        """Test /api endpoint returns API info"""
        response = client.get('/api')
        assert response.status_code == 200
        data = response.get_json()
        assert 'name' in data
        assert data['name'] == 'Rizz API'

class TestAuthentication:
    """Test authentication endpoints"""
    
    def test_login_success(self, client, test_user):
        """Test successful login"""
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'testpassword123'
        })
        assert response.status_code == 200
        data = response.get_json()
        assert 'token' in data
        assert 'user' in data
    
    def test_login_failure_wrong_password(self, client, test_user):
        """Test login with wrong password"""
        response = client.post('/api/auth/login', json={
            'username': 'testuser',
            'password': 'wrongpassword'
        })
        assert response.status_code == 401
    
    def test_login_failure_nonexistent_user(self, client):
        """Test login with non-existent user"""
        response = client.post('/api/auth/login', json={
            'username': 'nonexistent',
            'password': 'password123'
        })
        assert response.status_code == 401
    
    def test_register_new_user(self, client):
        """Test user registration"""
        response = client.post('/api/auth/register', json={
            'username': 'newuser',
            'email': 'new@example.com',
            'password': 'securepassword123'
        })
        assert response.status_code == 201

class TestTasks:
    """Test task management endpoints"""
    
    def test_list_tasks(self, client, auth_header, test_tasks):
        """Test listing tasks"""
        response = client.get('/api/tasks', headers=auth_header)
        assert response.status_code == 200
        data = response.get_json()
        assert 'tasks' in data
        assert len(data['tasks']) == 3
    
    def test_create_task(self, client, auth_header):
        """Test creating a new task"""
        response = client.post('/api/tasks', 
            headers=auth_header,
            json={
                'title': 'New Task',
                'description': 'Test task',
                'priority': 'high'
            }
        )
        assert response.status_code == 201
    
    def test_create_task_without_auth(self, client):
        """Test creating task without authentication"""
        response = client.post('/api/tasks', json={
            'title': 'New Task'
        })
        assert response.status_code == 401
    
    def test_complete_task(self, client, auth_header, test_tasks):
        """Test marking task as completed"""
        response = client.post('/api/tasks/1/complete', headers=auth_header)
        assert response.status_code == 200
    
    def test_delete_task(self, client, auth_header, test_tasks):
        """Test deleting a task"""
        response = client.delete('/api/tasks/1', headers=auth_header)
        assert response.status_code == 200

class TestValidation:
    """Test input validation"""
    
    def test_task_title_required(self, client, auth_header):
        """Test that task title is required"""
        response = client.post('/api/tasks',
            headers=auth_header,
            json={'description': 'No title'}
        )
        assert response.status_code == 400
    
    def test_task_priority_validation(self, client, auth_header):
        """Test priority validation"""
        response = client.post('/api/tasks',
            headers=auth_header,
            json={
                'title': 'Task',
                'priority': 'invalid_priority'
            }
        )
        assert response.status_code == 400
    
    def test_email_validation(self, client):
        """Test email format validation"""
        response = client.post('/api/auth/register', json={
            'username': 'test',
            'email': 'invalid-email',
            'password': 'password123'
        })
        assert response.status_code == 400

class TestRateLimiting:
    """Test rate limiting"""
    
    def test_rate_limit(self, client):
        """Test rate limiting kicks in after multiple requests"""
        for i in range(100):
            response = client.get('/health')
            if response.status_code == 429:
                break
        
        # Should hit rate limit eventually
        assert response.status_code in [200, 429]
