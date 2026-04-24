---
name: coverage-fetch
description: Generate or refresh task coverage data by running the simulation Python CLI and returning the VDB path and test name for later coverage queries.
compatibility: opencode
---

## What I Do

Use this skill when a task needs a current coverage database after an ISG script has been generated.
The fetch operation is implemented by the simulation runner; it copies the ISG script into the task simulation directory, runs FORCE-RISCV generation, runs RTL simulation, and returns the VDB path.

## Command

```bash
python3 .opencode/skills/coverage-fetch/scripts/simulation_runner.py --script-name <script_name> --iter-count <iter_count> --task-name <task_name>
```

## Parameters

- `script_name`: ISG Python script filename located under `workspace/isgScripts/<task_name>/`.
- `iter_count`: iteration number used in the generated test name.
- `task_name`: runtime task directory name under `coverageDB/tasks/<task_name>/`.

## Expected Output

Successful output is JSON containing:

- `status: "success"`
- `test_name`: the test name to pass into `coverage-query`
- `iter_count`: the executed iteration
- `cov_report_path`: detected `simv.vdb` path

After success, use the `coverage-query` skill:

```bash
python3 .opencode/skills/coverage-query/scripts/ucapi_client.py list-tests --task-name <task_name>
python3 .opencode/skills/coverage-query/scripts/ucapi_client.py query --rtl-file <rtl_file> --testname <test_name> --start-line <start_line> --end-line <end_line> --task-name <task_name> --kind line+cond+vp --api-url http://localhost:5000/api/v1/query
```

## Failure Handling

- `Simulation directory not found`: task initialization did not create `coverageDB/tasks/<task_name>/sim`.
- `Script not found`: ensure the script exists under `workspace/isgScripts/<task_name>/`.
- `Make target 'force_rv' failed`: randomness can produce invalid streams; retry a small number of times before changing the script.
- `Make 'run' failed`: report the returned stderr and stop for diagnosis.
