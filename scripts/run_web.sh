#!/usr/bin/env bash
set -euo pipefail
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")"/.. && pwd)"
cd "$PROJECT_ROOT"

if [ ! -d ".venv" ]; then
  echo "[archnote] Creating virtual environment at .venv"
  python3 -m venv .venv
fi

# shellcheck source=/dev/null
source .venv/bin/activate

if ! python -c "import archnote" >/dev/null 2>&1; then
  echo "[archnote] Installing project dependencies"
  pip install -e .
fi

echo "[archnote] Starting web app on http://localhost:8000"
exec uvicorn archnote.web.app:app --reload
