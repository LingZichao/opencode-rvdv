#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PORT="${SCOREBOARD_PORT:-8011}"
HOST="${SCOREBOARD_HOST:-0.0.0.0}"
APP_PATH="$PROJECT_ROOT/webui/scoreboard/app.py"
SCOREBOARD_DIR="${SCOREBOARD_DATA_DIR:-$PROJECT_ROOT/webui/scoreboard/data}"

choose_python() {
    if [ -n "${SCOREBOARD_PYTHON:-}" ] && [ -x "${SCOREBOARD_PYTHON}" ]; then
        echo "${SCOREBOARD_PYTHON}"
        return
    fi

    if [ -x "$PROJECT_ROOT/../.venv/bin/python3.13" ]; then
        echo "$PROJECT_ROOT/../.venv/bin/python3.13"
        return
    fi

    if command -v python3.12 >/dev/null 2>&1; then
        command -v python3.12
        return
    fi

    if command -v python3 >/dev/null 2>&1; then
        command -v python3
        return
    fi

    echo ""
}

PYTHON_BIN="$(choose_python)"
if [ -z "$PYTHON_BIN" ]; then
    echo "No Python interpreter found."
    exit 1
fi

PYTHON_VERSION="$($PYTHON_BIN -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")')"
PYTHON_MAJOR="${PYTHON_VERSION%%.*}"
PYTHON_MINOR="${PYTHON_VERSION##*.}"

if [ "$PYTHON_MAJOR" -lt 3 ] || { [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 7 ]; }; then
    echo "Selected Python is too old: $PYTHON_BIN ($PYTHON_VERSION). Need >= 3.7"
    echo "Set SCOREBOARD_PYTHON to a newer interpreter, e.g.:"
    echo "  export SCOREBOARD_PYTHON=$PROJECT_ROOT/../.venv/bin/python3.13"
    exit 1
fi

if [ ! -f "$APP_PATH" ]; then
    echo "Missing standalone scoreboard app: $APP_PATH"
    exit 1
fi

if [ ! -d "$SCOREBOARD_DIR" ]; then
    echo "Missing scoreboard data dir: $SCOREBOARD_DIR"
    echo "You can set SCOREBOARD_DATA_DIR to point to another folder."
    exit 1
fi

if [ ! -f "$SCOREBOARD_DIR/scoreboard.csv" ]; then
    echo "Missing scoreboard CSV: $SCOREBOARD_DIR/scoreboard.csv"
    exit 1
fi

echo "Starting standalone Scoreboard WebUI"
echo "  Data: $SCOREBOARD_DIR"
echo "  Python: $PYTHON_BIN ($PYTHON_VERSION)"
echo "  URL : http://$HOST:$PORT/scoreboard"
echo ""

cd "$PROJECT_ROOT"
exec "$PYTHON_BIN" "$APP_PATH" \
  --data-dir "$SCOREBOARD_DIR" \
  --host "$HOST" \
  --port "$PORT"
