# APV YAML Reference

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
    condition:
      - "some_valid == 1'b1"
    capture:
      - some_pc
```

`globalFlush` is optional. It terminates dependent searches that cross a flush boundary.

## Task Fields

- `id`: unique task id. Use stable snake_case.
- `name`: human-readable label.
- `dependsOn`: upstream task id. Omit for root trigger tasks.
- `matchMode`: `first`, `all`, or `unique_per_var`.
- `maxMatch`: per-upstream match cap. `0` means unlimited.
- `condition`: list of expression lines joined with spaces. Keep `&&` and `||` explicit when splitting lines.
- `capture`: signals persisted at the matched time point.
- `logging`: optional report line using captured signal names.

## Condition Syntax

- Signal: `sig`, `module.sig`, `sig[31:0]`.
- Pattern variable: `ifu_idu_ib_inst{idx}_vld`.
- Dependency: `$dep.task_id.signal_name`.
- Split packed data: `$dep.biu_read.biu_ifu_rd_data.$split(4)`.
- Containment: `inst_data[31:0] <@ $dep.biu_read.biu_ifu_rd_data.$split(4)`.
- Verilog literals: `1'b1`, `32'h00000013`, `8'd3`.
- Boolean operators: `&&`, `||`, `!`, comparison operators, and bitwise operators.

## Report

APV writes `trace_lifecycle.txt` in `output.directory`.

With `verbose: true`, each path includes captured signal values. Use that report as the runtime instruction evidence source.
