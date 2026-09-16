"""Shared household task list.

Stored in its own table in the same SQLite file used for conversation memory,
but completely independent of LangGraph's checkpoint tables (checkpoints,
writes). This means /reset — which only clears a conversation's checkpoint
history — never touches the task list, and tasks are visible to every
authorized user regardless of which private conversation thread they use.
"""

import sqlite3
from datetime import datetime, timezone

from langchain_core.tools import tool

DB_PATH = "memory.db"

_conn = sqlite3.connect(DB_PATH, check_same_thread=False)
_conn.execute(
    """
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        description TEXT NOT NULL,
        created_by TEXT,
        created_at TEXT NOT NULL,
        done INTEGER NOT NULL DEFAULT 0,
        completed_at TEXT
    )
    """
)
_conn.commit()


@tool
def add_task(description: str, created_by: str = "") -> str:
    """Add a new item to the shared household task/to-do list.

    Use this whenever someone asks to add, remember, or note down something
    to do around the house. Pass `created_by` as the name of the person
    speaking (given at the start of their message) so everyone can see who
    added each task.
    """
    now = datetime.now(timezone.utc).isoformat()
    cur = _conn.cursor()
    cur.execute(
        "INSERT INTO tasks (description, created_by, created_at) VALUES (?, ?, ?)",
        (description, created_by, now),
    )
    _conn.commit()
    return f"Task added (#{cur.lastrowid}): {description}"


@tool
def list_tasks(include_done: bool = False) -> str:
    """List the shared household tasks/to-do items.

    By default only shows tasks that aren't done yet. Set include_done=True
    to also include already-completed tasks.
    """
    cur = _conn.cursor()
    if include_done:
        cur.execute("SELECT id, description, created_by, done FROM tasks ORDER BY id")
    else:
        cur.execute("SELECT id, description, created_by, done FROM tasks WHERE done = 0 ORDER BY id")
    rows = cur.fetchall()

    if not rows:
        return "No tasks found."

    lines = []
    for task_id, description, created_by, done in rows:
        status = "✅" if done else "⬜"
        who = f" (added by {created_by})" if created_by else ""
        lines.append(f"{status} #{task_id}: {description}{who}")
    return "\n".join(lines)


@tool
def complete_task(task_id: int) -> str:
    """Mark a household task as done, given its numeric ID (shown by list_tasks)."""
    now = datetime.now(timezone.utc).isoformat()
    cur = _conn.cursor()
    cur.execute("UPDATE tasks SET done = 1, completed_at = ? WHERE id = ?", (now, task_id))
    _conn.commit()
    if cur.rowcount == 0:
        return f"No task found with id {task_id}."
    return f"Task #{task_id} marked as done."


@tool
def delete_task(task_id: int) -> str:
    """Permanently delete a household task, given its numeric ID (shown by list_tasks)."""
    cur = _conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    _conn.commit()
    if cur.rowcount == 0:
        return f"No task found with id {task_id}."
    return f"Task #{task_id} deleted."
