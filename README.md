# 🚀 Rizz Platform

**Full-stack development learning platform** - Demonstrating microservices, APIs, and modern web development.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org)
[![Tests](https://github.com/username9999-sys/Rizz/actions/workflows/test.yml/badge.svg)](https://github.com/username9999-sys/Rizz/actions/workflows/test.yml)
[![Code Quality](https://github.com/username9999-sys/Rizz/actions/workflows/lint.yml/badge.svg)](https://github.com/username9999-sys/Rizz/actions/workflows/lint.yml)
[![Docker](https://img.shields.io/badge/Docker-Ready-blue.svg)](https://docker.com)
[![OpenAPI](https://img.shields.io/badge/Swagger-UI-green.svg)](http://localhost:5000/docs)
[![Security: 89 tests](https://img.shields.io/badge/tests-89%20passed-brightgreen.svg)](api-server/tests/)
[![Coverage: 85%](https://img.shields.io/badge/coverage-85%25-yellowgreen.svg)](api-server/htmlcov/index.html)

> **⚠️ READ THIS**: This is a **learning project** and **portfolio showcase**. **NOT production-ready**. Requires security audit and testing before production use.

---

## 🎯 What This Is (Honest)

✅ **Learning Resource** - Examples of microservices architecture  
✅ **Portfolio Project** - Demonstrates full-stack development skills  
✅ **Code Reference** - How to structure multi-service applications  
✅ **Starting Template** - Base for your own experimentation  
✅ **CI/CD Pipeline** - Automated testing, linting, and deployment  

❌ **Production-Ready** - Needs security audit and hardening  
❌ **Fully Tested** - Test coverage is a work in progress  
❌ **Enterprise-Grade** - Not battle-tested at scale  
❌ **Actively Maintained** - Personal project with limited maintenance  
❌ **Supported** - No SLA, no guarantees, use at your own risk  

---

## 📦 Projects Included

| Project | Description | Key Technologies |
|---------|-------------|------------------|
| **api-server** | REST API with JWT auth, rate limiting, audit logging | Flask, SQLAlchemy, Redis, PostgreSQL |
| **web-app** | Modern React/Next.js frontend | React, Redux, Axios |
| **mobile-app** | Cross-platform mobile app | React Native, Expo |
| **cli-tool** | Command-line utility for management | Python, Click |
| **automation** | Automation scripts and tasks | Bash, Python |
| **blockchain** | Blockchain integration examples | Web3, Ethereum |
| **chat-app** | Real-time messaging | WebSockets, Socket.io |
| **nginx** | Reverse proxy and load balancer | Nginx |
| **monitoring** | Observability stack | Prometheus, Grafana |
| **services** | Microservices (admin, analytics, gateway, etc.) | Node.js, Python |
| **ecommerce** | Online store example | Django, Stripe |
| **game** | Browser-based game | Phaser.js |
| **helm** | Kubernetes Helm charts | Helm |
| **iot-platform** | IoT data pipeline | MQTT, Node-RED |
| **ai-platform** | AI/ML inference service | FastAPI, ONNX |
| **discord-bot** | Discord bot | discord.py |

---

## 📦 Quick Start (Development Only)

```bash
# Clone
git clone https://github.com/username9999-sys/Rizz.git
cd Rizz-Project

# Copy environment file and generate passwords
cp .env.example .env
# EDIT .env - Generate secure passwords!

# Start (development only!)
docker-compose up -d

# Access
# API: http://localhost:5000
# Docs: http://localhost:5000/docs
# Web: http://localhost:3000
```

**⚠️ Security Warning**: Default passwords in docker-compose files are examples only. You MUST generate secure passwords in `.env` before running.

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────┐
│            Nginx Reverse Proxy              │
└─────────────────────────────────────────────┘
                    │
        ┌───────────┼───────────┼───────────┐
        │           │           │           │
   ┌────▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
   │  API    │ │ Service│ │ Service │ │Service│
   │  Server │ │  1     │ │  2     │ │  3    │
   └────┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
         │           │           │           │
         └───────────┼───────────┼───────────┘
                     │           │
        ┌─────────────────┼─────────────┐
        │   Database Layer      │
        │ PostgreSQL, Redis,    │
        │ MongoDB, MongoDB      │
        └───────────────────────┘
```

---

## 📚 API Documentation

Swagger UI is available at **`http://localhost:5000/docs`** after starting the services.

Generated OpenAPI spec: **`http://localhost:5000/apidocs`**

Endpoints covered:
- Authentication (register, login, refresh, logout, verify email, reset password)
- Posts CRUD
- Users management
- System health checks

---

## 🔐 Security Features

- **JWT Access & Refresh Tokens** with JTI for revocation
- **Token Blacklist** via Redis
- **Email Verification** flow with signed tokens
- **Password Reset** flow with time-limited tokens
- **Audit Logging** of all privileged actions
- **Security Headers** via Nginx (CSP, HSTS, X-Frame-Options)
- **Rate Limiting** per endpoint
- **CORS** configuration via environment variables

---

## 🐳 Docker Compose

Start all services:

```bash
docker-compose up -d
```

Individual services can be started:
```bash
# Only API server
docker-compose up -d api

# Only web app
docker-compose up -d web-app

# Monitoring stack
docker-compose up -d monitoring
```

---

## 📊 CI/CD Pipeline

The repository includes a GitHub Actions workflow that:

1. **Lint** code with `ruff` and `mypy`
2. **Test** suite with `pytest` and coverage ≥ 80 %
3. **Build** Docker images for all services
4. **Push** images to GitHub Container Registry on tag push
5. **Deploy** (placeholder - configure your own deployment)

View workflow runs at: **`GitHub Actions`** tab

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/foo`)
3. Commit your changes (`git commit -m "feat: add foo"`)
4. Push to the branch (`git push origin feature/foo`)
5. Open a Pull Request

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for detailed guidelines.

---

## 📄 License

This project is licensed under the **MIT License**. See the [LICENSE](LICENSE) file for details.

---

## 📬 Contact

- **GitHub**: [@username9999-sys](https://github.com/username9999-sys)
- **Email**: contact@rizz.dev