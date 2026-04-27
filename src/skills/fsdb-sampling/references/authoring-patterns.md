# APV Authoring Patterns

## Route-First Workflow

Before writing YAML, identify the local instruction route:

- Ingress: where this local item takes over the instruction (`boundary_takeover` when available).
- Internal recognition or transformation point: decode, queue create, selector result, rename/ROB allocation, arbitration grant, or packed-data extraction.
- Egress: every instruction-relevant handoff (`boundary_handoffs` when available).

Use the smallest task chain that proves that route. Add a task only when it samples a distinct time point or removes real identity ambiguity. Do not split a chain just to repeat `valid == 1'b1` at adjacent stages.

## Identity Priority

Use the strongest available identity relation:

1. PC equality.
2. Instruction bits equality.
3. Packed data bus slice or split membership.
4. IID, ROB id, queue entry id, or rename tag after allocation.
5. Valid/vld only as a gate, not as primary identity proof.

Good dependent condition:

```yaml
condition:
  - "$dep.fetch_complete.pcgen_ifctrl_pc == ifdp_ipdp_vpc"
  - "&& ifctrl_ifdp_pipedown == 1'b1"
capture:
  - ifdp_ipdp_vpc
  - ifctrl_ifdp_pipedown
```

Weak condition:

```yaml
condition:
  - "$dep.fetch_complete.if_valid == if_valid"
```

Authoring implications:

- Capture the same identity signal that the next task must reference through `$dep`.
- If an upstream capture and local signal can be tied in the same condition, include that relation directly.
- If the route exposes PC, inst, data, IID, ROB id, queue id, or tag signals, a valid-only condition can support timing but cannot prove same-instruction identity.
- If a needed value is packed in a bus, use the real bus slice or `$split(N)`. Do not invent convenience aliases.
- For root trigger tasks, identity evidence is local-only. For dependent tasks, at least one condition term should tie a `$dep` value to a local signal when such a relation exists.

## Branching and Ambiguity

If one instruction may exit through several lanes, do not collapse the route unless local evidence proves the lane.

Pattern-variable style:

```yaml
- id: ifu_to_idu_lane
  dependsOn: fetch_line
  matchMode: unique_per_var
  maxMatch: 3
  condition:
    - "ifu_idu_ib_inst{idx}_vld == 1'b1"
    - "&& ifu_idu_ib_inst{idx}_data[31:0] <@ $dep.fetch_line.biu_ifu_rd_data.$split(4)"
  capture:
    - ifu_idu_ib_inst{idx}_data
  logging:
    - "[IFU_IDU] lane={idx} inst={ifu_idu_ib_inst{idx}_data:x}"
```

Sibling-task style:

```yaml
- id: pipe0_accept
  dependsOn: decode_entry
  matchMode: first
  condition:
    - "pipe0_vld == 1'b1"
    - "&& pipe0_inst[31:0] == $dep.decode_entry.inst[31:0]"
  capture: [pipe0_inst]

- id: pipe1_accept
  dependsOn: decode_entry
  matchMode: first
  condition:
    - "pipe1_vld == 1'b1"
    - "&& pipe1_inst[31:0] == $dep.decode_entry.inst[31:0]"
  capture: [pipe1_inst]
```

Branching rules:

- Use sibling tasks for mutually exclusive selector outcomes, channel choices, issue pipes, queue creates, crossbar routes, or FSM outcomes.
- Use pattern variables for regular lane/slot/way families where the same predicate shape applies.
- If several sibling exits remain plausible, represent every plausible sibling or report the route as partial.
- A known source family such as bypass, ibuf, or lbuf does not prove a final slot such as `inst0` or `inst1` unless local evidence maps it.
- Multiple children may depend on the same parent, but each child must distinguish its path in `condition`.
- Terminal siblings need unique `id` values so the lifecycle report exports separate paths.

## Match Mode Selection

- `first`: ordinary pipeline progress from one stage to the next.
- `all`: repeated events, broadcast, or multiple completions that must be inspected.
- `unique_per_var`: lane/slot/way pattern matching where each variable value should appear once.

Use `maxMatch` whenever the hardware bound is known.

## Local Dependency Discipline

- A task without `dependsOn` is a root trigger and must not reference `$dep`.
- A task with `dependsOn` should reference only that dependency in `$dep.<task_id>.<signal>` terms.
- Do not mix multiple dependency sources in one task. Split the proof into a parent relay task and one or more children.
- Declare the shared ingress or relay task before its sibling children.
- A dependent task may match in the same cycle as its dependency or later, never earlier.
- Every `$dep` signal must be captured by the referenced task.
- Prefer short stable task ids that show branch purpose, such as `pcgen_ifctrl_leaf`, `bypass_leaf`, or `pipe0_accept`.

## Completeness and Reporting

Use the following language when summarizing APV results:

- `complete`: all resolved instruction-relevant terminal paths are represented, and every terminal path keeps same-instruction identity through concrete captured values.
- `partial`: one or more required identity relations, terminal branches, path selectors, or signal declarations remain unproven.
- `blocked`: required FSDB, clock, scope, or local signal evidence is unavailable.

Examples:

- Good `pcgen` pattern: one ingress task fans out to `pcgen_ifctrl`, `pcgen_icache`, `pcgen_btb`, and `pcgen_bht` terminal tasks when all are real handoffs.
- Bad `pcgen` pattern: emitting only the visually strongest `ifctrl` leaf while other proven handoffs remain relevant.
- Bad `ibdp` pattern: `boundary_handoffs` exposes `inst0/inst1/inst2`, but YAML emits only `inst0` because the source path was bypass. Bypass selection alone does not prove slot identity.

## Failure Interpretation

- No root matches: trigger condition or FSDB/scope may be wrong.
- No dependent matches: identity relation may be too strict, timeout too short, or trace crossed `globalFlush`.
- Duplicate matches: condition is under-constrained or multiple upstream traces are aliasing the same row.

## Pre-run Self-check

- Each task has a unique stable `id`.
- Each dependent task has one `dependsOn` source.
- Every `$dep` reference uses that same dependency source.
- Every `$dep` signal was listed in the dependency task's `capture`.
- Every condition split keeps explicit `&&` or `||`.
- Every task captures the local signals needed by downstream tasks and human debugging.
- Every terminal lane/slot/pipe/channel that remains plausible is represented or reported as unresolved.
- `globalFlush` covers pipeline-wide flush/exception events that would invalidate in-flight traces.
