---
name: fsdb-sampling
description: Use the bundled AgenticPipeViewer tool to generate APV YAML, sample FSDB waveforms, and extract runtime instruction evidence from trace_lifecycle reports.
compatibility: opencode
---

# FSDB Sampling

## What I Do

Use this skill when an agent needs runtime instruction data from FSDB waveforms, especially to trace one instruction through C910 pipeline signals.

The skill bundles AgenticPipeViewer (APV) under `AgenticPipeViewer/`. APV reads a YAML task graph, samples FSDB signals, follows task dependencies, and writes the native report `trace_lifecycle.txt`.

## Required Inputs

Do not guess these unless the user explicitly asks for discovery:

- `fsdbFile`: absolute or YAML-relative FSDB path.
- `globalClock`: clock signal path.
- `scope`: common RTL scope used to resolve local signal names.
- `output.directory`: report directory.
- Target instruction or event: PC, instruction bits, opcode class, RTL handoff, or coverage-driven signal objective.
- Identity anchors: prefer PC, then instruction bits, then packed data slices, then valid/vld as supporting evidence only.

## Command

Run from the repo root:

```bash
python3 .opencode/skills/fsdb-sampling/AgenticPipeViewer/view.py -c <apv_yaml>
```

Debug with only the first N trigger matches:

```bash
python3 .opencode/skills/fsdb-sampling/AgenticPipeViewer/view.py -c <apv_yaml> --debug-num 1
```

Check only the dependency graph and config shape:

```bash
python3 .opencode/skills/fsdb-sampling/AgenticPipeViewer/view.py -c <apv_yaml> --deps-only
```

If working from inside the skill directory, use:

```bash
python3 AgenticPipeViewer/view.py -c <apv_yaml>
```

## Workflow

1. Read the relevant RTL/context first and choose the smallest task chain that proves the instruction route.
2. Create an APV YAML file in a task-owned workspace path, not inside the bundled APV source.
3. Start with one root trigger task, then add dependent trace tasks only when a later observation point carries stronger identity evidence.
4. For each task, capture the signals needed by downstream `$dep.<task>.<signal>` references and by human debugging.
5. Use `--deps-only` before full FSDB analysis for non-trivial task graphs.
6. Run APV, then read `<output.directory>/trace_lifecycle.txt`.
7. Report runtime instruction evidence from the native APV report: path count, task chain, time points, matched variables, captured PC/inst/data/IID, and any duplicate or missing matches.

## Authoring Rules

- Preserve single-instruction identity across the chain. A dependent task should tie current signals to upstream captures using `$dep`.
- Prefer conditions such as `$dep.fetch.pc == local_pc`, `$dep.decode.inst[31:0] == ir_inst[31:0]`, or IID equality after rename/ROB allocation.
- Valid-only conditions are acceptable as gates, but they are weak identity anchors. Do not present them as proof if PC, inst, data, or IID signals are available.
- Enumerate unresolved slot, pipe, way, queue, or buffer ambiguity with sibling tasks or `{idx}` pattern variables.
- Use `matchMode: first` for expected one-to-one progress, `all` for real fanout/repeated matches, and `unique_per_var` for lane or slot patterns.
- Keep `maxMatch` tight when a hardware fanout bound is known.
- Add `globalFlush` when pipeline-wide flush or exception signals would invalidate in-flight traces.
- If evidence is incomplete, make the YAML conservative and say what identity relation could not be proven.

## References

- Read `references/apv-yaml.md` for the APV YAML schema and condition syntax.
- Read `references/authoring-patterns.md` for instruction identity and branching patterns.
- Read `references/examples.md` for compact IFU/IDU/RTU-style examples.

## Output Contract

APV keeps its native outputs. The primary report is:

```text
<output.directory>/trace_lifecycle.txt
```

Do not create a second JSON result format unless the user explicitly asks for it.
