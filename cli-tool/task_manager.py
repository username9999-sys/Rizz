#!/usr/bin/env python3
"""
Rizz Task Manager - CLI Tool
A powerful command-line task management application
"""

import click
import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import sqlite3
from pathlib import Path

# Database configuration
DB_PATH = Path.home() / '.rizz_tasks.db'

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT DEFAULT 'pending',
            priority TEXT DEFAULT 'medium',
            category TEXT DEFAULT 'general',
            due_date TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT,
            completed_at TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL,
            color TEXT DEFAULT '#6366f1'
        )
    ''')
    
    # Insert default categories
    default_categories = [
        ('general', '#6366f1'),
        ('work', '#10b981'),
        ('personal', '#f59e0b'),
        ('urgent', '#ef4444'),
        ('learning', '#8b5cf6')
    ]
    
    for name, color in default_categories:
        cursor.execute(
            'INSERT OR IGNORE INTO categories (name, color) VALUES (?, ?)',
            (name, color)
        )
    
    conn.commit()
    conn.close()

@click.group()
@click.version_option(version='1.0.0', prog_name='Rizz Task Manager')
def cli():
    """
    🚀 Rizz Task Manager - Your personal CLI task management tool
    
    Manage your tasks efficiently from the command line.
    """
    init_db()

# ===== TASK COMMANDS =====

@cli.command()
@click.option('--title', '-t', required=True, help='Task title')
@click.option('--description', '-d', default='', help='Task description')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high']), default='medium', help='Task priority')
@click.option('--category', '-c', default='general', help='Task category')
@click.option('--due-date', '-due', default=None, help='Due date (YYYY-MM-DD)')
def add(title, description, priority, category, due_date):
    """Add a new task"""
    conn = get_db()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    cursor.execute('''
        INSERT INTO tasks (title, description, status, priority, category, due_date, created_at)
        VALUES (?, ?, 'pending', ?, ?, ?, ?)
    ''', (title, description, priority, category, due_date, now))
    
    conn.commit()
    task_id = cursor.lastrowid
    conn.close()
    
    click.echo(click.style(f'✅ Task #{task_id} added successfully!', fg='green'))
    click.echo(f'   Title: {title}')
    if description:
        click.echo(f'   Description: {description}')
    click.echo(f'   Priority: {priority}')
    click.echo(f'   Category: {category}')
    if due_date:
        click.echo(f'   Due Date: {due_date}')

@cli.command()
@click.option('--status', '-s', type=click.Choice(['all', 'pending', 'completed']), default='all', help='Filter by status')
@click.option('--priority', '-p', type=click.Choice(['all', 'low', 'medium', 'high']), default='all', help='Filter by priority')
@click.option('--category', '-c', default=None, help='Filter by category')
@click.option('--limit', '-l', default=10, help='Number of tasks to show')
def list(status, priority, category, limit):
    """List tasks with optional filters"""
    conn = get_db()
    cursor = conn.cursor()
    
    query = 'SELECT * FROM tasks WHERE 1=1'
    params = []
    
    if status != 'all':
        query += ' AND status = ?'
        params.append(status)
    
    if priority != 'all':
        query += ' AND priority = ?'
        params.append(priority)
    
    if category:
        query += ' AND category = ?'
        params.append(category)
    
    query += ' ORDER BY CASE priority WHEN "high" THEN 1 WHEN "medium" THEN 2 WHEN "low" THEN 3 END, created_at DESC LIMIT ?'
    params.append(limit)
    
    cursor.execute(query, params)
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        click.echo(click.style('📭 No tasks found!', fg='yellow'))
        return
    
    click.echo(f'\n📋 Task List ({len(tasks)} tasks)\n')
    click.echo('=' * 70)
    
    for task in tasks:
        status_icon = '✅' if task['status'] == 'completed' else '⏳'
        priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task['priority'], '🟡')
        
        click.echo(f'{status_icon} #{task["id"]} {priority_icon} {task["title"]}')
        if task['description']:
            click.echo(f'   {task["description"]}')
        click.echo(f'   Category: {task["category"]} | Due: {task["due_date"] or "No date"}')
        click.echo('-' * 70)

@cli.command()
@click.argument('task_id', type=int)
def complete(task_id):
    """Mark a task as completed"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    
    if not task:
        click.echo(click.style(f'❌ Task #{task_id} not found!', fg='red'))
        conn.close()
        return
    
    completed_at = datetime.now().isoformat()
    
    cursor.execute('''
        UPDATE tasks 
        SET status = 'completed', completed_at = ?, updated_at = ?
        WHERE id = ?
    ''', (completed_at, completed_at, task_id))
    
    conn.commit()
    conn.close()
    
    click.echo(click.style(f'✅ Task #{task_id} "{task["title"]}" marked as completed!', fg='green'))

@cli.command()
@click.argument('task_id', type=int)
def delete(task_id):
    """Delete a task"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    
    if not task:
        click.echo(click.style(f'❌ Task #{task_id} not found!', fg='red'))
        conn.close()
        return
    
    cursor.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    conn.commit()
    conn.close()
    
    click.echo(click.style(f'🗑️ Task #{task_id} "{task["title"]}" deleted!', fg='yellow'))

@cli.command()
@click.argument('task_id', type=int)
@click.option('--title', '-t', default=None, help='New title')
@click.option('--description', '-d', default=None, help='New description')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high']), default=None, help='New priority')
@click.option('--category', '-c', default=None, help='New category')
@click.option('--due-date', '-due', default=None, help='New due date (YYYY-MM-DD)')
def update(task_id, title, description, priority, category, due_date):
    """Update an existing task"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    
    if not task:
        click.echo(click.style(f'❌ Task #{task_id} not found!', fg='red'))
        conn.close()
        return
    
    updates = []
    params = []
    
    if title:
        updates.append('title = ?')
        params.append(title)
    if description is not None:
        updates.append('description = ?')
        params.append(description)
    if priority:
        updates.append('priority = ?')
        params.append(priority)
    if category:
        updates.append('category = ?')
        params.append(category)
    if due_date:
        updates.append('due_date = ?')
        params.append(due_date)
    
    if updates:
        updates.append('updated_at = ?')
        params.append(datetime.now().isoformat())
        params.append(task_id)
        
        query = f'UPDATE tasks SET {", ".join(updates)} WHERE id = ?'
        cursor.execute(query, params)
        conn.commit()
        
        click.echo(click.style(f'✅ Task #{task_id} updated successfully!', fg='green'))
    else:
        click.echo(click.style('⚠️ No updates provided!', fg='yellow'))
    
    conn.close()

@cli.command()
@click.argument('task_id', type=int)
def show(task_id):
    """Show details of a specific task"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks WHERE id = ?', (task_id,))
    task = cursor.fetchone()
    conn.close()
    
    if not task:
        click.echo(click.style(f'❌ Task #{task_id} not found!', fg='red'))
        return
    
    status_icon = '✅' if task['status'] == 'completed' else '⏳'
    priority_icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(task['priority'], '🟡')
    
    click.echo(f'\n{status_icon} Task #{task_id} {priority_icon}')
    click.echo('=' * 50)
    click.echo(f'Title:       {task["title"]}')
    click.echo(f'Description: {task["description"] or "None"}')
    click.echo(f'Status:      {task["status"]}')
    click.echo(f'Priority:    {task["priority"]}')
    click.echo(f'Category:    {task["category"]}')
    click.echo(f'Due Date:    {task["due_date"] or "Not set"}')
    click.echo(f'Created:     {task["created_at"]}')
    click.echo(f'Updated:     {task["updated_at"] or "Never"}')
    if task['completed_at']:
        click.echo(f'Completed:   {task["completed_at"]}')
    click.echo()

@cli.command()
def stats():
    """Show task statistics"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Total tasks
    cursor.execute('SELECT COUNT(*) FROM tasks')
    total = cursor.fetchone()[0]
    
    # By status
    cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    status_counts = dict(cursor.fetchall())
    
    # By priority
    cursor.execute("SELECT priority, COUNT(*) FROM tasks GROUP BY priority")
    priority_counts = dict(cursor.fetchall())
    
    # By category
    cursor.execute("SELECT category, COUNT(*) FROM tasks GROUP BY category")
    category_counts = dict(cursor.fetchall())
    
    # Overdue tasks
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*) FROM tasks 
        WHERE due_date < ? AND status = 'pending'
    ''', (today,))
    overdue = cursor.fetchone()[0]
    
    conn.close()
    
    click.echo('\n📊 Task Statistics\n')
    click.echo('=' * 40)
    click.echo(f'Total Tasks:    {total}')
    click.echo(f'Completed:      {status_counts.get("completed", 0)}')
    click.echo(f'Pending:        {status_counts.get("pending", 0)}')
    click.echo(f'Overdue:        {click.style(str(overdue), fg="red") if overdue else 0}')
    click.echo('\nBy Priority:')
    for priority, count in priority_counts.items():
        icon = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(priority, '⚪')
        click.echo(f'  {icon} {priority.capitalize()}: {count}')
    click.echo('\nBy Category:')
    for category, count in category_counts.items():
        click.echo(f'  📁 {category.capitalize()}: {count}')
    click.echo()

@cli.command()
def clear():
    """Clear all completed tasks"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM tasks WHERE status = "completed"')
    count = cursor.fetchone()[0]
    
    if count == 0:
        click.echo(click.style('📭 No completed tasks to clear!', fg='yellow'))
        conn.close()
        return
    
    if click.confirm(f'Are you sure you want to delete {count} completed task(s)?'):
        cursor.execute('DELETE FROM tasks WHERE status = "completed"')
        conn.commit()
        click.echo(click.style(f'🗑️ Cleared {count} completed task(s)!', fg='green'))
    
    conn.close()

# ===== CATEGORY COMMANDS =====

@cli.group()
def category():
    """Manage task categories"""
    pass

@category.command('list')
def list_categories():
    """List all categories"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM categories ORDER BY name')
    categories = cursor.fetchall()
    
    cursor.execute('''
        SELECT category, COUNT(*) as count 
        FROM tasks 
        GROUP BY category
    ''')
    task_counts = dict(cursor.fetchall())
    conn.close()
    
    click.echo('\n📁 Categories\n')
    for cat in categories:
        count = task_counts.get(cat['name'], 0)
        click.echo(f'  {cat["color"]} ● {cat["name"].capitalize()} ({count} tasks)')
    click.echo()

@category.command()
@click.option('--name', '-n', required=True, help='Category name')
@click.option('--color', '-c', default='#6366f1', help='Category color (hex)')
def add(name, color):
    """Add a new category"""
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('INSERT INTO categories (name, color) VALUES (?, ?)', (name, color))
        conn.commit()
        click.echo(click.style(f'✅ Category "{name}" added!', fg='green'))
    except sqlite3.IntegrityError:
        click.echo(click.style(f'❌ Category "{name}" already exists!', fg='red'))
    
    conn.close()

@category.command()
@click.argument('name')
def delete(name):
    """Delete a category"""
    if name == 'general':
        click.echo(click.style('❌ Cannot delete the default "general" category!', fg='red'))
        return
    
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM categories WHERE name = ?', (name,))
    conn.commit()
    
    if cursor.rowcount > 0:
        click.echo(click.style(f'🗑️ Category "{name}" deleted!', fg='yellow'))
    else:
        click.echo(click.style(f'❌ Category "{name}" not found!', fg='red'))
    
    conn.close()

# ===== SEARCH COMMAND =====

@cli.command()
@click.argument('query')
@click.option('--field', '-f', type=click.Choice(['title', 'description', 'all']), default='all', help='Search field')
def search(query, field):
    """Search tasks"""
    conn = get_db()
    cursor = conn.cursor()
    
    search_query = f'%{query}%'
    
    if field == 'title':
        cursor.execute('''
            SELECT * FROM tasks 
            WHERE title LIKE ? 
            ORDER BY created_at DESC
        ''', (search_query,))
    elif field == 'description':
        cursor.execute('''
            SELECT * FROM tasks 
            WHERE description LIKE ? 
            ORDER BY created_at DESC
        ''', (search_query,))
    else:
        cursor.execute('''
            SELECT * FROM tasks 
            WHERE title LIKE ? OR description LIKE ?
            ORDER BY created_at DESC
        ''', (search_query, search_query))
    
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        click.echo(click.style(f'🔍 No tasks found matching "{query}"', fg='yellow'))
        return
    
    click.echo(f'\n🔍 Search Results for "{query}" ({len(tasks)} found)\n')
    
    for task in tasks:
        status_icon = '✅' if task['status'] == 'completed' else '⏳'
        click.echo(f'{status_icon} #{task["id"]} {task["title"]}')
        click.echo(f'   {task["description"][:50]}...' if task['description'] and len(task['description']) > 50 else f'   {task["description"] or ""}')
        click.echo('-' * 50)

# ===== EXPORT COMMAND =====

@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv']), default='json', help='Export format')
@click.option('--output', '-o', default='tasks_export', help='Output filename (without extension)')
def export(format, output):
    """Export tasks to file"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
    tasks = cursor.fetchall()
    conn.close()
    
    if format == 'json':
        filename = f'{output}.json'
        with open(filename, 'w') as f:
            json.dump([dict(task) for task in tasks], f, indent=2)
    else:
        filename = f'{output}.csv'
        with open(filename, 'w') as f:
            f.write('id,title,description,status,priority,category,due_date,created_at,updated_at,completed_at\n')
            for task in tasks:
                f.write(f'{task["id"]},"{task["title"]}","{task["description"]}",{task["status"]},{task["priority"]},{task["category"]},{task["due_date"] or ""},{task["created_at"]},{task["updated_at"] or ""},{task["completed_at"] or ""}\n')
    
    click.echo(click.style(f'✅ Exported {len(tasks)} tasks to {filename}', fg='green'))

if __name__ == '__main__':
    cli()
