#!/usr/bin/env python3
"""
Coverage Data Parser - Parse coverage query results for agent consumption.

This script formats raw coverage data into human-readable reports.
Called by TypeScript tool wrappers when needed.
"""

import json
import sys
from pathlib import Path


def parse_coverage_report(data, kind="line"):
    """Parse coverage data into a human-readable format."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return data

    if "error" in data:
        return f"Error: {data['error']}"

    lines = []
    vp_summary = data.get("vp", {})
    metrics = vp_summary.get("metrics", {})

    for coverage_type, metric_data in metrics.items():
        pct = metric_data.get("pct", 0)
        covered = metric_data.get("covered", 0)
        coverable = metric_data.get("coverable", 0)
        matched = metric_data.get("matched", 0)

        lines.append(f"## {coverage_type.upper()} Coverage")
        lines.append(f"  Coverage: {pct:.1f}% ({covered}/{coverable})")
        lines.append(f"  Matched instances: {matched}")
        lines.append("")

    query_info = vp_summary.get("query", {})
    if query_info:
        lines.append(f"Module: {query_info.get('module', 'N/A')}")
        lines.append(f"Source file: {query_info.get('source_file', 'N/A')}")
        lines.append(
            f"Qualified instance: {query_info.get('qualified_instance', 'N/A')}"
        )

    return "\n".join(lines)


def extract_uncovered_vp(data, threshold=95.0):
    """Extract uncovered verification points from coverage data."""
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            return []

    uncovered = []
    vp_summary = data.get("vp", {})
    metrics = vp_summary.get("metrics", {})

    for kind, metric_data in metrics.items():
        pct = metric_data.get("pct", 0)
        if pct < threshold:
            uncovered.append(
                {
                    "kind": kind,
                    "pct": pct,
                    "covered": metric_data.get("covered", 0),
                    "coverable": metric_data.get("coverable", 0),
                }
            )

    return uncovered


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--input", required=True, help="JSON coverage data or file path"
    )
    parser.add_argument("--kind", default="line")
    parser.add_argument("--extract-uncovered", action="store_true")
    parser.add_argument("--threshold", type=float, default=95.0)
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.exists():
        data = json.loads(input_path.read_text())
    else:
        data = json.loads(args.input)

    if args.extract_uncovered:
        result = extract_uncovered_vp(data, args.threshold)
        print(json.dumps(result, indent=2))
    else:
        print(parse_coverage_report(data, args.kind))
