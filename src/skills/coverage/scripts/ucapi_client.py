#!/usr/bin/env python3
"""
UCAPI HTTP Client - Coverage query CLI wrapper for OpenCode-RVDV tools.

Usage:
    python3 ucapi_client.py query-baseline --rtl-file <file> --start-line <n> --end-line <n> --kind <type> --api-url <url>
    python3 ucapi_client.py query --rtl-file <file> --testname <name> --start-line <n> --end-line <n> --kind <type> --api-url <url>
    python3 ucapi_client.py list-tests
"""

import argparse
import json
import sys
from pathlib import Path

import requests


def find_project_root():
    for parent in Path(__file__).resolve().parents:
        if (
            (parent / "opencode.jsonc").exists()
            or (parent / "coverageDB").exists()
        ) and (parent / "workspace").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()
SKILL_ROOT = Path(__file__).resolve().parents[1]
COVERAGEDB_ROOT = SKILL_ROOT / "coverageDB"
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
DEFAULT_VDB_PATH = WORKSPACE_ROOT / "openc910" / "smart_run" / "work_force" / "simv.vdb"
TEMPLATE_ROOT = COVERAGEDB_ROOT / "template"


def path_is_relative_to(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def get_baseline_vdb_path():
    return TEMPLATE_ROOT / "BASELINE.vdb"


def get_task_sim_root(task_name):
    return COVERAGEDB_ROOT / "tasks" / task_name / "sim"


def detect_vdb_path(task_name):
    if not task_name:
        return None
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


def resolve_vdb_path(vdb_path, task_name=None):
    if vdb_path:
        candidate = Path(vdb_path).expanduser()
        if not candidate.is_absolute():
            raise FileNotFoundError(f"--vdb-path must be an absolute path: {vdb_path}")
        candidate = candidate.resolve()
        if not path_is_relative_to(candidate, WORKSPACE_ROOT):
            raise FileNotFoundError(
                f"--vdb-path must be under workspace: {candidate}; workspace={WORKSPACE_ROOT}"
            )
        if not candidate.exists() or not candidate.is_dir():
            raise FileNotFoundError(f"VDB directory not found: {candidate}")
        return candidate

    if task_name:
        detected = detect_vdb_path(task_name)
        if detected is None:
            raise FileNotFoundError(f"No .vdb found for task {task_name}")
        return detected

    if DEFAULT_VDB_PATH.exists() and DEFAULT_VDB_PATH.is_dir():
        return DEFAULT_VDB_PATH.resolve()

    raise FileNotFoundError(
        f"Default VDB directory not found: {DEFAULT_VDB_PATH}. "
        "Run coverage/scripts/simulation_runner.py first or pass --vdb-path."
    )


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


def query_task_coverage(args):
    module_name = Path(args.rtl_file).stem

    if not args.testname:
        print(
            json.dumps(
                {"error": "testname is REQUIRED", "suggestion": "Use list-tests first"}
            )
        )
        sys.exit(1)

    try:
        detected_vdb = resolve_vdb_path(args.vdb_path, args.task_name)
    except FileNotFoundError as e:
        print(json.dumps({"error": str(e)}))
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
    try:
        vdb_path = resolve_vdb_path(args.vdb_path, args.task_name)
    except FileNotFoundError as e:
        print(
            json.dumps(
                {
                    "error": str(e),
                    "suggestion": "Run coverage/scripts/simulation_runner.py first or pass --vdb-path",
                }
            )
        )
        sys.exit(1)

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
    query_parser.add_argument("--vdb-path", default=None)
    query_parser.add_argument("--task-name", default=None)
    query_parser.add_argument("--kind", default="line")
    query_parser.add_argument("--api-url", default="http://localhost:5000/api/v1/query")

    list_parser = subparsers.add_parser("list-tests")
    list_parser.add_argument("--vdb-path", default=None)
    list_parser.add_argument("--task-name", default=None)

    args = parser.parse_args()
    if args.command == "query-baseline":
        query_baseline(args)
    elif args.command == "query":
        query_task_coverage(args)
    elif args.command == "list-tests":
        list_tests(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
