---
name: isg-compile
description: Compile FORCE-RISCV ISG scripts through the Columbus forcerv_test_compile.py command and guide the edit-compile repair loop.
compatibility: opencode
---

## What I Do

Use this skill after creating or editing an ISG Python script.
The agent invokes the Columbus FORCE-RISCV compile frontend from a chosen output directory, using an explicit ISG script path and the design-local FORCE-RISCV reference tree.

## Default Paths

- `<compile_script>`: `<workspace>/columbus_verif/test_factory/platform/vcs/run_sim/forcerv/forcerv_test_compile.py`
- `<force_riscv_root>`: 
Contains `bin/friscv`, `configs`, and ISG source code.
`<workspace>/columbus_verif/env/simbase/testbench/reference/force-riscv`
- `<config_file>`:
System, Instruction definintion or Microarchitechture configuration `<force_riscv_root>/config/riscv_rv64.config`

## Compile Command

Run exactly one Columbus compile command with the working directory set to `<output_dir>`:

```bash
python3 <compile_script> <compile_script_args>
```

Use the native arguments required by `forcerv_test_compile.py` for the ISG script path, output location, and FORCE-RISCV reference root. If the native argument names are unknown, inspect the script help or source first, then run the single compile command. Do not invoke `friscv` directly for the default Columbus flow.

## Parameters

- `script_path`: absolute path to the ISG `.py` script. Required.
- `output_dir`: absolute compile working directory. Required; create it before running the command.
- `compile_script`: absolute path to `forcerv_test_compile.py`. Use the default path above unless the task provides a different design workspace.
- `force_riscv_root`: absolute path to the design-local FORCE-RISCV reference tree. Use the default path above unless the task provides another source tree.

## Workspace and Path Rules

- Use the OpenCode project workspace. Do not invent or read a separate workspace override environment variable.
- Pass `script_path`, `output_dir`, `compile_script`, and `force_riscv_root` explicitly in generator flow to avoid hidden coupling.
- `script_path`, `output_dir`, `compile_script`, and `force_riscv_root` must be absolute paths when invoking the command.
- Do not hard-code C910 config paths when the task targets another design or provides another FORCE-RISCV reference tree.

## Workflow

1. Create exactly one ISG script for the assigned plan under the generator-chosen task script path.
2. Choose an explicit absolute `output_dir` for this compile round and create it if needed.
3. Resolve `compile_script` and `force_riscv_root`; use design-specific paths from the task when present.
4. Run the Columbus compile command above from `output_dir`.
5. If compilation fails, inspect stdout/stderr, fix only that script, and compile again.
6. Stop when the command exits with code 0 and a matching ELF exists.
7. Report the final script path, output directory, command used, and ELF path. Do not run RTL/VCS simulation from the generator.

## ELF Detection

After a successful compile, look in `output_dir` first for:

- `<script_stem>.Default.ELF`
- `<script_stem>.ELF`

If neither exists, inspect `output_dir/work_force/` and the FORCE-RISCV stdout/stderr. Pass the confirmed ELF path to `gem5-prescreen`.

## Script Constraints

- Keep the script atomic: one target, one scenario, one clear instruction stream strategy.
- Include the iteration number in the filename, for example `isg_branch_probe_iter_1.py`.
- Do not use Python `print()` for frontend logging.

## Failure Handling

- FORCE-RISCV reference path issue: confirm `force_riscv_root` exists and contains the expected `bin/`, testbench, config, and YAML content.
- Output path issue: confirm `output_dir` is an absolute writable directory and not a file path.
- Nonzero exit code: use stderr/stdout to repair imports, instruction names, or API usage.
- Missing ELF after success: inspect `output_dir`, `output_dir/work_force/`, and FORCE-RISCV stdout; next stage needs a matching `<script_stem>.Default.ELF` or `<script_stem>.ELF`.
