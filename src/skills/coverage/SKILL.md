---
name: coverage
description: Query, list, generate, and manage coverage data through bundled Python CLIs and the skill-local coverageDB directory.
compatibility: opencode
---

## What I Do

Use this skill for all coverage-related work:

- Query BASELINE coverage.
- List available tests in a task VDB.
- Query coverage for a generated test.
- Run an ISG script through the simulation flow to generate or refresh coverage data.

All tools and coverage data live inside this skill package. Do not read VDB files directly and do not use repo-root `coverageDB` paths.

## Data Layout

- Skill coverage root: `.opencode/skills/coverage/coverageDB/`
- Baseline VDB: `.opencode/skills/coverage/coverageDB/template/BASELINE.vdb`
- Simulation template: `.opencode/skills/coverage/coverageDB/template/sim/`
- Task runtime data: `.opencode/skills/coverage/coverageDB/tasks/<task_name>/`
- Regression data: `.opencode/skills/coverage/coverageDB/regression/`

## Query Commands

Query BASELINE coverage:

```bash
python3 .opencode/skills/coverage/scripts/ucapi_client.py query-baseline --rtl-file <rtl_file> --start-line <start_line> --end-line <end_line> --kind <kind> --api-url <api_url>
```

List tests available in a task VDB:

```bash
python3 .opencode/skills/coverage/scripts/ucapi_client.py list-tests --task-name <task_name>
```

Query coverage for a generated test:

```bash
python3 .opencode/skills/coverage/scripts/ucapi_client.py query --rtl-file <rtl_file> --testname <test_name> --start-line <start_line> --end-line <end_line> --task-name <task_name> --kind <kind> --api-url <api_url>
```

Use `http://localhost:5000/api/v1/query` as the default API URL unless the task explicitly provides another endpoint.

## Fetch/Simulation Command

Generate or refresh task coverage data:

```bash
python3 .opencode/skills/coverage/scripts/simulation_runner.py --script-name <script_name> --iter-count <iter_count> --task-name <task_name>
```

Successful output includes `test_name` and `cov_report_path`. Use `test_name` with the query command above.

## Workflow

1. For a new task, query BASELINE first with `line+cond+vp`.
2. Focus analysis on BASELINE-uncovered verification points and uncovered lines/conditions.
3. For post-simulation analysis, call `list-tests` first, then query the selected test with `query`.
4. If current task coverage data is missing, run the fetch/simulation command and then query the returned test.
5. Report the command used, key uncovered points, and any returned error.

## Parameters

- `rtl_file`: RTL source filename, for example `ct_idu_ir_ctrl.v`.
- `start_line` / `end_line`: inclusive source line range from the task.
- `kind`: coverage kind. Prefer `line+cond+vp` for initial analysis.
- `task_name`: runtime task directory name under `.opencode/skills/coverage/coverageDB/tasks/<task_name>/`.
- `test_name`: test name returned by `list-tests`; do not guess it.
- `script_name`: ISG Python script under the generator-chosen task script path.
- `iter_count`: iteration number used in the generated test name.

## Failure Handling

- `Cannot connect to coverage server`: UCAPI is not running or the URL is wrong.
- `BASELINE database not found`: baseline VDB is missing under this skill's `coverageDB/template/BASELINE.vdb`.
- `testname is REQUIRED`: call `list-tests` and retry with an actual returned test name.
- `No .vdb found`: run the fetch/simulation command first or query BASELINE instead.
- `Simulation directory not found`: initialize the task simulation directory from the skill-local template.
- `Script not found`: ensure the script exists under the generator-chosen task script path.
