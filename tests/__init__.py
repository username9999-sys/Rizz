"""
Rizz Platform - Comprehensive Test Suite
Test coverage goals: 80%+ for all modules
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Test configuration
pytest_plugins = [
    "tests.fixtures.database",
    "tests.fixtures.api_client",
    "tests.fixtures.auth"
]

# Run with: pytest --cov=. --cov-report=html --cov-report=term-missing
