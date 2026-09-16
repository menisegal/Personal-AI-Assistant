"""Unit tests for the shared household task list tool."""

import importlib
import sqlite3

import pytest


@pytest.fixture
def tasks_module(monkeypatch, tmp_path):
    """Reload tools.tasks against a fresh temporary SQLite file for test isolation."""
    db_path = tmp_path / "test_tasks.db"
    import tools.tasks as tasks_module

    monkeypatch.setattr(tasks_module, "DB_PATH", str(db_path))
    tasks_module._conn.close()
    tasks_module._conn = sqlite3.connect(str(db_path), check_same_thread=False)
    tasks_module._conn.execute(
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
    tasks_module._conn.commit()
    return tasks_module


class TestTasks:
    """Test add_task, list_tasks, complete_task, delete_task."""

    def test_add_and_list_task(self, tasks_module):
        result = tasks_module.add_task.invoke({"description": "Buy milk", "created_by": "Alice"})
        assert "Buy milk" in result

        listing = tasks_module.list_tasks.invoke({})
        assert "Buy milk" in listing
        assert "Alice" in listing
        assert "⬜" in listing

    def test_list_tasks_empty(self, tasks_module):
        listing = tasks_module.list_tasks.invoke({})
        assert "No tasks found" in listing

    def test_complete_task(self, tasks_module):
        tasks_module.add_task.invoke({"description": "Take out trash", "created_by": "Bob"})

        # The task was just inserted with id 1 in this fresh DB.
        result = tasks_module.complete_task.invoke({"task_id": 1})
        assert "marked as done" in result

        listing = tasks_module.list_tasks.invoke({})
        assert "Take out trash" not in listing  # hidden by default once done

        listing_with_done = tasks_module.list_tasks.invoke({"include_done": True})
        assert "Take out trash" in listing_with_done
        assert "✅" in listing_with_done

    def test_complete_nonexistent_task(self, tasks_module):
        result = tasks_module.complete_task.invoke({"task_id": 999})
        assert "No task found" in result

    def test_delete_task(self, tasks_module):
        tasks_module.add_task.invoke({"description": "Water the plants", "created_by": "Alice"})

        result = tasks_module.delete_task.invoke({"task_id": 1})
        assert "deleted" in result

        listing = tasks_module.list_tasks.invoke({"include_done": True})
        assert "Water the plants" not in listing

    def test_delete_nonexistent_task(self, tasks_module):
        result = tasks_module.delete_task.invoke({"task_id": 999})
        assert "No task found" in result

    def test_tasks_persist_independently_of_conversation_reset(self, tasks_module):
        """Sanity check: the tasks table is separate from any checkpoint/writes table."""
        tasks_module.add_task.invoke({"description": "Persistent task", "created_by": "Alice"})

        cur = tasks_module._conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
        table_names = {row[0] for row in cur.fetchall()}

        assert "tasks" in table_names
        assert "checkpoints" not in table_names
        assert "writes" not in table_names
