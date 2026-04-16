#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f "$PROJECT_ROOT/.env" ]; then
    set -a
    source "$PROJECT_ROOT/.env"
    set +a
fi

RTL_FILE="${1:?Usage: run-task.sh <rtl_file> <line_range>}"
LINE_RANGE="${2:?Usage: run-task.sh <rtl_file> <line_range>}"
EXTRA_ARGS="${3:-}"

echo "Running verification task: $RTL_FILE $LINE_RANGE"
opencode run "/verify $RTL_FILE $LINE_RANGE $EXTRA_ARGS"