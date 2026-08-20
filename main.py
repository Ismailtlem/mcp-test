import os
import sqlite3
from contextlib import contextmanager

from mcp.server.fastmcp import FastMCP

DB_PATH = os.environ.get("TODO_DB_PATH", "todo.db")

mcp = FastMCP("my-todo", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))


def init_db():
    with get_db() as db:
        db.execute(
            """
            CREATE TABLE IF NOT EXISTS todos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )


@contextmanager
def get_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    try:
        yield db
        db.commit()
    finally:
        db.close()


def row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "task": row["task"],
        "done": bool(row["done"]),
        "created_at": row["created_at"],
    }


@mcp.tool()
def add_todo(task: str) -> dict:
    """Add a new todo item."""
    with get_db() as db:
        cur = db.execute("INSERT INTO todos (task) VALUES (?)", (task,))
        row = db.execute(
            "SELECT * FROM todos WHERE id = ?", (cur.lastrowid,)
        ).fetchone()
        return row_to_dict(row)


@mcp.tool()
def list_todos(include_done: bool = True) -> list[dict]:
    """List todo items, optionally excluding completed ones."""
    with get_db() as db:
        if include_done:
            rows = db.execute("SELECT * FROM todos ORDER BY id").fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM todos WHERE done = 0 ORDER BY id"
            ).fetchall()
        return [row_to_dict(row) for row in rows]


@mcp.tool()
def complete_todo(todo_id: int) -> dict:
    """Mark a todo item as done."""
    with get_db() as db:
        db.execute("UPDATE todos SET done = 1 WHERE id = ?", (todo_id,))
        row = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        if row is None:
            raise ValueError(f"No todo with id {todo_id}")
        return row_to_dict(row)


@mcp.tool()
def delete_todo(todo_id: int) -> dict:
    """Delete a todo item."""
    with get_db() as db:
        row = db.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
        if row is None:
            raise ValueError(f"No todo with id {todo_id}")
        db.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
        return row_to_dict(row)


init_db()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
