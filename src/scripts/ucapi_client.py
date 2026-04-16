#!/usr/bin/env python3
"""
UCAPI HTTP Client - Coverage query CLI wrapper for OpenCode-RVDV tools.

Usage:
    python3 ucapi_client.py query-baseline --rtl-file <file> --start-line <n> --end-line <n> --kind <type> --api-url <url>
    python3 ucapi_client.py query --rtl-file <file> --testname <name> --start-line <n> --end-line <n> --task-name <name> --kind <type> --api-url <url>
    python3 ucapi_client.py list-tests --task-name <name> [--vdb-path <path>]
"""

import argparse
import json
import sys
import os
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COVERAGEDB_ROOT = PROJECT_ROOT / "coverageDB"
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
TEMPLATE_ROOT = COVERAGEDB_ROOT / "template"


def get_baseline_vdb_path():
    return TEMPLATE_ROOT / "BASELINE.vdb"


def get_task_sim_root(task_name):
    return COVERAGEDB_ROOT / "tasks" / task_name / "sim"


def detect_vdb_path(task_name):
    sim_root = get_task_sim_root(task_name)
    preferred = [
        sim_root / "work_force" / "simv.vdb",
        sim_root / "simv.vdb",
    ]
    for candidate in preferred:
        if candidate.exists() and candidate.is_dir():
            return candidate
    if sim_root.exists():
        for p in sim_root.rglob("*.vdb"):
            if p.is_dir():
                return p
    return None


def query_baseline(args):
    module_name = Path(args.rtl_file).stem
    baseline_vdb = get_baseline_vdb_path()
    if not baseline_vdb.exists():
        print(json.dumps({"error": f"BASELINE database not found at {baseline_vdb}"}))
        sys.exit(1)

    vdb_path = str(baseline_vdb)
    test_path = f"{vdb_path}/test"

    payload = {
        "vdb_path": vdb_path,
        "test_name": test_path,
        "module": module_name,
        "start_line": args.start_line,
        "end_line": args.end_line,
        "kind": args.kind,
    }

    try:
        resp = requests.post(args.api_url, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if not result.get("success", False):
            print(json.dumps({"error": result.get("error", "Unknown error")}))
            sys.exit(1)
        print(json.dumps(result.get("data", {}), ensure_ascii=False, indent=2))
    except requests.exceptions.ConnectionError:
        print(json.dumps({"error": "Cannot connect to coverage server"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def query_coverage(args):
    module_name = Path(args.rtl_file).stem

    if not args.testname:
        print(
            json.dumps(
                {"error": "testname is REQUIRED", "suggestion": "Use list-tests first"}
            )
        )
        sys.exit(1)

    detected_vdb = detect_vdb_path(args.task_name)
    if detected_vdb is None:
        print(json.dumps({"error": f"No .vdb found for task {args.task_name}"}))
        sys.exit(1)

    vdb_path = str(detected_vdb)
    test_path = f"{vdb_path}/{args.testname}"

    payload = {
        "vdb_path": vdb_path,
        "test_name": test_path,
        "module": module_name,
        "start_line": args.start_line,
        "end_line": args.end_line,
        "kind": args.kind,
    }

    try:
        resp = requests.post(args.api_url, json=payload, timeout=60)
        resp.raise_for_status()
        result = resp.json()
        if not result.get("success", False):
            print(json.dumps({"error": result.get("error", "Unknown error")}))
            sys.exit(1)
        print(json.dumps(result.get("data", {}), ensure_ascii=False, indent=2))
    except requests.exceptions.ConnectionError:
        print(json.dumps({"error": "Cannot connect to coverage server"}))
        sys.exit(1)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


def list_tests(args):
    if args.vdb_path:
        vdb_path = Path(args.vdb_path)
    else:
        detected = detect_vdb_path(args.task_name)
        if detected is None:
            print(
                json.dumps(
                    {
                        "error": f"No .vdb found for task {args.task_name}",
                        "suggestion": "Run fetch first",
                    }
                )
            )
            sys.exit(1)
        vdb_path = detected

    testdata_dir = vdb_path / "snps" / "coverage" / "db" / "testdata"
    if not testdata_dir.exists():
        print(json.dumps({"error": f"testdata not found at {testdata_dir}"}))
        sys.exit(1)

    tests = []
    for item in testdata_dir.iterdir():
        if item.is_dir() and not item.name.startswith("."):
            tests.append(item.name)

    tests.sort()
    print(
        json.dumps(
            {"vdb_path": str(vdb_path), "tests": tests, "test_count": len(tests)},
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(
        description="UCAPI Coverage Client for OpenCode-RVDV"
    )
    subparsers = parser.add_subparsers(dest="command")

    baseline_parser = subparsers.add_parser("query-baseline")
    baseline_parser.add_argument("--rtl-file", required=True)
    baseline_parser.add_argument("--start-line", type=int, default=0)
    baseline_parser.add_argument("--end-line", type=int, default=50000)
    baseline_parser.add_argument("--kind", default="line")
    baseline_parser.add_argument(
        "--api-url", default="http://localhost:5000/api/v1/query"
    )

    query_parser = subparsers.add_parser("query")
    query_parser.add_argument("--rtl-file", required=True)
    query_parser.add_argument("--testname", required=True)
    query_parser.add_argument("--start-line", type=int, default=0)
    query_parser.add_argument("--end-line", type=int, default=50000)
    query_parser.add_argument("--task-name", required=True)
    query_parser.add_argument("--kind", default="line")
    query_parser.add_argument("--api-url", default="http://localhost:5000/api/v1/query")

    list_parser = subparsers.add_parser("list-tests")
    list_parser.add_argument("--task-name", required=True)
    list_parser.add_argument("--vdb-path", default=None)

    args = parser.parse_args()
    if args.command == "query-baseline":
        query_baseline(args)
    elif args.command == "query":
        query_coverage(args)
    elif args.command == "list-tests":
        list_tests(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
