---
name: gem5-prescreen
description: Run local gem5 CLI pre-screen simulations for compiled ISG ELFs and inspect generated m5out artifacts.
compatibility: opencode
---

## What I Do

Use this skill after `isg-compile` produces a confirmed ELF.
The agent runs local gem5 directly from `<workspace>/gem5` with the bare-metal RISC-V config and inspects the generated m5out artifacts.

This is a generator pre-screen only. It does not run RTL/VCS simulation and does not generate coverage VDB data.

## Default Paths

- `gem5_root`: `<workspace>/gem5`
- `gem5_binary`: `<workspace>/gem5/build/RISCV/gem5.debug`
- `gem5_config`: `<workspace>/gem5/config/riscv/fs_bare_metal.py`
- `artifact_path`: an absolute output directory chosen by the generator for this gem5 run

If `gem5-flags.md` exists in the workspace or is provided in the task, read it before choosing debug flags.

## Command

Run exactly one local gem5 command with the working directory set to `gem5_root`:

```bash
./build/RISCV/gem5.debug --outdir=<artifact_path> --debug-flags=ExecAll,Faults --debug-file=trace.out config/riscv/fs_bare_metal.py --bare-metal-elf <elf_path> --mem-start=0x0
```

`--debug-flags` and `--debug-file` are gem5 options and must appear before `gem5_config`.
`--bare-metal-elf` and `--mem-start` are config options and must appear after `gem5_config`.

You may omit or change debug flags when the test goal calls for a smaller or more targeted trace. Use `ExecAll,Faults` as the normal first-pass choice for instruction-flow and exception evidence. Add other flags only when the test plan or `gem5-flags.md` justifies them.

This skill intentionally has no wrapper script or remote runner.

## Parameters

- `elf_path`: absolute path to the compiled `.ELF` from `isg-compile`. Required.
- `artifact_path`: absolute gem5 output directory. Required; pass it to `--outdir`.
- `debug_flags`: optional gem5 debug flags. Default first-pass value is `ExecAll,Faults`.
- `debug_file`: optional debug output filename. Default is `trace.out` when debug flags are enabled.
- `mem_start`: default `0x0` unless the task or config requires another value.

## Path Rules

- Use the OpenCode project workspace. Do not invent or read a separate workspace override environment variable.
- `gem5_root`, `gem5_binary`, `gem5_config`, `elf_path`, and `artifact_path` must be absolute paths when checking them.
- Run the command from `gem5_root`, but keep the command itself relative as shown above so gem5 resolves its tree-local files normally.
- Do not pass a `.py` ISG script to gem5. Resolve and pass the compiled ELF path.

## Evidence Workflow

1. Run this only after `isg-compile` has produced a confirmed ELF.
2. Translate the test goal into expected observable evidence, such as committed instruction type, exception/fault trace, branch behavior, memory behavior, or M5 exit behavior.
3. Run the local gem5 command above with `--outdir=<artifact_path>`.
4. Treat process exit code 0 as a process result only, not proof of the ISG goal.
5. Inspect files under `artifact_path`, especially `stats.txt`, `simout`, `simerr`, `config.ini`, and `trace.out` when debug flags were enabled.
6. The conclusion must cite concrete files, lines, or metrics, for example `stats.txt` with `simInsts = ...` or `trace.out` with a committed target instruction.
7. Clearly distinguish "gem5 process completed" from "the ISG functional target is supported by gem5 evidence".
8. If evidence is insufficient, revise the ISG script and repeat compile plus gem5 pre-screen.

## Common Evidence

- Instruction execution: `trace.out` with `ExecAll` records for target instructions.
- Fault/exception behavior: `trace.out` with `Faults` records and `simerr`.
- Exit mode: `simout` / `simerr` messages showing normal exit or failure.
- General metrics: `stats.txt` entries such as `simInsts`, `system.cpu.cpi`, and `system.cpu.ipc` when available.
- Configuration sanity: `config.ini` confirming the expected system, memory, and CPU setup.

## Failure Handling

- `gem5.debug` not found or not executable: confirm `gem5_binary` under `<workspace>/gem5/build/RISCV/`.
- `fs_bare_metal.py` not found: confirm `gem5_config` under `<workspace>/gem5/config/riscv/`.
- `--bare-metal-elf` path error: confirm `elf_path` is an absolute existing `.ELF`.
- Nonzero exit code: inspect `simout`, `simerr`, and terminal output for config errors, illegal instructions, faults, or early exits.
- Missing `stats.txt`: gem5 likely failed before stats dump; inspect `simerr`, `simout`, and `trace.out`.
- Oversized `trace.out`: rerun with narrower debug flags justified by `gem5-flags.md` or the test plan.
