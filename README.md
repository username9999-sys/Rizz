# 🚀 Rizz Project Collection - Enhanced Edition

Koleksi project lengkap yang telah di-enhance dengan fitur-fitur advanced! Dibuat dengan ❤️ oleh **username9999**

## 📁 Daftar Project (Enhanced)

### 1. 🌐 Web Application - Portfolio + Blog + Backend
**Lokasi:** `web-app/`

Portfolio website modern dengan backend Express.js, blog CMS, dan dark/light theme.

**Fitur Baru:**
- ✨ **Dark/Light Theme Toggle** dengan localStorage persistence
- 📝 **Blog System** dengan categories, tags, views counter
- 🔌 **Express.js Backend** dengan MongoDB
- 📧 **Contact Form** dengan email notifications
- 📊 **Visitor Analytics** dengan tracking
- 🔐 **Admin Authentication** (JWT)
- 📱 **Fully Responsive** mobile design
- ⚡ **SEO Optimized**

**Tech Stack:**
- Frontend: HTML5, CSS3, JavaScript (Vanilla)
- Backend: Node.js, Express.js
- Database: MongoDB
- Features: JWT Auth, Rate Limiting, CORS, Helmet

**Quick Start:**
```bash
cd web-app
npm install
cp .env.example .env
npm run dev
```

---

### 2. 💻 CLI Tool - Task Manager + GUI
**Lokasi:** `cli-tool/`

Task management application dengan CLI dan Desktop GUI.

**Fitur Baru:**
- 🖥️ **Desktop GUI** dengan Tkinter (dark theme)
- 🔄 **Recurring Tasks** (daily, weekly, monthly)
- 📊 **Statistics Dashboard** dengan charts
- 💾 **Export** ke JSON/CSV/PDF
- 🔍 **Advanced Search** dengan filters
- ⚡ **Keyboard Shortcuts** lengkap
- 📅 **Due Date Reminders**
- 🎨 **Modern UI** dengan treeview

**Commands:**
```bash
# CLI Version
python task_manager.py add -t "Task" -p high
python task_manager.py gui  # Launch GUI

# Or directly
python task_manager_gui.py
```

---

### 3. 🔌 API Server - Production Ready
**Lokasi:** `api-server/`

REST API yang scalable dengan PostgreSQL, Redis, dan Docker support.

**Fitur Baru:**
- 🐘 **PostgreSQL** database dengan advanced schema
- 🔴 **Redis** caching untuk performance
- 📚 **Swagger/OpenAPI** documentation
- 🐳 **Docker** containerization
- 🔐 **Rate Limiting** dengan Redis
- 📝 **Audit Logging** system
- 🏷️ **Tags System** untuk posts
- 📊 **Database Views** untuk statistics
- 🔄 **Database Triggers** untuk auto-update

**Endpoints:**
- `/api/auth/*` - Authentication
- `/api/posts/*` - Blog posts CRUD
- `/api/comments/*` - Comments system
- `/api/tags/*` - Tag management
- `/api/stats` - Analytics
- `/api/health` - Health check

**Quick Start:**
```bash
# With Docker
docker-compose up -d

# Manual
cd api-server
pip install -r requirements.txt
python app.py
```

---

### 4. 🎮 Snake Game - Enhanced Edition
**Lokasi:** `game/`

Classic snake game dengan power-ups, multiple modes, dan leaderboard.

**Fitur Baru:**
- ⚡ **Power-ups:**
  - 🟡 Speed Boost - Move faster
  - 🔵 Slow Motion - Move slower
  - 🟣 Double Points - 2x score
  - 🩷 Ghost Mode - Pass through walls
  - 🟢 Shrink - Reduce snake size
- 🎯 **Game Modes:**
  - Classic - Unlimited play
  - Timed - 3 minutes challenge
  - Survival - Increasing difficulty
- 🏆 **Leaderboard** dengan localStorage
- 🔥 **Combo System** - Eat fast for multiplier
- 📊 **Statistics** tracking
- 🎨 **Enhanced Graphics** dengan gradients
- 📱 **Mobile Controls** support

**Controls:**
- Arrow Keys / WASD - Move
- SPACE / P - Pause
- Touch controls on mobile

---

### 5. 🗂️ File Organizer - Pro Version
**Lokasi:** `automation/`

File organization tool dengan GUI dan real-time monitoring.

**Fitur Baru:**
- 🖥️ **Desktop GUI** dengan Tkinter (dark theme)
- 👁️ **Real-time Monitoring** dengan Watchdog
- ⚡ **Auto-organization** untuk new files
- 📊 **Progress Tracking** dengan statistics
- 📝 **Activity Log** dengan timestamps
- 🔄 **Undo Support** dengan manifest
- 📋 **Custom Rules** editor
- 📤 **Export Reports** (TXT, CSV)
- 🎨 **Modern UI** dengan progress bars

**Usage:**
```bash
# GUI Version
python file_organizer_gui.py

# CLI Version
python file_organizer.py organize --type ~/Downloads
python file_organizer.py organize --date --date-format "%Y-%m" ~/Documents
```

---

## 🛠️ Tech Stack (Complete)

| Project | Frontend | Backend | Database | DevOps |
|---------|----------|---------|----------|--------|
| Web App | HTML/CSS/JS | Node.js/Express | MongoDB | Docker |
| CLI Tool | Tkinter | Python | SQLite | - |
| API Server | - | Python/Flask | PostgreSQL/Redis | Docker |
| Game | HTML5 Canvas | JavaScript | LocalStorage | - |
| File Organizer | Tkinter | Python | - | - |

---

## 🐳 Docker Deployment

### Quick Deploy
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop all
docker-compose down
```

### Services
- **PostgreSQL** (port 5432) - Main database
- **Redis** (port 6379) - Caching layer
- **MongoDB** (port 27017) - Portfolio database
- **API Server** (port 5000) - REST API
- **Portfolio** (port 3000) - Web app
- **Nginx** (port 80/443) - Reverse proxy

---

## 🔄 CI/CD Pipeline

GitHub Actions workflow includes:
- ✅ Multi-version Python testing (3.9, 3.10, 3.11)
- ✅ Multi-version Node.js testing (18, 20, 21)
- ✅ Code linting (flake8, black)
- ✅ Unit tests dengan coverage
- ✅ Docker image building
- ✅ Security scanning (Trivy)
- ✅ Auto-deployment to production

---

## 📊 Project Statistics

```
Total Files: 50+
Lines of Code: 10,000+
Features: 100+
Technologies: 15+
Docker Containers: 6
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.9+
- Node.js 18+
- Docker & Docker Compose
- Git

### Installation

```bash
# Clone repository
git clone https://github.com/username9999-sys/Rizz.git
cd Rizz-Project

# Install Python dependencies
pip install -r requirements.txt

# Install Node.js dependencies
cd web-app && npm install

# Start with Docker
docker-compose up -d
```

### Environment Setup

```bash
# Copy environment files
cp .env.example .env

# Edit with your credentials
# - Database URLs
# - API keys
# - Secret keys
```

---

## 📖 Documentation

- [Web App Guide](web-app/README.md)
- [CLI Tool Guide](cli-tool/README.md)
- [API Server Guide](api-server/README.md)
- [Game Guide](game/README.md)
- [File Organizer Guide](automation/README.md)

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📄 License

MIT License - username9999

---

## 👨‍💻 Author

**username9999**
- GitHub: [@username9999-sys](https://github.com/username9999-sys)
- Email: faridalfarizi179@gmail.com
- Portfolio: https://username9999.dev

---

## 🙏 Acknowledgments

- Font Awesome for icons
- Flask/Express communities
- Python/Node.js communities
- All open-source contributors

---

Built with ❤️, ☕, and 🎵 by username9999

**Last Updated:** March 2026
