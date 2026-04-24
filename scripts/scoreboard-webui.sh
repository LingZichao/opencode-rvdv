#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SCOREBOARD_DIR="$PROJECT_ROOT/.opencode/skills/coverage/coverageDB/regression/long_agent_scoreboard"

if [ ! -d "$SCOREBOARD_DIR" ]; then
    echo "No scoreboard data found"
    exit 1
fi

echo "Scoreboard WebUI - Data location: $SCOREBOARD_DIR"
echo ""
echo "Available scoreboard files:"
ls -la "$SCOREBOARD_DIR/"*.csv "$SCOREBOARD_DIR/"*.json 2>/dev/null || echo "  No data files found"

echo ""
echo "To view scoreboard, use:"
echo "  python3 -c \"import pandas as pd; df=pd.read_csv('$SCOREBOARD_DIR/scoreboard.csv'); print(df.to_string())\""
