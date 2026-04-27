#!/usr/bin/env python3
"""Post-process trace_lifecycle.txt into a compact preview without captured signals.

Usage:
  python3 preview_trace.py <trace_lifecycle.txt> [-o <output_file>]
"""

import argparse
import re
import sys
from pathlib import Path


def parse_trace_lifecycle(filepath: str) -> list[dict]:
    """Parse trace_lifecycle.txt into structured path data."""
    paths = []
    current_path = None
    current_stage = None
    in_captured = False

    with open(filepath) as f:
        for line in f:
            line = line.rstrip()

            # Detect path header
            m = re.match(r"^Path #(\d+) \(Trace (\d+), Branch (\d+)\):", line)
            if m:
                if current_path:
                    paths.append(current_path)
                current_path = {
                    "path_num": int(m.group(1)),
                    "trace": int(m.group(2)),
                    "branch": int(m.group(3)),
                    "stages": [],
                    "complete": True,
                }
                current_stage = None
                in_captured = False
                continue

            # Skip empty lines and section separators
            if not line.strip() or line.startswith("==="):
                continue

            # Detect Duplicate Match Summary section - stop parsing
            if "Duplicate Match Summary" in line:
                if current_path:
                    paths.append(current_path)
                current_path = None
                break

            # Skip Captured signals block
            if in_captured:
                if line.startswith("       "):
                    continue
                else:
                    in_captured = False

            # Detect stage line: "  ●/→/◆ [task_name] row=N fsdb_time=M"
            m = re.match(
                r"^  ([●→◆]) \[(.+?)\] row=(\d+) fsdb_time=(\d+)(?:\s*\((.+?)\))?$",
                line,
            )
            if m:
                symbol = m.group(1)
                task_name = m.group(2)
                row_idx = int(m.group(3))
                fsdb_time = int(m.group(4))
                vars_str = m.group(5) or ""
                current_stage = {
                    "symbol": symbol,
                    "task_name": task_name,
                    "row": row_idx,
                    "fsdb_time": fsdb_time,
                    "vars": vars_str,
                    "log": "",
                }
                current_path["stages"].append(current_stage)
                in_captured = False
                continue

            # Detect LOG line
            m = re.match(r"^     LOG: (.+)$", line)
            if m and current_stage:
                current_stage["log"] = m.group(1)
                continue

            # Detect Captured signals header
            if line.startswith("     Captured signals:"):
                in_captured = True
                continue

    if current_path:
        paths.append(current_path)

    # Determine completeness: must reach a terminal stage (RTU retire)
    TERMINAL_KEYWORDS = ("RTU retire", "retire")
    for p in paths:
        if p["stages"]:
            last_name = p["stages"][-1]["task_name"]
            p["complete"] = any(kw in last_name for kw in TERMINAL_KEYWORDS)

    return paths


def extract_flush_info(filepath: str) -> str:
    """Extract flush boundary info from the full report if present."""
    flush_info = ""
    with open(filepath) as f:
        for line in f:
            if "Duplicate Match Summary" in line:
                break
            if "Flush boundaries:" in line or "Flush @" in line:
                flush_info += line
    return flush_info


def render_preview(paths: list[dict], filepath: str) -> str:
    """Render compact preview from parsed path data."""
    out = []

    total = len(paths)
    complete = sum(1 for p in paths if p["complete"])
    incomplete = total - complete

    out.append("=" * 70)
    out.append("Trace Lifecycle Preview")
    out.append("=" * 70)
    out.append("")
    out.append(f"Source: {filepath}")
    out.append(f"Total paths: {total}  Complete: {complete}  Incomplete: {incomplete}")
    out.append("")

    for p in paths:
        stages = p["stages"]
        if not stages:
            continue

        t_start = stages[0]["fsdb_time"]
        t_end = stages[-1]["fsdb_time"]
        status = "" if p["complete"] else " ◀ INCOMPLETE"

        out.append("-" * 70)
        out.append(
            f"Path #{p['path_num']} (Trace {p['trace']}, Branch {p['branch']})"
            f"  [{t_start} → {t_end}]{status}"
        )
        out.append("-" * 70)

        for stage in stages:
            symbol = stage["symbol"]
            name = stage["task_name"]
            ftime = stage["fsdb_time"]
            log = stage["log"]
            out.append(f"  {symbol} {name:<28s} {ftime:>10d}  {log}")

        out.append("")

    out.append("=" * 70)
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(
        description="Generate a compact preview of trace_lifecycle.txt"
    )
    parser.add_argument("input", help="Path to trace_lifecycle.txt")
    parser.add_argument("-o", "--output", help="Output file (default: stdout)")
    args = parser.parse_args()

    if not Path(args.input).exists():
        print(f"Error: file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    paths = parse_trace_lifecycle(args.input)

    if not paths:
        print("No paths found in trace_lifecycle.txt", file=sys.stderr)
        sys.exit(1)

    preview = render_preview(paths, args.input)

    if args.output:
        with open(args.output, "w") as f:
            f.write(preview + "\n")
        print(f"Preview written to: {args.output}")
    else:
        print(preview)


if __name__ == "__main__":
    main()
