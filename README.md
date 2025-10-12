# Archnote

Archnote standardizes free-text clinical notes into a consistent template and makes
it simple to append investigations from new visits without rewriting prior
documentation. The project ships both a Python API/CLI and an interactive web
application.

## Features

- **Formatter pipeline** – Normalizes whitespace, extracts core sections, and
  populates the HPI → Investigations → Assessment → Plan template.
- **Date normalization** – Converts common date formats into ISO 8601 to make
  timelines sortable.
- **Visit appender** – Append a new set of investigations to an existing note
  while preserving the original content.
- **Web UI** – A FastAPI-powered interface for formatting notes and adding new
  visits with one click.

## Quick start (for beginners)

If you just want to see Archnote in action, run the highlighted commands below
from the project root. The sections that follow explain each step in more
detail.

```bash
# 1. Create a virtual environment (only needs to be done once)
python -m venv .venv

# 2. Activate it (macOS/Linux shown; see below for Windows)
source .venv/bin/activate

# 3. Install Archnote and launch the web UI
pip install -e .
uvicorn archnote.web.app:app --reload
```

After the server starts, open <http://localhost:8000> and paste a note into the
left-hand panel. Use the **Append visit** tab to drop in a new investigation for
an existing note.

---

1. **Install Python 3.11 or newer.** On macOS/Linux you can check with
   `python3 --version`. Windows users can install from
   <https://www.python.org/downloads/>.
2. **Open a terminal** (Command Prompt/PowerShell on Windows, Terminal on
   macOS/Linux) and clone or download this repository.
3. **Create a virtual environment** so the dependencies stay isolated:

   ```bash
   python -m venv .venv
   ```

4. **Activate the environment** (run the command that matches your platform):

   ```bash
   # macOS / Linux
   source .venv/bin/activate

   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   ```

5. **Install the package and tools**:

   ```bash
   pip install -e .
   ```

   The editable install pulls in FastAPI, Uvicorn, and pytest automatically.

## Command-line usage

Format a note directly from a file or stdin:

```bash
archnote-format format note.txt
# or
cat note.txt | archnote-format format -
```

Append a new visit to an existing formatted note:

```bash
archnote-format append-visit existing_note.md new_visit.txt --label "Cardiology" --date 3/18/24
```

The updated note is printed to stdout so you can redirect it to a file.

> 📝 **Tip:** If you only have text on your clipboard, paste it into a temporary
> file (e.g., `raw.txt`) or run `pbpaste | archnote-format format -` on macOS to
> pipe clipboard contents directly to the formatter.

## Web application

Launch the interactive UI with Uvicorn (make sure your virtual environment is
still active):

```bash
uvicorn archnote.web.app:app --reload
```

Visit <http://localhost:8000> to paste raw notes, view the standardized output,
and append additional visits to a prior note. The UI includes a dual-panel
layout so you can keep iterating without leaving the browser.

To stop the server, press `Ctrl+C` in the terminal window that is running
Uvicorn.

### One-command web launch (macOS/Linux)

If you prefer not to remember the setup steps, run the helper script shipped
with the repo:

```bash
./scripts/run_web.sh
```

The script ensures a virtual environment exists, installs dependencies if
needed, and boots the local server. The first run may take a minute while pip
downloads packages.

## Deployment guide

### Container deployment

1. Ensure the project dependencies are installed: `pip install -e .[deploy]`
   (see `pyproject.toml`).
2. Build a container image (Docker example):

   ```bash
   cat <<'EOF' > Dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY . .
   RUN pip install --no-cache-dir .
   ENV ARCHNOTE_HOST=0.0.0.0 ARCHNOTE_PORT=8000
   CMD ["uvicorn", "archnote.web.app:app", "--host", "0.0.0.0", "--port", "8000"]
   EOF

   docker build -t archnote:latest .
   docker run -p 8000:8000 archnote:latest
   ```

3. Deploy the container to your hosting environment of choice (Fly.io, AWS
   App Runner, Google Cloud Run, etc.).

### Server deployment without containers

1. Provision a Python 3.11 environment on your server.
2. Install the package and its dependencies: `pip install archnote`.
3. Export optional environment overrides for host/port (defaults are
   `0.0.0.0:8000`):

   ```bash
   export ARCHNOTE_HOST=0.0.0.0
   export ARCHNOTE_PORT=9000
   ```

4. Start the server: `python -m archnote.web.app` or
   `uvicorn archnote.web.app:app --host "$ARCHNOTE_HOST" --port "$ARCHNOTE_PORT"`.
5. Place a reverse proxy such as Nginx or Caddy in front if you need HTTPS.

### Front-end customization

The bundled HTML and CSS live under `archnote/web/templates` and
`archnote/web/static`. Update these files to align with your branding. Because
the front-end is server-rendered, you can also integrate authentication or data
stores by extending `archnote/web/app.py`.

## Tests

Run the unit suite with:

```bash
pytest
```

## Contributing

Issues and pull requests are welcome. Please run `pytest` before submitting to
ensure existing functionality stays intact.
