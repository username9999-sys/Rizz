# 📦 WORKING DEMOS - Quick Start Guide

**Purpose:** Ensure every module has a working demo that can be run locally

---

## ✅ VERIFIED WORKING DEMOS

### 1. API Server
**Status:** ✅ Working  
**Quick Start:**
```bash
cd api-server
pip install -r requirements.txt
python app.py
# Access: http://localhost:5000
```

**Test:**
```bash
curl http://localhost:5000/health
```

### 2. Web App (Portfolio)
**Status:** ✅ Working  
**Quick Start:**
```bash
cd web-app
# Option 1: Static
open index.html

# Option 2: With backend
npm install
npm start
# Access: http://localhost:3000
```

### 3. CLI Tool
**Status:** ✅ Working  
**Quick Start:**
```bash
cd cli-tool
pip install -r requirements.txt
python task_manager.py --help
python task_manager.py add -t "Test Task"
python task_manager.py list
```

### 4. Discord Bot
**Status:** ✅ Working (requires token)  
**Quick Start:**
```bash
cd discord-bot
npm install
# Set DISCORD_TOKEN in .env
node index.js
```

### 5. Games (Snake & Tetris)
**Status:** ✅ Working  
**Quick Start:**
```bash
cd game
# Open in browser
open snake.html
open tetris.html
open arcade-enhanced.html
```

### 6. File Organizer
**Status:** ✅ Working  
**Quick Start:**
```bash
cd automation
python file_organizer.py organize --type ~/Downloads
python file_organizer.py organize --dry-run --type ~/Documents
```

### 7. Chat App
**Status:** ✅ Working  
**Quick Start:**
```bash
cd chat-app
npm install
npm start
# Access: http://localhost:3000
```

---

## ⚠️ DEMO/CONCEPT MODULES

These modules are conceptual demos, not full implementations:

### AI/ML Platform
**Status:** 🟡 Demo  
**What Works:** API endpoints, model registry  
**What Doesn't:** Actual ML models (placeholders)

### Blockchain
**Status:** 🟡 Demo  
**What Works:** Smart contract logic, DEX calculations  
**What Doesn't:** Not connected to real blockchain

### IoT Platform
**Status:** 🟡 Demo  
**What Works:** Device management API, MQTT integration  
**What Doesn't:** No real devices (simulation only)

### CRM
**Status:** 🟡 Demo  
**What Works:** Contact/deal management  
**What Doesn't:** Email integration, full automation

### E-commerce
**Status:** 🟡 Demo  
**What Works:** Product catalog, cart  
**What Doesn't:** Real payment processing

### Streaming
**Status:** 🟡 Demo  
**What Works:** Video upload, basic streaming  
**What Doesn't:** Live streaming, transcoding (needs FFmpeg setup)

### Cloud Storage
**Status:** 🟡 Demo  
**What Works:** File upload/download  
**What Doesn't:** Real-time collaboration (needs WebSocket setup)

### Social Media
**Status:** 🟡 Demo  
**What Works:** Posts, comments  
**What Doesn't:** Stories, reels (needs more development)

---

## 🛠️ HOW TO TEST DEMOS

### Automated Testing
```bash
# Run all demo tests
python scripts/test_demos.py

# Test specific module
python scripts/test_demos.py api-server
```

### Manual Testing Checklist
- [ ] Module starts without errors
- [ ] Basic functionality works
- [ ] API endpoints respond
- [ ] No console errors
- [ ] Documentation matches behavior

---

## 📝 DEMO IMPROVEMENT ROADMAP

### Phase 1: Core Modules (Week 1-2)
- [x] API Server - Already working
- [x] CLI Tool - Already working
- [x] Games - Already working
- [ ] Discord Bot - Add setup guide

### Phase 2: Web Apps (Week 2-3)
- [x] Web App - Already working
- [x] Chat App - Already working
- [ ] E-commerce - Add demo products
- [ ] Admin Dashboard - Create basic UI

### Phase 3: Advanced Modules (Week 3-4)
- [ ] AI/ML - Add working model examples
- [ ] Blockchain - Add testnet integration
- [ ] IoT - Add device simulation
- [ ] Streaming - Add FFmpeg setup

---

## 🎯 DEMO QUALITY STANDARDS

Each demo should have:
- ✅ Clear README with quick start
- ✅ Working code that runs without errors
- ✅ Example data/configuration
- ✅ Screenshot or GIF demo
- ✅ Known limitations documented

---

**Last Updated:** March 2026  
**Working Demos:** 7/20 modules  
**Demo/Concept:** 13/20 modules  
**Goal:** Make all 20 modules have working demos
