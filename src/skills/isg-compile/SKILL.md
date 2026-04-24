---
name: isg-compile
description: Compile FORCE-RISCV ISG scripts through the Python compiler CLI and guide the edit-compile repair loop.
compatibility: opencode
---

## What I Do

Use this skill after creating or editing an ISG Python script.
The compiler reads scripts from `workspace/isgScripts/<task_name>/` and invokes FORCE-RISCV with the project C910 RV64 configuration.

## Command

```bash
python3 .opencode/skills/isg-compile/scripts/isg_compiler.py --script-name <script_name> --task-name <task_name>
```

## Parameters

- `script_name`: ISG Python script filename, with or without `.py`.
- `task_name`: task directory name used to locate `workspace/isgScripts/<task_name>/`.

## Workflow

1. Create exactly one ISG script for the assigned plan under `workspace/isgScripts/<task_name>/`.
2. Compile with the command above.
3. If compilation fails, inspect the JSON `output`, fix only that script, and compile again.
4. Stop when `status` is `success`; report the final script name and path.

## Script Constraints

- Use standard FORCE-RISCV Python structure with `MainSequenceClass`, `GenThreadClass`, and `EnvClass`.
- Do not use C910 custom extension instructions; target RV64GC only.
- Keep the script atomic: one target, one scenario, one clear instruction stream strategy.
- Include the iteration number in the filename, for example `isg_branch_probe_iter_1.py`.
- Do not use Python `print()` for frontend logging.

## Failure Handling

- `FORCE-RISCV binary not found`: the local FORCE-RISCV installation or config path is missing.
- `Script not found`: confirm the file is under `workspace/isgScripts/<task_name>/`.
- `Compilation timed out`: simplify the script or reduce generation complexity.
- Nonzero `exit_code`: use stderr/stdout in `output` to repair imports, instruction names, or API usage.
