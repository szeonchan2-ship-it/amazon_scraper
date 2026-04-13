#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON_BIN="$SCRIPT_DIR/.venv/bin/python"
PARSER_SCRIPT="$SCRIPT_DIR/parse_pasted_reviews.py"
OUTPUT_FILE="$SCRIPT_DIR/parsed_reviews.csv"

if [[ ! -x "$PYTHON_BIN" ]]; then
  echo "Virtual environment not found at .venv."
  echo "Run: /usr/bin/python3 -m venv .venv && source .venv/bin/activate && python -m pip install -r requirements.txt"
  exit 1
fi

echo "Paste review text, then press Ctrl+D to finish."
"$PYTHON_BIN" "$PARSER_SCRIPT" -o "$OUTPUT_FILE"
