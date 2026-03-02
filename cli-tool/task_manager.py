import sqlite3, sys, argparse, time
from datetime import datetime

# ANSI Colors for Terminal
G, Y, R, B, C, RES = "\033[92m", "\033[93m", "\033[91m", "\033[1m", "\033[96m", "\033[0m"

def init_db():
    conn = sqlite3.connect("tasks.db")
    conn.cursor().execute("CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, task TEXT, priority TEXT, status TEXT, created_at TEXT)")
    conn.commit()
    conn.close()

def add_task(task, priority):
    conn = sqlite3.connect("tasks.db")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn.cursor().execute("INSERT INTO tasks (task, priority, status, created_at) VALUES (?, ?, ?, ?)", (task, priority, "Pending", now))
    conn.commit()
    conn.close()
    print(f"{G}✔ Task added [{priority}]:{RES} {task}")

def list_tasks(search=None):
    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()
    if search:
        c.execute("SELECT * FROM tasks WHERE task LIKE ?", ("%"+search+"%",))
    else:
        c.execute("SELECT * FROM tasks")
    tasks = c.fetchall()
    print(f"\n{B}{C}--- ADVANCED TASK DASHBOARD ---{RES}")
    if not tasks:
        print("No tasks found.")
    for t in tasks:
        p_col = R if t[2] == "High" else (Y if t[2] == "Medium" else G)
        s_col = G if t[3] == "Completed" else Y
        print(f"[{t[0]}] {t[1]} | {p_col}{t[2]}{RES} | {s_col}{t[3]}{RES} | {t[4]}")
    conn.close()

def stats():
    conn = sqlite3.connect("tasks.db")
    c = conn.cursor()
    total = c.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
    done = c.execute("SELECT COUNT(*) FROM tasks WHERE status = 'Completed'").fetchone()[0]
    pending = total - done
    print(f"\n{B}📊 TASK STATISTICS:{RES}")
    print(f"Total Tasks: {total}")
    print(f"{G}Completed: {done}{RES}")
    print(f"{Y}Pending: {pending}{RES}")
    if total > 0:
        rate = (done / total) * 100
        print(f"{B}Completion Rate: {int(rate)}%{RES}")
    conn.close()

if __name__ == "__main__":
    init_db()
    parser = argparse.ArgumentParser(description='Professional CLI Task Manager v3.0')
    parser.add_argument('action', choices=['add', 'list', 'done', 'del', 'stats', 'search'])
    parser.add_argument('--task')
    parser.add_argument('--priority', default='Medium', choices=['High', 'Medium', 'Low'])
    parser.add_argument('--id', type=int)
    parser.add_argument('--query')
    args = parser.parse_args()

    if args.action == 'add' and args.task:
        add_task(args.task, args.priority)
    elif args.action == 'list':
        list_tasks()
    elif args.action == 'search' and args.query:
        list_tasks(args.query)
    elif args.action == 'stats':
        stats()
    elif args.action == 'done' and args.id:
        conn = sqlite3.connect("tasks.db")
        conn.cursor().execute("UPDATE tasks SET status = 'Completed' WHERE id = ?", (args.id,))
        conn.commit()
        conn.close()
        print(f"{G}✔ Task marked as completed!{RES}")
    elif args.action == 'del' and args.id:
        conn = sqlite3.connect("tasks.db")
        conn.cursor().execute("DELETE FROM tasks WHERE id = ?", (args.id,))
        conn.commit()
        conn.close()
        print(f"{R}✔ Task deleted.{RES}")
