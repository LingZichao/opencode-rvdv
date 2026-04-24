---
name: coverage-query
description: Query BASELINE and task coverage through the UCAPI Python CLI, including test discovery and line/condition/branch/VP report lookups.
compatibility: opencode
---

## What I Do

Use this skill when a task needs coverage data for an RTL file and line range.
All coverage queries go through the Python CLI bundled with this skill; do not read VDB files or coverage report directories directly.

## Commands

Query BASELINE coverage:

```bash
python3 .opencode/skills/coverage-query/scripts/ucapi_client.py query-baseline --rtl-file <rtl_file> --start-line <start_line> --end-line <end_line> --kind <kind> --api-url <api_url>
```

List tests available in a task VDB:

```bash
python3 .opencode/skills/coverage-query/scripts/ucapi_client.py list-tests --task-name <task_name>
```

List tests from an explicit VDB path:

```bash
python3 .opencode/skills/coverage-query/scripts/ucapi_client.py list-tests --task-name <task_name> --vdb-path <vdb_path>
```

Query coverage for a generated test:

```bash
python3 .opencode/skills/coverage-query/scripts/ucapi_client.py query --rtl-file <rtl_file> --testname <test_name> --start-line <start_line> --end-line <end_line> --task-name <task_name> --kind <kind> --api-url <api_url>
```

Use `http://localhost:5000/api/v1/query` as the default API URL unless the task explicitly provides another endpoint.

## Parameters

- `rtl_file`: RTL source filename, for example `ct_idu_ir_ctrl.v`.
- `start_line` / `end_line`: inclusive source line range from the task.
- `kind`: coverage kind. Prefer `line+cond+vp` for initial analysis. Use `branch` only when branch-specific detail is needed.
- `task_name`: runtime task directory name under `coverageDB/tasks/<task_name>/`.
- `test_name`: test name returned by `list-tests`; do not guess it.

## Workflow

1. For a new task, query BASELINE first with `line+cond+vp`.
2. Focus analysis on BASELINE-uncovered verification points and uncovered lines/conditions.
3. For post-simulation analysis, call `list-tests` first, then query the selected test with `query`.
4. Report the queried command, the key uncovered points, and any error returned by the CLI.

## Failure Handling

- `Cannot connect to coverage server`: UCAPI is not running or the URL is wrong. Report this directly.
- `BASELINE database not found`: baseline VDB is missing under `coverageDB/template/BASELINE.vdb`.
- `testname is REQUIRED`: call `list-tests` and retry with an actual returned test name.
- `No .vdb found`: run simulation first or query BASELINE instead.
