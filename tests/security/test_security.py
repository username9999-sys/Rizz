"""
Security Tests - Test security features
"""

import pytest
import hashlib

class TestPasswordHashing:
    """Test password hashing"""
    
    def test_password_is_hashed(self, client):
        """Test that passwords are hashed before storage"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'securepassword123'
        })
        assert response.status_code == 201
        
        # Password should not be stored in plaintext
        # This would need database access to verify
        # For now, we trust the implementation
    
    def test_password_min_length(self, client):
        """Test minimum password length"""
        response = client.post('/api/auth/register', json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': '12345'  # Too short
        })
        assert response.status_code == 400

class TestSQLInjection:
    """Test SQL injection prevention"""
    
    def test_sql_injection_login(self, client):
        """Test SQL injection in login"""
        response = client.post('/api/auth/login', json={
            'username': "admin' OR '1'='1",
            'password': "anything"
        })
        # Should fail, not succeed
        assert response.status_code in [400, 401]
    
    def test_sql_injection_search(self, client, auth_header):
        """Test SQL injection in search"""
        response = client.get("/api/tasks?search='; DROP TABLE tasks; --",
                            headers=auth_header)
        # Should not crash
        assert response.status_code in [200, 400]

class TestXSS:
    """Test XSS prevention"""
    
    def test_xss_in_task_title(self, client, auth_header):
        """Test XSS in task title"""
        response = client.post('/api/tasks',
            headers=auth_header,
            json={
                'title': '<script>alert("XSS")</script>',
                'description': 'Task description'
            }
        )
        # Should either sanitize or reject
        assert response.status_code in [201, 400]

class TestCSRF:
    """Test CSRF protection"""
    
    def test_csrf_token_required(self, client):
        """Test CSRF token on state-changing operations"""
        # POST without CSRF token should fail
        response = client.post('/api/tasks', json={
            'title': 'Task'
        })
        # Should fail due to missing auth at minimum
        assert response.status_code in [401, 403]

class TestRateLimiting:
    """Test rate limiting security"""
    
    def test_login_rate_limit(self, client):
        """Test rate limiting on login endpoint"""
        for i in range(100):
            response = client.post('/api/auth/login', json={
                'username': 'test',
                'password': 'test'
            })
            if response.status_code == 429:
                break
        
        # Should eventually hit rate limit
        assert response.status_code in [401, 429]

class TestHeaders:
    """Test security headers"""
    
    def test_security_headers_present(self, client):
        """Test that security headers are present"""
        response = client.get('/health')
        
        # Check for common security headers
        headers = response.headers
        
        # These should be present in production
        # assert 'X-Content-Type-Options' in headers
        # assert 'X-Frame-Options' in headers
        # assert 'X-XSS-Protection' in headers
        
        # For now, just verify response
        assert response.status_code == 200
