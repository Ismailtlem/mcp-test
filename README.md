# notes-mcp

A small MCP server that manages a personal notes/knowledge-base backed by
SQLite, with full-text search (FTS5). Runs locally over stdio — no API keys
required.

## Tools

- `add_note(title, content, tags="")` — create a note
- `search_notes(query, limit=10)` — full-text search (ranked by relevance)
- `list_notes(tag=None, limit=50)` — list notes, newest first, optional tag filter
- `get_note(note_id)` — fetch a note by id
- `update_note(note_id, title=None, content=None, tags=None)` — partial update
- `delete_note(note_id)` — delete a note

## Resource

- `notes://all` — markdown listing of all notes

Data is stored in `notes.db` next to `main.py` (created automatically on
first run, gitignored).

## Run standalone

```bash
uv run main.py
```

## Add to Claude Code

From this directory:

```bash
claude mcp add notes -- uv run --directory "$(pwd)" main.py
```

Then restart Claude Code (or run `/mcp` to check connection status).

## Add to Claude Desktop

Add this to your `claude_desktop_config.json`
(`~/.config/Claude/claude_desktop_config.json` on Linux):

```json
{
  "mcpServers": {
    "notes": {
      "command": "uv",
      "args": ["run", "--directory", "/home/ismail/Documents/DEV/playgrounds/ai-exercices/mcp-server-init", "main.py"]
    }
  }
}
```

Restart Claude Desktop after saving.

## Deploy to Render + use from claude.ai (browser)

claude.ai's browser chat only supports **remote** MCP servers over HTTPS, not
local stdio processes. `main.py` supports an HTTP mode for this: set
`MCP_TRANSPORT=http` and it serves streamable-HTTP on `$PORT` (default 8000)
at path `/mcp`, instead of stdio.

**Note:** Render's free tier has no persistent disk — `notes.db` resets on
every redeploy/restart, and the service spins down after inactivity (cold
start on the next request). This is fine for test data; don't rely on it for
anything you need to keep. There is also no authentication on the endpoint —
anyone with the URL can read/write notes.

### 1. Push this repo to GitHub

Render deploys from a git repo:

```bash
git init   # if not already a repo
git add .
git commit -m "Add notes MCP server"
git remote add origin <your-github-repo-url>
git push -u origin main
```

### 2. Deploy on Render

1. Go to https://dashboard.render.com → **New** → **Blueprint**.
2. Connect the GitHub repo you just pushed. Render will detect `render.yaml`
   in this repo and configure the service (Docker runtime, free plan,
   `MCP_TRANSPORT=http`) automatically.
3. Click **Apply** / **Deploy**. Wait for the build to finish (uses the
   `Dockerfile` in this repo).
4. Once live, note the public URL Render gives you, e.g.
   `https://notes-mcp.onrender.com`. The MCP endpoint is that URL + `/mcp`,
   e.g. `https://notes-mcp.onrender.com/mcp`.

If you'd rather not use the Blueprint: **New → Web Service**, connect the
repo, choose **Docker** as the runtime/environment, and manually add the env
var `MCP_TRANSPORT=http` — everything else uses the `Dockerfile` defaults.

### 3. Add it as a connector in claude.ai

1. In claude.ai, go to **Settings → Connectors → Add custom connector**.
2. Paste the `/mcp` URL from step 2 (e.g.
   `https://notes-mcp.onrender.com/mcp`).
3. No authentication needed — leave auth fields blank.
4. Save, then enable the `notes` tools in a chat.

First request after idle time will be slow (cold start on Render's free
tier) — that's expected.
