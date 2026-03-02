# Testing Infrastructure

## Setup

```bash
# Install test dependencies
pip install -r requirements-dev.txt

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html

# Run security tests
pytest tests/security/
```

## Test Structure

```
tests/
├── unit/           # Unit tests
├── integration/    # Integration tests
├── e2e/           # End-to-end tests
├── security/      # Security tests
└── conftest.py    # Test configuration
```

## Coverage Goals

- **Unit Tests:** 80%+ coverage
- **Integration Tests:** Critical paths
- **Security Tests:** All auth endpoints
- **E2E Tests:** Main user flows
