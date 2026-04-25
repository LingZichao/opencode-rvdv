---
name: isg-compile
description: Compile FORCE-RISCV ISG scripts through the Python compiler CLI and guide the edit-compile repair loop.
compatibility: opencode
---

## What I Do

Use this skill after creating or editing an ISG Python script.
The compiler reads scripts from `<workspace>/isgScripts/<task_name>/` and invokes FORCE-RISCV with the project C910 RV64 configuration.
On success it also ensures the matching ELF is available in the task simulation directory so `gem5-prescreen` can run the exact compiled script.

## CLI Path Constraint

Run the CLI from this skill directory: `.opencode/skills/isg-compile/`.

Use the bundled script path relative to this directory:

```bash
python3 scripts/isg_compiler.py --script-name <script_name> --task-name <task_name>
```

If you run from the repo root, prepend `.opencode/skills/isg-compile/` to the script path.

## Command

```bash
python3 scripts/isg_compiler.py --script-name <script_name> --task-name <task_name>
```

## Parameters

- `script_name`: ISG Python script filename, with or without `.py`.
- `task_name`: generator-chosen task directory name used to locate `<workspace>/isgScripts/<task_name>/`. It must be a single path component using only ASCII letters, digits, `_`, and `-`; do not include `/`, spaces, `.`, or `..`.

## Workspace and Task Name Rules

- Use the OpenCode project workspace. Do not invent or read a separate workspace override environment variable.
- If the coordinator/user did not provide a task name, the generator must create one before writing files. Use a short stable slug derived from the target or plan, for example `idu_branch_probe_iter_1`.
- Reuse the exact same `task_name` for script creation and `isg-compile`. `gem5-prescreen` uses explicit paths instead of `task_name`.
- Create the script under the path chosen by the generator for this task, and make sure `isg-compile` can locate it with the provided `task_name` and `script_name`.

## Workflow

1. Create exactly one ISG script for the assigned plan under the generator-chosen task script path.
2. Compile with the command above.
3. If compilation fails, inspect the JSON `output`, fix only that script, and compile again.
4. Stop when `status` is `success`; report the final script name and path.
5. Use the returned `elf_path` only as evidence that the compile artifact exists; do not run RTL/VCS simulation from the generator.

## Script Constraints

- Use standard FORCE-RISCV Python structure with `MainSequenceClass`, `GenThreadClass`, and `EnvClass`.
- Do not use C910 custom extension instructions; target RV64GC only.
- Keep the script atomic: one target, one scenario, one clear instruction stream strategy.
- Include the iteration number in the filename, for example `isg_branch_probe_iter_1.py`.
- Do not use Python `print()` for frontend logging.

## Failure Handling

- `FORCE-RISCV binary not found`: the local FORCE-RISCV installation or config path is missing.
- `Script not found`: confirm the file path matches the generator-chosen task script path and the `--script-name` passed to this skill.
- `Compilation timed out`: simplify the script or reduce generation complexity.
- Nonzero `exit_code`: use stderr/stdout in `output` to repair imports, instruction names, or API usage.
- Missing `elf_path` after success: inspect the task sim directory and FORCE-RISCV stdout; gem5 pre-screen needs a matching `<script_stem>.Default.ELF` or `<script_stem>.ELF`.
