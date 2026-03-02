# 🚀 Rizz Project Collection

Koleksi project lengkap yang dibuat dengan ❤️ oleh **username9999**

## 📁 Daftar Project

### 1. 🌐 Web Application - Portfolio Website
**Lokasi:** `web-app/`

Portfolio website modern dengan desain dark theme yang elegan.

**Fitur:**
- ✨ Responsive design (mobile-friendly)
- 🎨 Dark theme dengan gradient accents
- 📱 Mobile navigation
- 📧 Contact form dengan validasi
- ⚡ Smooth scroll animations
- 🎯 Intersection Observer untuk animasi

**File:**
- `index.html` - Struktur HTML
- `styles.css` - Styling CSS
- `script.js` - Interaktivitas JavaScript

**Cara Menggunakan:**
```bash
# Buka langsung di browser
open web-app/index.html
```

---

### 2. 💻 CLI Tool - Task Manager
**Lokasi:** `cli-tool/`

Aplikasi manajemen tugas berbasis command-line yang powerful.

**Fitur:**
- ✅ CRUD operations untuk tasks
- 📊 Statistik dan tracking
- 🔍 Pencarian tasks
- 📁 Manajemen kategori
- 🏷️ Priority levels
- 📅 Due date tracking
- 💾 SQLite database
- 📤 Export ke JSON/CSV

**Instalasi:**
```bash
cd cli-tool
pip install -r requirements.txt
python task_manager.py --help
```

**Contoh Penggunaan:**
```bash
# Tambah task baru
python task_manager.py add -t "Belajar Python" -p high -c learning

# List semua tasks
python task_manager.py list

# Complete task
python task_manager.py complete 1

# Lihat statistik
python task_manager.py stats
```

---

### 3. 🔌 API Server - REST API
**Lokasi:** `api-server/`

REST API yang scalable dengan autentikasi JWT dan database integration.

**Fitur:**
- 🔐 JWT Authentication
- 👤 User registration & login
- 📝 CRUD Posts API
- 💬 Comments system
- 🔒 Protected endpoints
- 📚 Auto-generated API docs

**Instalasi:**
```bash
cd api-server
pip install -r requirements.txt
python app.py
```

**Endpoint Utama:**
```bash
# Login
POST /api/auth/login

# Get Posts
GET /api/posts

# Create Post (auth required)
POST /api/posts
Headers: Authorization: Bearer <token>

# Add Comment
POST /api/posts/:id/comments
```

**Default Credentials:**
- Username: `admin`
- Password: `admin123`

---

### 4. 🎮 Game - Snake Game
**Lokasi:** `game/`

Classic snake game yang dibangun dengan HTML5 Canvas dan JavaScript.

**Fitur:**
- 🐍 Smooth snake movement
- 🍎 Glowing food effect
- 📊 Score & High Score tracking
- ⏸️ Pause functionality
- 📱 Mobile controls support
- 🎨 Modern dark theme
- 💾 LocalStorage untuk high score

**Cara Bermain:**
```bash
# Buka di browser
open game/index.html
```

**Kontrol:**
- **Arrow Keys** atau **WASD** - Gerakan snake
- **SPACE** atau **P** - Pause game

---

### 5. 🗂️ Automation - File Organizer
**Lokasi:** `automation/`

Script otomatisasi untuk mengorganisir file berdasarkan type, date, atau custom rules.

**Fitur:**
- 📁 Organize by file type
- 📅 Organize by date
- ⚙️ Custom rules support
- 💾 Dry run mode
- ↩️ Undo functionality
- 📊 Detailed statistics

**Instalasi:**
```bash
cd automation
# Tidak perlu install dependencies (pure Python)
```

**Contoh Penggunaan:**
```bash
# Organize by type
python file_organizer.py organize --type ~/Downloads

# Organize by date
python file_organizer.py organize --date ~/Documents

# Dry run (preview)
python file_organizer.py organize --dry-run --type ~/Downloads

# Custom rules
python file_organizer.py organize --rules organizer_rules.json ~/Projects

# Undo last operation
python file_organizer.py undo
```

---

## 🛠️ Tech Stack

| Project | Technologies |
|---------|-------------|
| Web App | HTML5, CSS3, JavaScript, Font Awesome |
| CLI Tool | Python, Click, SQLite |
| API Server | Python, Flask, Flask-CORS, PyJWT |
| Game | HTML5 Canvas, JavaScript, CSS3 |
| Automation | Python (standard library) |

---

## 📦 Quick Start

```bash
# Clone repository
git clone https://github.com/username9999-sys/Rizz.git
cd Rizz-Project

# Install all dependencies
pip install -r requirements.txt

# Or install per project
cd cli-tool && pip install -r requirements.txt
cd ../api-server && pip install -r requirements.txt
```

---

## 📸 Screenshots

### Portfolio Website
Modern dark-themed portfolio with smooth animations

### Task Manager CLI
Powerful command-line task management

### REST API
Full-featured API with authentication

### Snake Game
Classic arcade game with modern UI

### File Organizer
Automated file organization tool

---

## 🤝 Contributing

Feel free to fork this project and submit pull requests!

## 📄 License

MIT License - username9999

## 👨‍💻 Author

**username9999**
- GitHub: [@username9999-sys](https://github.com/username9999-sys)
- Email: faridalfarizi179@gmail.com

---

Built with ❤️ and lots of coffee ☕
