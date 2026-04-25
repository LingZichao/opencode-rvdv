---
name: gem5-prescreen
description: Run gem5 pre-screen simulations for compiled ISG scripts and download persisted m5out artifacts.
compatibility: opencode
---

## What I Do

Use this skill after `isg-compile` succeeds. It runs a compiled ISG ELF through the gem5 service and saves the returned artifacts.

This is a generator pre-screen only. It does not run RTL/VCS simulation and does not generate coverage VDB data.

## CLI Path Constraint

Run the CLI from this skill directory: `.opencode/skills/gem5-prescreen/`.

Use the bundled script path relative to this directory:

```bash
python3 scripts/gem5_prescreener.py run --script-path <script_path> --artifact-path <artifact_path> --maxinsts 500000
```

If you run from the repo root, prepend `.opencode/skills/gem5-prescreen/` to the script path.

## Commands

Run gem5 pre-screen:

```bash
python3 scripts/gem5_prescreener.py run --script-path <script_path> --artifact-path <artifact_path> [--maxinsts <n>]
```

## Parameters

- `script_path`: generator-chosen absolute input path. It may point directly to a compiled `.ELF`, or to a compiled ISG `.py` whose matching `<stem>.Default.ELF` or `<stem>.ELF` is in the same directory or `work_force/`.
- `artifact_path`: generator-chosen absolute output directory. The runner writes `output.log`, `manifest.json`, `m5out.tar.gz`, and extracted `m5out/` there.
- `maxinsts`: gem5 maximum instruction count. Default is `500000`.

## Path Rules

- This skill does not need `task_name` and does not infer task layout.
- Pass both paths explicitly, and both are required absolute paths.
- If `script_path` points to `.py`, make sure it is the compiled copy or colocated with its ELF. Passing the returned `elf_path` from `isg-compile` is the most direct option.

## Evidence Workflow

1. Run this only after `isg-compile` reports `status: success`.
2. Translate the test goal into expected observable evidence, such as committed instruction type, cache/branch stats, exception/log marker, or M5 exit behavior.
3. After `run`, treat `Status: completed` and `Exit Code: 0` as process results only, not proof of the ISG goal.
4. Use OpenCode's normal `grep` and `read` tools on the returned `output_log` and `m5out_extract_dir` paths to cite concrete files and metrics.
5. The conclusion must cite concrete files, lines, or metrics, for example `m5out/stats.txt` with `committedInstType_0::FloatDiv = 47`.
6. Clearly distinguish "gem5 process completed" from "the ISG functional target is supported by m5out evidence".
7. Common evidence:
   - Instruction type: `committedInstType_0::<OpClass>`
   - Branch prediction: `branchPred.committed_0` / `mispredicted_0`
   - Cache: `dcache.demandMisses` / `icache.demandMisses`
   - Exit mode: `output.log` with `Exiting @ tick`
   - General metrics: `simInsts`, `system.cpu.cpi`, `system.cpu.ipc`
8. Read `agentDoc/gem5_m5out_guide.md` when metric meanings or grep patterns are unclear.
9. If evidence is insufficient, revise the ISG script and repeat compile plus gem5 pre-screen.

## Failure Handling

- `No ELF file found`: compile the exact script with `isg-compile` first.
- `path must be absolute` or `path does not exist`: check `script_path`/`artifact_path`, or pass the compiled ELF path returned by `isg-compile`.
- `Error uploading ELF`: gem5 service is unreachable or `GEM5_SERVICE_URL` is wrong.
- `m5out Downloaded: no`: inspect `output.log` and the manifest; gem5 may have failed before artifacts were available.
