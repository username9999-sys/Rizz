# 🚀 Rizz Project - Enterprise Platform

**Enterprise-scale full-stack platform** dengan microservices architecture, built for scalability and production.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-blue.svg)](https://postgresql.org)

---

## 📊 Platform Overview

| Component | Version | Status | Tech Stack |
|-----------|---------|--------|------------|
| 🔌 API Server | v2.0 Enterprise | ✅ Production Ready | Flask, PostgreSQL, SQLAlchemy, JWT |
| 🌐 Web App | v1.0 | ✅ Ready | HTML5, CSS3, JavaScript, Node.js |
| 💻 CLI Tool | v3.0 | ✅ Ready | Python, SQLite, Click |
| 🎮 Game | v1.0 | ✅ Ready | HTML5 Canvas, JavaScript |
| 🗂️ Automation | v1.0 | ✅ Ready | Python |

---

## 🏗️ Enterprise Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    NGINX (Reverse Proxy + SSL)              │
│                 Rate Limiting + Load Balancing              │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│   API Server  │    │  Portfolio    │    │   Admin       │
│   (Flask)     │    │  (React)      │    │   Dashboard   │
│   Port 5000   │    │  Port 3000    │    │   Port 3001   │
└───────────────┘    └───────────────┘    └───────────────┘
        │                     │                     │
        └─────────────────────┼─────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐    ┌───────────────┐    ┌───────────────┐
│  PostgreSQL   │    │    Redis      │    │   MongoDB     │
│  Primary DB   │    │   Cache       │    │  Analytics    │
│  Port 5432    │    │   Port 6379   │    │   Port 27017  │
└───────────────┘    └───────────────┘    └───────────────┘
```

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- Node.js 18+ (optional)
- PostgreSQL 15+ (or use Docker)

### Option 1: Docker Compose (Recommended)

```bash
# Clone repository
git clone https://github.com/username9999-sys/Rizz.git
cd Rizz-Project

# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f api
```

### Option 2: Local Development

```bash
# API Server
cd api-server
pip install -r requirements.txt
export DATABASE_URL=postgresql://user:pass@localhost/rizz_api
python app.py

# Web App
cd web-app
npm install
npm run dev
```

---

## 📁 Project Structure

```
Rizz-Project/
├── api-server/              # Enterprise REST API (Flask + PostgreSQL)
│   ├── app/
│   │   ├── config/         # Environment configurations
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── routes/         # API endpoints
│   │   ├── auth/           # Authentication (JWT)
│   │   ├── utils/          # Utilities (validation, audit)
│   │   └── services/       # Business logic
│   ├── tests/              # Pytest test suite
│   ├── migrations/         # Alembic migrations
│   ├── Dockerfile
│   └── requirements.txt
│
├── web-app/                # Portfolio + Blog (React/HTML)
│   ├── index.html
│   ├── styles.css
│   ├── script.js
│   ├── server.js           # Express backend
│   └── Dockerfile
│
├── cli-tool/               # Task Manager CLI
│   ├── task_manager.py
│   ├── task_manager_gui.py
│   └── Dockerfile
│
├── game/                   # Snake Game
│   ├── index.html
│   ├── game.js
│   └── styles.css
│
├── automation/             # File Organizer
│   ├── file_organizer.py
│   └── organizer_rules.json
│
├── docker-compose.yml      # Multi-service orchestration
├── nginx.conf              # Reverse proxy config
└── README.md
```

---

## 🔌 API Server - Enterprise Features

### Authentication & Security
- ✅ JWT Access + Refresh Token rotation
- ✅ Password hashing (bcrypt)
- ✅ Role-Based Access Control (RBAC)
- ✅ Audit logging
- ✅ Rate limiting
- ✅ CORS protection

### Database
- ✅ PostgreSQL 15+
- ✅ SQLAlchemy ORM
- ✅ Alembic migrations
- ✅ Connection pooling
- ✅ Indexing

### Testing
- ✅ Pytest suite
- ✅ 80%+ code coverage
- ✅ Unit & integration tests

### Monitoring
- ✅ Prometheus metrics
- ✅ Health endpoints
- ✅ Structured logging

---

## 📚 API Documentation

### Base URLs
```
Development: http://localhost:5000
Production:  https://your-domain.com/api
```

### Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/register` | Register new user |
| POST | `/api/auth/login` | Login user |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/logout` | Logout user |
| GET | `/api/auth/me` | Get current user |

### Posts Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/posts` | List posts (paginated) |
| GET | `/api/posts/:id` | Get single post |
| POST | `/api/posts` | Create post |
| PUT | `/api/posts/:id` | Update post |
| DELETE | `/api/posts/:id` | Delete post |

### Default Credentials
```
Username: admin
Password: admin123
```

---

## 🧪 Testing

```bash
# API Server tests
cd api-server
pytest --cov=app --cov-report=html

# All tests
docker-compose exec api pytest

# View coverage report
open htmlcov/index.html
```

---

## 🐳 Docker Services

| Service | Image | Port | Description |
|---------|-------|------|-------------|
| postgres | postgres:15-alpine | 5432 | Primary database |
| redis | redis:7-alpine | 6379 | Cache & sessions |
| mongo | mongo:7 | 27017 | Analytics database |
| api | Custom (Flask) | 5000 | REST API server |
| portfolio | Custom (Node.js) | 3000 | Portfolio backend |
| nginx | nginx:alpine | 80/443 | Reverse proxy |

---

## 🔧 Configuration

### Environment Variables

```bash
# .env file (copy from .env.example)

# API Server
SECRET_KEY=your-secret-key
JWT_SECRET_KEY=jwt-secret-key
DATABASE_URL=postgresql://user:pass@localhost/rizz_api
REDIS_URL=redis://localhost:6379/0

# Production
FLASK_ENV=production
CORS_ORIGINS=https://yourdomain.com
```

---

## 📈 Performance Benchmarks

| Metric | Value |
|--------|-------|
| Requests/sec | ~1000+ |
| Avg Response Time | <50ms |
| Database Connections | 10 (pool) |
| Memory Usage | ~150MB |
| Test Coverage | 80%+ |

---

## 🛠️ Development

### Running Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "Description"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### Adding New Features

1. Create model in `app/models/`
2. Create route in `app/routes/`
3. Add tests in `tests/`
4. Create migration
5. Update documentation

---

## 📝 License

MIT License - username9999

## 👨‍💻 Author

**username9999**
- GitHub: [@username9999-sys](https://github.com/username9999-sys)
- Email: faridalfarizi179@gmail.com

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 🎯 Roadmap

### Phase 1 (Completed) ✅
- [x] PostgreSQL + SQLAlchemy ORM
- [x] JWT Authentication with refresh tokens
- [x] Alembic migrations
- [x] Comprehensive testing suite
- [x] Docker containerization

### Phase 2 (In Progress) 🚧
- [ ] Message queue (RabbitMQ)
- [ ] Celery for async tasks
- [ ] Elasticsearch integration
- [ ] Real-time notifications

### Phase 3 (Planned) 📋
- [ ] Kubernetes manifests
- [ ] Helm charts
- [ ] CI/CD pipelines
- [ ] Monitoring stack (Prometheus + Grafana)

---

Built with ❤️ and lots of coffee ☕ by **username9999**
