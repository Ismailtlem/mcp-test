# mcp-server-my-todo

A minimal MCP (Model Context Protocol) server for a personal todo list, backed by SQLite.

## Tools

- `add_todo(task: str)` — add a new todo item
- `list_todos(include_done: bool = True)` — list todos, optionally hiding completed ones
- `complete_todo(todo_id: int)` — mark a todo as done
- `delete_todo(todo_id: int)` — delete a todo

## Run locally

```bash
uv sync
uv run main.py
```

The server listens on `http://0.0.0.0:8000/mcp` using the `streamable-http` transport.

Env vars:

- `PORT` — port to listen on (default `8000`)
- `TODO_DB_PATH` — path to the SQLite file (default `todo.db`)

Point an MCP client at `http://localhost:8000/mcp` to try it, e.g. with the MCP inspector:

```bash
uv run mcp dev main.py
```

## Deploy to Render

This repo includes a `Dockerfile` and a `render.yaml` blueprint that builds it and
provisions a web service plus a 1GB persistent disk mounted at `/data` (so the SQLite
file survives deploys/restarts — Render's regular filesystem is ephemeral, and disks
require a paid instance type, hence `plan: starter`).

1. Push this repo to GitHub.
2. In Render, create a new **Blueprint** and point it at the repo — it will read
   `render.yaml`, build the `Dockerfile`, and run the container.
3. Once deployed, your MCP endpoint is `https://<your-service>.onrender.com/mcp`.

You can also build/run the image locally to sanity-check it first:

```bash
docker build -t mcp-server-my-todo .
docker run --rm -p 8000:8000 mcp-server-my-todo
```

If you don't need persistence across deploys, you can skip the blueprint and just create
a plain Render web service with the same build/start commands on the free tier — the
todo list will just reset whenever the service redeploys or spins down.
