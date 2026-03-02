"""
Test configuration
"""

import os

# Test database
os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
os.environ['REDIS_URL'] = 'redis://localhost:6379/1'
os.environ['JWT_SECRET'] = 'test-secret-key'
os.environ['TESTING'] = 'true'
