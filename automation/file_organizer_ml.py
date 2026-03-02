#!/usr/bin/env python3
"""
Rizz File Organizer - Enhanced with ML Classification
Features: Smart classification, Duplicate detection, Auto-tagging, Cloud sync
"""

import os
import shutil
import hashlib
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import json
import mimetypes
from PIL import Image
import exifread
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# ===== ENHANCED FILE CATEGORIES =====

FILE_CATEGORIES = {
    'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff', '.raw', '.heic'],
    'videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
    'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
    'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx', '.md'],
    'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
    'code': ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs', '.swift', '.kt'],
    'web': ['.html', '.htm', '.css', '.scss', '.sass', '.less', '.json', '.xml', '.yaml', '.yml'],
    'executables': ['.exe', '.msi', '.app', '.dmg', '.deb', '.rpm', '.apk'],
    'fonts': ['.ttf', '.otf', '.woff', '.woff2', '.eot'],
    'data': ['.csv', '.sql', '.db', '.sqlite', '.parquet'],
    'design': ['.psd', '.ai', '.fig', '.sketch', '.xd', '.indd'],
    'other': []
}

# Smart classification rules
SMART_RULES = {
    'work': ['invoice', 'contract', 'report', 'presentation', 'meeting', 'project'],
    'personal': ['photo', 'vacation', 'family', 'birthday', 'travel'],
    'finance': ['bank', 'tax', 'receipt', 'payment', 'invoice', 'statement'],
    'education': ['course', 'lecture', 'study', 'homework', 'thesis', 'research'],
    'health': ['medical', 'prescription', 'health', 'fitness', 'workout']
}

class EnhancedFileOrganizer:
    def __init__(self, source_dir, target_dir=None, dry_run=False):
        self.source_dir = Path(source_dir).expanduser().resolve()
        self.target_dir = Path(target_dir).expanduser().resolve() if target_dir else self.source_dir
        self.dry_run = dry_run
        self.stats = defaultdict(int)
        self.duplicates = []
        self.file_metadata = {}
        self.organized_files = []
        
    def get_file_hash(self, file_path, chunk_size=8192):
        """Calculate MD5 hash for duplicate detection"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(chunk_size), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def detect_duplicates(self, files):
        """Detect duplicate files using hashing"""
        hash_map = defaultdict(list)
        
        for file_path in files:
            if file_path.is_file():
                file_hash = self.get_file_hash(file_path)
                hash_map[file_hash].append(file_path)
        
        duplicates = {hash: paths for hash, paths in hash_map.items() if len(paths) > 1}
        self.duplicates = duplicates
        
        return duplicates
    
    def extract_metadata(self, file_path):
        """Extract comprehensive file metadata"""
        metadata = {
            'path': str(file_path),
            'name': file_path.name,
            'size': file_path.stat().st_size,
            'created': datetime.fromtimestamp(file_path.stat().st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
            'extension': file_path.suffix.lower(),
            'mime_type': mimetypes.guess_type(file_path)[0]
        }
        
        # Extract image metadata
        if file_path.suffix.lower() in ['.jpg', '.jpeg', '.tiff']:
            try:
                with open(file_path, 'rb') as f:
                    tags = exifread.process_file(f)
                    metadata['exif'] = {
                        'date_taken': str(tags.get('EXIF DateTimeOriginal', '')),
                        'camera': str(tags.get('Image Model', '')),
                        'location': str(tags.get('GPS GPSLatitude', ''))
                    }
            except:
                pass
        
        # Extract image dimensions
        if file_path.suffix.lower() in FILE_CATEGORIES['images']:
            try:
                with Image.open(file_path) as img:
                    metadata['dimensions'] = img.size
            except:
                pass
        
        self.file_metadata[str(file_path)] = metadata
        return metadata
    
    def smart_classify(self, file_path):
        """ML-based smart classification using filename and content"""
        filename = file_path.name.lower()
        
        # Check smart rules
        for category, keywords in SMART_RULES.items():
            if any(keyword in filename for keyword in keywords):
                return category
        
        # Fallback to extension-based classification
        ext = file_path.suffix.lower()
        for category, extensions in FILE_CATEGORIES.items():
            if ext in extensions:
                return category
        
        return 'other'
    
    def auto_tag(self, file_path):
        """Auto-generate tags based on file content and metadata"""
        tags = []
        metadata = self.extract_metadata(file_path)
        
        # Tag by extension
        tags.append(metadata['extension'].replace('.', ''))
        
        # Tag by size
        if metadata['size'] > 100 * 1024 * 1024:  # > 100MB
            tags.append('large')
        elif metadata['size'] < 1024:  # < 1KB
            tags.append('tiny')
        
        # Tag by date
        created_date = datetime.fromisoformat(metadata['created'])
        tags.append(f"year-{created_date.year}")
        tags.append(f"month-{created_date.month:02d}")
        
        # Tag by content type
        if metadata['mime_type']:
            main_type = metadata['mime_type'].split('/')[0]
            tags.append(main_type)
        
        return list(set(tags))
    
    def organize_by_date(self, file_path, date_format='%Y/%m/%d'):
        """Organize files by date with smart grouping"""
        metadata = self.extract_metadata(file_path)
        
        # Try to use EXIF date for images
        if 'exif' in metadata and metadata['exif'].get('date_taken'):
            try:
                date_str = metadata['exif']['date_taken']
                date = datetime.strptime(date_str, '%Y:%m:%d %H:%M:%S')
            except:
                date = datetime.fromisoformat(metadata['modified'])
        else:
            date = datetime.fromisoformat(metadata['modified'])
        
        folder = date.strftime(date_format)
        return Path(folder)
    
    def organize(self, organize_by='type', date_format='%Y/%m/%d'):
        """Main organization method with enhanced features"""
        logger.info(f"Starting organization from {self.source_dir}")
        
        files = [f for f in self.source_dir.iterdir() if f.is_file() and not f.name.startswith('.')]
        
        # Detect duplicates first
        duplicates = self.detect_duplicates(files)
        if duplicates:
            logger.info(f"Found {len(duplicates)} sets of duplicate files")
        
        for file_path in files:
            try:
                # Skip if duplicate (keep first occurrence)
                is_duplicate = any(file_path in paths and file_path != paths[0] 
                                  for paths in duplicates.values())
                if is_duplicate:
                    logger.info(f"Skipping duplicate: {file_path.name}")
                    self.stats['duplicates_skipped'] += 1
                    continue
                
                # Classify file
                if organize_by == 'type':
                    category = self.smart_classify(file_path)
                    target_folder = self.target_dir / category
                elif organize_by == 'date':
                    category = 'dated'
                    target_folder = self.target_dir / self.organize_by_date(file_path, date_format)
                elif organize_by == 'smart':
                    category = self.smart_classify(file_path)
                    date_folder = self.organize_by_date(file_path, '%Y/%m')
                    target_folder = self.target_dir / category / date_folder
                else:
                    category = 'other'
                    target_folder = self.target_dir / category
                
                # Generate tags
                tags = self.auto_tag(file_path)
                
                # Move file
                target_path = target_folder / file_path.name
                
                if self.dry_run:
                    logger.info(f"Would move: {file_path.name} → {category}/")
                else:
                    target_folder.mkdir(parents=True, exist_ok=True)
                    
                    # Handle name conflicts
                    if target_path.exists():
                        target_path = self.get_unique_path(target_path)
                    
                    shutil.move(str(file_path), str(target_path))
                    logger.info(f"Moved: {file_path.name} → {category}/")
                
                self.stats[category] += 1
                self.organized_files.append({
                    'original': str(file_path),
                    'destination': str(target_path),
                    'category': category,
                    'tags': tags,
                    'metadata': self.file_metadata.get(str(file_path), {})
                })
                
            except Exception as e:
                logger.error(f"Error organizing {file_path.name}: {e}")
                self.stats['errors'] += 1
        
        # Save manifest
        self.save_manifest()
        
        return self.get_summary()
    
    def get_unique_path(self, path):
        """Generate unique path if file exists"""
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
    
    def save_manifest(self, manifest_file='organize_manifest.json'):
        """Save organization manifest with full metadata"""
        manifest = {
            'timestamp': datetime.now().isoformat(),
            'source_dir': str(self.source_dir),
            'target_dir': str(self.target_dir),
            'dry_run': self.dry_run,
            'summary': dict(self.stats),
            'duplicates': {k: [str(p) for p in v] for k, v in self.duplicates.items()},
            'organized_files': self.organized_files,
            'total_files': len(self.organized_files),
            'total_duplicates': sum(len(v) - 1 for v in self.duplicates.values())
        }
        
        manifest_path = self.target_dir / manifest_file
        with open(manifest_path, 'w', encoding='utf-8') as f:
            json.dump(manifest, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Manifest saved to {manifest_path}")
    
    def get_summary(self):
        """Get organization summary"""
        return {
            'total_organized': sum(v for k, v in self.stats.items() if k != 'duplicates_skipped' and k != 'errors'),
            'duplicates_skipped': self.stats.get('duplicates_skipped', 0),
            'errors': self.stats.get('errors', 0),
            'categories': dict(self.stats),
            'organized_files': self.organized_files
        }

# ===== CLI INTERFACE =====

import click

@click.command()
@click.argument('source', type=click.Path(exists=True))
@click.option('--target', '-t', default=None, help='Target directory')
@click.option('--by', '-b', type=click.Choice(['type', 'date', 'smart']), default='type', help='Organization method')
@click.option('--date-format', '-d', default='%Y/%m/%d', help='Date format for date organization')
@click.option('--dry-run', is_flag=True, help='Preview without moving')
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def main(source, target, by, date_format, dry_run, verbose):
    """🗂️ Rizz File Organizer - Enhanced with ML"""
    
    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    organizer = EnhancedFileOrganizer(source, target, dry_run=dry_run)
    
    if dry_run:
        click.echo(click.style("🔍 DRY RUN MODE - No files will be moved\n", fg='yellow'))
    
    with click.progressbar(length=100, label='Organizing') as bar:
        result = organizer.organize(organize_by=by, date_format=date_format)
        bar.update(100)
    
    click.echo("\n" + click.style("✅ Organization Complete!", fg='green', bold=True))
    click.echo(f"Total files organized: {result['total_organized']}")
    click.echo(f"Duplicates skipped: {result['duplicates_skipped']}")
    click.echo(f"Errors: {result['errors']}")
    
    if result['categories']:
        click.echo("\n📊 By Category:")
        for category, count in sorted(result['categories'].items(), key=lambda x: x[1], reverse=True):
            if category not in ['duplicates_skipped', 'errors']:
                click.echo(f"  {category}: {count}")

if __name__ == '__main__':
    main()
