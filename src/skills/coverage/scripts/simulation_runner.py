#!/usr/bin/env python3
"""
VCS Simulation Runner - Execute FORCE-RISCV generation and RTL simulation.

The runner uses the migrated OpenC910 smart_run flow directly:
1. Copy the requested ISG script to workspace/openc910/smart_run/AgenticTargetTest.py
2. Run FORCE-RISCV to generate instructions through makefileFRV
3. Compile the OpenC910 simulation binary through makefileFRV
4. Execute the simulator in workspace/openc910/smart_run/work_force
5. Return the fixed smart_run/work_force/simv.vdb path for coverage queries
"""

import json
import os
import shutil
import subprocess
from pathlib import Path


def path_is_relative_to(path, root):
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def find_project_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "opencode.json").exists() or (parent / "package.json").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
SMART_RUN_ROOT = WORKSPACE_ROOT / "openc910" / "smart_run"
WORK_FORCE_ROOT = SMART_RUN_ROOT / "work_force"
VDB_PATH = WORK_FORCE_ROOT / "simv.vdb"
CODE_BASE_PATH = WORKSPACE_ROOT / "openc910" / "C910_RTL_FACTORY"
REQUIRED_SMART_RUN_FILES = [
    Path("makefileFRV"),
    Path("logical") / "filelists" / "sim.fl",
    Path("tests") / "bin" / "Srec2vmem",
    Path("..") / "C910_RTL_FACTORY" / "gen_rtl" / "filelists" / "C910_asic_rtl.fl",
]


def resolve_workspace_path(path_arg, arg_name, *, must_exist=False):
    if not path_arg:
        raise FileNotFoundError(f"{arg_name} is required")

    candidate = Path(path_arg).expanduser()
    if not candidate.is_absolute():
        raise FileNotFoundError(f"{arg_name} must be an absolute path: {path_arg}")

    candidate = candidate.resolve()
    if not path_is_relative_to(candidate, WORKSPACE_ROOT):
        raise FileNotFoundError(
            f"{arg_name} must be under workspace: {candidate}; workspace={WORKSPACE_ROOT}"
        )

    if must_exist and not candidate.exists():
        raise FileNotFoundError(f"Path does not exist: {candidate}")
    return candidate


def resolve_script_path(script_path):
    candidate = resolve_workspace_path(script_path, "--script-path", must_exist=True)
    if not candidate.is_file():
        raise FileNotFoundError(f"Script path is not a file: {candidate}")
    if candidate.suffix != ".py":
        raise FileNotFoundError(f"Script path must point to a .py file: {candidate}")
    return candidate


def ensure_smart_run_root():
    required = [SMART_RUN_ROOT / rel for rel in REQUIRED_SMART_RUN_FILES]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Simulation root is incomplete under workspace/openc910/smart_run. "
            "Missing: " + ", ".join(missing)
        )
    return SMART_RUN_ROOT


def run_make(args, step):
    env = os.environ.copy()
    env.setdefault("CODE_BASE_PATH", str(CODE_BASE_PATH.resolve()))
    proc = subprocess.run(
        ["make", "-f", "makefileFRV", *args],
        cwd=str(SMART_RUN_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
    )
    if proc.returncode == 0:
        return None

    return {
        "error": f"Make target '{step}' failed",
        "step": step,
        "returncode": proc.returncode,
        "stdout": proc.stdout[-1000:],
        "stderr": proc.stderr[-1000:],
        "smart_run_root": str(SMART_RUN_ROOT),
        "work_force": str(WORK_FORCE_ROOT),
        "vdb_path": str(VDB_PATH),
        "cov_report_path": str(VDB_PATH),
    }


def success_payload(script_path, test_name, iter_count):
    return {
        "status": "success",
        "test_name": test_name,
        "iter_count": iter_count,
        "script_path": str(script_path),
        "smart_run_root": str(SMART_RUN_ROOT),
        "work_force": str(WORK_FORCE_ROOT),
        "vdb_path": str(VDB_PATH),
        "cov_report_path": str(VDB_PATH),
        "note": "Use coverage list-tests/query with --vdb-path and this test_name.",
    }


def execute_simulation(script_path, iter_count, sim_root=None):
    try:
        script_path = resolve_script_path(script_path)
        ensure_smart_run_root()

        dest_script = SMART_RUN_ROOT / "AgenticTargetTest.py"
        shutil.copy2(str(script_path), str(dest_script))

        error = run_make(["setup", "force_rv"], "setup force_rv")
        if error:
            return json.dumps(error, ensure_ascii=False, indent=2)

        error = run_make(["compile"], "compile")
        if error:
            return json.dumps(error, ensure_ascii=False, indent=2)

        test_name = f"{script_path.stem}_iter_{iter_count}"
        error = run_make(
            ["run", f"COVTEST={test_name}", f"ITER_NUM={iter_count}"],
            f"run COVTEST={test_name} ITER_NUM={iter_count}",
        )
        if error:
            return json.dumps(error, ensure_ascii=False, indent=2)

        return json.dumps(
            success_payload(script_path, test_name, iter_count),
            ensure_ascii=False,
            indent=2,
        )
    except Exception as exc:
        return json.dumps({"error": f"Simulation failed: {exc}"})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--script-path", required=True)
    parser.add_argument("--iter-count", type=int, default=1)
    parser.add_argument("--sim-root", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--task-name", default=None, help=argparse.SUPPRESS)
    parser.add_argument("--script-name", default=None, help=argparse.SUPPRESS)
    args = parser.parse_args()
    print(execute_simulation(args.script_path, args.iter_count, args.sim_root))
