---
name: coverage
description: Query, list, generate, and manage coverage data through bundled Python CLIs and the skill-local coverageDB directory.
compatibility: opencode
---

## What I Do

Use this skill for all coverage-related work:

- Query BASELINE coverage.
- List available tests in an explicit VDB.
- Query coverage for a generated test.
- Run an ISG script through the workspace OpenC910 smart_run simulation flow to generate coverage data.

The simulation runner and UCAPI query client both use explicit workspace paths. Do not use `task_name` for new flows.

## Data Layout

- Skill coverage root: `.opencode/skills/coverage/coverageDB/`
- Baseline VDB: `.opencode/skills/coverage/coverageDB/template/BASELINE.vdb`
- OpenC910 workspace: `workspace/openc910/`, including `C910_RTL_FACTORY/` and `smart_run/`.
- Simulation template: `workspace/openc910/smart_run/`, including the migrated default `work_force/` simulator cache.
- Current simulation VDB: `workspace/openc910/smart_run/work_force/simv.vdb`
- Regression data: `.opencode/skills/coverage/coverageDB/regression/`

## Query Commands

Query BASELINE coverage:

```bash
python3 .opencode/skills/coverage/scripts/ucapi_client.py query-baseline --rtl-file <rtl_file> --start-line <start_line> --end-line <end_line> --kind <kind> --api-url <api_url>
```

List tests available in a generated VDB:

```bash
python3 .opencode/skills/coverage/scripts/ucapi_client.py list-tests --vdb-path <abs_workspace_simv.vdb>
```

If `--vdb-path` is omitted, the client uses `workspace/openc910/smart_run/work_force/simv.vdb`.

Query coverage for a generated test:

```bash
python3 .opencode/skills/coverage/scripts/ucapi_client.py query --rtl-file <rtl_file> --testname <test_name> --start-line <start_line> --end-line <end_line> --vdb-path <abs_workspace_simv.vdb> --kind <kind> --api-url <api_url>
```

If `--vdb-path` is omitted, the client uses `workspace/openc910/smart_run/work_force/simv.vdb`.

Use `http://localhost:5000/api/v1/query` as the default API URL unless the task explicitly provides another endpoint.

## Simulation Command

Generate or refresh coverage data from a workspace ISG script:

```bash
python3 .opencode/skills/coverage/scripts/simulation_runner.py --script-path <abs_workspace_script.py> --iter-count <iter_count>
```

Successful output includes `test_name`, `smart_run_root`, `work_force`, `vdb_path`, and `cov_report_path`. Use `cov_report_path` with `list-tests` and `query`.

The runner executes `make -f makefileFRV setup force_rv`, `make -f makefileFRV compile`, and `make -f makefileFRV run` directly inside `workspace/openc910/smart_run/`. It reuses the `work_force/` directory created by the makefile flow, with `CODE_BASE_PATH` defaulting to `workspace/openc910/C910_RTL_FACTORY`; it does not create per-run directories or copy VDBs.

## Workflow

1. For a new task, query BASELINE first with `line+cond+vp`.
2. Focus analysis on BASELINE-uncovered verification points and uncovered lines/conditions.
3. If current task coverage data is missing, run `simulation_runner.py` first and keep its returned `cov_report_path`.
4. For post-simulation analysis, call `list-tests --vdb-path <cov_report_path>` first, then query the selected test with `query --vdb-path <cov_report_path>`.
5. Report the command used, key uncovered points, and any returned error.

## Parameters

- `rtl_file`: RTL source filename, for example `ct_idu_ir_ctrl.v`.
- `start_line` / `end_line`: inclusive source line range from the task.
- `kind`: coverage kind. Prefer `line+cond+vp` for initial analysis.
- `script_path`: absolute path to the ISG `.py` script under `workspace/`.
- `vdb_path`: absolute path to a generated VDB under `workspace/`, normally `workspace/openc910/smart_run/work_force/simv.vdb`.
- `test_name`: test name returned by `list-tests`; do not guess it.
- `iter_count`: iteration number used in the generated simulation test name.

## Failure Handling

- `Cannot connect to coverage server`: UCAPI is not running or the URL is wrong.
- `BASELINE database not found`: baseline VDB is missing under this skill's `coverageDB/template/BASELINE.vdb`.
- `testname is REQUIRED`: call `list-tests` and retry with an actual returned test name.
- `--script-path must be an absolute path`: pass the full workspace script path.
- `Default VDB directory not found`: run the simulation command first or provide an explicit generated VDB path.
- `VDB directory not found`: confirm the `cov_report_path` returned by the simulation command.
