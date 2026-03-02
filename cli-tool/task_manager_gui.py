#!/usr/bin/env python3
"""
Rizz Task Manager - GUI Version
Desktop application with Tkinter for task management
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import json

# Database configuration
DB_PATH = Path.home() / '.rizz_tasks.db'

class TaskManagerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("🚀 Rizz Task Manager")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Set theme
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        # Configure colors
        self.colors = {
            'bg': '#0f172a',
            'card': '#1e293b',
            'border': '#334155',
            'text': '#f1f5f9',
            'text_sec': '#94a3b8',
            'primary': '#6366f1',
            'success': '#10b981',
            'warning': '#f59e0b',
            'danger': '#ef4444'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # Configure styles
        self.setup_styles()
        
        # Create UI
        self.create_menu()
        self.create_header()
        self.create_filters()
        self.create_task_list()
        self.create_task_form()
        self.create_status_bar()
        
        # Load tasks
        self.load_tasks()
        
    def setup_styles(self):
        """Configure ttk styles"""
        self.style.configure('TFrame', background=self.colors['bg'])
        self.style.configure('TLabel', background=self.colors['bg'], foreground=self.colors['text'])
        self.style.configure('Header.TLabel', font=('Helvetica', 16, 'bold'))
        self.style.configure('TButton', font=('Helvetica', 10))
        self.style.configure('Primary.TButton', background=self.colors['primary'])
        self.style.configure('Success.TButton', background=self.colors['success'])
        self.style.configure('Danger.TButton', background=self.colors['danger'])
        self.style.configure('Treeview', 
                            background=self.colors['card'],
                            foreground=self.colors['text'],
                            fieldbackground=self.colors['card'],
                            rowheight=30)
        self.style.configure('Treeview.Heading',
                            background=self.colors['card'],
                            foreground=self.colors['text'])
        
    def create_menu(self):
        """Create menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Task", command=self.show_new_task_dialog, accelerator="Ctrl+N")
        file_menu.add_separator()
        file_menu.add_command(label="Export JSON", command=self.export_json)
        file_menu.add_command(label="Export CSV", command=self.export_csv)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        edit_menu.add_command(label="Edit Task", command=self.edit_selected_task, accelerator="Ctrl+E")
        edit_menu.add_command(label="Delete Task", command=self.delete_selected_task, accelerator="Delete")
        edit_menu.add_command(label="Complete Task", command=self.complete_selected_task, accelerator="Ctrl+Enter")
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        view_menu.add_command(label="Show All Tasks", command=lambda: self.filter_tasks('all'))
        view_menu.add_command(label="Show Pending", command=lambda: self.filter_tasks('pending'))
        view_menu.add_command(label="Show Completed", command=lambda: self.filter_tasks('completed'))
        view_menu.add_separator()
        view_menu.add_command(label="Show Statistics", command=self.show_statistics)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Keyboard Shortcuts", command=self.show_shortcuts)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Keyboard shortcuts
        self.root.bind('<Control-n>', lambda e: self.show_new_task_dialog())
        self.root.bind('<Control-e>', lambda e: self.edit_selected_task())
        self.root.bind('<Control-Return>', lambda e: self.complete_selected_task())
        self.root.bind('<Delete>', lambda e: self.delete_selected_task())
        
    def create_header(self):
        """Create header section"""
        header_frame = ttk.Frame(self.root, padding="20")
        header_frame.pack(fill=tk.X)
        
        title_label = ttk.Label(
            header_frame,
            text="🚀 Rizz Task Manager",
            style='Header.TLabel'
        )
        title_label.pack(side=tk.LEFT)
        
        # Stats labels
        self.stats_frame = ttk.Frame(header_frame)
        self.stats_frame.pack(side=tk.RIGHT)
        
        self.pending_label = ttk.Label(
            self.stats_frame,
            text="⏳ Pending: 0",
            foreground=self.colors['warning']
        )
        self.pending_label.pack(side=tk.LEFT, padx=10)
        
        self.completed_label = ttk.Label(
            self.stats_frame,
            text="✅ Completed: 0",
            foreground=self.colors['success']
        )
        self.completed_label.pack(side=tk.LEFT, padx=10)
        
    def create_filters(self):
        """Create filter section"""
        filter_frame = ttk.Frame(self.root, padding="10")
        filter_frame.pack(fill=tk.X, padx=20)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        
        self.filter_var = tk.StringVar(value="all")
        filter_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.filter_var,
            values=["all", "pending", "completed", "high", "medium", "low"],
            state="readonly",
            width=15
        )
        filter_combo.pack(side=tk.LEFT, padx=5)
        filter_combo.bind('<<ComboboxSelected>>', lambda e: self.load_tasks())
        
        ttk.Label(filter_frame, text="Category:").pack(side=tk.LEFT, padx=(20, 5))
        
        self.category_var = tk.StringVar(value="all")
        category_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.category_var,
            values=["all", "general", "work", "personal", "urgent", "learning"],
            state="readonly",
            width=15
        )
        category_combo.pack(side=tk.LEFT, padx=5)
        category_combo.bind('<<ComboboxSelected>>', lambda e: self.load_tasks())
        
        # Search box
        ttk.Label(filter_frame, text="Search:").pack(side=tk.LEFT, padx=(20, 5))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(filter_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side=tk.LEFT, padx=5)
        search_entry.bind('<KeyRelease>', lambda e: self.load_tasks())
        
        # Add task button
        add_btn = ttk.Button(
            filter_frame,
            text="➕ Add Task",
            command=self.show_new_task_dialog
        )
        add_btn.pack(side=tk.RIGHT)
        
    def create_task_list(self):
        """Create task list/treeview"""
        list_frame = ttk.Frame(self.root, padding="20")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Treeview with scrollbar
        columns = ("id", "title", "category", "priority", "due_date", "status")
        
        self.task_tree = ttk.Treeview(
            list_frame,
            columns=columns,
            show="headings",
            selectmode="browse"
        )
        
        # Configure columns
        self.task_tree.heading("id", text="ID")
        self.task_tree.column("id", width=50, anchor=tk.CENTER)
        
        self.task_tree.heading("title", text="Title")
        self.task_tree.column("title", width=300)
        
        self.task_tree.heading("category", text="Category")
        self.task_tree.column("category", width=100, anchor=tk.CENTER)
        
        self.task_tree.heading("priority", text="Priority")
        self.task_tree.column("priority", width=80, anchor=tk.CENTER)
        
        self.task_tree.heading("due_date", text="Due Date")
        self.task_tree.column("due_date", width=100, anchor=tk.CENTER)
        
        self.task_tree.heading("status", text="Status")
        self.task_tree.column("status", width=80, anchor=tk.CENTER)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.task_tree.yview)
        self.task_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack
        self.task_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Double-click to edit
        self.task_tree.bind('<Double-1>', lambda e: self.edit_selected_task())
        
    def create_task_form(self):
        """Create quick add form"""
        form_frame = ttk.Frame(self.root, padding="20")
        form_frame.pack(fill=tk.X)
        
        # Quick add row
        ttk.Label(form_frame, text="Quick Add:").pack(side=tk.LEFT, padx=5)
        
        self.quick_title = ttk.Entry(form_frame, width=40)
        self.quick_title.pack(side=tk.LEFT, padx=5)
        self.quick_title.bind('<Return>', lambda e: self.quick_add_task())
        
        self.quick_priority = ttk.Combobox(
            form_frame,
            values=["low", "medium", "high"],
            state="readonly",
            width=10
        )
        self.quick_priority.set("medium")
        self.quick_priority.pack(side=tk.LEFT, padx=5)
        
        quick_btn = ttk.Button(
            form_frame,
            text="Add",
            command=self.quick_add_task
        )
        quick_btn.pack(side=tk.LEFT, padx=5)
        
    def create_status_bar(self):
        """Create status bar"""
        self.status_bar = ttk.Label(
            self.root,
            text="Ready",
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=5
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def get_db(self):
        """Get database connection"""
        return sqlite3.connect(str(DB_PATH))
    
    def load_tasks(self):
        """Load tasks from database"""
        # Clear existing items
        for item in self.task_tree.get_children():
            self.task_tree.delete(item)
        
        conn = self.get_db()
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM tasks WHERE 1=1"
        params = []
        
        # Apply filters
        if self.filter_var.get() != 'all':
            filter_val = self.filter_var.get()
            if filter_val in ['pending', 'completed']:
                query += " AND status = ?"
                params.append(filter_val)
            elif filter_val in ['high', 'medium', 'low']:
                query += " AND priority = ?"
                params.append(filter_val)
        
        if self.category_var.get() != 'all':
            query += " AND category = ?"
            params.append(self.category_var.get())
        
        if self.search_var.get():
            query += " AND (title LIKE ? OR description LIKE ?)"
            search_term = f"%{self.search_var.get()}%"
            params.extend([search_term, search_term])
        
        query += " ORDER BY CASE priority WHEN 'high' THEN 1 WHEN 'medium' THEN 2 WHEN 'low' THEN 3 END, created_at DESC"
        
        cursor.execute(query, params)
        tasks = cursor.fetchall()
        conn.close()
        
        # Add to treeview
        for task in tasks:
            status_icon = "✅" if task['status'] == 'completed' else "⏳"
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task['priority'], "⚪")
            
            self.task_tree.insert("", tk.END, iid=task['id'], values=(
                task['id'],
                task['title'],
                task['category'],
                f"{priority_icon} {task['priority']}",
                task['due_date'] or "-",
                f"{status_icon} {task['status']}"
            ))
        
        # Update stats
        self.update_stats()
        self.status_bar.config(text=f"Loaded {len(tasks)} tasks")
        
    def update_stats(self):
        """Update statistics labels"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'pending'")
        pending = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM tasks WHERE status = 'completed'")
        completed = cursor.fetchone()[0]
        
        conn.close()
        
        self.pending_label.config(text=f"⏳ Pending: {pending}")
        self.completed_label.config(text=f"✅ Completed: {completed}")
        
    def show_new_task_dialog(self):
        """Show dialog to add new task"""
        dialog = tk.Toplevel(self.root)
        dialog.title("New Task")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.colors['bg'])
        
        ttk.Label(dialog, text="Title:").pack(anchor=tk.W, padx=20, pady=(20, 5))
        title_entry = ttk.Entry(dialog, width=50)
        title_entry.pack(padx=20, fill=tk.X)
        
        ttk.Label(dialog, text="Description:").pack(anchor=tk.W, padx=20, pady=(15, 5))
        desc_text = tk.Text(dialog, width=50, height=5)
        desc_text.pack(padx=20)
        
        ttk.Label(dialog, text="Priority:").pack(anchor=tk.W, padx=20, pady=(15, 5))
        priority_var = tk.StringVar(value="medium")
        priority_combo = ttk.Combobox(
            dialog,
            textvariable=priority_var,
            values=["low", "medium", "high"],
            state="readonly",
            width=20
        )
        priority_combo.pack(padx=20, anchor=tk.W)
        
        ttk.Label(dialog, text="Category:").pack(anchor=tk.W, padx=20, pady=(15, 5))
        category_var = tk.StringVar(value="general")
        category_combo = ttk.Combobox(
            dialog,
            textvariable=category_var,
            values=["general", "work", "personal", "urgent", "learning"],
            state="readonly",
            width=20
        )
        category_combo.pack(padx=20, anchor=tk.W)
        
        ttk.Label(dialog, text="Due Date (YYYY-MM-DD):").pack(anchor=tk.W, padx=20, pady=(15, 5))
        due_entry = ttk.Entry(dialog, width=20)
        due_entry.pack(padx=20, anchor=tk.W)
        
        def save():
            if not title_entry.get().strip():
                messagebox.showerror("Error", "Title is required", parent=dialog)
                return
            
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                INSERT INTO tasks (title, description, status, priority, category, due_date, created_at)
                VALUES (?, ?, 'pending', ?, ?, ?, ?)
            ''', (
                title_entry.get().strip(),
                desc_text.get("1.0", tk.END).strip(),
                priority_var.get(),
                category_var.get(),
                due_entry.get().strip() or None,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            self.load_tasks()
            dialog.destroy()
            self.status_bar.config(text="Task added successfully!")
        
        ttk.Button(dialog, text="Save Task", command=save).pack(pady=20)
        
    def quick_add_task(self):
        """Quick add task from form"""
        title = self.quick_title.get().strip()
        if not title:
            messagebox.showerror("Error", "Title is required")
            return
        
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO tasks (title, description, status, priority, category, created_at)
            VALUES (?, ?, 'pending', ?, 'general', ?)
        ''', (title, '', self.quick_priority.get(), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
        
        self.quick_title.delete(0, tk.END)
        self.load_tasks()
        self.status_bar.config(text="Task added successfully!")
        
    def edit_selected_task(self):
        """Edit selected task"""
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a task to edit")
            return
        
        task_id = selection[0]
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        task = cursor.fetchone()
        conn.close()
        
        if not task:
            return
        
        # Create edit dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit Task")
        dialog.geometry("500x450")
        dialog.transient(self.root)
        dialog.grab_set()
        dialog.configure(bg=self.colors['bg'])
        
        ttk.Label(dialog, text="Title:").pack(anchor=tk.W, padx=20, pady=(20, 5))
        title_entry = ttk.Entry(dialog, width=50)
        title_entry.pack(padx=20, fill=tk.X)
        title_entry.insert(0, task['title'])
        
        ttk.Label(dialog, text="Description:").pack(anchor=tk.W, padx=20, pady=(15, 5))
        desc_text = tk.Text(dialog, width=50, height=4)
        desc_text.pack(padx=20)
        desc_text.insert("1.0", task['description'] or '')
        
        ttk.Label(dialog, text="Priority:").pack(anchor=tk.W, padx=20, pady=(15, 5))
        priority_var = tk.StringVar(value=task['priority'])
        priority_combo = ttk.Combobox(
            dialog,
            textvariable=priority_var,
            values=["low", "medium", "high"],
            state="readonly",
            width=20
        )
        priority_combo.pack(padx=20, anchor=tk.W)
        
        ttk.Label(dialog, text="Category:").pack(anchor=tk.W, padx=20, pady=(15, 5))
        category_var = tk.StringVar(value=task['category'])
        category_combo = ttk.Combobox(
            dialog,
            textvariable=category_var,
            values=["general", "work", "personal", "urgent", "learning"],
            state="readonly",
            width=20
        )
        category_combo.pack(padx=20, anchor=tk.W)
        
        ttk.Label(dialog, text="Due Date (YYYY-MM-DD):").pack(anchor=tk.W, padx=20, pady=(15, 5))
        due_entry = ttk.Entry(dialog, width=20)
        due_entry.pack(padx=20, anchor=tk.W)
        due_entry.insert(0, task['due_date'] or '')
        
        def save():
            if not title_entry.get().strip():
                messagebox.showerror("Error", "Title is required", parent=dialog)
                return
            
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute('''
                UPDATE tasks 
                SET title = ?, description = ?, priority = ?, category = ?, due_date = ?, updated_at = ?
                WHERE id = ?
            ''', (
                title_entry.get().strip(),
                desc_text.get("1.0", tk.END).strip(),
                priority_var.get(),
                category_var.get(),
                due_entry.get().strip() or None,
                datetime.now().isoformat(),
                task_id
            ))
            
            conn.commit()
            conn.close()
            
            self.load_tasks()
            dialog.destroy()
            self.status_bar.config(text="Task updated successfully!")
        
        ttk.Button(dialog, text="Save Changes", command=save).pack(pady=20)
        
    def complete_selected_task(self):
        """Mark selected task as completed"""
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a task to complete")
            return
        
        task_id = selection[0]
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE tasks 
            SET status = 'completed', completed_at = ?, updated_at = ?
            WHERE id = ?
        ''', (datetime.now().isoformat(), datetime.now().isoformat(), task_id))
        
        conn.commit()
        conn.close()
        
        self.load_tasks()
        self.status_bar.config(text="Task completed!")
        
    def delete_selected_task(self):
        """Delete selected task"""
        selection = self.task_tree.selection()
        if not selection:
            messagebox.showwarning("Warning", "Please select a task to delete")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete this task?"):
            task_id = selection[0]
            conn = self.get_db()
            cursor = conn.cursor()
            
            cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
            conn.commit()
            conn.close()
            
            self.load_tasks()
            self.status_bar.config(text="Task deleted!")
            
    def filter_tasks(self, status):
        """Filter tasks by status"""
        self.filter_var.set(status)
        self.load_tasks()
        
    def show_statistics(self):
        """Show statistics window"""
        conn = self.get_db()
        cursor = conn.cursor()
        
        # Get stats
        cursor.execute('SELECT COUNT(*) FROM tasks')
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
        status_counts = dict(cursor.fetchall())
        
        cursor.execute("SELECT priority, COUNT(*) FROM tasks GROUP BY priority")
        priority_counts = dict(cursor.fetchall())
        
        cursor.execute("SELECT category, COUNT(*) FROM tasks GROUP BY category")
        category_counts = dict(cursor.fetchall())
        
        conn.close()
        
        # Create stats window
        stats_win = tk.Toplevel(self.root)
        stats_win.title("Statistics")
        stats_win.geometry("400x500")
        stats_win.transient(self.root)
        stats_win.configure(bg=self.colors['bg'])
        
        ttk.Label(stats_win, text="📊 Task Statistics", style='Header.TLabel').pack(pady=20)
        
        stats_frame = ttk.Frame(stats_win)
        stats_frame.pack(fill=tk.BOTH, expand=True, padx=20)
        
        # Total
        ttk.Label(stats_frame, text=f"Total Tasks: {total}", font=('Helvetica', 12, 'bold')).pack(pady=5)
        
        # By status
        ttk.Label(stats_frame, text=f"✅ Completed: {status_counts.get('completed', 0)}").pack(pady=2)
        ttk.Label(stats_frame, text=f"⏳ Pending: {status_counts.get('pending', 0)}").pack(pady=2)
        
        ttk.Separator(stats_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # By priority
        ttk.Label(stats_frame, text="By Priority:", font=('Helvetica', 11, 'bold')).pack(pady=5)
        for priority, count in priority_counts.items():
            icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
            ttk.Label(stats_frame, text=f"{icon} {priority.capitalize()}: {count}").pack(pady=1)
        
        ttk.Separator(stats_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # By category
        ttk.Label(stats_frame, text="By Category:", font=('Helvetica', 11, 'bold')).pack(pady=5)
        for category, count in category_counts.items():
            ttk.Label(stats_frame, text=f"📁 {category.capitalize()}: {count}").pack(pady=1)
        
        ttk.Button(stats_frame, text="Close", command=stats_win.destroy).pack(pady=20)
        
    def export_json(self):
        """Export tasks to JSON"""
        from tkinter import filedialog
        import json
        
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        tasks = cursor.fetchall()
        conn.close()
        
        # Convert to list of dicts
        columns = [desc[0] for desc in cursor.description]
        tasks_list = [dict(zip(columns, task)) for task in tasks]
        
        # Save to file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")]
        )
        
        if file_path:
            with open(file_path, 'w') as f:
                json.dump(tasks_list, f, indent=2, default=str)
            self.status_bar.config(text=f"Exported to {file_path}")
            
    def export_csv(self):
        """Export tasks to CSV"""
        from tkinter import filedialog
        import csv
        
        conn = self.get_db()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
        tasks = cursor.fetchall()
        conn.close()
        
        # Save to file
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        
        if file_path:
            columns = [desc[0] for desc in cursor.description]
            with open(file_path, 'w', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=columns)
                writer.writeheader()
                for task in tasks:
                    writer.writerow(dict(zip(columns, task)))
            self.status_bar.config(text=f"Exported to {file_path}")
            
    def show_shortcuts(self):
        """Show keyboard shortcuts"""
        shortcuts_win = tk.Toplevel(self.root)
        shortcuts_win.title("Keyboard Shortcuts")
        shortcuts_win.geometry("400x350")
        shortcuts_win.transient(self.root)
        shortcuts_win.configure(bg=self.colors['bg'])
        
        ttk.Label(shortcuts_win, text="⌨️ Keyboard Shortcuts", style='Header.TLabel').pack(pady=20)
        
        shortcuts = [
            ("Ctrl+N", "New Task"),
            ("Ctrl+E", "Edit Task"),
            ("Ctrl+Enter", "Complete Task"),
            ("Delete", "Delete Task"),
        ]
        
        for shortcut, desc in shortcuts:
            frame = ttk.Frame(shortcuts_win)
            frame.pack(fill=tk.X, padx=40, pady=5)
            ttk.Label(frame, text=shortcut, font=('Courier', 10, 'bold'), width=15).pack(side=tk.LEFT)
            ttk.Label(frame, text=desc).pack(side=tk.LEFT)
        
        ttk.Button(shortcuts_win, text="Close", command=shortcuts_win.destroy).pack(pady=20)
        
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About",
            "🚀 Rizz Task Manager GUI\n\n"
            "Version 2.0.0\n\n"
            "A powerful task management application\n"
            "with a beautiful desktop interface.\n\n"
            "Built with ❤️ by username9999"
        )


def main():
    root = tk.Tk()
    app = TaskManagerGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()
