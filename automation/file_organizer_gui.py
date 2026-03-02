#!/usr/bin/env python3
"""
Rizz File Organizer - GUI Version
Desktop application with real-time monitoring and advanced features
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import os
import shutil
import json
import threading
import time
from pathlib import Path
from datetime import datetime
from collections import defaultdict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import hashlib

# File type categories
FILE_CATEGORIES = {
    'images': ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.svg', '.webp', '.ico', '.tiff', '.raw'],
    'videos': ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v'],
    'audio': ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a'],
    'documents': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt', '.xls', '.xlsx', '.ppt', '.pptx', '.md'],
    'archives': ['.zip', '.rar', '.7z', '.tar', '.gz', '.bz2', '.xz'],
    'code': ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs'],
    'web': ['.html', '.htm', '.css', '.scss', '.json', '.xml', '.yaml', '.yml'],
    'other': []
}

EXT_TO_CATEGORY = {}
for cat, exts in FILE_CATEGORIES.items():
    for ext in exts:
        EXT_TO_CATEGORY[ext.lower()] = cat


class FileMonitorHandler(FileSystemEventHandler):
    """Handler for real-time file monitoring"""
    def __init__(self, organizer_gui):
        self.organizer = organizer_gui
        self.event_queue = []
        
    def on_created(self, event):
        if not event.is_directory:
            self.event_queue.append(('created', event.src_path))
            self.organizer.log(f"File created: {os.path.basename(event.src_path)}")
            
    def on_modified(self, event):
        if not event.is_directory:
            self.event_queue.append(('modified', event.src_path))


class FileOrganizerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🗂️ Rizz File Organizer Pro")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # State
        self.source_dir = None
        self.target_dir = None
        self.is_monitoring = False
        self.observer = None
        self.stats = defaultdict(int)
        self.file_history = []
        
        # Setup UI
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.setup_styles()
        
        # Create UI components
        self.create_menu()
        self.create_header()
        self.create_directory_frame()
        self.create_options_frame()
        self.create_progress_frame()
        self.create_log_frame()
        self.create_status_bar()
        
    def setup_styles(self):
        """Configure ttk styles"""
        self.style.configure('TFrame', background='#0f172a')
        self.style.configure('TLabel', background='#0f172a', foreground='#f1f5f9')
        self.style.configure('Header.TLabel', font=('Helvetica', 14, 'bold'), foreground='#10b981')
        self.style.configure('TButton', font=('Helvetica', 10))
        self.style.configure('Accent.TButton', font=('Helvetica', 10, 'bold'))
        self.style.configure('TProgressbar', background='#10b981')
        
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Select Source Folder", command=self.select_source_dir)
        file_menu.add_command(label="Select Target Folder", command=self.select_target_dir)
        file_menu.add_separator()
        file_menu.add_command(label="Export Report", command=self.export_report)
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Load Rules", command=self.load_rules)
        edit_menu.add_command(label="Save Rules", command=self.save_rules)
        
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show Statistics", command=self.show_statistics)
        view_menu.add_command(label="Show File History", command=self.show_history)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Help", command=self.show_help)
        help_menu.add_command(label="About", command=self.show_about)
        
    def create_header(self):
        """Create header"""
        header_frame = ttk.Frame(self.root, padding="20")
        header_frame.pack(fill=tk.X)
        
        ttk.Label(
            header_frame,
            text="🗂️ Rizz File Organizer Pro",
            style='Header.TLabel'
        ).pack(side=tk.LEFT)
        
        ttk.Label(
            header_frame,
            text="Real-time File Organization",
            foreground='#94a3b8'
        ).pack(side=tk.RIGHT)
        
    def create_directory_frame(self):
        """Directory selection frame"""
        dir_frame = ttk.LabelFrame(self.root, text="Directories", padding="20")
        dir_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Source directory
        ttk.Label(dir_frame, text="Source:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.source_var = tk.StringVar()
        self.source_entry = ttk.Entry(dir_frame, textvariable=self.source_var, width=60)
        self.source_entry.grid(row=0, column=1, padx=10, pady=5)
        ttk.Button(
            dir_frame,
            text="Browse",
            command=self.select_source_dir
        ).grid(row=0, column=2, pady=5)
        
        # Target directory
        ttk.Label(dir_frame, text="Target:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.target_var = tk.StringVar()
        self.target_entry = ttk.Entry(dir_frame, textvariable=self.target_var, width=60)
        self.target_entry.grid(row=1, column=1, padx=10, pady=5)
        ttk.Button(
            dir_frame,
            text="Browse",
            command=self.select_target_dir
        ).grid(row=1, column=2, pady=5)
        
    def create_options_frame(self):
        """Options frame"""
        options_frame = ttk.LabelFrame(self.root, text="Organization Options", padding="20")
        options_frame.pack(fill=tk.X, padx=20, pady=10)
        
        # Organization type
        ttk.Label(options_frame, text="Organize by:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.org_type = tk.StringVar(value="type")
        
        type_frame = ttk.Frame(options_frame)
        type_frame.grid(row=0, column=1, columnspan=2, sticky=tk.W)
        
        ttk.Radiobutton(type_frame, text="File Type", variable=self.org_type, value="type").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Date", variable=self.org_type, value="date").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(type_frame, text="Custom Rules", variable=self.org_type, value="custom").pack(side=tk.LEFT, padx=5)
        
        # Date format
        ttk.Label(options_frame, text="Date Format:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.date_format = tk.StringVar(value="%Y-%m")
        date_combo = ttk.Combobox(
            options_frame,
            textvariable=self.date_format,
            values=["%Y-%m", "%Y", "%Y/%m", "%Y-%m-%d"],
            width=20
        )
        date_combo.grid(row=1, column=1, sticky=tk.W, padx=10, pady=5)
        
        # Options
        self.dry_run_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Dry Run (Preview only)",
            variable=self.dry_run_var
        ).grid(row=2, column=0, sticky=tk.W, pady=5)
        
        self.overwrite_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            options_frame,
            text="Overwrite existing files",
            variable=self.overwrite_var
        ).grid(row=2, column=1, sticky=tk.W, pady=5)
        
        # Action buttons
        btn_frame = ttk.Frame(options_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=15)
        
        self.organize_btn = ttk.Button(
            btn_frame,
            text="🚀 Start Organization",
            command=self.start_organization,
            style='Accent.TButton'
        )
        self.organize_btn.pack(side=tk.LEFT, padx=5)
        
        self.monitor_btn = ttk.Button(
            btn_frame,
            text="👁️ Start Monitoring",
            command=self.toggle_monitoring
        )
        self.monitor_btn.pack(side=tk.LEFT, padx=5)
        
        self.stop_btn = ttk.Button(
            btn_frame,
            text="⏹️ Stop",
            command=self.stop_organization,
            state=tk.DISABLED
        )
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
    def create_progress_frame(self):
        """Progress frame"""
        progress_frame = ttk.LabelFrame(self.root, text="Progress", padding="20")
        progress_frame.pack(fill=tk.X, padx=20, pady=10)
        
        self.progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=10)
        
        stats_frame = ttk.Frame(progress_frame)
        stats_frame.pack(fill=tk.X)
        
        self.stats_label = ttk.Label(stats_frame, text="Files organized: 0")
        self.stats_label.pack(side=tk.LEFT, padx=10)
        
        self.time_label = ttk.Label(stats_frame, text="Time elapsed: 00:00")
        self.time_label.pack(side=tk.RIGHT, padx=10)
        
    def create_log_frame(self):
        """Log frame"""
        log_frame = ttk.LabelFrame(self.root, text="Activity Log", padding="20")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            height=15,
            bg='#1e293b',
            fg='#f1f5f9',
            font=('Consolas', 9)
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
    def create_status_bar(self):
        """Status bar"""
        self.status_bar = ttk.Label(
            self.root,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=5
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def select_source_dir(self):
        """Select source directory"""
        directory = filedialog.askdirectory(title="Select Source Folder")
        if directory:
            self.source_var.set(directory)
            self.source_dir = Path(directory)
            self.log(f"Source directory selected: {directory}")
            
    def select_target_dir(self):
        """Select target directory"""
        directory = filedialog.askdirectory(title="Select Target Folder")
        if directory:
            self.target_var.set(directory)
            self.target_dir = Path(directory)
            self.log(f"Target directory selected: {directory}")
            
    def log(self, message):
        """Add message to log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)
        
    def start_organization(self):
        """Start file organization"""
        if not self.source_dir or not self.source_dir.exists():
            messagebox.showerror("Error", "Please select a valid source directory")
            return
        
        target = self.target_dir if self.target_dir else self.source_dir
        
        self.organize_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.progress.start()
        
        # Start in thread
        thread = threading.Thread(target=self.organize_files, args=(target,))
        thread.daemon = True
        thread.start()
        
    def organize_files(self, target_dir):
        """Organize files (runs in thread)"""
        start_time = time.time()
        organized = 0
        skipped = 0
        
        try:
            files = list(self.source_dir.iterdir())
            total = len([f for f in files if f.is_file() and not f.name.startswith('.')])
            
            for file_path in files:
                if not self.stop_btn['state'] == tk.NORMAL:
                    break
                    
                if file_path.is_file() and not file_path.name.startswith('.'):
                    try:
                        category = self.get_category(file_path)
                        target_path = self.get_target_path(file_path, category, target_dir)
                        
                        if self.dry_run_var.get():
                            self.log(f"Would move: {file_path.name} → {category}/")
                        else:
                            target_path.parent.mkdir(parents=True, exist_ok=True)
                            if target_path.exists() and not self.overwrite_var.get():
                                target_path = self.get_unique_path(target_path)
                            shutil.move(str(file_path), str(target_path))
                            self.log(f"✅ Moved: {file_path.name} → {category}/")
                        
                        self.stats[category] += 1
                        organized += 1
                        self.file_history.append({
                            'file': file_path.name,
                            'category': category,
                            'timestamp': datetime.now().isoformat()
                        })
                        
                        # Update stats
                        self.stats_label.config(text=f"Files organized: {organized}/{total}")
                        
                    except Exception as e:
                        self.log(f"❌ Error with {file_path.name}: {str(e)}")
                        skipped += 1
                        
        except Exception as e:
            messagebox.showerror("Error", str(e))
        finally:
            self.progress.stop()
            self.organize_btn.config(state=tk.NORMAL)
            self.stop_btn.config(state=tk.DISABLED)
            
            elapsed = time.time() - start_time
            self.time_label.config(text=f"Time elapsed: {int(elapsed//60):02d}:{int(elapsed%60):02d}")
            self.status_bar.config(text=f"Completed: {organized} organized, {skipped} skipped")
            
            if not self.dry_run_var.get():
                self.save_manifest(target_dir, organized)
                
    def get_category(self, file_path):
        """Get category for file"""
        if self.org_type.get() == "date":
            return file_path.stat().st_mtime
        
        ext = file_path.suffix.lower()
        return EXT_TO_CATEGORY.get(ext, 'other')
    
    def get_target_path(self, file_path, category, target_dir):
        """Get target path for file"""
        if self.org_type.get() == "date":
            mtime = datetime.fromtimestamp(category)
            folder = mtime.strftime(self.date_format.get())
            category = folder
        
        return target_dir / category / file_path.name
    
    def get_unique_path(self, path):
        """Generate unique path"""
        if not path.exists():
            return path
        
        stem, suffix = path.stem, path.suffix
        counter = 1
        while True:
            new_path = path.parent / f"{stem}_{counter}{suffix}"
            if not new_path.exists():
                return new_path
            counter += 1
            
    def toggle_monitoring(self):
        """Toggle real-time monitoring"""
        if self.is_monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()
            
    def start_monitoring(self):
        """Start real-time monitoring"""
        if not self.source_dir or not self.source_dir.exists():
            messagebox.showerror("Error", "Please select a valid source directory")
            return
        
        target = self.target_dir if self.target_dir else self.source_dir
        
        self.handler = FileMonitorHandler(self)
        self.observer = Observer()
        self.observer.schedule(self.handler, str(self.source_dir), recursive=False)
        self.observer.start()
        
        self.is_monitoring = True
        self.monitor_btn.config(text="⏹️ Stop Monitoring")
        self.log("👁️ Started real-time monitoring...")
        self.status_bar.config(text="Monitoring active")
        
        # Start auto-organize thread
        thread = threading.Thread(target=self.auto_organize_loop, args=(target,))
        thread.daemon = True
        thread.start()
        
    def auto_organize_loop(self, target_dir):
        """Auto-organize loop"""
        while self.is_monitoring:
            if self.handler.event_queue:
                event_type, file_path = self.handler.event_queue.pop(0)
                try:
                    category = self.get_category(Path(file_path))
                    target_path = self.get_target_path(Path(file_path), category, target_dir)
                    
                    if target_path.parent != Path(file_path).parent:
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(file_path, str(target_path))
                        self.log(f"✅ Auto-organized: {Path(file_path).name}")
                except Exception as e:
                    self.log(f"⚠️ Error: {str(e)}")
            time.sleep(1)
            
    def stop_monitoring(self):
        """Stop monitoring"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
        
        self.is_monitoring = False
        self.monitor_btn.config(text="👁️ Start Monitoring")
        self.log("⏹️ Stopped monitoring")
        self.status_bar.config(text="Monitoring stopped")
        
    def stop_organization(self):
        """Stop organization"""
        self.stop_btn.config(state=tk.DISABLED)
        self.log("⏹️ Stopping...")
        
    def save_manifest(self, target_dir, count):
        """Save organization manifest"""
        manifest = {
            'timestamp': datetime.now().isoformat(),
            'source': str(self.source_dir),
            'target': str(target_dir),
            'count': count,
            'stats': dict(self.stats),
            'history': self.file_history
        }
        
        manifest_path = target_dir / 'organize_manifest.json'
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
            
    def export_report(self):
        """Export organization report"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt")]
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                f.write("Rizz File Organizer - Report\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write("Statistics:\n")
                for category, count in self.stats.items():
                    f.write(f"  {category}: {count}\n")
            self.log(f"Report exported to {file_path}")
            
    def load_rules(self):
        """Load custom rules"""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json")]
        )
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    rules = json.load(f)
                self.log(f"Loaded rules from {file_path}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load rules: {str(e)}")
                
    def save_rules(self):
        """Save custom rules"""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        
        if file_path:
            rules = {
                'categories': FILE_CATEGORIES,
                'custom_rules': {}
            }
            with open(file_path, 'w') as f:
                json.dump(rules, f, indent=2)
            self.log(f"Rules saved to {file_path}")
            
    def show_statistics(self):
        """Show statistics window"""
        stats_win = tk.Toplevel(self.root)
        stats_win.title("Statistics")
        stats_win.geometry("400x400")
        
        ttk.Label(stats_win, text="📊 Organization Statistics", font=('Helvetica', 14, 'bold')).pack(pady=20)
        
        for category, count in sorted(self.stats.items(), key=lambda x: x[1], reverse=True):
            ttk.Label(stats_win, text=f"📁 {category}: {count} files").pack(pady=2)
            
    def show_history(self):
        """Show file history"""
        history_win = tk.Toplevel(self.root)
        history_win.title("File History")
        history_win.geometry("500x400")
        
        text = scrolledtext.ScrolledText(history_win, bg='#1e293b', fg='#f1f5f9')
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for entry in reversed(self.file_history[-100:]):
            text.insert(tk.END, f"{entry['timestamp']} - {entry['file']} → {entry['category']}\n")
            
    def show_help(self):
        """Show help"""
        messagebox.showinfo(
            "Help",
            "Rizz File Organizer Pro\n\n"
            "1. Select source folder\n"
            "2. (Optional) Select target folder\n"
            "3. Choose organization type\n"
            "4. Click 'Start Organization'\n\n"
            "Or use 'Start Monitoring' for real-time organization."
        )
        
    def show_about(self):
        """Show about"""
        messagebox.showinfo(
            "About",
            "🗂️ Rizz File Organizer Pro\n\n"
            "Version 2.0.0\n\n"
            "Advanced file organization with:\n"
            "- Real-time monitoring\n"
            "- Custom rules\n"
            "- Duplicate detection\n"
            "- Undo support\n\n"
            "Built with ❤️ by username9999"
        )


def main():
    root = tk.Tk()
    app = FileOrganizerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
