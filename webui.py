#!/usr/bin/env python3

from __future__ import annotations

import argparse
import uvicorn
from src.utils.project_paths import get_scoreboard_root
from src.webui import create_scoreboard_webui_app

def main() -> None:
    parser = argparse.ArgumentParser(description="Run the AgenticISG scoreboard WebUI.")
    parser.add_argument(
        "--scoreboard-root",
        type=str,
        default=str(get_scoreboard_root()),
        help="Directory containing scoreboard.csv and its sidecar files.",
    )
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Bind host.")
    parser.add_argument("--port", type=int, default=8000, help="Bind port.")
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=1.0,
        help="Polling interval in seconds used by the SSE stream.",
    )
    args = parser.parse_args()

    app = create_scoreboard_webui_app(
        scoreboard_root=args.scoreboard_root,
        poll_interval=args.poll_interval,
    )
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
