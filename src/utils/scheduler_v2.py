from __future__ import annotations

import argparse
import csv
import fcntl
import json
import os
import shutil
import subprocess
import time
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from src.utils.project_paths import (
    get_baseline_vdb_path,
    get_coverage_root,
    get_scoreboard_root,
    get_ucapi_snapshot_tool_path,
)


KIND_ORDER = ("line", "cond", "branch", "tgl", "fsm")
GROUP_ORDER = ("ifu", "idu", "iu", "rtu", "others")
RUNNING_IDLE = "idle"
RUNNING_QUEUED = "queued"
RUNNING_RUNNING = "running"
RUNNING_STALE = "stale"
BLOCKED_STATUS_PREFIX = "blocked_"
CSV_FIELD_ALIASES = {"full_name": "full_instance_name"}
SCOREBOARD_FIELDS = [
    "vp_id",
    "full_name",
    "kind",
    "range",
    "vp_group",
    "rtl_file",
    "vp_feasibility",
    "vp_feasibility_reason",
    "vp_feasibility_source",
    "baseline_line_pct",
    "current_line_pct",
    "exec_count",
    "running_state",
    "status",
    "improvement_count",
    "last_improved_by_task",
    "last_improved_by_script",
    "last_improved_delta_pct",
]
FLOAT_FIELDS = {"baseline_line_pct", "current_line_pct", "last_improved_delta_pct"}
INT_FIELDS = {"exec_count", "improvement_count"}
BLOCKING_FEASIBILITY = {"dead_code", "out_of_scope"}

SnapshotLoaderFn = Callable[[Path, str | None], tuple[dict[tuple[str, str, str], dict[str, Any]], Mapping[str, Any]]]
MergeRunnerFn = Callable[[Path, Path | None, Path, Path], Mapping[str, Any]]


@dataclass(frozen=True)
class ScoreboardPaths:
    root: Path
    csv_path: Path
    state_path: Path
    events_path: Path
    details_path: Path
    merged_vdb_path: Path
    lock_path: Path


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _round_pct(value: float) -> float:
    return round(value + 1e-9, 2)


def _coerce_path(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve()


def _is_relative_to(path: Path, other: Path) -> bool:
    try:
        path.relative_to(other)
    except ValueError:
        return False
    return True


def _resolve_merged_vdb_root(scoreboard_root: Path) -> Path:
    coverage_root = get_coverage_root().resolve()
    if _is_relative_to(scoreboard_root, coverage_root):
        return scoreboard_root
    return get_scoreboard_root().resolve()


def get_scoreboard_paths(output_dir: str | os.PathLike[str] | None = None) -> ScoreboardPaths:
    root = _coerce_path(output_dir) if output_dir else get_scoreboard_root().resolve()
    merged_root = _resolve_merged_vdb_root(root)
    return ScoreboardPaths(
        root=root,
        csv_path=root / "scoreboard.csv",
        state_path=root / "scoreboard_state.json",
        events_path=root / "scoreboard_events.jsonl",
        details_path=root / "scoreboard_details.json",
        merged_vdb_path=merged_root / "merged_cov.vdb",
        lock_path=root / ".scoreboard.lock",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _atomic_write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_name(f".{path.name}.tmp")
    temp_path.write_text(content, encoding="utf-8")
    os.replace(temp_path, path)


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False))


@contextmanager
def _scoreboard_lock(paths: ScoreboardPaths):
    paths.root.mkdir(parents=True, exist_ok=True)
    with paths.lock_path.open("a+", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)


def _append_event(paths: ScoreboardPaths, event: str, **payload: Any) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": _now(), "event": event, **payload}
    with paths.events_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def _csv_field_name(field: str) -> str:
    return CSV_FIELD_ALIASES.get(field, field)


def _format_csv_value(field: str, value: Any) -> str:
    if field in FLOAT_FIELDS:
        return f"{float(value):.2f}"
    if field in INT_FIELDS:
        return str(int(value))
    return "" if value is None else str(value)


def _build_details_payload(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "rtl_file_by_vp_id": {str(row["vp_id"]): str(row.get("rtl_file", "")) for row in rows},
        "vp_key_by_vp_id": {
            str(row["vp_id"]): f"{row.get('full_name', '')}::{row.get('kind', '')}::{row.get('range', '')}"
            for row in rows
        },
    }


def save_scoreboard(output_dir: str | os.PathLike[str], rows: list[dict[str, Any]], state: Mapping[str, Any]) -> None:
    paths = get_scoreboard_paths(output_dir)
    paths.root.mkdir(parents=True, exist_ok=True)
    csv_fields = [field for field in SCOREBOARD_FIELDS if field != "rtl_file"]
    temp_csv_path = paths.csv_path.with_name(f".{paths.csv_path.name}.tmp")
    with temp_csv_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=[_csv_field_name(field) for field in csv_fields])
        writer.writeheader()
        for row in sorted(rows, key=_row_sort_key):
            writer.writerow({_csv_field_name(field): _format_csv_value(field, row.get(field, "")) for field in csv_fields})
    os.replace(temp_csv_path, paths.csv_path)
    _write_json(paths.state_path, state)
    _write_json(paths.details_path, _build_details_payload(rows))


def load_scoreboard(output_dir: str | os.PathLike[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = get_scoreboard_paths(output_dir)
    state = _read_json(paths.state_path) if paths.state_path.exists() else {}
    details = _read_json(paths.details_path) if paths.details_path.exists() else {}
    rtl_file_by_vp_id = details.get("rtl_file_by_vp_id", {}) if isinstance(details, Mapping) else {}
    rows: list[dict[str, Any]] = []
    if not paths.csv_path.exists():
        return rows, state
    with paths.csv_path.open("r", encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            row: dict[str, Any] = {}
            for field in SCOREBOARD_FIELDS:
                if field == "rtl_file":
                    row[field] = str(rtl_file_by_vp_id.get(raw.get("vp_id", ""), ""))
                else:
                    value = raw.get(_csv_field_name(field), "")
                    if field in FLOAT_FIELDS:
                        row[field] = float(value or 0.0)
                    elif field in INT_FIELDS:
                        row[field] = int(value or 0)
                    else:
                        row[field] = value or ""
            rows.append(row)
    return rows, state


def load_scoreboard_events(output_dir: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    paths = get_scoreboard_paths(output_dir)
    if not paths.events_path.exists():
        return []
    with paths.events_path.open("r", encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]


def infer_vp_group(full_name: str) -> str:
    text = str(full_name)
    if ".x_ct_ifu_" in text or ".x_ifu_" in text:
        return "ifu"
    if ".x_ct_idu_" in text or ".x_idu_" in text:
        return "idu"
    if ".x_ct_iu_" in text or ".x_iu_" in text:
        return "iu"
    if ".x_ct_rtu_" in text or ".x_rtu_" in text:
        return "rtu"
    return "others"


def flatten_vp_list(vp_list_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for module_index, module in enumerate(vp_list_payload.get("modules", [])):
        full_name = str(module.get("full_name", "")).strip()
        rtl_file = Path(str(module.get("rtl_file", "")).strip()).name
        if not full_name:
            continue
        for vp_index, vp in enumerate(module.get("vps", [])):
            kind = str(vp.get("kind", "")).strip()
            range_text = str(vp.get("range", "")).strip()
            if not kind or not range_text:
                continue
            rows.append(
                {
                    "vp_id": f"modules[{module_index}].vps[{vp_index}]",
                    "full_name": full_name,
                    "rtl_file": rtl_file,
                    "kind": kind,
                    "range": range_text,
                    "vp_group": infer_vp_group(full_name),
                }
            )
    return sorted(rows, key=_row_sort_key)


def _merge_vp_list_payloads(vp_payloads: list[Mapping[str, Any]]) -> dict[str, Any]:
    merged_modules: list[dict[str, Any]] = []
    modules_by_full_name: dict[str, dict[str, Any]] = {}
    for payload in vp_payloads:
        for module in payload.get("modules", []):
            full_name = str(module.get("full_name", "")).strip()
            if not full_name:
                continue
            existing = modules_by_full_name.get(full_name)
            if existing is None:
                existing = {
                    "full_name": full_name,
                    "rtl_file": str(module.get("rtl_file", "")).strip(),
                    "vps": [],
                }
                modules_by_full_name[full_name] = existing
                merged_modules.append(existing)
            elif not existing.get("rtl_file"):
                existing["rtl_file"] = str(module.get("rtl_file", "")).strip()
            existing["vps"].extend(list(module.get("vps", [])))
    return {
        "version": "MULTI_VP_LIST" if len(vp_payloads) > 1 else str(vp_payloads[0].get("version", "VP_LIST") if vp_payloads else "VP_LIST"),
        "modules": merged_modules,
    }


def _range_bounds(range_text: str) -> tuple[int, int]:
    cleaned = str(range_text).strip()
    if not cleaned:
        # Keep malformed rows sortable instead of crashing long-running automation.
        return 10**9, 10**9
    if "-" not in cleaned:
        value = int(cleaned)
        return value, value
    start_text, end_text = cleaned.split("-", 1)
    start = int(start_text.strip())
    end = int(end_text.strip())
    if end < start:
        start, end = end, start
    return start, end


def _row_sort_key(row: Mapping[str, Any]) -> tuple[int, int, str, int, int, str]:
    start_line, end_line = _range_bounds(str(row["range"]))
    kind_index = KIND_ORDER.index(str(row["kind"])) if str(row["kind"]) in KIND_ORDER else len(KIND_ORDER)
    group_index = GROUP_ORDER.index(str(row["vp_group"])) if str(row["vp_group"]) in GROUP_ORDER else len(GROUP_ORDER)
    return kind_index, group_index, str(row["full_name"]), start_line, end_line, str(row["vp_id"])


def _is_blocked_status(status: str) -> bool:
    return status.startswith(BLOCKED_STATUS_PREFIX)


def _derive_row_status(row: Mapping[str, Any], max_exec_count: int) -> str:
    status = str(row.get("status", "pending"))
    if _is_blocked_status(status):
        return status
    feasibility = str(row.get("vp_feasibility", "")).strip()
    if feasibility in BLOCKING_FEASIBILITY:
        return f"blocked_{feasibility}"
    if float(row.get("current_line_pct", 0.0)) >= 100.0:
        return "done_covered"
    if int(row.get("exec_count", 0)) >= max_exec_count:
        return "done_max_rounds"
    return "pending"


def _is_open_work(row: Mapping[str, Any], max_exec_count: int) -> bool:
    return (
        not _is_blocked_status(str(row.get("status", "")))
        and float(row.get("current_line_pct", 0.0)) < 100.0
        and int(row.get("exec_count", 0)) < max_exec_count
    )


def _derive_active_kind(rows: list[Mapping[str, Any]], max_exec_count: int) -> str | None:
    for kind in KIND_ORDER:
        if any(row["kind"] == kind and _is_open_work(row, max_exec_count) for row in rows):
            return kind
    return None


def _snapshot_key(full_name: str, kind: str, range_text: str) -> tuple[str, str, str]:
    return str(full_name).strip(), str(kind).strip(), str(range_text).strip()


def _detect_ucapi_test_name(vdb_path: Path) -> str | None:
    if vdb_path.name == "BASELINE.vdb":
        return f"{vdb_path}/test"
    testdata_dir = vdb_path / "snps" / "coverage" / "db" / "testdata"
    if not testdata_dir.exists():
        return None
    test_dirs = sorted(path for path in testdata_dir.iterdir() if path.is_dir() and not path.name.startswith("."))
    if not test_dirs:
        return None
    return f"{vdb_path}/{test_dirs[0].name}"


def _parse_snapshot_payload(payload: Mapping[str, Any], expected_kind: str) -> dict[tuple[str, str, str], dict[str, Any]]:
    snapshot: dict[tuple[str, str, str], dict[str, Any]] = {}
    for module in payload.get("modules", []):
        full_name = str(module.get("full_name", "")).strip()
        rtl_file = Path(str(module.get("rtl_file", "")).strip()).name
        if not full_name:
            continue
        for vp in module.get("vps", []):
            kind = str(vp.get("kind", "")).strip()
            range_text = str(vp.get("range", "")).strip()
            if kind != expected_kind or not range_text:
                continue
            snapshot[_snapshot_key(full_name, kind, range_text)] = {
                "full_name": full_name,
                "rtl_file": rtl_file,
                "kind": kind,
                "range": range_text,
                "covered": int(vp.get("covered", 0) or 0),
                "coverable": int(vp.get("coverable", 0) or 0),
                "pct": _round_pct(float(vp.get("pct", 0.0) or 0.0)),
            }
            if "expr" in vp:
                snapshot[_snapshot_key(full_name, kind, range_text)]["expr"] = str(vp.get("expr", "") or "")
            if "expr_count" in vp:
                snapshot[_snapshot_key(full_name, kind, range_text)]["expr_count"] = int(vp.get("expr_count", 0) or 0)
            if isinstance(vp.get("exprs"), list):
                snapshot[_snapshot_key(full_name, kind, range_text)]["exprs"] = [str(x) for x in vp.get("exprs", [])]
    return snapshot


def load_line_snapshot(vdb_path: Path, module_filter: str | None = None) -> tuple[dict[tuple[str, str, str], dict[str, Any]], Mapping[str, Any]]:
    tool_path = get_ucapi_snapshot_tool_path("line")
    if not tool_path.exists():
        raise FileNotFoundError(f"Line snapshot tool not found: {tool_path}")
    test_name = _detect_ucapi_test_name(vdb_path)
    if test_name is None:
        raise FileNotFoundError(f"No test data found for VDB: {vdb_path}")
    cmd = [str(tool_path), str(vdb_path), test_name, "first"]
    if module_filter:
        cmd.append(module_filter)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "line snapshot tool failed")
    payload = json.loads(proc.stdout)
    return _parse_snapshot_payload(payload, "line"), payload


def load_condition_snapshot(vdb_path: Path, module_filter: str | None = None) -> tuple[dict[tuple[str, str, str], dict[str, Any]], Mapping[str, Any]]:
    tool_path = get_ucapi_snapshot_tool_path("cond")
    if not tool_path.exists():
        raise FileNotFoundError(f"Condition snapshot tool not found: {tool_path}")
    test_name = _detect_ucapi_test_name(vdb_path)
    if test_name is None:
        raise FileNotFoundError(f"No test data found for VDB: {vdb_path}")
    cmd = [str(tool_path), str(vdb_path), test_name, "first"]
    if module_filter:
        cmd.append(module_filter)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "condition snapshot tool failed")
    payload = json.loads(proc.stdout)
    return _parse_snapshot_payload(payload, "cond"), payload


def load_branch_snapshot(vdb_path: Path, module_filter: str | None = None) -> tuple[dict[tuple[str, str, str], dict[str, Any]], Mapping[str, Any]]:
    tool_path = get_ucapi_snapshot_tool_path("branch")
    if not tool_path.exists():
        raise FileNotFoundError(f"Branch snapshot tool not found: {tool_path}")
    test_name = _detect_ucapi_test_name(vdb_path)
    if test_name is None:
        raise FileNotFoundError(f"No test data found for VDB: {vdb_path}")
    cmd = [str(tool_path), str(vdb_path), test_name, "first"]
    if module_filter:
        cmd.append(module_filter)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "branch snapshot tool failed")
    payload = json.loads(proc.stdout)
    return _parse_snapshot_payload(payload, "branch"), payload


def load_fsm_snapshot(vdb_path: Path, module_filter: str | None = None) -> tuple[dict[tuple[str, str, str], dict[str, Any]], Mapping[str, Any]]:
    tool_path = get_ucapi_snapshot_tool_path("fsm")
    if not tool_path.exists():
        raise FileNotFoundError(f"FSM snapshot tool not found: {tool_path}")
    test_name = _detect_ucapi_test_name(vdb_path)
    if test_name is None:
        raise FileNotFoundError(f"No test data found for VDB: {vdb_path}")
    cmd = [str(tool_path), str(vdb_path), test_name, "first"]
    if module_filter:
        cmd.append(module_filter)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or proc.stdout.strip() or "fsm snapshot tool failed")
    payload = json.loads(proc.stdout)
    return _parse_snapshot_payload(payload, "fsm"), payload


def _load_kind_snapshot(kind: str, vdb_path: Path, module_filter: str | None = None) -> tuple[dict[tuple[str, str, str], dict[str, Any]], Mapping[str, Any]]:
    if kind == "line":
        return load_line_snapshot(vdb_path, module_filter)
    if kind == "cond":
        return load_condition_snapshot(vdb_path, module_filter)
    if kind == "branch":
        return load_branch_snapshot(vdb_path, module_filter)
    if kind == "fsm":
        return load_fsm_snapshot(vdb_path, module_filter)
    raise ValueError(f"Unsupported snapshot kind: {kind}")


def _urg_output_candidates(dbname_path: Path) -> list[Path]:
    appended_suffix = dbname_path.with_name(f"{dbname_path.name}.vdb")
    deduped: list[Path] = []
    for candidate in [dbname_path, appended_suffix]:
        if candidate not in deduped:
            deduped.append(candidate)
    return deduped


def _cleanup_urg_outputs(dbname_path: Path) -> None:
    for candidate in _urg_output_candidates(dbname_path):
        if candidate.exists():
            shutil.rmtree(candidate)


def _resolve_urg_output(dbname_path: Path) -> Path | None:
    for candidate in _urg_output_candidates(dbname_path):
        if candidate.exists():
            return candidate
    return None


def merge_vdb_with_urg(
    task_vdb_path: Path,
    previous_merged_vdb_path: Path | None,
    output_vdb_path: Path,
    baseline_vdb_path: Path,
    urg_bin: str = "urg",
    max_attempts: int = 3,
    retry_delay_seconds: float = 1.0,
) -> Mapping[str, Any]:
    task_vdb_path = task_vdb_path.expanduser().resolve()
    output_vdb_path = output_vdb_path.expanduser().resolve()
    baseline_vdb_path = baseline_vdb_path.expanduser().resolve()
    previous = previous_merged_vdb_path.expanduser().resolve() if previous_merged_vdb_path else None
    attempts = max(1, int(max_attempts))
    retry_delay = max(0.0, float(retry_delay_seconds))
    if not task_vdb_path.exists():
        return {"success": False, "error": f"Task VDB not found: {task_vdb_path}"}
    source_dirs: list[Path] = []
    if previous is not None and previous.exists():
        source_dirs.append(previous)
    elif baseline_vdb_path.exists():
        source_dirs.append(baseline_vdb_path)
    else:
        return {"success": False, "error": f"Baseline VDB not found: {baseline_vdb_path}"}
    source_dirs.append(task_vdb_path)
    output_vdb_path.parent.mkdir(parents=True, exist_ok=True)
    temp_output = output_vdb_path.with_name(f"{output_vdb_path.name}.tmp")
    _cleanup_urg_outputs(temp_output)
    cmd = [urg_bin]
    for source_dir in source_dirs:
        cmd.extend(["-dir", str(source_dir)])
    cmd.extend(["-dbname", str(temp_output)])
    errors: list[str] = []
    for attempt in range(1, attempts + 1):
        _cleanup_urg_outputs(temp_output)
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True)
            actual_temp_output = _resolve_urg_output(temp_output)
            if proc.returncode != 0:
                error = proc.stderr.strip() or proc.stdout.strip() or "urg merge failed"
            elif actual_temp_output is None:
                error = f"urg merge did not produce output: {temp_output}"
            else:
                if output_vdb_path.exists():
                    shutil.rmtree(output_vdb_path)
                shutil.move(str(actual_temp_output), str(output_vdb_path))
                return {"success": True, "merged_vdb_path": str(output_vdb_path), "command": cmd, "attempt_count": attempt}
        except Exception as exc:
            error = str(exc)
        errors.append(error)
        _cleanup_urg_outputs(temp_output)
        if attempt < attempts and retry_delay > 0:
            time.sleep(retry_delay)
    return {"success": False, "error": errors[-1] if errors else "urg merge failed", "command": cmd, "attempt_count": attempts, "errors": errors}


def initialize_scoreboard(
    output_dir: str | os.PathLike[str],
    *,
    vp_list_path: str | os.PathLike[str] | None = None,
    vp_list_paths: list[str | os.PathLike[str]] | None = None,
    baseline_vdb_path: str | os.PathLike[str] | None = None,
    line_snapshot_loader: SnapshotLoaderFn | None = None,
    condition_snapshot_loader: SnapshotLoaderFn | None = None,
    branch_snapshot_loader: SnapshotLoaderFn | None = None,
    fsm_snapshot_loader: SnapshotLoaderFn | None = None,
    max_exec_count: int = 3,
    parallelism: int = 4,
) -> dict[str, Any]:
    paths = get_scoreboard_paths(output_dir)
    paths.root.mkdir(parents=True, exist_ok=True)
    with _scoreboard_lock(paths):
        normalized_vp_list_paths: list[Path] = []
        if vp_list_paths:
            normalized_vp_list_paths.extend(_coerce_path(path) for path in vp_list_paths)
        elif vp_list_path is not None:
            normalized_vp_list_paths.append(_coerce_path(vp_list_path))
        else:
            normalized_vp_list_paths.append(_coerce_path("vp_list.json"))
        baseline_path = _coerce_path(baseline_vdb_path) if baseline_vdb_path else get_baseline_vdb_path().resolve()
        vp_payload = _merge_vp_list_payloads([_read_json(path) for path in normalized_vp_list_paths])
        rows = flatten_vp_list(vp_payload)
        snapshot_loaders: dict[str, SnapshotLoaderFn] = {
            "line": line_snapshot_loader or load_line_snapshot,
            "cond": condition_snapshot_loader or load_condition_snapshot,
            "branch": branch_snapshot_loader or load_branch_snapshot,
            "fsm": fsm_snapshot_loader or load_fsm_snapshot,
        }
        snapshots: dict[str, dict[tuple[str, str, str], dict[str, Any]]] = {}
        for kind in ("line", "cond", "branch", "fsm"):
            if any(str(row.get("kind", "")) == kind for row in rows):
                snapshot, snapshot_payload = snapshot_loaders[kind](baseline_path, None)
                snapshots[kind] = snapshot
                _write_json(paths.root / f"baseline_{kind}_snapshot.json", snapshot_payload)
        initialized_rows: list[dict[str, Any]] = []
        if paths.events_path.exists():
            paths.events_path.unlink()
        for item in rows:
            row = {
                **item,
                "vp_feasibility": "unknown",
                "vp_feasibility_reason": "",
                "vp_feasibility_source": "",
                "baseline_line_pct": 0.0,
                "current_line_pct": 0.0,
                "exec_count": 0,
                "running_state": RUNNING_IDLE,
                "status": "pending",
                "improvement_count": 0,
                "last_improved_by_task": "",
                "last_improved_by_script": "",
                "last_improved_delta_pct": 0.0,
            }
            if row["kind"] not in {"line", "cond", "branch", "fsm"}:
                row["status"] = "blocked_unsupported_kind"
                initialized_rows.append(row)
                _append_event(paths, "refresh", merge_version=0, vdb_path=str(baseline_path), vp_id=row["vp_id"], status=row["status"], error="scheduler_v2 currently supports line/cond/branch/fsm VPs only")
                continue
            snapshot_entry = snapshots.get(row["kind"], {}).get(_snapshot_key(row["full_name"], row["kind"], row["range"]))
            if snapshot_entry is None:
                row["status"] = "blocked_missing_snapshot"
                initialized_rows.append(row)
                _append_event(paths, "refresh", merge_version=0, vdb_path=str(baseline_path), vp_id=row["vp_id"], status=row["status"], error=f"{row['kind']} VP missing from local snapshot")
                continue
            if not row["rtl_file"]:
                row["rtl_file"] = str(snapshot_entry.get("rtl_file", "") or "")
            row["baseline_line_pct"] = _round_pct(float(snapshot_entry.get("pct", 0.0)))
            row["current_line_pct"] = _round_pct(float(snapshot_entry.get("pct", 0.0)))
            row["status"] = _derive_row_status(row, max_exec_count=max_exec_count)
            initialized_rows.append(row)
            _append_event(paths, "refresh", merge_version=0, vdb_path=str(baseline_path), vp_id=row["vp_id"], status=row["status"], before_pct=0.0, after_pct=row["current_line_pct"], coverage={"source": f"local_{row['kind']}_snapshot", **snapshot_entry}, error="")
        now = _now()
        state = {
            "generated_at": now,
            "updated_at": now,
            "active_kind": _derive_active_kind(initialized_rows, max_exec_count=max_exec_count),
            "max_exec_count": max_exec_count,
            "parallelism": parallelism,
            "group_pointer": 0,
            "baseline_vdb_path": str(baseline_path),
            "merged_vdb_path": str(paths.merged_vdb_path),
            "last_refresh_vdb_path": str(baseline_path),
            "last_refresh_at": now,
            "last_merge_version": 0,
            "inflight": {},
            "stale_inflight": {},
            "scheduler_version": "v2",
        }
        save_scoreboard(paths.root, initialized_rows, state)
    return {
        "output_dir": str(paths.root),
        "scoreboard_csv": str(paths.csv_path),
        "state_path": str(paths.state_path),
        "events_path": str(paths.events_path),
        "details_path": str(paths.details_path),
        "active_kind": state["active_kind"],
        "vp_count": len(initialized_rows),
    }


def _choose_candidate(rows: list[dict[str, Any]], state: dict[str, Any], max_exec_count: int) -> dict[str, Any] | None:
    active_kind = state.get("active_kind") or _derive_active_kind(rows, max_exec_count)
    if active_kind is None:
        return None
    phase_rows = [row for row in rows if row["kind"] == active_kind and _is_open_work(row, max_exec_count)]
    if not phase_rows:
        return None
    min_exec_count = min(int(row["exec_count"]) for row in phase_rows)
    inflight_ids = set(state.get("inflight", {}).keys())
    candidates = [row for row in phase_rows if int(row["exec_count"]) == min_exec_count and row["vp_id"] not in inflight_ids and str(row["status"]) == "pending" and str(row.get("running_state", RUNNING_IDLE)) == RUNNING_IDLE]
    if not candidates:
        return None
    group_pointer = int(state.get("group_pointer", 0))
    for offset in range(len(GROUP_ORDER)):
        group = GROUP_ORDER[(group_pointer + offset) % len(GROUP_ORDER)]
        group_candidates = [row for row in candidates if row["vp_group"] == group]
        if not group_candidates:
            continue
        chosen = min(group_candidates, key=lambda row: (float(row["current_line_pct"]), int(row["exec_count"]), str(row["vp_id"])))
        state["group_pointer"] = (GROUP_ORDER.index(group) + 1) % len(GROUP_ORDER)
        return chosen
    return None


def select_next_vps(output_dir: str | os.PathLike[str], slots: int | None = None) -> list[dict[str, Any]]:
    paths = get_scoreboard_paths(output_dir)
    with _scoreboard_lock(paths):
        rows, state = load_scoreboard(output_dir)
        max_exec_count = int(state.get("max_exec_count", 3))
        parallelism = int(state.get("parallelism", 4))
        state["active_kind"] = _derive_active_kind(rows, max_exec_count)
        if state["active_kind"] is None:
            save_scoreboard(paths.root, rows, state)
            return []
        inflight = state.setdefault("inflight", {})
        available_capacity = max(parallelism - len(inflight), 0)
        wanted = available_capacity if slots is None else min(max(slots, 0), available_capacity)
        selected: list[dict[str, Any]] = []
        for _ in range(wanted):
            chosen = _choose_candidate(rows, state, max_exec_count)
            if chosen is None:
                break
            chosen["running_state"] = RUNNING_QUEUED
            inflight[chosen["vp_id"]] = {
                "selected_at": _now(),
                "completed_at": "",
                "inflight_agent_id": "",
                "task_name": "",
                "task_vdb_path": "",
                "isg_script": "",
            }
            _append_event(paths, "select", vp_id=chosen["vp_id"], active_kind=state["active_kind"], vp_group=chosen["vp_group"], exec_count=chosen["exec_count"], current_line_pct=chosen["current_line_pct"])
            selected.append(dict(chosen))
        state["updated_at"] = _now()
        save_scoreboard(paths.root, rows, state)
        return selected


def manual_select_vp(output_dir: str | os.PathLike[str], vp_id: str) -> dict[str, Any]:
    paths = get_scoreboard_paths(output_dir)
    with _scoreboard_lock(paths):
        rows, state = load_scoreboard(output_dir)
        rows_by_id = {row["vp_id"]: row for row in rows}
        if vp_id not in rows_by_id:
            raise KeyError(f"Unknown vp_id: {vp_id}")
        row = rows_by_id[vp_id]
        inflight = state.setdefault("inflight", {})
        if vp_id in inflight:
            raise KeyError(f"VP is already selected: {vp_id}")
        status = str(row.get("status", ""))
        if _is_blocked_status(status) or status in {"done_covered", "done_max_rounds"}:
            raise ValueError(f"VP status does not allow selection: {status}")
        row["running_state"] = RUNNING_QUEUED
        inflight[vp_id] = {"selected_at": _now(), "completed_at": "", "inflight_agent_id": "", "task_name": "", "task_vdb_path": "", "isg_script": ""}
        _append_event(paths, "manual_select", vp_id=vp_id, kind=row.get("kind", ""), vp_group=row.get("vp_group", ""), exec_count=row.get("exec_count", 0), current_line_pct=row.get("current_line_pct", 0.0))
        state["updated_at"] = _now()
        save_scoreboard(paths.root, rows, state)
        return dict(row)


def mark_vp_launched(output_dir: str | os.PathLike[str], vp_id: str, *, task_name: str, agent_id: str = "", task_vdb_path: str = "", isg_script: str = "") -> dict[str, Any]:
    paths = get_scoreboard_paths(output_dir)
    with _scoreboard_lock(paths):
        rows, state = load_scoreboard(output_dir)
        rows_by_id = {row["vp_id"]: row for row in rows}
        if vp_id not in rows_by_id:
            raise KeyError(f"Unknown vp_id: {vp_id}")
        inflight = state.setdefault("inflight", {})
        if vp_id not in inflight:
            raise KeyError(f"VP is not selected for launch: {vp_id}")
        row = rows_by_id[vp_id]
        row["running_state"] = RUNNING_RUNNING
        inflight[vp_id].update({"task_name": task_name, "inflight_agent_id": agent_id, "task_vdb_path": task_vdb_path, "isg_script": isg_script})
        state["updated_at"] = _now()
        save_scoreboard(paths.root, rows, state)
        _append_event(paths, "launch", vp_id=vp_id, task_name=task_name, inflight_agent_id=agent_id, task_vdb_path=task_vdb_path, isg_script=isg_script)
        return dict(row)


def record_vp_failure(output_dir: str | os.PathLike[str], vp_id: str, *, task_name: str, error: str) -> dict[str, Any]:
    paths = get_scoreboard_paths(output_dir)
    with _scoreboard_lock(paths):
        rows, state = load_scoreboard(output_dir)
        rows_by_id = {row["vp_id"]: row for row in rows}
        if vp_id not in rows_by_id:
            raise KeyError(f"Unknown vp_id: {vp_id}")
        row = rows_by_id[vp_id]
        state.setdefault("inflight", {}).pop(vp_id, None)
        row["running_state"] = RUNNING_IDLE
        row["status"] = _derive_row_status(row, max_exec_count=int(state.get("max_exec_count", 3)))
        state["updated_at"] = _now()
        state["active_kind"] = _derive_active_kind(rows, max_exec_count=int(state.get("max_exec_count", 3)))
        save_scoreboard(paths.root, rows, state)
        _append_event(paths, "fail", vp_id=vp_id, task_name=task_name, error=error)
        return dict(row)


def complete_vp_task(
    output_dir: str | os.PathLike[str],
    vp_id: str,
    *,
    task_name: str,
    task_vdb_path: str | os.PathLike[str],
    isg_script: str = "",
    merge_runner: MergeRunnerFn | None = None,
    line_snapshot_loader: SnapshotLoaderFn | None = None,
    condition_snapshot_loader: SnapshotLoaderFn | None = None,
    branch_snapshot_loader: SnapshotLoaderFn | None = None,
    fsm_snapshot_loader: SnapshotLoaderFn | None = None,
) -> dict[str, Any]:
    paths = get_scoreboard_paths(output_dir)
    with _scoreboard_lock(paths):
        rows, state = load_scoreboard(output_dir)
        rows_by_id = {row["vp_id"]: row for row in rows}
        if vp_id not in rows_by_id:
            raise KeyError(f"Unknown vp_id: {vp_id}")
        row = rows_by_id[vp_id]
        inflight = state.setdefault("inflight", {})
        if vp_id not in inflight:
            raise KeyError(f"VP is not inflight: {vp_id}")
        previous_merged_vdb = Path(str(state["merged_vdb_path"])).resolve() if Path(str(state["merged_vdb_path"])).exists() else None
        baseline_vdb_path = Path(str(state["baseline_vdb_path"])).resolve()
        runner = merge_runner or merge_vdb_with_urg
        task_vdb = _coerce_path(task_vdb_path)
        _append_event(paths, "complete", vp_id=vp_id, task_name=task_name, task_vdb_path=str(task_vdb), isg_script=isg_script)
        merge_result = runner(task_vdb, previous_merged_vdb, paths.merged_vdb_path, baseline_vdb_path)
        if not merge_result.get("success", False):
            inflight.pop(vp_id, None)
            row["running_state"] = RUNNING_IDLE
            row["status"] = _derive_row_status(row, max_exec_count=int(state.get("max_exec_count", 3)))
            state["updated_at"] = _now()
            save_scoreboard(paths.root, rows, state)
            _append_event(paths, "fail", vp_id=vp_id, task_name=task_name, error=str(merge_result.get("error", "merge failed")))
            return {"vp_id": vp_id, "task_name": task_name, "merged": False, "error": merge_result.get("error", "merge failed")}
        merged_vdb_path = Path(str(merge_result.get("merged_vdb_path", paths.merged_vdb_path))).resolve()
        state["merged_vdb_path"] = str(merged_vdb_path)
        state["last_merge_version"] = int(state.get("last_merge_version", 0)) + 1
        merge_version = int(state["last_merge_version"])
        _append_event(paths, "merge", vp_id=vp_id, task_name=task_name, task_vdb_path=str(task_vdb), merged_vdb_path=str(merged_vdb_path), merge_version=merge_version, command=merge_result.get("command"))
        row["exec_count"] = int(row["exec_count"]) + 1
        refresh_kind = str(state.get("active_kind") or row.get("kind") or "line")
        snapshot_loader_map: dict[str, SnapshotLoaderFn] = {
            "line": line_snapshot_loader or load_line_snapshot,
            "cond": condition_snapshot_loader or load_condition_snapshot,
            "branch": branch_snapshot_loader or load_branch_snapshot,
            "fsm": fsm_snapshot_loader or load_fsm_snapshot,
        }
        if refresh_kind not in snapshot_loader_map:
            raise ValueError(f"scheduler_v2 does not support refresh kind: {refresh_kind}")
        kind_snapshot, snapshot_payload = snapshot_loader_map[refresh_kind](merged_vdb_path, None)
        _write_json(paths.root / f"merged_{refresh_kind}_snapshot.json", snapshot_payload)
        improved_vps: list[str] = []
        max_exec_count = int(state.get("max_exec_count", 3))
        inflight_ids = set(inflight.keys())
        for current_row in rows:
            if current_row["kind"] != refresh_kind:
                continue
            snapshot_entry = kind_snapshot.get(_snapshot_key(str(current_row["full_name"]), refresh_kind, str(current_row["range"])))
            if snapshot_entry is None:
                continue
            before_pct = float(current_row["current_line_pct"])
            preserve_inflight = current_row["vp_id"] in inflight_ids and current_row["vp_id"] != vp_id
            current_row["current_line_pct"] = _round_pct(float(snapshot_entry.get("pct", 0.0)))
            if not current_row["rtl_file"]:
                current_row["rtl_file"] = str(snapshot_entry.get("rtl_file", "") or "")
            if not preserve_inflight:
                current_row["status"] = _derive_row_status(current_row, max_exec_count=max_exec_count)
            after_pct = float(current_row["current_line_pct"])
            _append_event(paths, "refresh", merge_version=merge_version, vdb_path=str(merged_vdb_path), vp_id=current_row["vp_id"], task_name=task_name, status=current_row["status"], before_pct=before_pct, after_pct=after_pct, coverage={"source": f"local_{refresh_kind}_snapshot", **snapshot_entry}, error="")
            if after_pct > before_pct:
                delta_pct = _round_pct(after_pct - before_pct)
                current_row["improvement_count"] = int(current_row["improvement_count"]) + 1
                current_row["last_improved_by_task"] = task_name
                current_row["last_improved_by_script"] = isg_script
                current_row["last_improved_delta_pct"] = delta_pct
                if str(current_row.get("vp_feasibility", "")).strip() in BLOCKING_FEASIBILITY:
                    previous_feasibility = str(current_row.get("vp_feasibility", "")).strip()
                    previous_reason = str(current_row.get("vp_feasibility_reason", "")).strip()
                    current_row["vp_feasibility"] = "hard"
                    current_row["vp_feasibility_reason"] = (
                        f"{previous_reason}; "
                        f"auto_upgraded_from_{previous_feasibility}_to_hard_because_other_task_improved_coverage"
                    ).strip("; ")
                    current_row["vp_feasibility_source"] = "scheduler_v2.refresh"
                    if not preserve_inflight:
                        current_row["status"] = _derive_row_status(current_row, max_exec_count=max_exec_count)
                    _append_event(
                        paths,
                        "classify",
                        vp_id=current_row["vp_id"],
                        feasibility=current_row["vp_feasibility"],
                        reason=current_row["vp_feasibility_reason"],
                        source=current_row["vp_feasibility_source"],
                        status=current_row["status"],
                    )
                improved_vps.append(current_row["vp_id"])
                _append_event(paths, "vp_improved", vp_id=current_row["vp_id"], task_name=task_name, task_vdb=str(task_vdb), isg_script=isg_script, before_pct=before_pct, after_pct=after_pct, delta_pct=delta_pct, merge_version=merge_version, error="")
        inflight.pop(vp_id, None)
        rows_by_id[vp_id]["running_state"] = RUNNING_IDLE
        rows_by_id[vp_id]["status"] = _derive_row_status(rows_by_id[vp_id], max_exec_count=max_exec_count)
        state["last_refresh_vdb_path"] = str(merged_vdb_path)
        state["last_refresh_at"] = _now()
        state["active_kind"] = _derive_active_kind(rows, max_exec_count=max_exec_count)
        state["updated_at"] = _now()
        save_scoreboard(paths.root, rows, state)
        return {"vp_id": vp_id, "task_name": task_name, "merged": True, "merged_vdb_path": str(merged_vdb_path), "merge_version": merge_version, "improved_vps": improved_vps}


def recover_scoreboard(output_dir: str | os.PathLike[str], *, requeue_stale: bool = False) -> dict[str, Any]:
    paths = get_scoreboard_paths(output_dir)
    with _scoreboard_lock(paths):
        rows, state = load_scoreboard(output_dir)
        inflight = state.setdefault("inflight", {})
        stale = state.setdefault("stale_inflight", {})
        recovered: list[str] = []
        for vp_id, entry in list(inflight.items()):
            row = next((row for row in rows if row["vp_id"] == vp_id), None)
            if row is None:
                inflight.pop(vp_id, None)
                continue
            if requeue_stale:
                row["running_state"] = RUNNING_IDLE
                inflight.pop(vp_id, None)
            else:
                row["running_state"] = RUNNING_STALE
                stale[vp_id] = entry
                inflight.pop(vp_id, None)
            recovered.append(vp_id)
        state["updated_at"] = _now()
        save_scoreboard(paths.root, rows, state)
        _append_event(paths, "recover", requeue_stale=requeue_stale, recovered_vp_ids=recovered)
        return {"recovered_vp_ids": recovered, "requeue_stale": requeue_stale}


def classify_vp(
    output_dir: str | os.PathLike[str],
    vp_id: str,
    *,
    feasibility: str,
    reason: str = "",
    source: str = "",
) -> dict[str, Any]:
    paths = get_scoreboard_paths(output_dir)
    with _scoreboard_lock(paths):
        rows, state = load_scoreboard(output_dir)
        rows_by_id = {row["vp_id"]: row for row in rows}
        if vp_id not in rows_by_id:
            raise KeyError(f"Unknown vp_id: {vp_id}")
        row = rows_by_id[vp_id]
        normalized = str(feasibility or "unknown").strip() or "unknown"
        effective_reason = str(reason or "").strip()
        row["vp_feasibility"] = normalized
        row["vp_feasibility_reason"] = effective_reason
        row["vp_feasibility_source"] = str(source or "").strip()
        if str(row.get("running_state", RUNNING_IDLE)) == RUNNING_IDLE:
            row["status"] = _derive_row_status(row, max_exec_count=int(state.get("max_exec_count", 3)))
        state["updated_at"] = _now()
        state["active_kind"] = _derive_active_kind(rows, max_exec_count=int(state.get("max_exec_count", 3)))
        save_scoreboard(paths.root, rows, state)
        _append_event(
            paths,
            "classify",
            vp_id=vp_id,
            feasibility=row["vp_feasibility"],
            reason=row["vp_feasibility_reason"],
            source=row["vp_feasibility_source"],
            status=row["status"],
        )
        return dict(row)


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Scoreboard scheduler v2 (UCAPI snapshot based)")
    parser.add_argument("--output-dir", default=str(get_scoreboard_root()))
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init", help="Initialize scoreboard from UCAPI VP list + baseline snapshot")
    init_parser.add_argument("--vp-list", action="append", default=None, help="Repeat to load multiple VP list JSON files")
    init_parser.add_argument("--baseline-vdb", default=str(get_baseline_vdb_path()))
    init_parser.add_argument("--max-exec-count", type=int, default=3)
    init_parser.add_argument("--parallelism", type=int, default=4)
    select_parser = subparsers.add_parser("select", help="Select the next schedulable VPs")
    select_parser.add_argument("--slots", type=int, default=None)
    manual_select_parser = subparsers.add_parser("manual-select", help="Manually select a specific VP for launch")
    manual_select_parser.add_argument("--vp-id", required=True)
    launch_parser = subparsers.add_parser("launch", help="Mark a selected VP as launched")
    launch_parser.add_argument("--vp-id", required=True)
    launch_parser.add_argument("--task-name", required=True)
    launch_parser.add_argument("--agent-id", default="")
    launch_parser.add_argument("--task-vdb-path", default="")
    launch_parser.add_argument("--isg-script", default="")
    complete_parser = subparsers.add_parser("complete", help="Merge a completed task VDB and refresh line snapshot")
    complete_parser.add_argument("--vp-id", required=True)
    complete_parser.add_argument("--task-name", required=True)
    complete_parser.add_argument("--task-vdb-path", required=True)
    complete_parser.add_argument("--isg-script", default="")
    fail_parser = subparsers.add_parser("fail", help="Mark an inflight VP as failed without merge")
    fail_parser.add_argument("--vp-id", required=True)
    fail_parser.add_argument("--task-name", required=True)
    fail_parser.add_argument("--error", required=True)
    recover_parser = subparsers.add_parser("recover", help="Recover stale inflight tasks")
    recover_parser.add_argument("--requeue-stale", action="store_true")
    return parser


def main() -> int:
    parser = _build_cli()
    args = parser.parse_args()
    if args.command == "init":
        result = initialize_scoreboard(args.output_dir, vp_list_paths=args.vp_list, baseline_vdb_path=args.baseline_vdb, max_exec_count=args.max_exec_count, parallelism=args.parallelism)
    elif args.command == "select":
        result = {"selected": select_next_vps(args.output_dir, slots=args.slots)}
    elif args.command == "manual-select":
        result = {"selected": manual_select_vp(args.output_dir, vp_id=args.vp_id)}
    elif args.command == "launch":
        result = mark_vp_launched(args.output_dir, args.vp_id, task_name=args.task_name, agent_id=args.agent_id, task_vdb_path=args.task_vdb_path, isg_script=args.isg_script)
    elif args.command == "complete":
        result = complete_vp_task(args.output_dir, args.vp_id, task_name=args.task_name, task_vdb_path=args.task_vdb_path, isg_script=args.isg_script)
    elif args.command == "fail":
        result = record_vp_failure(args.output_dir, args.vp_id, task_name=args.task_name, error=args.error)
    else:
        result = recover_scoreboard(args.output_dir, requeue_stale=args.requeue_stale)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
