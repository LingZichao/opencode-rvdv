---
name: fsdb-sampling
description: Use the bundled AgenticPipeViewer tool to generate APV YAML, sample FSDB waveforms, and extract runtime instruction evidence from trace_lifecycle reports.
compatibility: opencode
---

# FSDB Sampling

## What I Do

Use this skill when an agent needs runtime instruction data from FSDB waveforms, especially to trace one instruction through C910 pipeline signals.

The skill bundles AgenticPipeViewer (APV) under `AgenticPipeViewer/`. APV reads a YAML task graph, samples FSDB signals, follows task dependencies, and writes the native report `trace_lifecycle.txt`.

This skill is the source of truth for APV YAML authoring. Do not rely on older prompt-only APV fragment contracts when they conflict with this skill.

## Required Inputs

Do not guess these unless the user explicitly asks for discovery:

- `fsdbFile`: absolute or YAML-relative FSDB path.
- `globalClock`: clock signal path.
- `scope`: common RTL scope used to resolve local signal names.
- `output.directory`: report directory.
- Target instruction or event: PC, instruction bits, opcode class, RTL handoff, or coverage-driven signal objective.
- Identity anchors: prefer PC, then instruction bits, then packed data slices, then valid/vld as supporting evidence only.

## Workspace Defaults

- YAML path: `workspace/apvTraces/<task_name>/trace.yaml`
- APV output directory: `workspace/apvTraces/<task_name>/report`
- If no task name is given, create a short stable name from the target instruction or event.
- Never write generated APV YAML or reports inside `.opencode/skills/fsdb-sampling/AgenticPipeViewer/`.

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

## APV Mental Model

- APV evaluates all tasks under one `globalClock`.
- A task is one local observation point. Its `condition` lines are joined into one boolean expression for one candidate time point.
- Keep `&&` and `||` explicit when splitting a condition across multiple YAML lines.
- `capture` signals are sampled at the matched time point and persisted as that task's row data.
- `$dep.<task_id>.<signal>` reads a value captured by the dependency task at the dependency task's own matched time point. It does not re-sample that signal at the current candidate time.
- A task without `dependsOn` is a trigger task: APV scans the time axis directly for matches.
- A task with `dependsOn` is a trace task: for each upstream matched row, APV searches forward from that row's matched time. A dependent match may be in the same cycle as its dependency or later, never earlier.
- For instruction tracing, use exactly one upstream task in `dependsOn`. If logic appears to need multiple dependency sources, split the proof into smaller tasks instead of mixing `$dep` sources in one condition.
- Declare tasks in dependency order. A local task should only depend on an earlier task in the YAML.
- A task graph may be a tree. Multiple children may depend on the same parent when they represent different slots, lanes, pipes, selector outcomes, queues, crossbar routes, or FSM outcomes.
- `matchMode: first` keeps the first match per upstream row, `all` keeps every match in the search window, and `unique_per_var` keeps one match for each unique pattern-variable binding.
- `maxMatch` is a local per-upstream bound. Keep it tight when hardware fanout is known.

## Instruction Route Contract

- Start from the local route ingress, usually the current item's `boundary_takeover`, and end at the instruction-relevant `boundary_handoffs`.
- Build the smallest high-confidence event chain or branching tree that explains how the instruction enters this local item, is recognized or transformed, and exits or hands off.
- Prefer observation points that remove instruction-identity ambiguity over generic valid-bit snapshots.
- Preserve single-instruction identity across the chain whenever evidence allows. Prefer continuity anchors in this order: PC, instruction bits, packed data bus or bit slice, allocated IID/ROB/queue tag, then valid/vld only as a supporting gate.
- If local PC, instruction, data, IID, or tag anchors are visible, a valid-only relation cannot by itself prove the same instruction.
- Capture identity-carrying and handoff-carrying values that downstream tasks may need through `$dep`. Do not capture broad background state unless it directly helps debug a match.
- Every dependent task should include at least one same-line relation between an upstream captured value and a current local signal when such a relation is visible, for example `$dep.fetch.pc == ib_vpc` or `$dep.decode.inst[31:0] == pipe0_inst[31:0]`.
- Do not invent alias signals. Use only signals visible in the RTL/context or verified through source inspection. If a needed value is packed in a real bus, use the real bus slice or APV split syntax.
- Branch, buffer, out-of-order, crossbar, arbitration, and FSM ambiguity must be represented explicitly. Use sibling tasks or pattern variables for every plausible unresolved destination.
- Do not assume slot identity from source-path identity alone. A known bypass/ibuf/lbuf path does not prove `inst0`, `inst1`, `pipe0`, or `pipe1` unless local signals prove that mapping.
- Treat advisory route hints as comments, not proof. Encode path selection, gating, stall, cancel, and fanout discrimination in real `condition` logic.
- Add `globalFlush` when pipeline-wide flush or exception signals invalidate in-flight traces. Use mutually exclusive task conditions for local flush-like path splits.
- When evidence is incomplete, keep the YAML conservative and report exactly which identity relation, branch choice, or signal declaration could not be proven.

## Workflow

1. Read the relevant RTL/context first and choose the smallest task chain that proves the instruction route.
2. Create an APV YAML file in a task-owned workspace path, not inside the bundled APV source.
3. Start with one root trigger task, then add dependent trace tasks only when a later observation point carries stronger identity evidence.
4. For each task, capture the signals needed by downstream `$dep.<task>.<signal>` references and by human debugging.
5. For non-trivial graphs, run `--deps-only` before full FSDB analysis.
6. Run APV. Start with `--debug-num 1` when validating a new root trigger.
7. Read `<output.directory>/trace_lifecycle.txt`.
8. Report runtime instruction evidence from the native APV report: path count, task chain, time points, matched variables, captured PC/inst/data/IID/tag values, and any duplicate or missing matches.

## Authoring Rules

- Preserve single-instruction identity across the chain. A dependent task should tie current signals to upstream captures using `$dep`.
- Prefer conditions such as `$dep.fetch.pc == local_pc`, `$dep.decode.inst[31:0] == ir_inst[31:0]`, or IID equality after rename/ROB allocation.
- Valid-only conditions are acceptable as gates, but they are weak identity anchors. Do not present them as proof if PC, inst, data, or IID signals are available.
- Enumerate unresolved slot, pipe, way, queue, or buffer ambiguity with sibling tasks or `{idx}` pattern variables.
- Use `matchMode: first` for expected one-to-one progress, `all` for real fanout/repeated matches, and `unique_per_var` for lane or slot patterns.
- Keep `maxMatch` tight when a hardware fanout bound is known.
- Add `globalFlush` when pipeline-wide flush or exception signals would invalidate in-flight traces.
- If evidence is incomplete, make the YAML conservative and say what identity relation could not be proven.

## Completeness Standard

Call an APV trace complete only when every resolved instruction-relevant terminal path in the local route is represented by a terminal APV task that downstream tracing can continue from. Covering only the strongest main path is partial if sibling handoffs remain plausible.

Use explicit report language:

- `complete`: all resolved terminal paths are sampled, and each terminal path preserves instruction identity.
- `partial`: at least one required signal, identity relation, branch distinction, or terminal handoff remains unproven.
- `blocked`: required FSDB, clock, scope, or signal evidence is missing.

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

Before reporting, self-check:

- Every task has a unique stable `id`.
- Every dependent task uses one `dependsOn` source and every `$dep.<task_id>...` reference uses that same source.
- Every `$dep` signal was captured by the dependency task.
- Every condition line split preserves explicit boolean connectors.
- Every local signal name is real for the configured `scope`, or uses an explicit module path.
- Every terminal lane/slot/pipe/channel that remains plausible is either represented or called out as an unresolved gap.
