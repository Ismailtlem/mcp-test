import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from mcp.server.mcpserver import MCPServer

DB_PATH = Path(__file__).parent / "notes.db"

mcp = MCPServer("notes")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                tags TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts USING fts5(
                title, content, tags, content='notes', content_rowid='id'
            );

            CREATE TRIGGER IF NOT EXISTS notes_ai AFTER INSERT ON notes BEGIN
                INSERT INTO notes_fts(rowid, title, content, tags)
                VALUES (new.id, new.title, new.content, new.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS notes_ad AFTER DELETE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
                VALUES ('delete', old.id, old.title, old.content, old.tags);
            END;

            CREATE TRIGGER IF NOT EXISTS notes_au AFTER UPDATE ON notes BEGIN
                INSERT INTO notes_fts(notes_fts, rowid, title, content, tags)
                VALUES ('delete', old.id, old.title, old.content, old.tags);
                INSERT INTO notes_fts(rowid, title, content, tags)
                VALUES (new.id, new.title, new.content, new.tags);
            END;
            """
        )
        conn.commit()
    finally:
        conn.close()


def now() -> str:
    return datetime.now(UTC).isoformat()


def row_to_dict(row: sqlite3.Row) -> dict:
    return {
        "id": row["id"],
        "title": row["title"],
        "content": row["content"],
        "tags": row["tags"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@mcp.tool()
def add_note(title: str, content: str, tags: str = "") -> dict:
    """Create a new note and return the created record."""
    conn = get_connection()
    try:
        timestamp = now()
        cursor = conn.execute(
            "INSERT INTO notes (title, content, tags, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (title, content, tags, timestamp, timestamp),
        )
        conn.commit()
        row = conn.execute(
            "SELECT * FROM notes WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
        return row_to_dict(row)
    finally:
        conn.close()


@mcp.tool()
def search_notes(query: str, limit: int = 10) -> list[dict]:
    """Full-text search notes by title/content/tags, ranked by relevance."""
    conn = get_connection()
    try:
        rows = conn.execute(
            """
            SELECT notes.id, notes.title, notes.tags, notes.created_at,
                   snippet(notes_fts, 1, '[', ']', '...', 10) AS snippet
            FROM notes_fts
            JOIN notes ON notes.id = notes_fts.rowid
            WHERE notes_fts MATCH ?
            ORDER BY bm25(notes_fts)
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [
            {
                "id": row["id"],
                "title": row["title"],
                "tags": row["tags"],
                "created_at": row["created_at"],
                "snippet": row["snippet"],
            }
            for row in rows
        ]
    finally:
        conn.close()


@mcp.tool()
def list_notes(tag: str | None = None, limit: int = 50) -> list[dict]:
    """List notes, newest first, optionally filtered by a tag substring."""
    conn = get_connection()
    try:
        if tag:
            rows = conn.execute(
                "SELECT * FROM notes WHERE tags LIKE ? "
                "ORDER BY created_at DESC LIMIT ?",
                (f"%{tag}%", limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM notes ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [row_to_dict(row) for row in rows]
    finally:
        conn.close()


@mcp.tool()
def get_note(note_id: int) -> dict:
    """Fetch a single note by id."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if row is None:
            return {"error": f"No note found with id {note_id}"}
        return row_to_dict(row)
    finally:
        conn.close()


@mcp.tool()
def update_note(
    note_id: int,
    title: str | None = None,
    content: str | None = None,
    tags: str | None = None,
) -> dict:
    """Partially update a note's title, content, and/or tags."""
    conn = get_connection()
    try:
        row = conn.execute("SELECT * FROM notes WHERE id = ?", (note_id,)).fetchone()
        if row is None:
            return {"error": f"No note found with id {note_id}"}

        new_title = title if title is not None else row["title"]
        new_content = content if content is not None else row["content"]
        new_tags = tags if tags is not None else row["tags"]

        conn.execute(
            "UPDATE notes SET title = ?, content = ?, tags = ?, updated_at = ? "
            "WHERE id = ?",
            (new_title, new_content, new_tags, now(), note_id),
        )
        conn.commit()
        updated = conn.execute(
            "SELECT * FROM notes WHERE id = ?", (note_id,)
        ).fetchone()
        return row_to_dict(updated)
    finally:
        conn.close()


@mcp.tool()
def delete_note(note_id: int) -> dict:
    """Delete a note by id."""
    conn = get_connection()
    try:
        cursor = conn.execute("DELETE FROM notes WHERE id = ?", (note_id,))
        conn.commit()
        if cursor.rowcount == 0:
            return {"error": f"No note found with id {note_id}"}
        return {"deleted": note_id}
    finally:
        conn.close()


@mcp.resource("notes://all")
def all_notes_resource() -> str:
    """Markdown listing of all notes for quick browsing."""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT id, title, tags, created_at FROM notes ORDER BY created_at DESC"
        ).fetchall()
        if not rows:
            return "# Notes\n\n_No notes yet._"
        lines = ["# Notes\n"]
        for row in rows:
            tags = f" `{row['tags']}`" if row["tags"] else ""
            lines.append(f"- **#{row['id']}** {row['title']}{tags} ({row['created_at']})")
        return "\n".join(lines)
    finally:
        conn.close()


def main():
    init_db()
    if os.environ.get("MCP_TRANSPORT") == "http":
        port = int(os.environ.get("PORT", "8000"))
        mcp.run(transport="streamable-http", host="0.0.0.0", port=port, stateless_http=True)
    else:
        mcp.run()


if __name__ == "__main__":
    main()
