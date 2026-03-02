import sqlite3, sys, argparse
GREEN, YELLOW, RED, RESET, BOLD = '[92m', '[93m', '[91m', '[0m', '[1m'
def init_db():
    conn = sqlite3.connect('tasks.db')
    conn.cursor().execute('CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, task TEXT, status TEXT)')
    conn.commit(); conn.close()
def add_task(task):
    conn = sqlite3.connect('tasks.db')
    conn.cursor().execute('INSERT INTO tasks (task, status) VALUES (?, ?)', (task, 'Pending'))
    conn.commit(); conn.close()
    print(f'{GREEN}✔ Task added:{RESET} {task}')
def list_tasks():
    conn = sqlite3.connect('tasks.db'); tasks = conn.cursor().execute('SELECT * FROM tasks').fetchall()
    print(f'
{BOLD}--- YOUR TASK LIST ---{RESET}')
    for t in tasks:
        color = GREEN if t[2] == 'Completed' else YELLOW
        print(f'[{t[0]}] {t[1]} - {color}{t[2]}{RESET}')
    conn.close()
def complete_task(task_id):
    conn = sqlite3.connect('tasks.db'); c = conn.cursor()
    c.execute("UPDATE tasks SET status = 'Completed' WHERE id = ?", (task_id,))
    print(f'{GREEN}✔ Task {task_id} completed!{RESET}') if c.rowcount > 0 else print(f'{RED}✘ Task {task_id} not found.{RESET}')
    conn.commit(); conn.close()
def delete_task(task_id):
    conn = sqlite3.connect('tasks.db'); c = conn.cursor()
    c.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    print(f'{RED}✔ Task {task_id} deleted.{RESET}') if c.rowcount > 0 else print(f'{RED}✘ Task {task_id} not found.{RESET}')
    conn.commit(); conn.close()
if __name__ == '__main__':
    init_db(); parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=['add', 'list', 'done', 'del'])
    parser.add_argument('--task'); parser.add_argument('--id', type=int)
    args = parser.parse_args()
    if args.action == 'add' and args.task: add_task(args.task)
    elif args.action == 'list': list_tasks()
    elif args.action == 'done' and args.id: complete_task(args.id)
    elif args.action == 'del' and args.id: delete_task(args.id)
