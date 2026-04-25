from __future__ import annotations

import asyncio
import hashlib
import json
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from src.utils.project_paths import get_scoreboard_root
from src.utils.scoreboard_scheduler import (
    CSV_FIELD_ALIASES,
    FLOAT_FIELDS,
    GROUP_ORDER,
    INT_FIELDS,
    KIND_ORDER,
    SCOREBOARD_FIELDS,
    get_scoreboard_paths,
    load_scoreboard,
    load_scoreboard_events,
)


TABLE_WINDOW_LIMIT = 200
MAX_TABLE_LIMIT = 1000
DEFAULT_POLL_INTERVAL_SECONDS = 1.0
BADGE_COLUMNS = {"kind", "vp_group", "running_state", "status"}
DISPLAY_FIELD_ORDER = [field for field in SCOREBOARD_FIELDS if field != "rtl_file"]
DISPLAY_KEY_BY_FIELD = {
    field: CSV_FIELD_ALIASES.get(field, field)
    for field in DISPLAY_FIELD_ORDER
}
INTERNAL_FIELD_BY_DISPLAY_KEY = {
    display_key: field for field, display_key in DISPLAY_KEY_BY_FIELD.items()
}
DISPLAY_FLOAT_FIELDS = {
    DISPLAY_KEY_BY_FIELD[field] for field in FLOAT_FIELDS if field in DISPLAY_KEY_BY_FIELD
}
DISPLAY_INT_FIELDS = {
    DISPLAY_KEY_BY_FIELD[field] for field in INT_FIELDS if field in DISPLAY_KEY_BY_FIELD
}
TABLE_COLUMNS = [
    {"key": "vp_id", "label": "VP ID", "numeric": False, "badge": False},
    {"key": "full_instance_name", "label": "Full Instance Name", "numeric": False, "badge": False},
    {"key": "kind", "label": "Kind", "numeric": False, "badge": True},
    {"key": "range", "label": "Range", "numeric": False, "badge": False},
    {"key": "vp_group", "label": "VP Group", "numeric": False, "badge": True},
    {"key": "baseline_line_pct", "label": "Baseline %", "numeric": True, "badge": False},
    {"key": "current_line_pct", "label": "Current %", "numeric": True, "badge": False},
    {"key": "exec_count", "label": "Exec Count", "numeric": True, "badge": False},
    {"key": "running_state", "label": "Running State", "numeric": False, "badge": True},
    {"key": "status", "label": "Status", "numeric": False, "badge": True},
    {"key": "improvement_count", "label": "Improvement Count", "numeric": True, "badge": False},
    {"key": "last_improved_by_task", "label": "Last Improved Task", "numeric": False, "badge": False},
    {"key": "last_improved_by_script", "label": "Last Improved Script", "numeric": False, "badge": False},
    {"key": "last_improved_delta_pct", "label": "Last Delta %", "numeric": True, "badge": False},
]
SORTABLE_COLUMNS = {column["key"] for column in TABLE_COLUMNS}
MODULE_ROOT = Path(__file__).resolve().parent
HTML_PATH = MODULE_ROOT / "static" / "scoreboard.html"
STATIC_DIR = MODULE_ROOT / "static"


@dataclass
class ScoreboardSnapshot:
    version: str
    summary: dict[str, Any]
    chart_points: list[dict[str, Any]]
    filter_options: dict[str, list[str]]
    rows: list[dict[str, Any]]
    columns: list[dict[str, Any]]


def _round_pct(value: float) -> float:
    return round(float(value) + 1e-9, 2)


def _status_is_blocked(status: str) -> bool:
    return str(status).startswith("blocked_")


def _make_version(signature: list[dict[str, Any]]) -> str:
    digest = hashlib.sha256(
        json.dumps(signature, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return digest[:16]


def _stat_signature(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False}
    stat = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
    }


def _preserve_order_unique(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for raw_value in values:
        value = str(raw_value)
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


def _display_row_from_internal(row: dict[str, Any], row_index: int) -> dict[str, Any]:
    display_row: dict[str, Any] = {"_index": row_index}
    searchable_parts: list[str] = []
    sort_values: dict[str, Any] = {}
    for field in DISPLAY_FIELD_ORDER:
        display_key = DISPLAY_KEY_BY_FIELD[field]
        value = row.get(field, "")
        display_row[display_key] = value
        searchable_parts.append(str(value))
        if display_key in DISPLAY_FLOAT_FIELDS:
            sort_values[display_key] = float(value or 0.0)
        elif display_key in DISPLAY_INT_FIELDS:
            sort_values[display_key] = int(value or 0)
        else:
            sort_values[display_key] = str(value).casefold()
    display_row["_search_blob"] = " ".join(searchable_parts).casefold()
    display_row["_sort_values"] = sort_values
    return display_row


class ScoreboardWebUIService:
    def __init__(
        self,
        scoreboard_root: str | Path | None = None,
        *,
        poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
        read_retry_attempts: int = 3,
        read_retry_delay_seconds: float = 0.05,
    ):
        default_root = Path(scoreboard_root).expanduser() if scoreboard_root is not None else get_scoreboard_root()
        self.scoreboard_root = default_root.resolve()
        self.paths = get_scoreboard_paths(self.scoreboard_root)
        self.poll_interval = max(0.05, float(poll_interval))
        self.read_retry_attempts = max(1, int(read_retry_attempts))
        self.read_retry_delay_seconds = max(0.0, float(read_retry_delay_seconds))
        self._lock = threading.Lock()
        self._cached_snapshot: ScoreboardSnapshot | None = None
        self._cached_signature: list[dict[str, Any]] | None = None

    def get_snapshot(self) -> ScoreboardSnapshot:
        signature = self._current_signature()
        with self._lock:
            if self._cached_snapshot is not None and signature == self._cached_signature:
                return self._cached_snapshot

        try:
            snapshot = self._load_snapshot_with_retry(signature)
        except Exception:
            with self._lock:
                if self._cached_snapshot is not None:
                    return self._cached_snapshot
            raise

        with self._lock:
            self._cached_snapshot = snapshot
            self._cached_signature = signature
        return snapshot

    def _current_signature(self) -> list[dict[str, Any]]:
        return [
            _stat_signature(self.paths.csv_path),
            _stat_signature(self.paths.state_path),
            _stat_signature(self.paths.events_path),
        ]

    def _load_snapshot_with_retry(self, signature: list[dict[str, Any]]) -> ScoreboardSnapshot:
        last_error: Exception | None = None
        for attempt in range(self.read_retry_attempts):
            try:
                rows, state = load_scoreboard(self.scoreboard_root)
                events = load_scoreboard_events(self.scoreboard_root)
                return self._build_snapshot(rows, state, events, signature)
            except Exception as exc:
                last_error = exc
                if attempt + 1 < self.read_retry_attempts and self.read_retry_delay_seconds > 0:
                    time.sleep(self.read_retry_delay_seconds)

        assert last_error is not None
        raise last_error

    def _build_snapshot(
        self,
        rows: list[dict[str, Any]],
        state: dict[str, Any],
        events: list[dict[str, Any]],
        signature: list[dict[str, Any]],
    ) -> ScoreboardSnapshot:
        display_rows = [_display_row_from_internal(row, row_index) for row_index, row in enumerate(rows)]
        summary = self._build_summary(rows, state)
        chart_points = self._build_chart_points(rows, state, events, summary)
        filter_options = self._build_filter_options(display_rows)
        return ScoreboardSnapshot(
            version=_make_version(signature),
            summary=summary,
            chart_points=chart_points,
            filter_options=filter_options,
            rows=display_rows,
            columns=list(TABLE_COLUMNS),
        )

    def _build_summary(self, rows: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
        active_kind = str(state.get("active_kind", "") or "")
        executable_rows = [row for row in rows if not _status_is_blocked(str(row.get("status", "")))]
        active_kind_rows = [row for row in executable_rows if str(row.get("kind", "")) == active_kind]

        def avg_pct(target_rows: list[dict[str, Any]]) -> float:
            if not target_rows:
                return 0.0
            return _round_pct(sum(float(row.get("current_line_pct", 0.0)) for row in target_rows) / len(target_rows))

        return {
            "scoreboard_root": str(self.scoreboard_root),
            "active_kind": active_kind,
            "overall_executable_pct": avg_pct(executable_rows),
            "active_kind_executable_pct": avg_pct(active_kind_rows),
            "total_vps": len(rows),
            "executable_vps": len(executable_rows),
            "blocked_vps": sum(1 for row in rows if _status_is_blocked(str(row.get("status", "")))),
            "pending_vps": sum(1 for row in rows if str(row.get("status", "")) == "pending"),
            "done_covered_vps": sum(1 for row in rows if str(row.get("status", "")) == "done_covered"),
            "inflight_vps": len(state.get("inflight", {})) if isinstance(state.get("inflight"), dict) else 0,
            "last_refresh_at": str(state.get("last_refresh_at", "") or ""),
            "last_merge_version": int(state.get("last_merge_version", 0) or 0),
            "parallelism": int(state.get("parallelism", 0) or 0),
        }

    def _build_chart_points(
        self,
        rows: list[dict[str, Any]],
        state: dict[str, Any],
        events: list[dict[str, Any]],
        summary: dict[str, Any],
    ) -> list[dict[str, Any]]:
        fallback = [
            {
                "merge_version": int(state.get("last_merge_version", 0) or 0),
                "timestamp": str(state.get("last_refresh_at", "") or ""),
                "overall_executable_pct": summary["overall_executable_pct"],
                "refreshed_vp_count": len(rows),
            }
        ]

        refresh_events = [event for event in events if str(event.get("event", "")) == "refresh" and event.get("vp_id")]
        if not refresh_events:
            return fallback

        refresh_events.sort(
            key=lambda event: (
                int(event.get("merge_version", 0) or 0),
                str(event.get("timestamp", "") or ""),
                str(event.get("vp_id", "") or ""),
            )
        )

        versions: dict[int, list[dict[str, Any]]] = {}
        for event in refresh_events:
            version = int(event.get("merge_version", 0) or 0)
            versions.setdefault(version, []).append(event)

        if len({str(event.get("vp_id", "")) for event in versions.get(0, [])}) != len(rows):
            return fallback

        by_vp: dict[str, dict[str, Any]] = {}
        chart_points: list[dict[str, Any]] = []
        for merge_version in sorted(versions):
            batch = versions[merge_version]
            for event in batch:
                vp_id = str(event.get("vp_id", ""))
                by_vp[vp_id] = {
                    "status": str(event.get("status", "") or ""),
                    "after_pct": float(event.get("after_pct", 0.0) or 0.0),
                }

            executable_pcts = [
                payload["after_pct"]
                for payload in by_vp.values()
                if not _status_is_blocked(payload["status"])
            ]
            overall_executable_pct = _round_pct(sum(executable_pcts) / len(executable_pcts)) if executable_pcts else 0.0
            chart_points.append(
                {
                    "merge_version": merge_version,
                    "timestamp": str(batch[-1].get("timestamp", "") or ""),
                    "overall_executable_pct": overall_executable_pct,
                    "refreshed_vp_count": len(batch),
                }
            )

        return chart_points or fallback

    def _build_filter_options(self, display_rows: list[dict[str, Any]]) -> dict[str, list[str]]:
        return {
            "kind": self._ordered_filter_values(display_rows, "kind", KIND_ORDER),
            "vp_group": self._ordered_filter_values(display_rows, "vp_group", GROUP_ORDER),
            "status": self._ordered_filter_values(display_rows, "status", ()),
            "running_state": self._ordered_filter_values(display_rows, "running_state", ()),
        }

    def _ordered_filter_values(
        self,
        rows: list[dict[str, Any]],
        key: str,
        preferred_order: Iterable[str],
    ) -> list[str]:
        seen = {str(row.get(key, "")) for row in rows if str(row.get(key, ""))}
        ordered = [value for value in preferred_order if value in seen]
        extras = sorted(seen - set(ordered))
        return ordered + extras

    def build_bootstrap_payload(self) -> dict[str, Any]:
        snapshot = self.get_snapshot()
        table_payload = self.query_table(snapshot=snapshot, offset=0, limit=TABLE_WINDOW_LIMIT)
        return {
            "snapshot_version": snapshot.version,
            "summary": snapshot.summary,
            "chart_points": snapshot.chart_points,
            "filter_options": snapshot.filter_options,
            "columns": snapshot.columns,
            "table": table_payload,
        }

    def query_table(
        self,
        *,
        snapshot: ScoreboardSnapshot | None = None,
        offset: int = 0,
        limit: int = TABLE_WINDOW_LIMIT,
        search: str = "",
        kind: str = "",
        vp_group: str = "",
        status: str = "",
        running_state: str = "",
        sort_by: str = "",
        sort_dir: str = "asc",
    ) -> dict[str, Any]:
        snapshot = snapshot or self.get_snapshot()
        filtered_rows = snapshot.rows
        normalized_search = search.strip().casefold()
        if normalized_search:
            filtered_rows = [row for row in filtered_rows if normalized_search in row["_search_blob"]]
        if kind:
            filtered_rows = [row for row in filtered_rows if str(row.get("kind", "")) == kind]
        if vp_group:
            filtered_rows = [row for row in filtered_rows if str(row.get("vp_group", "")) == vp_group]
        if status:
            filtered_rows = [row for row in filtered_rows if str(row.get("status", "")) == status]
        if running_state:
            filtered_rows = [row for row in filtered_rows if str(row.get("running_state", "")) == running_state]

        normalized_sort_by = sort_by if sort_by in SORTABLE_COLUMNS else ""
        normalized_sort_dir = "desc" if str(sort_dir).lower() == "desc" else "asc"
        if normalized_sort_by:
            filtered_rows = sorted(
                filtered_rows,
                key=lambda row: row["_sort_values"][normalized_sort_by],
                reverse=(normalized_sort_dir == "desc"),
            )

        safe_offset = max(0, int(offset))
        safe_limit = max(1, min(int(limit), MAX_TABLE_LIMIT))
        window = filtered_rows[safe_offset:safe_offset + safe_limit]
        public_rows = [self._public_row(row) for row in window]
        return {
            "snapshot_version": snapshot.version,
            "offset": safe_offset,
            "limit": safe_limit,
            "total": len(filtered_rows),
            "rows": public_rows,
            "sort_by": normalized_sort_by,
            "sort_dir": normalized_sort_dir,
        }

    def _public_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            column["key"]: row.get(column["key"], "")
            for column in TABLE_COLUMNS
        }

    async def stream_events(self, request: Request):
        last_version = ""
        keepalive_interval = max(self.poll_interval * 5.0, 5.0)
        last_keepalive_at = time.monotonic()

        while True:
            if await request.is_disconnected():
                break

            snapshot = self.get_snapshot()
            if snapshot.version != last_version:
                payload = json.dumps(
                    {
                        "snapshot_version": snapshot.version,
                        "summary": snapshot.summary,
                        "chart_points": snapshot.chart_points,
                    },
                    ensure_ascii=False,
                )
                yield f"event: snapshot\ndata: {payload}\n\n"
                last_version = snapshot.version
                last_keepalive_at = time.monotonic()
            else:
                now = time.monotonic()
                if now - last_keepalive_at >= keepalive_interval:
                    yield ": keep-alive\n\n"
                    last_keepalive_at = now

            await asyncio.sleep(self.poll_interval)


def create_scoreboard_webui_app(
    scoreboard_root: str | Path | None = None,
    *,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
    read_retry_attempts: int = 3,
    read_retry_delay_seconds: float = 0.05,
) -> FastAPI:
    service = ScoreboardWebUIService(
        scoreboard_root=scoreboard_root,
        poll_interval=poll_interval,
        read_retry_attempts=read_retry_attempts,
        read_retry_delay_seconds=read_retry_delay_seconds,
    )
    app = FastAPI(title="AgenticISG Scoreboard WebUI")
    app.state.scoreboard_service = service

    if STATIC_DIR.exists():
        app.mount("/scoreboard/static", StaticFiles(directory=STATIC_DIR), name="scoreboard_static")

    @app.get("/", include_in_schema=False)
    def index() -> RedirectResponse:
        return RedirectResponse(url="/scoreboard", status_code=307)

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/scoreboard", response_class=HTMLResponse)
    @app.get("/scoreboard/", response_class=HTMLResponse)
    def scoreboard_page() -> HTMLResponse:
        if not HTML_PATH.exists():
            raise HTTPException(status_code=500, detail=f"Missing scoreboard HTML asset: {HTML_PATH}")
        return HTMLResponse(HTML_PATH.read_text(encoding="utf-8"))

    @app.get("/scoreboard/api/bootstrap")
    def bootstrap() -> dict[str, Any]:
        try:
            return service.build_bootstrap_payload()
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Unable to load scoreboard snapshot: {exc}") from exc

    @app.get("/scoreboard/api/table")
    def table(
        offset: int = Query(0, ge=0),
        limit: int = Query(TABLE_WINDOW_LIMIT, ge=1, le=MAX_TABLE_LIMIT),
        search: str = "",
        kind: str = "",
        vp_group: str = "",
        status: str = "",
        running_state: str = "",
        sort_by: str = "",
        sort_dir: str = "asc",
    ) -> dict[str, Any]:
        try:
            return service.query_table(
                offset=offset,
                limit=limit,
                search=search,
                kind=kind,
                vp_group=vp_group,
                status=status,
                running_state=running_state,
                sort_by=sort_by,
                sort_dir=sort_dir,
            )
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Unable to query scoreboard table: {exc}") from exc

    @app.get("/scoreboard/api/stream")
    async def stream(request: Request) -> StreamingResponse:
        return StreamingResponse(
            service.stream_events(request),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    return app
