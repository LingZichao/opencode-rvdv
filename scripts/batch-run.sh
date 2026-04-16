#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
TASKS_DIR="$PROJECT_ROOT/coverageDB/tasks"

if [ ! -d "$TASKS_DIR" ]; then
    echo "No tasks directory found"
    exit 1
fi

echo "Available tasks:"
for task_dir in "$TASKS_DIR"/*/; do
    task_name=$(basename "$task_dir")
    echo "  - $task_name"
done

echo ""
echo "Running all tasks sequentially..."

for task_dir in "$TASKS_DIR"/*/; do
    task_name=$(basename "$task_dir")
    echo "=== Running task: $task_name ==="
    
    if [ -f "$task_dir/task_config.json" ]; then
        rtl_file=$(python3 -c "import json; d=json.load(open('$task_dir/task_config.json')); print(d.get('rtl_file',''))")
        line_range=$(python3 -c "import json; d=json.load(open('$task_dir/task_config.json')); print(d.get('line_range',''))")
        
        if [ -n "$rtl_file" ] && [ -n "$line_range" ]; then
            "$PROJECT_ROOT/scripts/run-task.sh" "$rtl_file" "$line_range"
        else
            echo "  Skipping: missing config"
        fi
    else
        echo "  Skipping: no task_config.json"
    fi
done