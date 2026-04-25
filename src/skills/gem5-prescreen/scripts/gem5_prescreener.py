#!/usr/bin/env python3
"""
Minimal gem5 pre-screen CLI for OpenCode-RVDV.

It runs a compiled ELF through the gem5 service, downloads m5out, and records
output.log/manifest.json. Evidence
inspection is intentionally left to OpenCode's normal read/grep tools.
"""

import argparse
import json
import os
import shutil
import sys
import tarfile
import time
from pathlib import Path

import requests  # type: ignore[reportMissingModuleSource]


DEFAULT_GEM5_SERVICE_URL = "http://192.168.122.1:8002"
POLL_INTERVAL = 3
POLL_TIMEOUT = 600
NO_PROXY = {"http": "", "https": ""}


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


def get_gem5_service_url():
    return os.getenv("GEM5_SERVICE_URL", DEFAULT_GEM5_SERVICE_URL).rstrip("/")


def resolve_absolute_path(path_arg, arg_name, *, must_exist=False):
    if not path_arg:
        raise FileNotFoundError("%s is required" % arg_name)
    raw_path = Path(path_arg).expanduser()
    if not raw_path.is_absolute():
        raise FileNotFoundError("%s must be an absolute path: %s" % (arg_name, path_arg))
    candidate = raw_path.resolve()
    if must_exist and not candidate.exists():
        raise FileNotFoundError("path does not exist: %s" % candidate)
    return candidate


def write_text(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_json(path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def candidate_elf_sort_key(path, primary_root, script_stem):
    if path.parent == primary_root:
        location_rank = 0
    elif path.parent == primary_root / "work_force":
        location_rank = 1
    else:
        location_rank = 2

    if path.name == "%s.Default.ELF" % script_stem:
        name_rank = 0
    elif path.name == "%s.ELF" % script_stem:
        name_rank = 1
    else:
        name_rank = 2

    try:
        mtime_rank = -path.stat().st_mtime
    except OSError:
        mtime_rank = 0.0
    return (location_rank, name_rank, mtime_rank, str(path))


def find_elf_file(script_path):
    input_path = resolve_absolute_path(script_path, "--script-path", must_exist=True)
    if input_path.suffix.upper() == ".ELF":
        if input_path.is_file():
            return input_path
        raise FileNotFoundError("ELF path is not a file: %s" % input_path)

    script_stem = input_path.stem
    if not script_stem:
        raise FileNotFoundError("Invalid script_path: %r" % script_path)

    expected_names = ["%s.Default.ELF" % script_stem, "%s.ELF" % script_stem]
    primary_root = input_path.parent
    search_roots = [primary_root, primary_root / "work_force"]
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
        for candidate in root.glob("%s*.ELF" % script_stem):
            if candidate.is_file() and candidate not in seen:
                matches.append(candidate)
                seen.add(candidate)

    if primary_root.exists():
        for candidate in primary_root.rglob("%s*.ELF" % script_stem):
            if not candidate.is_file() or "gem5_artifacts" in candidate.parts or candidate in seen:
                continue
            matches.append(candidate)
            seen.add(candidate)

    if matches:
        return sorted(matches, key=lambda path: candidate_elf_sort_key(path, primary_root, script_stem))[0]

    raise FileNotFoundError(
        "No ELF file found for script path '%s'\nSearched in: %s\nExpected one of: %s\n"
        "Pass an ELF path directly, or pass the compiled script path from the isg-compile output directory."
        % (input_path, primary_root, ", ".join(expected_names))
    )


def normalize_extracted_tree(extract_dir):
    entries = list(extract_dir.iterdir())
    if len(entries) != 1 or not entries[0].is_dir():
        return

    nested_root = entries[0]
    for child in nested_root.iterdir():
        if (extract_dir / child.name).exists():
            return
    for child in nested_root.iterdir():
        shutil.move(str(child), str(extract_dir / child.name))
    nested_root.rmdir()


def safe_extract_tar(archive_path, extract_dir):
    extract_dir.mkdir(parents=True, exist_ok=True)
    extract_root = extract_dir.resolve()

    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            target_path = (extract_dir / member.name).resolve()
            if not path_is_relative_to(target_path, extract_root):
                raise ValueError("Unsafe archive member path: %s" % member.name)
        try:
            archive.extractall(path=extract_dir, filter="data")
        except TypeError:
            archive.extractall(path=extract_dir)

    normalize_extracted_tree(extract_dir)
    return sorted(str(path.relative_to(extract_dir)) for path in extract_dir.rglob("*") if path.is_file())


def fetch_sse_output(task_id):
    lines = []
    try:
        with requests.get(
            "%s/output/%s" % (get_gem5_service_url(), task_id),
            stream=True,
            timeout=300,
            proxies=NO_PROXY,
        ) as response:
            response.raise_for_status()
            for line in response.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data = line[6:]
                    if data == "__DONE__":
                        break
                    lines.append(data)
    except requests.RequestException as exc:
        lines.append("[SSE Error] %s" % exc)
    return lines


def download_m5out(task_id, artifact_dir):
    archive_path = artifact_dir / "m5out.tar.gz"
    extract_dir = artifact_dir / "m5out"
    result = {
        "attempted": True,
        "success": False,
        "error": None,
        "archive_path": str(archive_path),
        "extract_dir": str(extract_dir),
        "extract_success": False,
        "extract_error": None,
        "files": [],
    }

    try:
        response = requests.get(
            "%s/download/%s" % (get_gem5_service_url(), task_id),
            timeout=120,
            proxies=NO_PROXY,
        )
        response.raise_for_status()
        archive_path.parent.mkdir(parents=True, exist_ok=True)
        archive_path.write_bytes(response.content)
        result["success"] = True
    except requests.RequestException as exc:
        result["error"] = str(exc)
        return result
    except OSError as exc:
        result["error"] = "Failed to write archive: %s" % exc
        return result

    try:
        if extract_dir.exists():
            shutil.rmtree(extract_dir)
        files = safe_extract_tar(archive_path, extract_dir)
        result["extract_success"] = True
        result["files"] = ["m5out/%s" % path for path in files]
    except (tarfile.TarError, OSError, ValueError) as exc:
        result["extract_error"] = str(exc)

    return result


def run_gem5_prescreen(script_path, artifact_path, maxinsts=500000):
    try:
        resolved_script_path = resolve_absolute_path(script_path, "--script-path", must_exist=True)
        artifact_dir = resolve_absolute_path(artifact_path, "--artifact-path")
        elf_path = find_elf_file(script_path)
    except FileNotFoundError as exc:
        return "Error: %s" % exc
    try:
        with elf_path.open("rb") as handle:
            upload_response = requests.post(
                "%s/upload" % get_gem5_service_url(),
                files={"file": (elf_path.name, handle, "application/octet-stream")},
                params={"maxinsts": maxinsts},
                timeout=60,
                proxies=NO_PROXY,
            )
            upload_response.raise_for_status()
    except FileNotFoundError:
        return "Error: ELF file not found at %s" % elf_path
    except requests.RequestException as exc:
        return "Error uploading ELF to gem5 service: %s" % exc

    upload_data = upload_response.json()
    task_id = upload_data.get("task_id")
    if not task_id:
        return "Error: No task_id in upload response: %s" % upload_response.text

    try:
        run_response = requests.post(
            "%s/run/%s" % (get_gem5_service_url(), task_id),
            timeout=30,
            proxies=NO_PROXY,
        )
        run_response.raise_for_status()
        run_data = run_response.json()
    except requests.RequestException as exc:
        return "Error starting gem5 simulation: %s" % exc

    start_time = time.time()
    final_status = None
    exit_code = None
    status_data = {}

    while True:
        if time.time() - start_time > POLL_TIMEOUT:
            return "Error: gem5 simulation timed out after %ss (task_id: %s)" % (POLL_TIMEOUT, task_id)
        try:
            status_response = requests.get(
                "%s/status/%s" % (get_gem5_service_url(), task_id),
                timeout=30,
                proxies=NO_PROXY,
            )
            status_response.raise_for_status()
            status_data = status_response.json()
            status = status_data.get("status", "unknown")
            exit_code = status_data.get("exit_code")
            if status in ("completed", "failed", "cancelled"):
                final_status = status
                break
        except requests.RequestException:
            pass
        time.sleep(POLL_INTERVAL)

    artifact_dir.mkdir(parents=True, exist_ok=True)

    output_lines = fetch_sse_output(task_id)
    output_log_path = artifact_dir / "output.log"
    write_text(output_log_path, "\n".join(output_lines) + ("\n" if output_lines else ""))

    download_info = {
        "attempted": False,
        "success": False,
        "error": None,
        "archive_path": str(artifact_dir / "m5out.tar.gz"),
        "extract_dir": str(artifact_dir / "m5out"),
        "extract_success": False,
        "extract_error": None,
        "files": [],
    }
    if final_status in ("completed", "failed"):
        download_info = download_m5out(task_id, artifact_dir)

    manifest_path = artifact_dir / "manifest.json"
    manifest = {
        "script_path": str(resolved_script_path),
        "task_id": task_id,
        "elf_file": str(elf_path),
        "artifact_path": str(artifact_dir),
        "maxinsts": maxinsts,
        "gem5_service_url": get_gem5_service_url(),
        "upload_response": upload_data,
        "run_response": run_data,
        "status_response": status_data,
        "final_status": final_status,
        "exit_code": exit_code,
        "paths": {
            "artifact_root": str(artifact_dir),
            "output_log": str(output_log_path),
            "manifest": str(manifest_path),
            "archive": download_info.get("archive_path"),
            "extract_dir": download_info.get("extract_dir"),
        },
        "download": {
            "attempted": download_info.get("attempted", False),
            "success": download_info.get("success", False),
            "error": download_info.get("error"),
        },
        "extract": {
            "success": download_info.get("extract_success", False),
            "error": download_info.get("extract_error"),
        },
        "files": download_info.get("files", []),
        "collected_at": time.time(),
    }
    write_json(manifest_path, manifest)

    summary = {
        "status": final_status,
        "exit_code": exit_code,
        "task_id": task_id,
        "script_path": str(resolved_script_path),
        "elf_file": str(elf_path),
        "artifact_path": str(artifact_dir),
        "output_log": str(output_log_path),
        "manifest": str(manifest_path),
        "m5out_archive": download_info.get("archive_path"),
        "m5out_extract_dir": download_info.get("extract_dir"),
        "m5out_downloaded": bool(download_info.get("success")),
        "m5out_extracted": bool(download_info.get("extract_success")),
        "download_error": download_info.get("error"),
        "extract_error": download_info.get("extract_error"),
        "files": download_info.get("files", []),
        "note": "Use OpenCode read/grep on output_log and m5out_extract_dir for evidence. This does not run RTL/VCS simulation.",
    }
    return json.dumps(summary, indent=2, ensure_ascii=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description="minimal gem5 pre-screen runner")
    subparsers = parser.add_subparsers(dest="command")

    run_parser = subparsers.add_parser("run", help="run gem5 pre-screen")
    run_parser.add_argument("--script-path", required=True)
    run_parser.add_argument("--artifact-path", required=True)
    run_parser.add_argument("--maxinsts", type=int, default=500000)

    args = parser.parse_args(argv)
    if not args.command:
        parser.error("command is required")
    if args.command == "run":
        print(run_gem5_prescreen(args.script_path, args.artifact_path, args.maxinsts))
        return 0
    parser.error("unknown command: %s" % args.command)
    return 2


if __name__ == "__main__":
    sys.exit(main())
