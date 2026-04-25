from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Mapping

from src.utils.project_paths import get_baseline_vdb_path, get_coverage_root, get_rtl_root, get_scoreboard_root,get_regression_root


KIND_ORDER = ("branch", "cond", "line")
GROUP_ORDER = ("ifu", "idu", "iu", "rtu", "others")
RUNNING_IDLE = "idle"
RUNNING_QUEUED = "queued"
RUNNING_RUNNING = "running"
RUNNING_STALE = "stale"
BLOCKED_STATUS_PREFIX = "blocked_"
CSV_FIELD_ALIASES = {
    "full_name": "full_instance_name",
}
LEGACY_STATUS_TO_RUNNING_STATE = {
    "selected": RUNNING_QUEUED,
    "inflight": RUNNING_RUNNING,
    "stale_inflight": RUNNING_STALE,
}
LEGACY_RUNNING_STATUSES = set(LEGACY_STATUS_TO_RUNNING_STATE)

SCOREBOARD_FIELDS = [
    "vp_id",
    "full_name",
    "kind",
    "range",
    "vp_group",
    "rtl_file",
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

INDEX_LINE_RE = re.compile(r"^\s*\d+\.\s*(?P<full_name>.*?)\s*->\s*(?P<target>.*?)\s*$")
TARGET_HTML_RE = re.compile(r"^(?P<html>[^#]+)")
SOURCE_FILE_RE = re.compile(r"openSrcFile\('(?P<path>[^']+\.v)'\)")
ANSI_ESCAPE_RE = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")
QUALIFIED_INSTANCE_RE = re.compile(r"got qualified instance:\s*(?P<full_name>.+)")
UCAPI_SOURCE_FILE_RE = re.compile(r"source file opened:\s*(?P<source_file>.+)")
LINE_STATUS_RE = re.compile(
    r"^Line\s+(?P<line_no>\d+)\s+cover status:\s*(?P<status>Yes|No)\s*\|\s*(?P<source>.*)$",
    re.MULTILINE,
)
LINE_COVERAGE_BEGIN = "======================Line Coverage Begin========================"
LINE_COVERAGE_END = "======================Line Coverage End========================"


CoverageQueryFn = Callable[[Path, str, int, int, Mapping[str, Any]], Mapping[str, Any]]
MergeRunnerFn = Callable[[Path, Path | None, Path, Path], Mapping[str, Any]]


@dataclass(frozen=True)
class ScoreboardPaths:
    root: Path
    csv_path: Path
    state_path: Path
    events_path: Path
    details_path: Path
    merged_vdb_path: Path


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _round_pct(value: float) -> float:
    return round(value + 1e-9, 2)


def _coerce_path(path: str | os.PathLike[str]) -> Path:
    return Path(path).expanduser().resolve()


def get_default_scoreboard_root() -> Path:
    return get_scoreboard_root()


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
    return get_default_scoreboard_root().resolve()


def get_scoreboard_paths(output_dir: str | os.PathLike[str] | None = None) -> ScoreboardPaths:
    root = _coerce_path(output_dir) if output_dir else get_default_scoreboard_root().resolve()
    merged_root = _resolve_merged_vdb_root(root)
    return ScoreboardPaths(
        root=root,
        csv_path=root / "scoreboard.csv",
        state_path=root / "scoreboard_state.json",
        events_path=root / "scoreboard_events.jsonl",
        details_path=root / "scoreboard_details.json",
        merged_vdb_path=merged_root / "merged_cov.vdb",
    )


def _format_csv_value(field: str, value: Any) -> str:
    if field in FLOAT_FIELDS:
        return f"{float(value):.2f}"
    if field in INT_FIELDS:
        return str(int(value))
    return "" if value is None else str(value)


def _csv_field_name(field: str) -> str:
    return CSV_FIELD_ALIASES.get(field, field)


def _derive_running_state_from_status(status: str) -> str:
    return LEGACY_STATUS_TO_RUNNING_STATE.get(status, RUNNING_IDLE)


def _normalize_loaded_status(status: str) -> str:
    if status in LEGACY_RUNNING_STATUSES:
        return "pending"
    return status or "pending"


def _extract_csv_value(raw_row: Mapping[str, Any], field: str) -> str:
    if field == "full_name":
        return str(raw_row.get("full_instance_name", raw_row.get("full_name", "")) or "")
    if field == "running_state":
        value = str(raw_row.get("running_state", "") or "")
        if value:
            return value
        legacy_status = str(raw_row.get("status", "") or "")
        return _derive_running_state_from_status(legacy_status)
    if field == "status":
        return _normalize_loaded_status(str(raw_row.get("status", "") or ""))
    return str(raw_row.get(_csv_field_name(field), raw_row.get(field, "")) or "")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _build_details_payload(rows: list[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "rtl_file_by_vp_id": {
            str(row["vp_id"]): str(row.get("rtl_file", ""))
            for row in rows
        },
        "vp_key_by_vp_id": {
            str(row["vp_id"]): f"{row.get('full_name', '')}::{row.get('kind', '')}::{row.get('range', '')}"
            for row in rows
        },
    }


def _load_details(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"rtl_file_by_vp_id": {}, "vp_key_by_vp_id": {}}
    payload = _read_json(path)
    rtl_file_by_vp_id = payload.get("rtl_file_by_vp_id", {})
    vp_key_by_vp_id = payload.get("vp_key_by_vp_id", {})
    if not isinstance(rtl_file_by_vp_id, dict):
        rtl_file_by_vp_id = {}
    if not isinstance(vp_key_by_vp_id, dict):
        vp_key_by_vp_id = {}
    return {"rtl_file_by_vp_id": rtl_file_by_vp_id, "vp_key_by_vp_id": vp_key_by_vp_id}


def _append_event(paths: ScoreboardPaths, event: str, **payload: Any) -> None:
    paths.root.mkdir(parents=True, exist_ok=True)
    row = {"timestamp": _now(), "event": event, **payload}
    with paths.events_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def load_scoreboard_events(output_dir: str | os.PathLike[str] | None = None) -> list[dict[str, Any]]:
    paths = get_scoreboard_paths(output_dir)
    if not paths.events_path.exists():
        return []

    rows: list[dict[str, Any]] = []
    with paths.events_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _range_bounds(range_text: str) -> tuple[int, int]:
    cleaned = str(range_text).strip()
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


def save_scoreboard(output_dir: str | os.PathLike[str], rows: list[dict[str, Any]], state: Mapping[str, Any]) -> None:
    paths = get_scoreboard_paths(output_dir)
    paths.root.mkdir(parents=True, exist_ok=True)

    with paths.csv_path.open("w", encoding="utf-8", newline="") as fh:
        csv_fields = [field for field in SCOREBOARD_FIELDS if field != "rtl_file"]
        writer = csv.DictWriter(fh, fieldnames=[_csv_field_name(field) for field in csv_fields])
        writer.writeheader()
        for row in sorted(rows, key=_row_sort_key):
            writer.writerow(
                {
                    _csv_field_name(field): _format_csv_value(field, row.get(field, ""))
                    for field in csv_fields
                }
            )

    _write_json(paths.state_path, state)
    _write_json(paths.details_path, _build_details_payload(rows))


def load_scoreboard(output_dir: str | os.PathLike[str]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    paths = get_scoreboard_paths(output_dir)
    rows: list[dict[str, Any]] = []
    details = _load_details(paths.details_path)
    rtl_file_by_vp_id = details["rtl_file_by_vp_id"]
    if paths.csv_path.exists():
        with paths.csv_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            csv_fields = set(reader.fieldnames or [])
            has_legacy_rtl_file = "rtl_file" in csv_fields
            for raw_row in reader:
                row: dict[str, Any] = {}
                for field in SCOREBOARD_FIELDS:
                    if field == "rtl_file" and not has_legacy_rtl_file:
                        value = rtl_file_by_vp_id.get(raw_row.get("vp_id", ""), "")
                        row[field] = value or ""
                        continue
                    value = _extract_csv_value(raw_row, field)
                    if field in FLOAT_FIELDS:
                        row[field] = float(value or 0.0)
                    elif field in INT_FIELDS:
                        row[field] = int(value or 0)
                    else:
                        row[field] = value or ""
                rows.append(row)

    state = _read_json(paths.state_path) if paths.state_path.exists() else {}
    legacy_merged_vdb_path = str((paths.root / "merged_cov.vdb").resolve())
    canonical_merged_vdb_path = str(paths.merged_vdb_path.resolve())
    merged_vdb_path = str(state.get("merged_vdb_path", "") or "")
    if not merged_vdb_path or merged_vdb_path == legacy_merged_vdb_path:
        state["merged_vdb_path"] = canonical_merged_vdb_path
    return rows, state


def infer_vp_group(full_name: str) -> str:
    if "x_ct_ifu_top" in full_name or "ct_ifu_" in full_name:
        return "ifu"
    if "x_ct_idu_top" in full_name or "ct_idu_" in full_name:
        return "idu"
    if "x_ct_iu_top" in full_name or "ct_iu_" in full_name:
        return "iu"
    if "x_ct_rtu_top" in full_name or "ct_rtu_" in full_name:
        return "rtu"
    return "others"


def _strip_instance_suffix(html_name: str) -> str:
    stem = Path(html_name).stem
    match = re.match(r"^(mod\d+)", stem)
    if match:
        return f"{match.group(1)}.html"
    return html_name


class RtlPathResolver:
    def __init__(
        self,
        index_path: Path | None = None,
        cov_report_dir: Path | None = None,
        rtl_root: Path | None = None,
    ):
        self.index_path = index_path
        self.cov_report_dir = cov_report_dir
        self.rtl_root = rtl_root
        self._rtl_file_names = self._build_rtl_file_names(rtl_root)
        self._source_cache: dict[str, str | None] = {}
        self._report_mapping = self._build_report_mapping()

    @staticmethod
    def _build_rtl_file_names(rtl_root: Path | None) -> set[str]:
        if rtl_root is None or not rtl_root.exists():
            return set()
        return {path.name for path in rtl_root.rglob("*.v") if path.is_file()}

    def _extract_source_file(self, html_name: str) -> str | None:
        if self.cov_report_dir is None:
            return None
        if html_name in self._source_cache:
            return self._source_cache[html_name]

        candidates = [html_name]
        stripped = _strip_instance_suffix(html_name)
        if stripped not in candidates:
            candidates.append(stripped)

        for candidate_name in candidates:
            html_path = self.cov_report_dir / candidate_name
            if not html_path.exists():
                continue
            content = html_path.read_text(encoding="utf-8", errors="ignore")
            match = SOURCE_FILE_RE.search(content)
            if match:
                file_name = Path(match.group("path")).name
                self._source_cache[html_name] = file_name
                return file_name

        self._source_cache[html_name] = None
        return None

    def _build_report_mapping(self) -> dict[str, str]:
        if self.index_path is None or not self.index_path.exists():
            return {}

        mapping: dict[str, str] = {}
        for line in self.index_path.read_text(encoding="utf-8", errors="ignore").splitlines():
            match = INDEX_LINE_RE.match(line)
            if not match:
                continue
            html_match = TARGET_HTML_RE.match(match.group("target").strip())
            if not html_match:
                continue
            source_file = self._extract_source_file(html_match.group("html"))
            if source_file:
                mapping[match.group("full_name").strip()] = source_file
        return mapping

    def resolve(self, full_name: str) -> str | None:
        if full_name in self._report_mapping:
            return self._report_mapping[full_name]

        leaf = full_name.split(".")[-1]
        leaf = re.sub(r"\[[^\]]+\]", "", leaf)
        if leaf.startswith("x_"):
            leaf = leaf[2:]
        candidate = f"{leaf}.v"
        if not self._rtl_file_names or candidate in self._rtl_file_names:
            return candidate
        return None


def _default_report_assets(
    regression_root: Path | None = None,
    version: str = "BASELINE",
) -> tuple[Path | None, Path | None]:
    root = regression_root or get_regression_root()
    index_path = root / f"md_out_{version}" / "all_full_index.txt"
    cov_report_dir = root / f"cov_report_{version}"
    return (
        index_path if index_path.exists() else None,
        cov_report_dir if cov_report_dir.exists() else None,
    )


def flatten_vp_list(vp_list_payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for module_index, module in enumerate(vp_list_payload.get("modules", [])):
        full_name = str(module.get("full_name", "")).strip()
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
                    "kind": kind,
                    "range": range_text,
                    "vp_group": infer_vp_group(full_name),
                }
            )
    return sorted(rows, key=_row_sort_key)


def normalize_ucapi_raw_output(raw_output: str) -> tuple[str, str]:
    normalized = raw_output.replace("\r\n", "\n").replace("\r", "\n")
    normalized = ANSI_ESCAPE_RE.sub("", normalized)
    normalized = "\n".join(line.rstrip() for line in normalized.split("\n"))
    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    return normalized, digest


def parse_ucapi_query_result(api_result: Mapping[str, Any]) -> dict[str, Any]:
    """解析 UCAPI 查询结果

    优先从 VP Summary 的 metrics 中获取覆盖率，这是最准确的数据源：
    - VP Summary 包含所有类型（line/cond/branch/tgl/fsm）的覆盖率汇总
    - 每个 VP 根据 kind 直接从 vp.metrics[kind] 获取对应覆盖率
    - 如果 VP Summary 不可用，回退到解析单独的 kind 字段或 raw_output
    """
    if not api_result.get("success", False):
        return {
            "status": "blocked_ucapi_error",
            "line_pct": 0.0,
            "coverage": None,
            "error": str(api_result.get("error", "Unknown UCAPI error")),
        }

    data = api_result.get("data")
    if not isinstance(data, Mapping):
        return {
            "status": "blocked_unparsed_ucapi",
            "line_pct": 0.0,
            "coverage": None,
            "error": "UCAPI response missing data object",
        }

    # 获取 kind（从 data 中获取，默认 line）
    kind = str(data.get("kind", "line"))
    # 处理 kind 参数中的 +vp 后缀（build_ucapi_fetcher 会添加）
    kind = kind.replace("+vp", "").strip()

    # 优先从 VP Summary 的 metrics 中获取（最准确的数据源）
    vp_summary = data.get("vp")
    if vp_summary and isinstance(vp_summary, Mapping):
        metrics = vp_summary.get("metrics", {})
        # 直接从 metrics 获取对应 kind 的覆盖率
        metric = metrics.get(kind)
        if metric and isinstance(metric, Mapping):
            pct = float(metric.get("pct", 0.0))
            covered = int(metric.get("covered", 0))
            coverable = int(metric.get("coverable", 0))
            matched = int(metric.get("matched", 0))

            query_info = vp_summary.get("query", {})
            coverage = {
                "query_module": str(query_info.get("module", "")),
                "query_range": str(query_info.get("range", "")),
                "qualified_instance": str(query_info.get("qualified_instance", "")),
                "source_file": str(query_info.get("source_file", "")),
                "kind": kind,
                "covered": covered,
                "coverable": coverable,
                "matched": matched,
                "pct": pct,
            }
            return {
                "status": "ok",
                "line_pct": pct,
                "coverage": coverage,
                "error": "",
            }

    # 回退：尝试从 data 中直接获取对应 kind 的解析结果
    # coverage_server 返回格式: {"line": {"status": "ok", "covered": 5, "total": 5, "pct": 100.0}, ...}
    kind_key = kind
    if kind == "cond":
        kind_key = "condition"
    elif kind == "tgl":
        kind_key = "toggle"

    parsed = data.get(kind_key)
    if parsed and isinstance(parsed, Mapping):
        status = str(parsed.get("status", "no_data"))
        if status == "ok":
            pct = float(parsed.get("pct", 0.0))
            covered = int(parsed.get("covered", 0))
            coverable = int(parsed.get("total", 0))

            coverage = {
                "query_module": str(data.get("module", "")),
                "query_range": str(data.get("range", "")),
                "kind": kind,
                "covered": covered,
                "coverable": coverable,
                "pct": pct,
            }
            return {
                "status": "ok",
                "line_pct": pct,
                "coverage": coverage,
                "error": "",
            }
        elif status == "no_data":
            raw_output = data.get("raw_output", "")
            return {
                "status": "blocked_empty_ucapi",
                "line_pct": 0.0,
                "coverage": None,
                "error": f"No coverage data for kind={kind}",
                "raw_output_digest": hashlib.sha256(raw_output.encode()).hexdigest()[:16] if raw_output else "",
            }

    # 回退：解析 raw_output（旧格式兼容）
    raw_output = data.get("raw_output")
    if not isinstance(raw_output, str):
        return {
            "status": "blocked_unparsed_ucapi",
            "line_pct": 0.0,
            "coverage": None,
            "error": "UCAPI response missing raw_output",
        }

    normalized_raw_output, raw_output_digest = normalize_ucapi_raw_output(raw_output)

    begin_idx = normalized_raw_output.find(LINE_COVERAGE_BEGIN)
    end_idx = normalized_raw_output.find(LINE_COVERAGE_END)
    if begin_idx < 0 or end_idx < 0 or end_idx <= begin_idx:
        return {
            "status": "blocked_unparsed_ucapi",
            "line_pct": 0.0,
            "coverage": None,
            "error": "Missing Line Coverage Begin/End markers",
            "raw_output_digest": raw_output_digest,
        }

    line_section = normalized_raw_output[begin_idx + len(LINE_COVERAGE_BEGIN):end_idx].strip("\n")
    line_matches = list(LINE_STATUS_RE.finditer(line_section))
    if not line_matches:
        return {
            "status": "blocked_empty_ucapi",
            "line_pct": 0.0,
            "coverage": None,
            "error": "Line Coverage section has no line status rows",
            "raw_output_digest": raw_output_digest,
        }

    line_map: dict[int, dict[str, Any]] = {}
    for match in line_matches:
        line_no = int(match.group("line_no"))
        entry = line_map.setdefault(
            line_no,
            {
                "line_no": line_no,
                "statuses": [],
                "sources": [],
            },
        )
        entry["statuses"].append(match.group("status"))
        entry["sources"].append(match.group("source"))

    line_statuses: list[dict[str, Any]] = []
    covered_line_count = 0
    for line_no in sorted(line_map):
        entry = line_map[line_no]
        final_status = "Yes" if "Yes" in entry["statuses"] else "No"
        if final_status == "Yes":
            covered_line_count += 1
        line_statuses.append(
            {
                "line_no": line_no,
                "final_status": final_status,
                "statuses": entry["statuses"],
                "sources": entry["sources"],
            }
        )

    unique_line_count = len(line_statuses)
    line_pct = 0.0 if unique_line_count == 0 else _round_pct(covered_line_count / unique_line_count * 100.0)

    qualified_instance_match = QUALIFIED_INSTANCE_RE.search(normalized_raw_output)
    source_file_match = UCAPI_SOURCE_FILE_RE.search(normalized_raw_output)
    coverage = {
        "query_module": str(data.get("module", "")),
        "query_range": str(data.get("range", "")),
        "qualified_instance": qualified_instance_match.group("full_name").strip() if qualified_instance_match else "",
        "source_file": source_file_match.group("source_file").strip() if source_file_match else "",
        "unique_line_count": unique_line_count,
        "covered_line_count": covered_line_count,
        "line_pct": line_pct,
        "line_statuses": line_statuses,
        "raw_output_digest": raw_output_digest,
    }
    return {
        "status": "ok",
        "line_pct": line_pct,
        "coverage": coverage,
        "error": "",
    }


def _is_blocked_status(status: str) -> bool:
    return status.startswith(BLOCKED_STATUS_PREFIX)


def _derive_row_status(row: Mapping[str, Any], max_exec_count: int, preserve_inflight: bool = False) -> str:
    status = str(row.get("status", "pending"))
    if _is_blocked_status(status):
        return status
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


def _refresh_row_from_coverage(
    row: dict[str, Any],
    parse_result: Mapping[str, Any],
    *,
    max_exec_count: int,
    preserve_inflight: bool = False,
) -> dict[str, Any]:
    result_status = str(parse_result["status"])
    if result_status == "ok":
        row["current_line_pct"] = _round_pct(float(parse_result["line_pct"]))
        row["status"] = _derive_row_status(row, max_exec_count=max_exec_count, preserve_inflight=preserve_inflight)
        return row

    if not preserve_inflight:
        row["status"] = result_status
    return row


def build_ucapi_fetcher(http_api_url: str = "http://localhost:5000/api/v1/query") -> CoverageQueryFn:
    """构建 UCAPI 查询函数
    
    Args:
        http_api_url: UCAPI 服务地址，默认为 http://localhost:5000/api/v1/query
    """
    def fetcher(vdb_path: Path, rtl_file: str, start_line: int, end_line: int, row: Mapping[str, Any]) -> Mapping[str, Any]:
        import requests

        try:
            vdb_path = vdb_path.expanduser().resolve()
            if not vdb_path.exists():
                return {"success": False, "error": f"VDB path not found: {vdb_path}"}

            module_name = Path(rtl_file).stem
            test_name = _detect_ucapi_test_name(vdb_path)
            if test_name is None:
                return {"success": False, "error": f"No test data found for VDB: {vdb_path}"}

            # 从 row 中获取 kind，默认为 line
            kind = str(row.get("kind", "line")) if row else "line"

            payload = {
                "vdb_path": str(vdb_path),
                "test_name": test_name,
                "module": module_name,
                "start_line": start_line,
                "end_line": end_line,
                "kind": f"{kind}+vp",  # 添加 +vp 确保 VP Summary 被返回，直接使用 vp.metrics 获取覆盖率
            }
            response = requests.post(http_api_url, json=payload, timeout=60)
            response.raise_for_status()
            result = response.json()
            if isinstance(result, Mapping):
                return result
            return {"success": False, "error": "UCAPI returned non-object JSON payload"}
        except requests.RequestException as exc:
            return {"success": False, "error": str(exc)}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    return fetcher


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


def _urg_output_candidates(dbname_path: Path) -> list[Path]:
    appended_suffix = dbname_path.with_name(f"{dbname_path.name}.vdb")
    candidates = [dbname_path, appended_suffix]
    deduped: list[Path] = []
    for candidate in candidates:
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
                return {
                    "success": True,
                    "merged_vdb_path": str(output_vdb_path),
                    "command": cmd,
                    "attempt_count": attempt,
                }
        except Exception as exc:
            error = str(exc)

        errors.append(error)
        _cleanup_urg_outputs(temp_output)
        if attempt < attempts and retry_delay > 0:
            time.sleep(retry_delay)

    return {
        "success": False,
        "error": errors[-1] if errors else "urg merge failed",
        "command": cmd,
        "attempt_count": attempts,
        "errors": errors,
    }


def initialize_scoreboard(
    output_dir: str | os.PathLike[str],
    *,
    vp_list_path: str | os.PathLike[str] = "vp_list.json",
    baseline_vdb_path: str | os.PathLike[str] | None = None,
    coverage_query: CoverageQueryFn | None = None,
    report_index_path: str | os.PathLike[str] | None = None,
    cov_report_dir: str | os.PathLike[str] | None = None,
    rtl_root: str | os.PathLike[str] | None = None,
    regression_root: str | os.PathLike[str] | None = None,
    max_exec_count: int = 3,
    parallelism: int = 4,
) -> dict[str, Any]:
    paths = get_scoreboard_paths(output_dir)
    paths.root.mkdir(parents=True, exist_ok=True)

    vp_path = _coerce_path(vp_list_path)
    baseline_path = _coerce_path(baseline_vdb_path) if baseline_vdb_path else get_baseline_vdb_path().resolve()
    regression_base = _coerce_path(regression_root) if regression_root else None
    default_index_path, default_cov_report_dir = _default_report_assets(regression_base)
    resolver = RtlPathResolver(
        index_path=_coerce_path(report_index_path) if report_index_path else default_index_path,
        cov_report_dir=_coerce_path(cov_report_dir) if cov_report_dir else default_cov_report_dir,
        rtl_root=_coerce_path(rtl_root) if rtl_root else get_rtl_root().resolve(),
    )
    fetcher = coverage_query or build_ucapi_fetcher()

    vp_payload = _read_json(vp_path)
    rows = flatten_vp_list(vp_payload)
    initialized_rows: list[dict[str, Any]] = []

    if paths.events_path.exists():
        paths.events_path.unlink()

    for item in rows:
        row = {
            **item,
            "rtl_file": resolver.resolve(str(item["full_name"])) or "",
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

        if not row["rtl_file"]:
            row["status"] = "blocked_unresolved_rtl"
            _append_event(paths, "refresh", merge_version=0, vdb_path=str(baseline_path), vp_id=row["vp_id"], status=row["status"], error="Unable to resolve RTL file")
            initialized_rows.append(row)
            continue

        start_line, end_line = _range_bounds(str(row["range"]))
        parse_result = parse_ucapi_query_result(fetcher(baseline_path, str(row["rtl_file"]), start_line, end_line, row))
        if str(parse_result["status"]) == "ok":
            row["baseline_line_pct"] = _round_pct(float(parse_result["line_pct"]))
            row["current_line_pct"] = _round_pct(float(parse_result["line_pct"]))
            row["status"] = _derive_row_status(row, max_exec_count=max_exec_count)
        else:
            row["status"] = str(parse_result["status"])

        initialized_rows.append(row)
        coverage = parse_result.get("coverage")
        _append_event(
            paths,
            "refresh",
            merge_version=0,
            vdb_path=str(baseline_path),
            vp_id=row["vp_id"],
            status=row["status"],
            before_pct=0.0,
            after_pct=row["current_line_pct"],
            coverage=coverage,
            error=parse_result.get("error", ""),
        )
        if coverage and coverage.get("source_file") and Path(str(coverage["source_file"])).name != row["rtl_file"]:
            _append_event(
                paths,
                "rtl_mismatch",
                merge_version=0,
                vp_id=row["vp_id"],
                rtl_file=row["rtl_file"],
                ucapi_source_file=coverage["source_file"],
            )

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


def _choose_candidate(
    rows: list[dict[str, Any]],
    state: dict[str, Any],
    max_exec_count: int,
) -> dict[str, Any] | None:
    active_kind = state.get("active_kind") or _derive_active_kind(rows, max_exec_count=max_exec_count)
    if active_kind is None:
        return None

    phase_rows = [row for row in rows if row["kind"] == active_kind and _is_open_work(row, max_exec_count=max_exec_count)]
    if not phase_rows:
        return None

    min_exec_count = min(int(row["exec_count"]) for row in phase_rows)
    inflight_ids = set(state.get("inflight", {}).keys())
    candidates = [
        row
        for row in phase_rows
        if int(row["exec_count"]) == min_exec_count
        and row["vp_id"] not in inflight_ids
        and str(row["status"]) == "pending"
        and str(row.get("running_state", RUNNING_IDLE)) == RUNNING_IDLE
    ]
    if not candidates:
        return None

    group_pointer = int(state.get("group_pointer", 0))
    for offset in range(len(GROUP_ORDER)):
        group = GROUP_ORDER[(group_pointer + offset) % len(GROUP_ORDER)]
        group_candidates = [row for row in candidates if row["vp_group"] == group]
        if not group_candidates:
            continue
        chosen = min(
            group_candidates,
            key=lambda row: (
                float(row["current_line_pct"]),
                int(row["exec_count"]),
                float(row["baseline_line_pct"]),
                str(row["vp_id"]),
            ),
        )
        state["group_pointer"] = (GROUP_ORDER.index(group) + 1) % len(GROUP_ORDER)
        return chosen
    return None


def select_next_vps(output_dir: str | os.PathLike[str], slots: int | None = None) -> list[dict[str, Any]]:
    rows, state = load_scoreboard(output_dir)
    paths = get_scoreboard_paths(output_dir)

    max_exec_count = int(state.get("max_exec_count", 3))
    parallelism = int(state.get("parallelism", 4))
    state["active_kind"] = _derive_active_kind(rows, max_exec_count=max_exec_count)
    if state["active_kind"] is None:
        save_scoreboard(paths.root, rows, state)
        return []

    inflight = state.setdefault("inflight", {})
    available_capacity = max(parallelism - len(inflight), 0)
    wanted = available_capacity if slots is None else min(max(slots, 0), available_capacity)

    selected: list[dict[str, Any]] = []
    for _ in range(wanted):
        chosen = _choose_candidate(rows, state, max_exec_count=max_exec_count)
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
        _append_event(
            paths,
            "select",
            vp_id=chosen["vp_id"],
            active_kind=state["active_kind"],
            vp_group=chosen["vp_group"],
            exec_count=chosen["exec_count"],
            current_line_pct=chosen["current_line_pct"],
        )
        selected.append(dict(chosen))

    state["updated_at"] = _now()
    save_scoreboard(paths.root, rows, state)
    return selected


def mark_vp_launched(
    output_dir: str | os.PathLike[str],
    vp_id: str,
    *,
    task_name: str,
    agent_id: str = "",
    task_vdb_path: str = "",
    isg_script: str = "",
) -> dict[str, Any]:
    rows, state = load_scoreboard(output_dir)
    paths = get_scoreboard_paths(output_dir)
    rows_by_id = {row["vp_id"]: row for row in rows}
    if vp_id not in rows_by_id:
        raise KeyError(f"Unknown vp_id: {vp_id}")
    inflight = state.setdefault("inflight", {})
    if vp_id not in inflight:
        raise KeyError(f"VP is not selected for launch: {vp_id}")

    row = rows_by_id[vp_id]
    row["running_state"] = RUNNING_RUNNING
    inflight[vp_id].update(
        {
            "task_name": task_name,
            "inflight_agent_id": agent_id,
            "task_vdb_path": task_vdb_path,
            "isg_script": isg_script,
        }
    )
    state["updated_at"] = _now()
    save_scoreboard(paths.root, rows, state)
    _append_event(
        paths,
        "launch",
        vp_id=vp_id,
        task_name=task_name,
        inflight_agent_id=agent_id,
        task_vdb_path=task_vdb_path,
        isg_script=isg_script,
    )
    return dict(row)


def record_vp_failure(
    output_dir: str | os.PathLike[str],
    vp_id: str,
    *,
    task_name: str,
    error: str,
) -> dict[str, Any]:
    rows, state = load_scoreboard(output_dir)
    paths = get_scoreboard_paths(output_dir)
    rows_by_id = {row["vp_id"]: row for row in rows}
    if vp_id not in rows_by_id:
        raise KeyError(f"Unknown vp_id: {vp_id}")

    row = rows_by_id[vp_id]
    inflight = state.setdefault("inflight", {})
    inflight.pop(vp_id, None)
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
    coverage_query: CoverageQueryFn | None = None,
) -> dict[str, Any]:
    rows, state = load_scoreboard(output_dir)
    paths = get_scoreboard_paths(output_dir)
    rows_by_id = {row["vp_id"]: row for row in rows}
    if vp_id not in rows_by_id:
        raise KeyError(f"Unknown vp_id: {vp_id}")

    row = rows_by_id[vp_id]
    inflight = state.setdefault("inflight", {})
    inflight_entry = inflight.get(vp_id)
    if inflight_entry is None:
        raise KeyError(f"VP is not inflight: {vp_id}")

    active_kind_before_merge = state.get("active_kind") or _derive_active_kind(rows, max_exec_count=int(state.get("max_exec_count", 3)))
    previous_merged_vdb = Path(str(state["merged_vdb_path"])).resolve() if Path(str(state["merged_vdb_path"])).exists() else None
    baseline_vdb_path = Path(str(state["baseline_vdb_path"])).resolve()
    runner = merge_runner or merge_vdb_with_urg
    fetcher = coverage_query or build_ucapi_fetcher()
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
        return {
            "vp_id": vp_id,
            "task_name": task_name,
            "merged": False,
            "error": merge_result.get("error", "merge failed"),
        }

    merged_vdb_path = Path(str(merge_result.get("merged_vdb_path", paths.merged_vdb_path))).resolve()
    state["merged_vdb_path"] = str(merged_vdb_path)
    state["last_merge_version"] = int(state.get("last_merge_version", 0)) + 1
    merge_version = int(state["last_merge_version"])
    _append_event(
        paths,
        "merge",
        vp_id=vp_id,
        task_name=task_name,
        task_vdb_path=str(task_vdb),
        merged_vdb_path=str(merged_vdb_path),
        merge_version=merge_version,
        command=merge_result.get("command"),
    )

    row["exec_count"] = int(row["exec_count"]) + 1

    refresh_kind = active_kind_before_merge or row["kind"]
    improved_vps: list[str] = []
    max_exec_count = int(state.get("max_exec_count", 3))
    inflight_ids = set(inflight.keys())
    for current_row in rows:
        if current_row["kind"] != refresh_kind:
            continue
        if not current_row["rtl_file"]:
            continue

        start_line, end_line = _range_bounds(str(current_row["range"]))
        before_pct = float(current_row["current_line_pct"])
        parse_result = parse_ucapi_query_result(fetcher(merged_vdb_path, str(current_row["rtl_file"]), start_line, end_line, current_row))
        preserve_inflight = current_row["vp_id"] in inflight_ids and current_row["vp_id"] != vp_id
        _refresh_row_from_coverage(current_row, parse_result, max_exec_count=max_exec_count, preserve_inflight=preserve_inflight)
        after_pct = float(current_row["current_line_pct"])
        coverage = parse_result.get("coverage")
        _append_event(
            paths,
            "refresh",
            merge_version=merge_version,
            vdb_path=str(merged_vdb_path),
            vp_id=current_row["vp_id"],
            task_name=task_name,
            status=current_row["status"],
            before_pct=before_pct,
            after_pct=after_pct,
            coverage=coverage,
            error=parse_result.get("error", ""),
        )

        if coverage and coverage.get("source_file") and Path(str(coverage["source_file"])).name != current_row["rtl_file"]:
            _append_event(
                paths,
                "rtl_mismatch",
                merge_version=merge_version,
                vp_id=current_row["vp_id"],
                rtl_file=current_row["rtl_file"],
                ucapi_source_file=coverage["source_file"],
            )

        if after_pct > before_pct:
            delta_pct = _round_pct(after_pct - before_pct)
            current_row["improvement_count"] = int(current_row["improvement_count"]) + 1
            current_row["last_improved_by_task"] = task_name
            current_row["last_improved_by_script"] = isg_script
            current_row["last_improved_delta_pct"] = delta_pct
            improved_vps.append(current_row["vp_id"])
            _append_event(
                paths,
                "vp_improved",
                vp_id=current_row["vp_id"],
                task_name=task_name,
                task_vdb=str(task_vdb),
                isg_script=isg_script,
                before_pct=before_pct,
                after_pct=after_pct,
                delta_pct=delta_pct,
                merge_version=merge_version,
                error=parse_result.get("error", ""),
            )

    inflight.pop(vp_id, None)
    rows_by_id[vp_id]["running_state"] = RUNNING_IDLE
    rows_by_id[vp_id]["status"] = _derive_row_status(rows_by_id[vp_id], max_exec_count=max_exec_count)
    state["last_refresh_vdb_path"] = str(merged_vdb_path)
    state["last_refresh_at"] = _now()
    state["active_kind"] = _derive_active_kind(rows, max_exec_count=max_exec_count)
    state["updated_at"] = _now()
    save_scoreboard(paths.root, rows, state)
    return {
        "vp_id": vp_id,
        "task_name": task_name,
        "merged": True,
        "merge_version": merge_version,
        "merged_vdb_path": str(merged_vdb_path),
        "improved_vps": improved_vps,
        "active_kind": state["active_kind"],
    }


def recover_scoreboard(output_dir: str | os.PathLike[str], *, requeue_stale: bool = False) -> dict[str, Any]:
    rows, state = load_scoreboard(output_dir)
    paths = get_scoreboard_paths(output_dir)
    rows_by_id = {row["vp_id"]: row for row in rows}
    inflight = state.setdefault("inflight", {})
    stale_inflight = state.setdefault("stale_inflight", {})
    recovered: list[str] = []

    for vp_id, info in list(inflight.items()):
        row = rows_by_id.get(vp_id)
        if row is None:
            inflight.pop(vp_id, None)
            continue
        recovered.append(vp_id)
        stale_inflight[vp_id] = {
            **info,
            "stale_at": _now(),
        }
        if requeue_stale:
            row["running_state"] = RUNNING_IDLE
            row["status"] = _derive_row_status(row, max_exec_count=int(state.get("max_exec_count", 3)))
        else:
            row["running_state"] = RUNNING_STALE
        inflight.pop(vp_id, None)
        _append_event(paths, "stale_inflight", vp_id=vp_id, requeue_stale=requeue_stale)

    state["active_kind"] = _derive_active_kind(rows, max_exec_count=int(state.get("max_exec_count", 3)))
    state["updated_at"] = _now()
    save_scoreboard(paths.root, rows, state)
    return {
        "output_dir": str(paths.root),
        "recovered_vp_ids": recovered,
        "requeue_stale": requeue_stale,
    }


def _build_cli() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Long-horizon scoreboard scheduler utilities.")
    parser.add_argument("--output-dir", default=str(get_default_scoreboard_root()), help="Scoreboard output directory")
    subparsers = parser.add_subparsers(dest="command", required=True)

    init_parser = subparsers.add_parser("init", help="Initialize scoreboard from vp_list.json")
    init_parser.add_argument("--vp-list", default="vp_list.json")
    init_parser.add_argument("--baseline-vdb", default=str(get_baseline_vdb_path()))
    init_parser.add_argument("--report-index", default=None)
    init_parser.add_argument("--cov-report-dir", default=None)
    init_parser.add_argument("--rtl-root", default=None)
    init_parser.add_argument("--regression-root", default=None)
    init_parser.add_argument("--http-api-url", default="http://localhost:5000/api/v1/query")

    select_parser = subparsers.add_parser("select", help="Select the next schedulable VPs")
    select_parser.add_argument("--slots", type=int, default=None)

    launch_parser = subparsers.add_parser("launch", help="Mark a selected VP as launched")
    launch_parser.add_argument("--vp-id", required=True)
    launch_parser.add_argument("--task-name", required=True)
    launch_parser.add_argument("--agent-id", default="")
    launch_parser.add_argument("--task-vdb-path", default="")
    launch_parser.add_argument("--isg-script", default="")

    complete_parser = subparsers.add_parser("complete", help="Merge a completed task VDB and refresh scoreboard")
    complete_parser.add_argument("--vp-id", required=True)
    complete_parser.add_argument("--task-name", required=True)
    complete_parser.add_argument("--task-vdb-path", required=True)
    complete_parser.add_argument("--isg-script", default="")
    complete_parser.add_argument("--http-api-url", default="http://localhost:5000/api/v1/query")
    complete_parser.add_argument("--urg-merge-attempts", type=int, default=3)
    complete_parser.add_argument("--urg-merge-retry-delay", type=float, default=1.0)

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
        result = initialize_scoreboard(
            args.output_dir,
            vp_list_path=args.vp_list,
            baseline_vdb_path=args.baseline_vdb,
            coverage_query=build_ucapi_fetcher(args.http_api_url),
            report_index_path=args.report_index,
            cov_report_dir=args.cov_report_dir,
            rtl_root=args.rtl_root,
            regression_root=args.regression_root,
        )
    elif args.command == "select":
        result = {"selected": select_next_vps(args.output_dir, slots=args.slots)}
    elif args.command == "launch":
        result = mark_vp_launched(
            args.output_dir,
            args.vp_id,
            task_name=args.task_name,
            agent_id=args.agent_id,
            task_vdb_path=args.task_vdb_path,
            isg_script=args.isg_script,
        )
    elif args.command == "complete":
        merge_runner = lambda task_vdb, previous_merged_vdb, output_vdb, baseline_vdb: merge_vdb_with_urg(
            task_vdb,
            previous_merged_vdb,
            output_vdb,
            baseline_vdb,
            max_attempts=args.urg_merge_attempts,
            retry_delay_seconds=args.urg_merge_retry_delay,
        )
        result = complete_vp_task(
            args.output_dir,
            args.vp_id,
            task_name=args.task_name,
            task_vdb_path=args.task_vdb_path,
            isg_script=args.isg_script,
            merge_runner=merge_runner,
            coverage_query=build_ucapi_fetcher(args.http_api_url),
        )
    elif args.command == "fail":
        result = record_vp_failure(args.output_dir, args.vp_id, task_name=args.task_name, error=args.error)
    else:
        result = recover_scoreboard(args.output_dir, requeue_stale=args.requeue_stale)

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
