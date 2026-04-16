#!/usr/bin/env python3
"""
Coverage Query Logic - Extracted from AgenticISG coverage_tools.py

This script is called by TypeScript tool wrappers via Bun subprocess.
It handles coverage querying logic including baseline and task-specific queries.
"""

import json
import sys
import re
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COVERAGEDB_ROOT = PROJECT_ROOT / "coverageDB"
TEMPLATE_ROOT = COVERAGEDB_ROOT / "template"


def get_baseline_vdb_path():
    return TEMPLATE_ROOT / "BASELINE.vdb"


def get_task_sim_root(task_name):
    return COVERAGEDB_ROOT / "tasks" / task_name / "sim"


def detect_vdb_path(task_name):
    sim_root = get_task_sim_root(task_name)
    for candidate in [sim_root / "work_force" / "simv.vdb", sim_root / "simv.vdb"]:
        if candidate.exists() and candidate.is_dir():
            return candidate
    if sim_root.exists():
        for p in sim_root.rglob("*.vdb"):
            if p.is_dir():
                return p
    return None


def query_ucapi(vdb_path, test_name, module, start_line, end_line, kind, api_url):
    payload = {
        "vdb_path": vdb_path,
        "test_name": test_name,
        "module": module,
        "start_line": start_line,
        "end_line": end_line,
        "kind": kind,
    }
    try:
        resp = requests.post(api_url, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if not result.get("success", False):
            return {"error": result.get("error", "Unknown error")}
        return result.get("data", {})
    except requests.exceptions.ConnectionError:
        return {"error": "Cannot connect to coverage server"}
    except requests.exceptions.Timeout:
        return {"error": "HTTP request timed out"}
    except Exception as e:
        return {"error": str(e)}


def parse_line_range(range_str):
    range_str = str(range_str).strip()
    range_str = re.sub(r"\([^)]*\)", "", range_str).strip()
    if "-" in range_str:
        parts = range_str.split("-")
        start = (
            int(re.search(r"\d+", parts[0]).group())
            if re.search(r"\d+", parts[0])
            else 0
        )
        end = (
            int(re.search(r"\d+", parts[1]).group())
            if re.search(r"\d+", parts[1])
            else 50000
        )
        return start, end
    match = re.search(r"\d+", range_str)
    if match:
        line = int(match.group())
        return line, line
    return 0, 50000
