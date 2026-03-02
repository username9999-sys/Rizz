# 🛠️ Developer Setup Guide

**Step-by-step guide** to set up your development environment for Rizz Platform.

---

## 📋 Prerequisites

Install these tools first:

- [ ] **Git** - Version control
- [ ] **Python 3.11+** - Backend development
- [ ] **Node.js 18+** - Frontend development
- [ ] **Docker & Docker Compose** - Containerization
- [ ] **VS Code** (recommended) or any code editor

---

## 🚀 Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/username9999-sys/Rizz.git
cd Rizz-Project
```

### 2. Setup Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Generate secure passwords
# Linux/Mac:
openssl rand -base64 32 >> .env

# Or edit .env manually and replace all CHANGE_ME values
```

**⚠️ IMPORTANT**: You MUST generate secure passwords! Don't use defaults.

### 3. Install Dependencies

```bash
# Python (API Server)
cd api-server
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
pip install -r requirements.txt

# JavaScript (Web App)
cd ../web-app
npm install

# Install pre-commit hooks (optional but recommended)
cd ..
pip install pre-commit
pre-commit install
```

### 4. Start Development Environment

```bash
# Start all services with Docker
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api

# Stop services
docker-compose down
```

---

## 🧪 Running Tests

### Python Tests

```bash
# Activate virtual environment first
cd api-server
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
pytest tests/test_comprehensive.py -v

# Run specific test
pytest tests/test_comprehensive.py::TestAuthentication::test_login_success -v
```

### JavaScript Tests

```bash
cd web-app
npm test
```

---

## 💻 Development Workflow

### 1. Create Feature Branch

```bash
git checkout -b feature/your-feature-name
```

### 2. Make Changes

- Write code
- Write tests
- Run linting

```bash
# Python linting
flake8 api-server/app/
black api-server/app/
isort api-server/app/

# JavaScript linting
npm run lint
```

### 3. Run Tests

```bash
# Make sure tests pass before committing
pytest
```

### 4. Commit Changes

```bash
# Pre-commit hooks will run automatically
git add .
git commit -m "feat: add your feature description"
```

### 5. Push and Create PR

```bash
git push origin feature/your-feature-name
# Then create Pull Request on GitHub
```

---

## 🔧 Common Issues

### Issue: Docker containers won't start

**Solution:**
```bash
# Check if ports are in use
docker ps
lsof -i :5000
lsof -i :5432

# Stop conflicting services
docker-compose down
docker-compose up -d
```

### Issue: Database connection errors

**Solution:**
```bash
# Check .env file has correct passwords
cat .env | grep PASSWORD

# Restart database
docker-compose restart postgres

# Check logs
docker-compose logs postgres
```

### Issue: Tests failing

**Solution:**
```bash
# Make sure dependencies are installed
pip install -r api-server/requirements.txt

# Check test database is setup
pytest --setup-db

# Run tests with more verbose output
pytest -v -s
```

### Issue: Pre-commit hooks failing

**Solution:**
```bash
# Install pre-commit
pip install pre-commit
pre-commit install

# Run hooks manually
pre-commit run --all-files

# Skip hooks (not recommended)
git commit -m "message" --no-verify
```

---

## 📁 Project Structure

```
Rizz-Project/
├── api-server/              # Python Flask API
│   ├── app/                # Main application
│   ├── tests/              # Test suite
│   ├── requirements.txt    # Python dependencies
│   └── Dockerfile
│
├── web-app/                # React/Node.js frontend
│   ├── src/               # Source code
│   ├── package.json       # Node dependencies
│   └── Dockerfile
│
├── .github/workflows/     # GitHub Actions
├── docker-compose.yml     # Docker configuration
├── .env.example          # Environment template
└── README.md             # This file
```

---

## 🎯 Next Steps

After setup, you can:

1. **Explore the codebase**
   - Start with `api-server/app/__init__.py`
   - Check out `api-server/tests/test_comprehensive.py`

2. **Make your first change**
   - Fix a small bug
   - Add a test
   - Improve documentation

3. **Learn the architecture**
   - Read [DEPLOYMENT.md](DEPLOYMENT.md)
   - Check [SECURITY.md](SECURITY.md)

4. **Contribute**
   - See [CONTRIBUTING.md](CONTRIBUTING.md)
   - Check open issues

---

## 📞 Getting Help

- **Documentation**: Check README.md, DEPLOYMENT.md
- **Issues**: Create GitHub issue
- **Code Questions**: Read existing code and tests

---

## ✅ Setup Checklist

Before you start developing:

- [ ] Git repository cloned
- [ ] Python 3.11+ installed
- [ ] Node.js 18+ installed
- [ ] Docker installed and running
- [ ] .env file created with secure passwords
- [ ] Dependencies installed (pip, npm)
- [ ] Pre-commit hooks installed (optional)
- [ ] Tests running successfully
- [ ] Docker containers starting successfully

---

**Happy Coding!** 🚀

If you encounter issues not covered here, please create a GitHub issue.
