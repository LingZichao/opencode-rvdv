---
name: coverage
description: Query, list, generate, and manage coverage data through bundled Python CLIs and the skill-local coverageDB directory.
compatibility: opencode
---

## What I Do

Use this skill for all coverage-related work:

- List available tests in a simulation-generated VDB.
- Query coverage for a generated test.
- Run an ISG script through the professional verification environment (`columbus_verif/run.py`) to generate coverage data.

The UCAPI query client uses explicit workspace paths. Do not use `task_name` for new flows.

## Data Layout

- Columbus CPU Verification workspace: `<workspace>/columbus_verif/`, including  RTL source code folder `<workspace>/columbus_verif/local_rtl`.
- Verification runner: `<workspace>/columbus_verif/run.py` (use `-h` to inspect its detailed usage).
- Simulation output directory: `columbus_verif/build_vcs_core_top_<hash>/` created by `run.py`.
- Version info: `build_vcs_core_top_<hash>/version_info/`   ,files here distinguish simulation versions.
- Current simulation VDB: located inside `build_vcs_core_top_<hash>/`; exact path determined from `run.py` output.

## Query Commands

List available tests (output is long — save to file and inspect):

```bash
cd <workspace>/columbus_verif && python3 run.py list > task_list.txt && cat task_list.txt
```

Query coverage for a generated test:

```bash
python3 .opencode/skills/coverage/scripts/ucapi_client.py query --rtl-file <rtl_file> --testname <test_name> --start-line <start_line> --end-line <end_line> --vdb-path <abs_vdb_path> --kind <kind> --api-url <api_url>
```

Use `http://localhost:5000/api/v1/query` as the default API URL unless the task explicitly provides another endpoint.

## Simulation Command

Generate or refresh coverage data using the professional verification environment located at `<workspace>/columbus_verif/run.py`.

Before constructing the command, always check the available options:

```bash
cd <workspace>/columbus_verif && python3 run.py -h
```

Then run the simulation with the appropriate flags for the target ISG script and iteration count. The exact command depends on the `run.py` interface — use `-h` output to determine the correct arguments.

After a successful run, locate the generated VDB path from the command output or from `build_vcs_core_top_<hash>/` under `columbus_verif/`. Use that path with `query`.

## Workflow

1. If coverage data is missing, run `columbus_verif/run.py` (check `-h` for options) and note the `build_vcs_core_top_<hash>/` output directory.
2. Inspect `build_vcs_core_top_<hash>/version_info/` to confirm the correct simulation version.
3. Run `python3 run.py list > task_list.txt` inside `columbus_verif/` and read `task_list.txt` to select a test name.
4. Query the selected test with `ucapi_client.py query --vdb-path <vdb_path> --testname <test_name>`.
5. Report the command used, key uncovered points, and any returned error.

## Parameters

- `rtl_file`: RTL source filename, for example `ct_idu_ir_ctrl.v`.
- `start_line` / `end_line`: inclusive source line range from the task.
- `kind`: coverage kind. Prefer `line+cond+vp` for initial analysis.
- `vdb_path`: absolute path to the VDB returned by `columbus_verif/run.py` after simulation.
- `test_name`: test name from `run.py list` output; do not guess it.
- `iter_count`: iteration number used in the generated simulation test name.

## Failure Handling

- `Cannot connect to coverage server`: UCAPI is not running or the URL is wrong.
- `testname is REQUIRED`: run `run.py list > task_list.txt`, pick a name from the output, and retry.
- `VDB directory not found`: run `columbus_verif/run.py` first, then pass the explicit VDB path from the `build_vcs_core_top_<hash>/` output directory.
