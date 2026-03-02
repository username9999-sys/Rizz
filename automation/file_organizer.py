#!/usr/bin/env python3
"""
Rizz File Organizer
Automatically organize files by type, date, or custom rules
"""

import os
import shutil
import argparse
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional
from collections import defaultdict
import mimetypes

# ===== File Type Categories =====

FILE_CATEGORIES = {
    'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff', '.raw'],
    'videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
    'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
    'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx', '.md'],
    'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
    'code': ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt'],
    'web': ['.html', '.htm', '.css', '.scss', '.sass', '.less', '.json', '.xml', '.yaml', '.yml'],
    'executables': ['.exe', '.msi', '.app', '.dmg', '.deb', '.rpm', '.apk'],
    'fonts': ['.ttf', '.otf', '.woff', '.woff2', '.eot'],
    'data': ['.csv', '.sql', '.db', '.sqlite'],
}

# Reverse lookup for quick category finding
EXTENSION_TO_CATEGORY = {}
for category, extensions in FILE_CATEGORIES.items():
    for ext in extensions:
        EXTENSION_TO_CATEGORY[ext.lower()] = category


class FileOrganizer:
    """Main file organizer class"""
    
    def __init__(self, source_dir: str, dry_run: bool = False, verbose: bool = True):
        self.source_dir = Path(source_dir).expanduser().resolve()
        self.dry_run = dry_run
        self.verbose = verbose
        self.stats = defaultdict(int)
        self.organized_files = []
        self.skipped_files = []
        
    def log(self, message: str, level: str = 'info'):
        """Log messages with different levels"""
        if not self.verbose and level == 'debug':
            return
            
        prefix = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌',
            'debug': '🔍'
        }.get(level, '•')
        
        print(f"{prefix} {message}")
    
    def get_category(self, file_path: Path) -> str:
        """Determine category based on file extension"""
        ext = file_path.suffix.lower()
        
        # Check extension mapping
        if ext in EXTENSION_TO_CATEGORY:
            return EXTENSION_TO_CATEGORY[ext]
        
        # Try MIME type
        mime_type, _ = mimetypes.guess_type(file_path.name)
        if mime_type:
            if mime_type.startswith('image/'):
                return 'images'
            elif mime_type.startswith('video/'):
                return 'videos'
            elif mime_type.startswith('audio/'):
                return 'audio'
            elif mime_type.startswith('text/'):
                return 'documents'
        
        return 'other'
    
    def get_date_folder(self, file_path: Path, date_format: str = '%Y-%m') -> str:
        """Get folder name based on file modification date"""
        mtime = os.path.getmtime(file_path)
        date = datetime.fromtimestamp(mtime)
        return date.strftime(date_format)
    
    def organize_by_type(self, organize_dir: Optional[str] = None) -> Dict:
        """Organize files by their type/category"""
        target_base = Path(organize_dir).expanduser().resolve() if organize_dir else self.source_dir
        
        self.log(f"Organizing files by type in: {self.source_dir}", 'info')
        if self.dry_run:
            self.log("DRY RUN - No files will be moved", 'warning')
        
        files = self._get_files_to_organize()
        
        for file_path in files:
            try:
                category = self.get_category(file_path)
                target_dir = target_base / category
                target_path = target_dir / file_path.name
                
                # Handle duplicate names
                target_path = self._get_unique_path(target_path)
                
                if self.dry_run:
                    self.log(f"Would move: {file_path.name} → {category}/", 'debug')
                else:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(target_path))
                    self.log(f"Moved: {file_path.name} → {category}/", 'success')
                
                self.stats[category] += 1
                self.organized_files.append({
                    'file': str(file_path),
                    'destination': str(target_path),
                    'category': category
                })
                
            except Exception as e:
                self.log(f"Error organizing {file_path.name}: {e}", 'error')
                self.skipped_files.append({
                    'file': str(file_path),
                    'error': str(e)
                })
        
        return self._get_summary()
    
    def organize_by_date(self, date_format: str = '%Y-%m', organize_dir: Optional[str] = None) -> Dict:
        """Organize files by their modification date"""
        target_base = Path(organize_dir).expanduser().resolve() if organize_dir else self.source_dir
        
        self.log(f"Organizing files by date ({date_format}) in: {self.source_dir}", 'info')
        if self.dry_run:
            self.log("DRY RUN - No files will be moved", 'warning')
        
        files = self._get_files_to_organize()
        
        for file_path in files:
            try:
                date_folder = self.get_date_folder(file_path, date_format)
                target_dir = target_base / date_folder
                target_path = target_dir / file_path.name
                
                # Handle duplicate names
                target_path = self._get_unique_path(target_path)
                
                if self.dry_run:
                    self.log(f"Would move: {file_path.name} → {date_folder}/", 'debug')
                else:
                    target_dir.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(file_path), str(target_path))
                    self.log(f"Moved: {file_path.name} → {date_folder}/", 'success')
                
                self.stats[date_folder] += 1
                self.organized_files.append({
                    'file': str(file_path),
                    'destination': str(target_path),
                    'date_folder': date_folder
                })
                
            except Exception as e:
                self.log(f"Error organizing {file_path.name}: {e}", 'error')
                self.skipped_files.append({
                    'file': str(file_path),
                    'error': str(e)
                })
        
        return self._get_summary()
    
    def organize_by_custom_rules(self, rules_file: str, organize_dir: Optional[str] = None) -> Dict:
        """Organize files based on custom rules from JSON file"""
        rules_path = Path(rules_file).expanduser().resolve()
        
        if not rules_path.exists():
            self.log(f"Rules file not found: {rules_path}", 'error')
            return self._get_summary()
        
        with open(rules_path, 'r') as f:
            rules = json.load(f)
        
        target_base = Path(organize_dir).expanduser().resolve() if organize_dir else self.source_dir
        
        self.log(f"Organizing files with custom rules from: {rules_path}", 'info')
        
        files = self._get_files_to_organize()
        
        for file_path in files:
            try:
                target_folder = self._match_custom_rules(file_path, rules)
                
                if target_folder:
                    target_dir = target_base / target_folder
                    target_path = target_dir / file_path.name
                    target_path = self._get_unique_path(target_path)
                    
                    if self.dry_run:
                        self.log(f"Would move: {file_path.name} → {target_folder}/", 'debug')
                    else:
                        target_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(file_path), str(target_path))
                        self.log(f"Moved: {file_path.name} → {target_folder}/", 'success')
                    
                    self.stats[target_folder] += 1
                    self.organized_files.append({
                        'file': str(file_path),
                        'destination': str(target_path),
                        'rule_folder': target_folder
                    })
                    
            except Exception as e:
                self.log(f"Error organizing {file_path.name}: {e}", 'error')
                self.skipped_files.append({
                    'file': str(file_path),
                    'error': str(e)
                })
        
        return self._get_summary()
    
    def _match_custom_rules(self, file_path: Path, rules: Dict) -> Optional[str]:
        """Match file against custom rules"""
        ext = file_path.suffix.lower()
        name = file_path.name.lower()
        
        # Check extension rules
        if 'extensions' in rules:
            for folder, extensions in rules['extensions'].items():
                if ext in [e.lower() for e in extensions]:
                    return folder
        
        # Check pattern rules
        if 'patterns' in rules:
            for folder, patterns in rules['patterns'].items():
                for pattern in patterns:
                    if pattern.lower() in name:
                        return folder
        
        # Check size rules
        if 'size_rules' in rules:
            file_size = file_path.stat().st_size
            for folder, size_range in rules['size_rules'].items():
                min_size = size_range.get('min', 0)
                max_size = size_range.get('max', float('inf'))
                if min_size <= file_size <= max_size:
                    return folder
        
        # Default folder
        return rules.get('default', 'other')
    
    def _get_files_to_organize(self) -> List[Path]:
        """Get list of files to organize (exclude directories and hidden files)"""
        files = []
        
        for item in self.source_dir.iterdir():
            if item.is_file() and not item.name.startswith('.'):
                # Skip the script itself and config files
                if item.name in ['file_organizer.py', 'organizer_rules.json']:
                    continue
                files.append(item)
        
        return files
    
    def _get_unique_path(self, path: Path) -> Path:
        """Generate unique path if file already exists"""
        if not path.exists():
            return path
        
        stem = path.stem
        suffix = path.suffix
        counter = 1
        
        while True:
            new_path = path.parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
    
    def _get_summary(self) -> Dict:
        """Get organization summary"""
        total_organized = sum(self.stats.values())
        
        return {
            'total_organized': total_organized,
            'total_skipped': len(self.skipped_files),
            'categories': dict(self.stats),
            'organized_files': self.organized_files,
            'skipped_files': self.skipped_files
        }
    
    def undo_last_operation(self, manifest_file: str = 'organize_manifest.json'):
        """Undo the last organization operation using manifest"""
        manifest_path = Path(manifest_file)
        
        if not manifest_path.exists():
            self.log("No manifest file found. Cannot undo.", 'error')
            return
        
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
        
        self.log(f"Undoing organization ({len(manifest.get('organized_files', []))} files)...", 'warning')
        
        for item in reversed(manifest.get('organized_files', [])):
            try:
                src = Path(item['destination'])
                dst = Path(item['file'])
                
                if src.exists():
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(src), str(dst))
                    self.log(f"Restored: {src.name}", 'success')
            except Exception as e:
                self.log(f"Error restoring: {e}", 'error')
        
        # Remove manifest
        manifest_path.unlink()
        self.log("Undo complete!", 'success')
    
    def save_manifest(self, summary: Dict, manifest_file: str = 'organize_manifest.json'):
        """Save organization manifest for undo capability"""
        manifest_path = Path(manifest_file)
        
        manifest = {
            'timestamp': datetime.now().isoformat(),
            'source_dir': str(self.source_dir),
            'summary': summary
        }
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        self.log(f"Manifest saved to: {manifest_path}", 'debug')


def create_sample_rules_file(output: str = 'organizer_rules.json'):
    """Create a sample rules file"""
    sample_rules = {
        'name': 'Sample File Organizer Rules',
        'description': 'Custom rules for organizing files',
        'extensions': {
            'projects': ['.py', '.js', '.java'],
            'design': ['.psd', '.ai', '.fig', '.sketch'],
            'music': ['.mp3', '.flac', '.wav']
        },
        'patterns': {
            'invoices': ['invoice', 'receipt', 'bill'],
            'contracts': ['contract', 'agreement', 'nda'],
            'reports': ['report', 'summary', 'analysis']
        },
        'size_rules': {
            'large_files': {'min': 100 * 1024 * 1024},  # > 100MB
            'small_files': {'max': 1 * 1024 * 1024}  # < 1MB
        },
        'default': 'misc'
    }
    
    with open(output, 'w') as f:
        json.dump(sample_rules, f, indent=2)
    
    print(f"Sample rules file created: {output}")


def main():
    parser = argparse.ArgumentParser(
        description='🗂️ Rizz File Organizer - Automatically organize your files',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Organize by file type
  python file_organizer.py organize --type /path/to/folder
  
  # Organize by date (YYYY-MM format)
  python file_organizer.py organize --date --date-format "%%Y-%%m" /path/to/folder
  
  # Organize with custom rules
  python file_organizer.py organize --rules rules.json /path/to/folder
  
  # Dry run (preview only)
  python file_organizer.py organize --dry-run --type /path/to/folder
  
  # Create sample rules file
  python file_organizer.py create-rules
  
  # Undo last operation
  python file_organizer.py undo
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Organize command
    organize_parser = subparsers.add_parser('organize', help='Organize files')
    organize_parser.add_argument('directory', nargs='?', default='.', help='Directory to organize')
    organize_parser.add_argument('--type', '-t', action='store_true', help='Organize by file type')
    organize_parser.add_argument('--date', '-d', action='store_true', help='Organize by date')
    organize_parser.add_argument('--rules', '-r', type=str, help='Custom rules JSON file')
    organize_parser.add_argument('--date-format', default='%Y-%m', help='Date folder format')
    organize_parser.add_argument('--output', '-o', type=str, help='Output directory')
    organize_parser.add_argument('--dry-run', action='store_true', help='Preview without moving')
    organize_parser.add_argument('--quiet', '-q', action='store_true', help='Minimal output')
    organize_parser.add_argument('--save-manifest', action='store_true', help='Save manifest for undo')
    
    # Undo command
    undo_parser = subparsers.add_parser('undo', help='Undo last organization')
    undo_parser.add_argument('--manifest', default='organize_manifest.json', help='Manifest file')
    
    # Create rules command
    rules_parser = subparsers.add_parser('create-rules', help='Create sample rules file')
    rules_parser.add_argument('--output', '-o', default='organizer_rules.json', help='Output file')
    
    args = parser.parse_args()
    
    if args.command == 'organize':
        organizer = FileOrganizer(args.directory, dry_run=args.dry_run, verbose=not args.quiet)
        
        if args.type:
            summary = organizer.organize_by_type(args.output)
        elif args.date:
            summary = organizer.organize_by_date(args.date_format, args.output)
        elif args.rules:
            summary = organizer.organize_by_custom_rules(args.rules, args.output)
        else:
            # Default: organize by type
            summary = organizer.organize_by_type(args.output)
        
        # Print summary
        print("\n" + "=" * 50)
        print("📊 Organization Summary")
        print("=" * 50)
        print(f"Total files organized: {summary['total_organized']}")
        print(f"Total files skipped: {summary['total_skipped']}")
        
        if summary['categories']:
            print("\nBy category:")
            for category, count in sorted(summary['categories'].items()):
                print(f"  📁 {category}: {count}")
        
        if args.save_manifest and not args.dry_run:
            organizer.save_manifest(summary)
            print("\n✅ Manifest saved (use 'undo' to revert)")
    
    elif args.command == 'undo':
        organizer = FileOrganizer('.', verbose=True)
        organizer.undo_last_operation(args.manifest)
    
    elif args.command == 'create-rules':
        create_sample_rules_file(args.output)
    
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
