from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles


TABLE_WINDOW_LIMIT = 200
MAX_TABLE_LIMIT = 1000
POLL_INTERVAL_SECONDS = 1.0

FLOAT_FIELDS = {"baseline_line_pct", "current_line_pct", "last_improved_delta_pct"}
INT_FIELDS = {"exec_count", "improvement_count"}

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
SORTABLE_COLUMNS = {col["key"] for col in TABLE_COLUMNS}


class ScoreboardStore:
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.csv_path = data_dir / "scoreboard.csv"
        self.state_path = data_dir / "scoreboard_state.json"
        self.events_path = data_dir / "scoreboard_events.jsonl"

    def _signature(self) -> list[dict[str, Any]]:
        def stat_of(path: Path) -> dict[str, Any]:
            if not path.exists():
                return {"path": str(path), "exists": False}
            st = path.stat()
            return {"path": str(path), "exists": True, "size": st.st_size, "mtime_ns": st.st_mtime_ns}

        return [stat_of(self.csv_path), stat_of(self.state_path), stat_of(self.events_path)]

    def _version(self, signature: list[dict[str, Any]]) -> str:
        payload = json.dumps(signature, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()[:16]

    def _load_rows(self) -> list[dict[str, Any]]:
        if not self.csv_path.exists():
            raise FileNotFoundError(f"Missing scoreboard.csv: {self.csv_path}")

        rows: list[dict[str, Any]] = []
        with self.csv_path.open("r", encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            for row in reader:
                out: dict[str, Any] = {}
                for col in TABLE_COLUMNS:
                    key = col["key"]
                    val = row.get(key, "")
                    if key in FLOAT_FIELDS:
                        out[key] = float(val or 0.0)
                    elif key in INT_FIELDS:
                        out[key] = int(float(val or 0))
                    else:
                        out[key] = str(val or "")
                blob = " ".join(str(out.get(col["key"], "")) for col in TABLE_COLUMNS).casefold()
                out["_search_blob"] = blob
                rows.append(out)
        return rows

    def _load_state(self) -> dict[str, Any]:
        if not self.state_path.exists():
            return {}
        return json.loads(self.state_path.read_text(encoding="utf-8"))

    def _load_events(self) -> list[dict[str, Any]]:
        if not self.events_path.exists():
            return []
        items: list[dict[str, Any]] = []
        with self.events_path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    items.append(json.loads(line))
        return items

    @staticmethod
    def _is_blocked(status: str) -> bool:
        return str(status).startswith("blocked_")

    def _summary(self, rows: list[dict[str, Any]], state: dict[str, Any]) -> dict[str, Any]:
        active_kind = str(state.get("active_kind", "") or "")
        exec_rows = [r for r in rows if not self._is_blocked(str(r.get("status", "")))]
        kind_rows = [r for r in exec_rows if str(r.get("kind", "")) == active_kind]

        def avg_pct(items: list[dict[str, Any]]) -> float:
            if not items:
                return 0.0
            return round(sum(float(r.get("current_line_pct", 0.0)) for r in items) / len(items) + 1e-9, 2)

        inflight = state.get("inflight", {})
        inflight_count = len(inflight) if isinstance(inflight, dict) else 0

        return {
            "scoreboard_root": str(self.data_dir),
            "active_kind": active_kind,
            "overall_executable_pct": avg_pct(exec_rows),
            "active_kind_executable_pct": avg_pct(kind_rows),
            "total_vps": len(rows),
            "executable_vps": len(exec_rows),
            "blocked_vps": sum(1 for r in rows if self._is_blocked(str(r.get("status", "")))),
            "pending_vps": sum(1 for r in rows if str(r.get("status", "")) == "pending"),
            "done_covered_vps": sum(1 for r in rows if str(r.get("status", "")) == "done_covered"),
            "inflight_vps": inflight_count,
            "last_refresh_at": str(state.get("last_refresh_at", "") or ""),
            "last_merge_version": int(state.get("last_merge_version", 0) or 0),
            "parallelism": int(state.get("parallelism", 0) or 0),
        }

    def _chart_points(self, rows: list[dict[str, Any]], state: dict[str, Any], events: list[dict[str, Any]], summary: dict[str, Any]) -> list[dict[str, Any]]:
        fallback = [
            {
                "merge_version": int(state.get("last_merge_version", 0) or 0),
                "timestamp": str(state.get("last_refresh_at", "") or ""),
                "overall_executable_pct": summary["overall_executable_pct"],
                "refreshed_vp_count": len(rows),
            }
        ]

        refresh_events = [e for e in events if str(e.get("event", "")) == "refresh" and e.get("vp_id")]
        if not refresh_events:
            return fallback

        refresh_events.sort(key=lambda e: (int(e.get("merge_version", 0) or 0), str(e.get("timestamp", "")), str(e.get("vp_id", ""))))
        by_version: dict[int, list[dict[str, Any]]] = defaultdict(list)
        for event in refresh_events:
            by_version[int(event.get("merge_version", 0) or 0)].append(event)

        by_vp: dict[str, dict[str, Any]] = {}
        points: list[dict[str, Any]] = []
        for version in sorted(by_version):
            batch = by_version[version]
            for event in batch:
                vp_id = str(event.get("vp_id", ""))
                by_vp[vp_id] = {
                    "status": str(event.get("status", "") or ""),
                    "after_pct": float(event.get("after_pct", 0.0) or 0.0),
                }

            pcts = [v["after_pct"] for v in by_vp.values() if not self._is_blocked(v["status"])]
            overall = round(sum(pcts) / len(pcts) + 1e-9, 2) if pcts else 0.0
            points.append(
                {
                    "merge_version": version,
                    "timestamp": str(batch[-1].get("timestamp", "") or ""),
                    "overall_executable_pct": overall,
                    "refreshed_vp_count": len(batch),
                }
            )

        return points or fallback

    def _filter_options(self, rows: list[dict[str, Any]]) -> dict[str, list[str]]:
        def ordered(field: str, pref: list[str]) -> list[str]:
            seen = {str(r.get(field, "")) for r in rows if str(r.get(field, ""))}
            out = [x for x in pref if x in seen]
            out.extend(sorted(seen - set(out)))
            return out

        return {
            "kind": ordered("kind", ["branch", "cond", "line"]),
            "vp_group": ordered("vp_group", ["ifu", "idu", "iu", "rtu", "others"]),
            "status": ordered("status", []),
            "running_state": ordered("running_state", []),
        }

    def snapshot(self) -> dict[str, Any]:
        signature = self._signature()
        rows = self._load_rows()
        state = self._load_state()
        events = self._load_events()

        summary = self._summary(rows, state)
        chart_points = self._chart_points(rows, state, events, summary)
        return {
            "snapshot_version": self._version(signature),
            "summary": summary,
            "chart_points": chart_points,
            "filter_options": self._filter_options(rows),
            "columns": TABLE_COLUMNS,
            "rows": rows,
            "signature": signature,
        }


def _sort_value(row: dict[str, Any], key: str) -> Any:
    value = row.get(key, "")
    if key in FLOAT_FIELDS:
        return float(value or 0.0)
    if key in INT_FIELDS:
        return int(value or 0)
    return str(value).casefold()


def build_app(data_dir: Path, static_dir: Path) -> FastAPI:
    store = ScoreboardStore(data_dir)
    html_path = static_dir / "scoreboard.html"

    app = FastAPI(title="Standalone Scoreboard WebUI")
    app.mount("/scoreboard/static", StaticFiles(directory=static_dir), name="scoreboard_static")

    @app.get("/", include_in_schema=False)
    def root() -> RedirectResponse:
        return RedirectResponse(url="/scoreboard", status_code=307)

    @app.get("/favicon.ico", include_in_schema=False)
    def favicon() -> Response:
        return Response(status_code=204)

    @app.get("/scoreboard", response_class=HTMLResponse)
    @app.get("/scoreboard/", response_class=HTMLResponse)
    def page() -> HTMLResponse:
        if not html_path.exists():
            raise HTTPException(status_code=500, detail=f"Missing scoreboard HTML: {html_path}")
        return HTMLResponse(html_path.read_text(encoding="utf-8"))

    @app.get("/scoreboard/api/bootstrap")
    def bootstrap() -> dict[str, Any]:
        snap = store.snapshot()
        table = table_query(snap, 0, TABLE_WINDOW_LIMIT, "", "", "", "", "", "", "asc")
        return {
            "snapshot_version": snap["snapshot_version"],
            "summary": snap["summary"],
            "chart_points": snap["chart_points"],
            "filter_options": snap["filter_options"],
            "columns": snap["columns"],
            "table": table,
        }

    def table_query(
        snap: dict[str, Any],
        offset: int,
        limit: int,
        search: str,
        kind: str,
        vp_group: str,
        status: str,
        running_state: str,
        sort_by: str,
        sort_dir: str,
    ) -> dict[str, Any]:
        rows = snap["rows"]
        q = search.strip().casefold()
        if q:
            rows = [r for r in rows if q in r.get("_search_blob", "")]
        if kind:
            rows = [r for r in rows if str(r.get("kind", "")) == kind]
        if vp_group:
            rows = [r for r in rows if str(r.get("vp_group", "")) == vp_group]
        if status:
            rows = [r for r in rows if str(r.get("status", "")) == status]
        if running_state:
            rows = [r for r in rows if str(r.get("running_state", "")) == running_state]

        if sort_by in SORTABLE_COLUMNS:
            rows = sorted(rows, key=lambda r: _sort_value(r, sort_by), reverse=(sort_dir.lower() == "desc"))

        safe_offset = max(0, int(offset))
        safe_limit = max(1, min(int(limit), MAX_TABLE_LIMIT))
        window = rows[safe_offset:safe_offset + safe_limit]

        public_rows = []
        for row in window:
            public_rows.append({col["key"]: row.get(col["key"], "") for col in TABLE_COLUMNS})

        return {
            "snapshot_version": snap["snapshot_version"],
            "offset": safe_offset,
            "limit": safe_limit,
            "total": len(rows),
            "rows": public_rows,
            "sort_by": sort_by if sort_by in SORTABLE_COLUMNS else "",
            "sort_dir": "desc" if sort_dir.lower() == "desc" else "asc",
        }

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
        snap = store.snapshot()
        return table_query(snap, offset, limit, search, kind, vp_group, status, running_state, sort_by, sort_dir)

    @app.get("/scoreboard/api/stream")
    async def stream(request: Request) -> StreamingResponse:
        async def gen():
            last_version = ""
            while True:
                if await request.is_disconnected():
                    break
                snap = store.snapshot()
                version = snap["snapshot_version"]
                if version != last_version:
                    payload = {
                        "snapshot_version": version,
                        "summary": snap["summary"],
                        "chart_points": snap["chart_points"],
                    }
                    yield f"event: snapshot\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
                    last_version = version
                else:
                    yield ": keep-alive\n\n"
                await asyncio.sleep(POLL_INTERVAL_SECONDS)

        return StreamingResponse(
            gen(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
        )

    return app


def main() -> None:
    import argparse
    import uvicorn

    module_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Standalone scoreboard web UI")
    parser.add_argument("--data-dir", type=str, default=str(module_root / "data"))
    parser.add_argument("--host", type=str, default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8011)
    args = parser.parse_args()

    app = build_app(Path(args.data_dir).expanduser().resolve(), module_root / "static")
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
