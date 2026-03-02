# 🗂️ Rizz File Organizer

Automatically organize your files by type, date, or custom rules.

## Features

- 📁 **Organize by Type** - Sort files into categories (images, videos, documents, code, etc.)
- 📅 **Organize by Date** - Group files by modification date
- ⚙️ **Custom Rules** - Define your own organization rules
- 💾 **Dry Run** - Preview changes before applying
- ↩️ **Undo Support** - Revert organization if needed
- 📊 **Detailed Stats** - See what was organized where

## Installation

No dependencies required! Uses Python 3 standard library.

```bash
# Make executable (optional)
chmod +x file_organizer.py
```

## Usage

### Organize by File Type

```bash
# Organize current directory
python file_organizer.py organize --type

# Organize specific directory
python file_organizer.py organize --type /path/to/folder

# Organize to different output directory
python file_organizer.py organize --type /path/to/folder --output /path/to/organized
```

**Categories:**
- `images/` - JPG, PNG, GIF, SVG, etc.
- `videos/` - MP4, AVI, MKV, MOV, etc.
- `audio/` - MP3, WAV, FLAC, etc.
- `documents/` - PDF, DOC, TXT, MD, etc.
- `archives/` - ZIP, RAR, 7Z, TAR, etc.
- `code/` - PY, JS, Java, C++, etc.
- `web/` - HTML, CSS, JSON, YAML, etc.
- `executables/` - EXE, MSI, APK, etc.
- `fonts/` - TTF, OTF, WOFF, etc.
- `data/` - CSV, SQL, DB, etc.
- `other/` - Uncategorized files

### Organize by Date

```bash
# Organize by month (YYYY-MM)
python file_organizer.py organize --date /path/to/folder

# Organize by year (YYYY)
python file_organizer.py organize --date --date-format "%Y" /path/to/folder

# Organize by year-month-day (YYYY-MM-DD)
python file_organizer.py organize --date --date-format "%Y-%m-%d" /path/to/folder
```

### Organize with Custom Rules

```bash
# Create sample rules file
python file_organizer.py create-rules

# Edit the rules file, then organize
python file_organizer.py organize --rules organizer_rules.json /path/to/folder
```

### Preview Mode (Dry Run)

```bash
# See what would happen without moving files
python file_organizer.py organize --dry-run --type /path/to/folder
```

### Undo Organization

```bash
# Undo last organization (requires manifest)
python file_organizer.py undo

# Use specific manifest file
python file_organizer.py undo --manifest custom_manifest.json
```

## Custom Rules Format

Create a JSON file with your custom rules:

```json
{
  "name": "My Custom Rules",
  "extensions": {
    "projects": [".py", ".js", ".java"],
    "design": [".psd", ".ai", ".fig"],
    "music": [".mp3", ".flac", ".wav"]
  },
  "patterns": {
    "invoices": ["invoice", "receipt", "bill"],
    "contracts": ["contract", "agreement", "nda"],
    "reports": ["report", "summary", "analysis"]
  },
  "size_rules": {
    "large_files": {"min": 104857600},
    "small_files": {"max": 1048576}
  },
  "default": "misc"
}
```

**Rule Types:**
- `extensions` - Match by file extension
- `patterns` - Match by filename pattern (case-insensitive)
- `size_rules` - Match by file size in bytes
- `default` - Folder for unmatched files

## Examples

```bash
# Organize Downloads folder by type
python file_organizer.py organize --type ~/Downloads

# Organize Desktop by month
python file_organizer.py organize --date --date-format "%Y-%m" ~/Desktop

# Preview organization of Documents folder
python file_organizer.py organize --dry-run --type ~/Documents

# Organize with custom rules and save manifest
python file_organizer.py organize --rules my_rules.json ~/Projects --save-manifest

# Quiet mode (minimal output)
python file_organizer.py organize -q --type /path/to/folder
```

## Command Line Options

| Option | Description |
|--------|-------------|
| `organize` | Organize files |
| `--type, -t` | Organize by file type |
| `--date, -d` | Organize by date |
| `--rules, -r` | Custom rules JSON file |
| `--date-format` | Date folder format (default: %Y-%m) |
| `--output, -o` | Output directory |
| `--dry-run` | Preview without moving |
| `--quiet, -q` | Minimal output |
| `--save-manifest` | Save manifest for undo |
| `undo` | Undo last organization |
| `create-rules` | Create sample rules file |

## Project Structure

```
automation/
├── file_organizer.py     # Main script
├── organizer_rules.json  # Custom rules (optional)
└── README.md             # This file
```

## Tips

1. **Always test with `--dry-run` first** to see what will happen
2. **Use `--save-manifest`** to enable undo functionality
3. **Back up important files** before bulk organization
4. **Run on subfolders** for better organization control
5. **Combine with cron** for automatic periodic organization

## License

MIT License - username9999
