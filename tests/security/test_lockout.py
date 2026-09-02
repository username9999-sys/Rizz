# -*- coding: utf-8 -*-
"""Security Tests - Login lockout"""

import pytest


def test_login_lockout(client):
    """After 5 consecutive failed logins within 15 minutes, further attempts return 429"""
    username = "nonexistent"
    password = "wrongpass"
    # 5 attempts should be 401 each
    for i in range(5):
        resp = client.post('/api/auth/login', json={'username': username, 'password': password})
        assert resp.status_code == 401
    # 6th attempt should be locked out
    resp = client.post('/api/auth/login', json={'username': username, 'password': password})
    assert resp.status_code == 429


def test_user_weak_password():
    """User model must reject weak passwords"""
    from models import User
    with pytest.raises(ValueError):
        User(username='u', email='e@example.com', password='short')
