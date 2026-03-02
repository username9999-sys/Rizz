"""
Test Fixtures - Database
Reusable database fixtures for testing
"""

import pytest
import sqlite3
from pathlib import Path

@pytest.fixture
def test_db():
    """Create in-memory SQLite database for testing"""
    conn = sqlite3.connect(':memory:')
    conn.row_factory = sqlite3.Row
    
    # Create test tables
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            user_id INTEGER,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    ''')
    
    conn.commit()
    yield conn
    
    conn.close()

@pytest.fixture
def test_user(test_db):
    """Create test user"""
    cursor = test_db.cursor()
    cursor.execute('''
        INSERT INTO users (username, email, password_hash)
        VALUES (?, ?, ?)
    ''', ('testuser', 'test@example.com', 'hashed_password_123'))
    
    test_db.commit()
    return {'id': cursor.lastrowid, 'username': 'testuser'}

@pytest.fixture
def test_tasks(test_db, test_user):
    """Create test tasks"""
    cursor = test_db.cursor()
    tasks = [
        ('Task 1', 'Description 1', 'pending', 'high', test_user['id']),
        ('Task 2', 'Description 2', 'completed', 'medium', test_user['id']),
        ('Task 3', 'Description 3', 'pending', 'low', test_user['id'])
    ]
    
    cursor.executemany('''
        INSERT INTO tasks (title, description, status, priority, user_id)
        VALUES (?, ?, ?, ?, ?)
    ''', tasks)
    
    test_db.commit()
    return tasks
