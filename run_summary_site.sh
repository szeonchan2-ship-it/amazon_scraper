#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
APP_SCRIPT="$SCRIPT_DIR/summary_site.py"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Virtual environment not found at .venv."
  echo "Run: /usr/bin/python3 -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt"
  exit 1
fi

echo "Starting summary site on http://127.0.0.1:5050"
"$PYTHON_BIN" "$APP_SCRIPT"
