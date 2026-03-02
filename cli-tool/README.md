# 🚀 Rizz Task Manager

A powerful command-line task management application built with Python.

## Features

- ✅ Add, update, delete, and complete tasks
- 📊 View task statistics
- 🔍 Search tasks
- 📁 Category management
- 🏷️ Priority levels (low, medium, high)
- 📅 Due date tracking
- 💾 SQLite database storage
- 📤 Export to JSON/CSV

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Make executable (optional)
chmod +x task_manager.py
```

## Usage

```bash
# Run the CLI
python task_manager.py [command] [options]

# Or with alias
alias rizz='python task_manager.py'
rizz [command] [options]
```

## Commands

### Task Commands

| Command | Description |
|---------|-------------|
| `add` | Add a new task |
| `list` | List tasks with filters |
| `complete` | Mark task as completed |
| `delete` | Delete a task |
| `update` | Update a task |
| `show` | Show task details |
| `stats` | Show statistics |
| `clear` | Clear completed tasks |
| `search` | Search tasks |
| `export` | Export tasks to file |

### Category Commands

| Command | Description |
|---------|-------------|
| `category list` | List all categories |
| `category add` | Add new category |
| `category delete` | Delete a category |

## Examples

```bash
# Add a new task
python task_manager.py add -t "Complete project" -d "Finish the Rizz project" -p high -c work -due 2026-03-10

# List all pending tasks
python task_manager.py list -s pending

# List high priority tasks
python task_manager.py list -p high

# Complete a task
python task_manager.py complete 1

# Update a task
python task_manager.py update 1 -p high -due 2026-03-15

# Show task details
python task_manager.py show 1

# Search tasks
python task_manager.py search "project"

# View statistics
python task_manager.py stats

# Export tasks
python task_manager.py export -f json -o my_tasks

# Manage categories
python task_manager.py category list
python task_manager.py category add -n "health" -c "#10b981"
```

## Default Categories

- 📁 general (purple)
- 💼 work (green)
- 👤 personal (orange)
- ⚠️ urgent (red)
- 📚 learning (violet)

## Database

Tasks are stored in `~/.rizz_tasks.db` (SQLite).

## License

MIT License - username9999
