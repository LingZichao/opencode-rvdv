#!/usr/bin/env python3
"""
FORCE-RISCV ISG Compiler - Compile ISG scripts using FORCE-RISCV.

This script is called by TypeScript tool wrappers via Bun subprocess.
It compiles ISG test scripts from workspace/isgScripts/<task_id>/.
"""

import json
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
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


def get_isg_script_root(task_name):
    return WORKSPACE_ROOT / "isgScripts" / task_name


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


def compile_script(script_name, task_name):
    try:
        script_path = find_script(script_name, task_name)

        force_riscv_bin = PROJECT_ROOT / "bin" / "friscv"
        if not force_riscv_bin.exists():
            env_bin = Path("/home/c910/force-riscv/bin/friscv")
            if env_bin.exists():
                force_riscv_bin = env_bin
            else:
                return json.dumps({"error": "FORCE-RISCV binary not found"})

        config_path = Path("/home/c910/force-riscv/config/riscv_rv64_c910.config")
        env_config = Path(
            PROJECT_ROOT
            / "workspace"
            / "agentDoc"
            / "forceRV"
            / "config"
            / "riscv_rv64_c910.config"
        )
        if env_config.exists():
            config_path = env_config

        proc = subprocess.run(
            [str(force_riscv_bin), "-c", str(config_path), "-i", str(script_path)],
            cwd=str(get_isg_script_root(task_name)),
            capture_output=True,
            text=True,
            timeout=120,
        )

        output = f"ISG Compilation Results for: {script_path}\n"
        output += "=" * 60 + "\n"
        output += f"Exit Code: {proc.returncode}\n\n"

        if proc.returncode == 0:
            output += "Compilation Successful\n\n"
        else:
            output += "Compilation Failed\n\n"

        if proc.stdout:
            stdout_lines = proc.stdout.splitlines()
            if len(stdout_lines) > 10:
                output += f"STDOUT (last 10 of {len(stdout_lines)} lines):\n"
                output += "\n".join(stdout_lines[-10:]) + "\n\n"
            else:
                output += "STDOUT:\n" + proc.stdout + "\n\n"

        if proc.stderr:
            output += "STDERR:\n" + proc.stderr + "\n"

        result = {
            "status": "success" if proc.returncode == 0 else "failed",
            "exit_code": proc.returncode,
            "output": output,
            "script_path": str(script_path),
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except FileNotFoundError as e:
        return json.dumps({"error": str(e)})
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Compilation timed out after 120 seconds"})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--script-name", required=True)
    parser.add_argument("--task-name", required=True)
    args = parser.parse_args()
    print(compile_script(args.script_name, args.task_name))
