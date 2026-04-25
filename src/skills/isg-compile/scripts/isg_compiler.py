#!/usr/bin/env python3
"""
FORCE-RISCV ISG Compiler - Compile ISG scripts using FORCE-RISCV.

It compiles ISG test scripts from workspace/isgScripts/<task_id>/.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path


def find_project_root():
    for parent in Path(__file__).resolve().parents:
        if (parent / "opencode.json").exists() or (parent / "package.json").exists():
            return parent
    return Path.cwd()


PROJECT_ROOT = find_project_root()


def load_project_dotenv():
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


load_project_dotenv()


def get_workspace_root():
    return (PROJECT_ROOT / "workspace").resolve()


WORKSPACE_ROOT = get_workspace_root()


def find_coverage_db_root():
    candidates = [
        PROJECT_ROOT / ".opencode" / "skills" / "coverage" / "coverageDB",
        PROJECT_ROOT / "src" / "skills" / "coverage" / "coverageDB",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


COVERAGEDB_ROOT = find_coverage_db_root()
TEMPLATE_ROOT = COVERAGEDB_ROOT / "template"


def get_isg_script_root(task_name):
    return WORKSPACE_ROOT / "isgScripts" / task_name


def validate_task_name(task_name):
    if not task_name:
        return False, "task_name is required"
    if Path(task_name).name != task_name or task_name in (".", ".."):
        return False, "task_name must be a single directory name, not a path"
    allowed = set("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-")
    if any(ch not in allowed for ch in task_name):
        return False, "task_name may only contain ASCII letters, digits, underscore, and hyphen"
    return True, task_name


def get_task_sim_root(task_name):
    return COVERAGEDB_ROOT / "tasks" / task_name / "sim"


def ensure_task_sim_root(task_name):
    sim_root = get_task_sim_root(task_name)
    if sim_root.exists():
        return sim_root

    template_sim = TEMPLATE_ROOT / "sim"
    sim_root.parent.mkdir(parents=True, exist_ok=True)
    if template_sim.exists():
        shutil.copytree(template_sim, sim_root)
    else:
        sim_root.mkdir(parents=True, exist_ok=True)
    return sim_root


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


def candidate_elf_sort_key(path, sim_root, script_stem):
    if path.parent == sim_root:
        location_rank = 0
    elif path.parent == sim_root / "work_force":
        location_rank = 1
    else:
        location_rank = 2

    if path.name == f"{script_stem}.Default.ELF":
        name_rank = 0
    elif path.name == f"{script_stem}.ELF":
        name_rank = 1
    else:
        name_rank = 2

    try:
        mtime_rank = -path.stat().st_mtime
    except OSError:
        mtime_rank = 0.0

    return (location_rank, name_rank, mtime_rank, str(path))


def find_elf_file(task_name, script_name):
    sim_root = get_task_sim_root(task_name)
    script_stem = Path(script_name).stem
    expected_names = [f"{script_stem}.Default.ELF", f"{script_stem}.ELF"]
    search_roots = [sim_root, sim_root / "work_force"]
    matches = []
    seen = set()

    for root in search_roots:
        if not root.exists():
            continue
        for name in expected_names:
            candidate = root / name
            if candidate.exists() and candidate.is_file():
                return candidate

    for root in search_roots:
        if not root.exists():
            continue
        for candidate in root.glob(f"{script_stem}*.ELF"):
            if candidate.is_file() and candidate not in seen:
                matches.append(candidate)
                seen.add(candidate)

    if sim_root.exists():
        for candidate in sim_root.rglob(f"{script_stem}*.ELF"):
            if not candidate.is_file() or "gem5_artifacts" in candidate.parts or candidate in seen:
                continue
            matches.append(candidate)
            seen.add(candidate)

    if matches:
        return sorted(matches, key=lambda path: candidate_elf_sort_key(path, sim_root, script_stem))[0]
    return None


def resolve_force_riscv_bin():
    env_bin = os.getenv("FORCE_RISCV_BIN")
    candidates = [
        Path(env_bin).expanduser() if env_bin else None,
        PROJECT_ROOT / "bin" / "friscv",
        Path("/home/c910/force-riscv/bin/friscv"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return None


def resolve_force_riscv_config():
    env_config = os.getenv("FORCE_RISCV_CONFIG")
    candidates = [
        Path(env_config).expanduser() if env_config else None,
        PROJECT_ROOT / "workspace" / "agentDoc" / "forceRV" / "config" / "riscv_rv64_c910.config",
        Path("/home/c910/force-riscv/config/riscv_rv64_c910.config"),
    ]
    for candidate in candidates:
        if candidate and candidate.exists():
            return candidate
    return candidates[-1]


def compile_script(script_name, task_name):
    try:
        task_ok, task_result = validate_task_name(task_name)
        if not task_ok:
            return json.dumps({"error": task_result})

        script_path = find_script(script_name, task_name)
        sim_root = ensure_task_sim_root(task_name)

        force_riscv_bin = resolve_force_riscv_bin()
        if force_riscv_bin is None:
            return json.dumps({"error": "FORCE-RISCV binary not found"})

        config_path = resolve_force_riscv_config()

        sim_script = sim_root / script_path.name
        if sim_script.exists():
            sim_script.unlink()
        shutil.copy2(str(script_path), str(sim_script))

        proc = subprocess.run(
            [str(force_riscv_bin), "-t", str(sim_script), "-c", str(config_path)],
            cwd=str(sim_root),
            capture_output=True,
            text=True,
            timeout=300,
        )

        if proc.returncode == 0:
            sim_log = sim_root / "sim.log"
            if sim_log.exists():
                try:
                    sim_log.rename(sim_root / "friscv_generation.log")
                except OSError:
                    pass

        elf_path = find_elf_file(task_name, script_path.name)

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
            "sim_script_path": str(sim_script),
            "sim_root": str(sim_root),
            "elf_path": str(elf_path) if elf_path else None,
            "note": "Use gem5-prescreen with this script after successful compilation; generator must not run RTL/VCS simulation.",
        }
        return json.dumps(result, ensure_ascii=False, indent=2)

    except FileNotFoundError as e:
        return json.dumps({"error": str(e)})
    except subprocess.TimeoutExpired:
        return json.dumps({"error": "Compilation timed out after 300 seconds"})
    except Exception as e:
        return json.dumps({"error": str(e)})


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--script-name", required=True)
    parser.add_argument("--task-name", required=True)
    args = parser.parse_args()
    print(compile_script(args.script_name, args.task_name))
