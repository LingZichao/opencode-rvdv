#!/usr/bin/env python3
"""
VCS Simulation Runner - Execute simulation and fetch coverage report.

This script is called by TypeScript tool wrappers via Bun subprocess.
Steps:
1. Copy ISG script to simulation directory
2. Run FORCE-RISCV to generate instructions (make force_rv)
3. Execute VCS simulation (make run)
4. Return VDB path for coverage query
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path


def find_project_root():
    for parent in Path(__file__).resolve().parents:
        if (
            (parent / "opencode.json").exists()
            or (parent / "coverageDB").exists()
        ) and (parent / "workspace").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()
SKILL_ROOT = Path(__file__).resolve().parents[1]
COVERAGEDB_ROOT = SKILL_ROOT / "coverageDB"
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
TEMPLATE_ROOT = COVERAGEDB_ROOT / "template"


def get_task_sim_root(task_name):
    return COVERAGEDB_ROOT / "tasks" / task_name / "sim"


def ensure_task_sim_root(task_name):
    sim_root = get_task_sim_root(task_name)
    if sim_root.exists():
        return sim_root

    template_sim = TEMPLATE_ROOT / "sim"
    if not template_sim.exists():
        raise FileNotFoundError(f"Simulation template not found: {template_sim}")

    sim_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_sim, sim_root)
    return sim_root


def get_isg_script_root(task_name):
    return WORKSPACE_ROOT / "isgScripts" / task_name


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


def find_script(script_name, task_name):
    filename = script_name if script_name.endswith(".py") else f"{script_name}.py"
    script_root = get_isg_script_root(task_name)

    candidate = script_root / filename
    if candidate.exists():
        return candidate

    for f in script_root.glob("*.py"):
        if f.stem == Path(filename).stem:
            return f

    raise FileNotFoundError(f"Script not found: {filename}")


def execute_simulation(script_name, iter_count, task_name):
    try:
        isg_scripts_root = get_isg_script_root(task_name)
        isg_scripts_root.mkdir(parents=True, exist_ok=True)

        sim_root = ensure_task_sim_root(task_name)

        src_script = find_script(script_name, task_name)
        dest_script = sim_root / "AgenticTargetTest.py"
        dest_script.unlink(missing_ok=True)
        shutil.copy2(str(src_script), str(dest_script))

        proc = subprocess.run(
            ["make", "-f", "makefileFRV", "force_rv"],
            cwd=str(sim_root),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return json.dumps(
                {
                    "error": "Make target 'force_rv' failed",
                    "suggestion": "Retry the simulation-run command; randomness may cause errors",
                    "stderr": proc.stderr[-500:],
                }
            )

        test_name = script_name.split("/")[-1].split(".")[0]
        proc = subprocess.run(
            [
                "make",
                "-f",
                "makefileFRV",
                "run",
                f"TASK_NAME={test_name}",
                f"ITER_NUM={iter_count}",
            ],
            cwd=str(sim_root),
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return json.dumps(
                {
                    "error": f"Make 'run' failed with TASK_NAME={test_name}, ITER_NUM={iter_count}",
                    "stderr": proc.stderr[-500:],
                }
            )

        vdb_path = detect_vdb_path(task_name)
        return json.dumps(
            {
                "status": "success",
                "test_name": test_name + "_iter_" + str(iter_count),
                "iter_count": iter_count,
                "cov_report_path": str(vdb_path)
                if vdb_path
                else str(sim_root / "work_force" / "simv.vdb"),
                "note": "load coverage and query this test name to get coverage information",
            }
        )
    except Exception as e:
        return json.dumps({"error": f"Simulation failed: {e}"})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--script-name", required=True)
    parser.add_argument("--iter-count", type=int, default=1)
    parser.add_argument("--task-name", required=True)
    args = parser.parse_args()
    print(execute_simulation(args.script_name, args.iter_count, args.task_name))
