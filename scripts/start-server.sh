#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if [ ! -f "$PROJECT_ROOT/opencode.jsonc" ]; then
    echo "Project not initialized. Run: bun run src/init/init.ts"
    exit 1
fi

if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

if ! curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "Warning: UCAPI coverage server not running at localhost:5000"
    echo "   Please start it manually if needed"
fi

echo "Starting OpenCode server..."
cd "$PROJECT_ROOT"

PORT="${OPENCODE_PORT:-4096}"
HOST="${OPENCODE_HOSTNAME:-0.0.0.0}"

opencode serve --port "$PORT" --hostname "$HOST"