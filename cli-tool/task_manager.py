import sqlite3
import sys
import argparse

def init_db():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, task TEXT, status TEXT)''')
    conn.commit()
    conn.close()

def add_task(task):
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('INSERT INTO tasks (task, status) VALUES (?, ?)', (task, 'Pending'))
    conn.commit()
    conn.close()
    print(f'Task added: {task}')

def list_tasks():
    conn = sqlite3.connect('tasks.db')
    c = conn.cursor()
    c.execute('SELECT * FROM tasks')
    tasks = c.fetchall()
    for t in tasks:
        print(f'[{t[0]}] {t[1]} - {t[2]}')
    conn.close()

if __name__ == '__main__':
    init_db()
    parser = argparse.ArgumentParser(description='Simple CLI Task Manager')
    parser.add_argument('action', choices=['add', 'list'], help='Action to perform')
    parser.add_argument('--task', help='Task description')
    args = parser.parse_args()

    if args.action == 'add' and args.task:
        add_task(args.task)
    elif args.action == 'list':
        list_tasks()
