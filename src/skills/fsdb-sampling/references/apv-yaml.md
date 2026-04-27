# APV YAML Reference

This reference describes the YAML consumed directly by `AgenticPipeViewer/view.py`.

## Root Fields

```yaml
fsdbFile: /abs/path/to/novas.fsdb
globalClock: tb.clk
scope: tb.x_soc.x_cpu_sub_system_axi.x_rv_integration_platform.x_cpu_top.x_ct_top_0.x_ct_core

output:
  directory: workspace/apvReports/<task_name>
  verbose: true
  timeout: 10000000
  dependency_graph: deps.png

globalFlush:
  condition:
    - "rtu_yy_xx_flush == 1'b1"
    - "|| rtu_ifu_flush == 1'b1"

tasks:
  - id: root_task
    name: Root task label
    matchMode: first
    maxMatch: 1
    condition:
      - "some_valid == 1'b1"
    capture:
      - some_pc
    logging:
      - "[ROOT] pc={some_pc:x}"
```

`globalFlush` is optional. It terminates dependent searches that cross a flush boundary.

Required root fields:

- `fsdbFile`: FSDB waveform path. Relative paths resolve from the current run directory.
- `tasks`: non-empty list of APV tasks.

Defaulted root fields:

- `globalClock`: defaults to `clk`, but C910 tracing should set the real clock explicitly.
- `scope`: defaults to empty. Use the common RTL scope that resolves local signal names.
- `output.directory`: defaults to `temp_reports`.
- `output.verbose`: defaults to `false`. Use `true` for instruction evidence collection.
- `output.timeout`: defaults to `100`. Use a realistic pipeline search window.
- `output.dependency_graph`: defaults to `deps.png`.

## Task Fields

- `id`: unique task id. Use stable snake_case.
- `name`: human-readable label.
- `dependsOn`: upstream task id. Omit for root trigger tasks. For instruction tracing, use one upstream task per dependent task.
- `matchMode`: `first`, `all`, or `unique_per_var`.
- `maxMatch`: per-upstream match cap. `0` means unlimited.
- `condition`: list of expression lines joined with spaces. Keep `&&` and `||` explicit when splitting lines.
- `capture`: signals persisted at the matched time point. Any signal later referenced through `$dep.<task_id>.<signal>` must be captured here.
- `logging`: optional report line using captured signal names.
- `scope`: optional task-local scope override.

Task semantics:

- A task without `dependsOn` is a trigger task. APV scans the whole time axis and creates one trace row for each matched time.
- A task with `dependsOn` is a trace task. For each upstream row, APV searches forward from the upstream matched time until the task condition matches, timeout expires, or a `globalFlush` boundary is crossed.
- Local signal terms are evaluated at the current candidate time.
- `$dep` terms read persisted values from the upstream row. They are historical captures, not current-time re-samples.
- A dependent task can match in the same cycle as its dependency or later, never earlier.
- Declare tasks in dependency order for readability and safer review.

## Condition Syntax

- Signal: `sig`, `module.sig`, `sig[31:0]`.
- Pattern variable: `ifu_idu_ib_inst{idx}_vld`.
- Dependency: `$dep.task_id.signal_name`.
- Split packed data: `$dep.biu_read.biu_ifu_rd_data.$split(4)`.
- Containment: `inst_data[31:0] <@ $dep.biu_read.biu_ifu_rd_data.$split(4)`.
- Verilog literals: `1'b1`, `32'h00000013`, `8'd3`.
- Boolean operators: `&&`, `||`, `!`, comparison operators, and bitwise operators.

Condition authoring rules:

- Write one boolean predicate per task. Split long predicates across lines only for readability.
- If line 1 and line 2 are both required, include a connector such as trailing `&&` on line 1 or leading `&&` on line 2.
- Prefer same-line identity relations such as `$dep.fetch.pc == local_pc`, `$dep.id.inst[31:0] == local_inst[31:0]`, or `$dep.rename.iid == issue_iid`.
- Use valid/vld checks as gates around a stronger identity relation when stronger identity signals are visible.
- Avoid conditions that compare only valid bits, such as `$dep.prev.vld == local_vld`, unless no stronger anchor exists and the result is reported as partial.

## Pattern Variables

Pattern variables let one task cover a bounded family of lanes or slots:

```yaml
- id: idu_lane
  dependsOn: fetch_line
  matchMode: unique_per_var
  maxMatch: 3
  condition:
    - "ifu_idu_ib_inst{idx}_vld == 1'b1"
    - "&& ifu_idu_ib_inst{idx}_data[31:0] <@ $dep.fetch_line.biu_ifu_rd_data.$split(4)"
  capture:
    - ifu_idu_ib_inst{idx}_data
```

Use `unique_per_var` when each lane or slot value should match once. Use sibling tasks instead when each branch needs distinct non-pattern conditions.

## Match Modes

- `first`: keep the first later-or-same-cycle match for each upstream row. Use this for ordinary one-to-one pipeline progress.
- `all`: keep every match in the forward window. Use this for real broadcasts, repeated events, or exploratory debugging.
- `unique_per_var`: keep one match for each unique pattern-variable binding. Use this for lane, slot, or way patterns.

Set `maxMatch` whenever hardware fanout is known.

## Dependency Discipline

- For instruction tracing, a dependent task should reference only the task named by its `dependsOn`.
- Do not mix `$dep.fetch...` and `$dep.decode...` in one condition. Split the proof into separate tasks.
- Every `$dep.<task_id>.<signal>` reference must resolve to a signal captured by `<task_id>`.
- If multiple downstream paths share one ingress, declare one parent ingress task, then add sibling children that depend on that parent.
- Give every terminal sibling a unique `id` so `trace_lifecycle.txt` exports distinct paths.

## Legacy Prompt Term Map

Older APV fragment prompts used raw JSON terminology. In final APV YAML:

- `ref_name` maps to task `id`.
- `dep_name` maps to task `dependsOn`; omit `dependsOn` for root trigger tasks.
- `condition_lines` maps to `condition`.
- `capture_signals` maps to `capture`.
- `logging_lines` maps to `logging`.
- `anchors` are authoring reasoning, not a YAML field. Express identity anchors with real `condition` relations and captured signals.
- `behavior_hint`, `handoff_hint`, `status`, and `unknown` are report text, not APV YAML fields.

## Report

APV writes `trace_lifecycle.txt` in `output.directory`.

With `verbose: true`, each path includes captured signal values. Use that report as the runtime instruction evidence source.
