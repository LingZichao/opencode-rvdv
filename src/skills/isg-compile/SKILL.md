---
name: isg-compile
description: Compile FORCE-RISCV ISG scripts through the Python compiler CLI and guide the edit-compile repair loop.
compatibility: opencode
---

## What I Do

Use this skill after creating or editing an ISG Python script.
The compiler reads an explicit ISG Python script path and invokes FORCE-RISCV with the project C910 RV64 configuration.
On success it also ensures the matching ELF is available in the requested output directory so `gem5-prescreen` can run the exact compiled script.

## CLI Path Constraint

Run the CLI from this skill directory: `.opencode/skills/isg-compile/`.

Use the bundled script path relative to this directory:

```bash
python3 scripts/isg_compiler.py --script-path <script_path> --output-dir <output_dir>
```

If you run from the repo root, prepend `.opencode/skills/isg-compile/` to the script path.

## Command

```bash
python3 scripts/isg_compiler.py --script-path <script_path> --output-dir <output_dir>
```

## Parameters

- `script_path`: generator-chosen absolute path to the ISG `.py` script. This path is required.
- `output_dir`: generator-chosen absolute output directory. This path is required.

## Workspace and Path Rules

- Use the OpenCode project workspace. Do not invent or read a separate workspace override environment variable.
- Pass both `script_path` and `output_dir` explicitly in generator flow to avoid hidden coupling.
- `script_path` and `output_dir` must be absolute paths.

## Workflow

1. Create exactly one ISG script for the assigned plan under the generator-chosen task script path.
2. Choose and pass an explicit `output_dir` for this compile round.
3. Compile with the command above.
4. If compilation fails, inspect the JSON `output`, fix only that script, and compile again.
5. Stop when `status` is `success`; report the final script name and path.
6. Use the returned `elf_path` only as evidence that the compile artifact exists; do not run RTL/VCS simulation from the generator.

## Script Constraints

- Use standard FORCE-RISCV Python structure with `MainSequenceClass`, `GenThreadClass`, and `EnvClass`.
- Do not use C910 custom extension instructions; target RV64GC only.
- Keep the script atomic: one target, one scenario, one clear instruction stream strategy.
- Include the iteration number in the filename, for example `isg_branch_probe_iter_1.py`.
- Do not use Python `print()` for frontend logging.

## Failure Handling

- `FORCE-RISCV binary not found`: the local FORCE-RISCV installation or config path is missing.
- `Script not found`: confirm `--script-path` is an absolute path to an existing `.py`.
- Output path issue: confirm `--output-dir` is an absolute writable directory and not a file path.
- `Compilation timed out`: simplify the script or reduce generation complexity.
- Nonzero `exit_code`: use stderr/stdout in `output` to repair imports, instruction names, or API usage.
- Missing `elf_path` after success: inspect `output_dir` and FORCE-RISCV stdout; gem5 pre-screen needs a matching `<script_stem>.Default.ELF` or `<script_stem>.ELF`.
