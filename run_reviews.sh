#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
PARSER_SCRIPT="$SCRIPT_DIR/parse_pasted_reviews.py"
UI_SCRIPT="$SCRIPT_DIR/reviews_ui.py"
WEB_UI_SCRIPT="$SCRIPT_DIR/reviews_web_ui.py"
OUTPUT_FILE="$SCRIPT_DIR/parsed_reviews.csv"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Virtual environment not found at .venv."
  echo "Run: /usr/bin/python3 -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt"
  exit 1
fi

if [[ "${1:-}" == "--cli" ]]; then
  echo "Paste review text, then press Ctrl+D to finish."
  "$PYTHON_BIN" "$PARSER_SCRIPT" -o "$OUTPUT_FILE"
  exit 0
fi

if [[ "${1:-}" == "--tk" ]]; then
  echo "Opening Tk UI..."
  TK_SILENCE_DEPRECATION=1 "$PYTHON_BIN" "$UI_SCRIPT"
  exit 0
fi

echo "Opening Web UI..."
"$PYTHON_BIN" "$WEB_UI_SCRIPT"
