#!/usr/bin/env python3
"""
FORCE-RISCV ISG Compiler - Compile ISG scripts using FORCE-RISCV.

It compiles ISG test scripts from explicit script paths.
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


def resolve_script_path(script_path):
    if not script_path:
        raise FileNotFoundError("--script-path is required")

    candidate = Path(script_path).expanduser()
    if not candidate.is_absolute():
        candidate = (PROJECT_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if not candidate.exists() or not candidate.is_file():
        raise FileNotFoundError(f"Script path does not exist: {candidate}")
    if candidate.suffix != ".py":
        raise FileNotFoundError(f"Script path must point to a .py file: {candidate}")
    return candidate


def resolve_output_dir(output_dir, script_path):
    if output_dir:
        candidate = Path(output_dir).expanduser()
        if not candidate.is_absolute():
            candidate = (PROJECT_ROOT / candidate).resolve()
        else:
            candidate = candidate.resolve()
    else:
        # Default to a sibling directory next to the script to reduce workspace coupling.
        candidate = (script_path.parent / f"{script_path.stem}_build").resolve()

    candidate.mkdir(parents=True, exist_ok=True)
    return candidate


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


def find_elf_file(sim_root, script_name):
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


def compile_script(script_path, output_dir=None):
    try:
        script_path = resolve_script_path(script_path=script_path)

        sim_root = resolve_output_dir(output_dir=output_dir, script_path=script_path)

        force_riscv_bin = resolve_force_riscv_bin()
        if force_riscv_bin is None:
            return json.dumps({"error": "FORCE-RISCV binary not found"})

        config_path = resolve_force_riscv_config()

        sim_script = sim_root / script_path.name
        if sim_script.exists() and sim_script.resolve() != script_path.resolve():
            sim_script.unlink()
        if sim_script.resolve() != script_path.resolve():
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

        elf_path = find_elf_file(sim_root, script_path.name)

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
            "output_dir": str(sim_root),
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
    parser.add_argument("--script-path", required=True)
    parser.add_argument("--output-dir")
    args = parser.parse_args()
    print(
        compile_script(
            script_path=args.script_path,
            output_dir=args.output_dir,
        )
    )
