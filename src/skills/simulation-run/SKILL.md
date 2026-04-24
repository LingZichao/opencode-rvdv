---
name: simulation-run
description: Run FORCE-RISCV generation and RTL simulation for a compiled ISG script through the Python simulation CLI.
compatibility: opencode
---

## What I Do

Use this skill when a compiled ISG script should be executed in the task simulation environment.
The runner copies the script to `AgenticTargetTest.py`, runs `make -f makefileFRV force_rv`, then runs `make -f makefileFRV run`.

## Command

```bash
python3 .opencode/skills/simulation-run/scripts/simulation_runner.py --script-name <script_name> --iter-count <iter_count> --task-name <task_name>
```

## Parameters

- `script_name`: script under `workspace/isgScripts/<task_name>/`.
- `iter_count`: current iteration number; it becomes part of the coverage test name.
- `task_name`: task directory under `.opencode/skills/coverage/coverageDB/tasks/`.

## Expected Output

Successful output is JSON containing the generated `test_name` and `cov_report_path`.
Use that `test_name` with the `coverage` skill to inspect coverage for the RTL range.

## Workflow

1. Run this only after `isg-compile` succeeds.
2. Keep the same `task_name` used for script generation and compilation.
3. On success, hand off to coverage querying with `line+cond+vp`.
4. On failure, report the failing step and stderr excerpt before modifying the script.

## Failure Handling

- `Simulation directory not found`: task setup is incomplete.
- `Script not found`: the script is not in the task ISG directory.
- `force_rv failed`: retry may be acceptable because random instruction generation can fail.
- `run failed`: treat as simulation or generated program failure; inspect stderr and revise the ISG script if needed.
