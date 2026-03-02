#!/usr/bin/env python3
"""
Rizz CLI Tool - Enhanced with TUI (Text User Interface)
Features: Rich TUI, Real-time updates, Interactive menus, Progress bars
"""

import click
from click.testing import CliRunner
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.align import Align
from rich import box
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
import time

console = Console()
DB_PATH = Path.home() / '.rizz_tasks.db'

# ===== TUI LAYOUT =====

def create_layout():
    """Create TUI layout"""
    layout = Layout()
    layout.split(
        Layout(name="header", size=3),
        Layout(name="body"),
        Layout(name="footer", size=3)
    )
    return layout

def create_header():
    """Create header panel"""
    text = Text("🚀 Rizz Task Manager", style="bold white on blue")
    text.append(" v2.0", style="italic")
    return Panel(text, box=box.DOUBLE)

def create_footer():
    """Create footer panel"""
    text = Text("Commands: [bold green]n[/]ew [bold green]e[/]dit [bold green]d[/]elete [bold green]q[/]uit")
    return Panel(text, box=box.DOUBLE)

def create_task_table(tasks):
    """Create task table"""
    table = Table(title="📋 Tasks", box=box.ROUNDED)
    
    table.add_column("ID", style="cyan", width=5)
    table.add_column("Title", style="white")
    table.add_column("Category", style="blue")
    table.add_column("Priority", style="yellow")
    table.add_column("Due Date", style="magenta")
    table.add_column("Status", style="green")
    
    for task in tasks:
        priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task['priority'], "⚪")
        status_icon = "✅" if task['status'] == 'completed' else "⏳"
        
        table.add_row(
            str(task['id']),
            task['title'],
            task['category'],
            f"{priority_icon} {task['priority']}",
            task['due_date'] or "-",
            f"{status_icon} {task['status']}"
        )
    
    return table

def create_stats_panel(stats):
    """Create statistics panel"""
    text = Text()
    text.append("📊 Statistics\n\n", style="bold")
    text.append(f"Total: ", style="white")
    text.append(f"{stats['total']}\n", style="bold cyan")
    text.append(f"Pending: ", style="white")
    text.append(f"{stats['pending']}\n", style="bold yellow")
    text.append(f"Completed: ", style="white")
    text.append(f"{stats['completed']}\n", style="bold green")
    text.append(f"Overdue: ", style="white")
    text.append(f"{stats['overdue']}\n", style="bold red")
    
    return Panel(text, box=box.ROUNDED, title="Stats")

# ===== ENHANCED CLI COMMANDS =====

@click.group()
@click.option('--verbose', '-v', is_flag=True, help='Verbose output')
def cli(verbose):
    """🚀 Rizz Task Manager - Enhanced Edition"""
    if verbose:
        console.print("[bold green]Verbose mode enabled[/]")

@cli.command()
@click.option('--title', '-t', required=True, help='Task title')
@click.option('--description', '-d', default='', help='Task description')
@click.option('--priority', '-p', type=click.Choice(['low', 'medium', 'high']), default='medium')
@click.option('--category', '-c', default='general')
@click.option('--due-date', '-due', default=None)
def add(title, description, priority, category, due_date):
    """Add a new task with progress indicator"""
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        task = progress.add_task("Adding task...", total=3)
        
        # Simulate database operation
        conn = get_db()
        cursor = conn.cursor()
        
        progress.update(task, advance=1, description="Validating data...")
        time.sleep(0.3)
        
        progress.update(task, advance=1, description="Saving to database...")
        
        now = datetime.now().isoformat()
        cursor.execute('''
            INSERT INTO tasks (title, description, status, priority, category, due_date, created_at)
            VALUES (?, ?, 'pending', ?, ?, ?, ?)
        ''', (title, description, priority, category, due_date, now))
        
        conn.commit()
        task_id = cursor.lastrowid
        conn.close()
        
        progress.update(task, advance=1, description="Task added!")
        time.sleep(0.5)
    
    console.print(f"[bold green]✅ Task #{task_id} added successfully![/]")
    console.print(f"  Title: {title}")
    console.print(f"  Priority: {priority}")
    console.print(f"  Category: {category}")

@cli.command()
@click.option('--status', '-s', type=click.Choice(['all', 'pending', 'completed']), default='all')
@click.option('--priority', '-p', type=click.Choice(['all', 'low', 'medium', 'high']), default='all')
@click.option('--limit', '-l', default=20)
def list(status, priority, limit):
    """List tasks with rich table display"""
    
    conn = get_db()
    cursor = conn.cursor()
    
    query = "SELECT * FROM tasks WHERE 1=1"
    params = []
    
    if status != 'all':
        query += " AND status = ?"
        params.append(status)
    
    if priority != 'all':
        query += " AND priority = ?"
        params.append(priority)
    
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    
    cursor.execute(query, params)
    tasks = cursor.fetchall()
    conn.close()
    
    if not tasks:
        console.print("[yellow]📭 No tasks found![/]")
        return
    
    table = create_task_table([dict(task) for task in tasks])
    console.print(table)
    
    # Show stats
    stats = get_stats()
    stats_panel = create_stats_panel(stats)
    console.print(stats_panel)

@cli.command()
def tui():
    """Launch interactive TUI"""
    console.clear()
    console.print("[bold blue]🚀 Rizz Task Manager - Interactive Mode[/]\n")
    
    layout = create_layout()
    layout["header"].update(create_header())
    layout["footer"].update(create_footer())
    
    # Main loop
    while True:
        # Get tasks
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tasks ORDER BY created_at DESC LIMIT 20")
        tasks = cursor.fetchall()
        conn.close()
        
        # Update body
        if tasks:
            table = create_task_table([dict(task) for task in tasks])
            layout["body"].update(table)
        else:
            layout["body"].update(Panel("No tasks found!", box=box.ROUNDED))
        
        # Display
        console.print(layout)
        
        # Get command
        try:
            cmd = Prompt.ask("\nCommand", choices=["n", "e", "d", "r", "q"], default="n")
            
            if cmd == "q":
                console.print("[bold green]Goodbye![/]")
                break
            elif cmd == "n":
                # New task
                title = Prompt.ask("Title")
                priority = Prompt.ask("Priority", choices=["low", "medium", "high"], default="medium")
                category = Prompt.ask("Category", default="general")
                
                # Add task (reuse add command)
                ctx = cli.make_context('add', ['--title', title, '--priority', priority, '--category', category])
                add.callback(title, '', priority, category, None)
            
            elif cmd == "r":
                # Refresh
                console.clear()
                continue
                
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Interrupted![/]")
            break

@cli.command()
def stats():
    """Show detailed statistics with charts"""
    
    stats = get_stats()
    
    console.print("\n[bold]📊 Task Statistics[/]\n")
    
    # Create stats table
    table = Table(box=box.ROUNDED)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")
    
    table.add_row("Total Tasks", str(stats['total']))
    table.add_row("Pending", f"[yellow]{stats['pending']}[/]")
    table.add_row("Completed", f"[green]{stats['completed']}[/]")
    table.add_row("Overdue", f"[red]{stats['overdue']}[/]")
    table.add_row("Completion Rate", f"[green]{stats['completion_rate']}%[/]")
    
    console.print(table)
    
    # Show by priority
    console.print("\n[bold]By Priority:[/]")
    priority_table = Table(box=box.SIMPLE)
    priority_table.add_column("Priority")
    priority_table.add_column("Count")
    
    for priority, count in stats['by_priority'].items():
        icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(priority, "⚪")
        priority_table.add_row(f"{icon} {priority}", str(count))
    
    console.print(priority_table)
    
    # Show by category
    console.print("\n[bold]By Category:[/]")
    category_table = Table(box=box.SIMPLE)
    category_table.add_column("Category")
    category_table.add_column("Count")
    
    for category, count in sorted(stats['by_category'].items(), key=lambda x: x[1], reverse=True)[:10]:
        category_table.add_row(f"📁 {category}", str(count))
    
    console.print(category_table)

@cli.command()
@click.option('--format', '-f', type=click.Choice(['json', 'csv', 'markdown']), default='json')
@click.option('--output', '-o', default=None)
def export(format, output):
    """Export tasks with progress"""
    
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM tasks ORDER BY created_at DESC')
    tasks = cursor.fetchall()
    conn.close()
    
    tasks_list = [dict(task) for task in tasks]
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        
        export_task = progress.add_task("Exporting...", total=100)
        
        if format == 'json':
            progress.update(export_task, description="Converting to JSON...", advance=50)
            data = json.dumps(tasks_list, indent=2, default=str)
            
            if output:
                progress.update(export_task, description=f"Saving to {output}...", advance=30)
                with open(output, 'w') as f:
                    f.write(data)
                progress.update(export_task, description="Done!", completed=100)
                console.print(f"[green]✅ Exported to {output}[/]")
            else:
                console.print_json(data)
                progress.update(export_task, description="Done!", completed=100)
        
        elif format == 'csv':
            import csv
            progress.update(export_task, description="Converting to CSV...", advance=50)
            
            if output:
                progress.update(export_task, description=f"Saving to {output}...", advance=30)
                with open(output, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=tasks_list[0].keys() if tasks_list else [])
                    writer.writeheader()
                    writer.writerows(tasks_list)
                progress.update(export_task, description="Done!", completed=100)
                console.print(f"[green]✅ Exported to {output}[/]")
        
        elif format == 'markdown':
            progress.update(export_task, description="Converting to Markdown...", advance=50)
            md = "# Tasks\n\n"
            md += "| ID | Title | Priority | Status |\n"
            md += "|---|---|---|---|\n"
            for task in tasks_list:
                md += f"| {task['id']} | {task['title']} | {task['priority']} | {task['status']} |\n"
            
            if output:
                progress.update(export_task, description=f"Saving to {output}...", advance=30)
                with open(output, 'w') as f:
                    f.write(md)
                progress.update(export_task, description="Done!", completed=100)
                console.print(f"[green]✅ Exported to {output}[/]")
            else:
                console.print(md)
                progress.update(export_task, description="Done!", completed=100)

# ===== HELPER FUNCTIONS =====

def get_db():
    """Get database connection"""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def get_stats():
    """Get task statistics"""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM tasks')
    total = cursor.fetchone()[0]
    
    cursor.execute("SELECT status, COUNT(*) FROM tasks GROUP BY status")
    status_counts = dict(cursor.fetchall())
    
    cursor.execute("SELECT priority, COUNT(*) FROM tasks GROUP BY priority")
    priority_counts = dict(cursor.fetchall())
    
    cursor.execute("SELECT category, COUNT(*) FROM tasks GROUP BY category")
    category_counts = dict(cursor.fetchall())
    
    today = datetime.now().strftime('%Y-%m-%d')
    cursor.execute('''
        SELECT COUNT(*) FROM tasks 
        WHERE due_date < ? AND status = 'pending'
    ''', (today,))
    overdue = cursor.fetchone()[0]
    
    conn.close()
    
    completion_rate = (status_counts.get('completed', 0) / total * 100) if total > 0 else 0
    
    return {
        'total': total,
        'pending': status_counts.get('pending', 0),
        'completed': status_counts.get('completed', 0),
        'overdue': overdue,
        'completion_rate': round(completion_rate, 1),
        'by_priority': priority_counts,
        'by_category': category_counts
    }

if __name__ == '__main__':
    cli()
