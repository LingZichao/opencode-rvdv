---
name: inst-sampling
description: Trace C910 instruction pipeline events in FSDB waveforms.
compatibility: opencode
---

# Inst Sampling

Trace instruction pipeline events in the C910 core's FSDB waveforms.

## Project Defaults

```python
FSDB = "/home/c910/lingzichao/openc910/smart_run/work_force/novas.fsdb"
CLOCK = "tb.clk"
SCOPE = "tb.x_soc.x_cpu_sub_system_axi.x_rv_integration_platform.x_cpu_top.x_ct_top_0.x_ct_core"
```

## Workspace

- Trace script: `workspace/instTraces/<task_name>/trace.py`
- Output: `workspace/instTraces/<task_name>/report/`

## API Reference

See the `wavekit` skill for full Pattern API, waveform operations, and viewer usage.

## Example

See [trace.py](trace.py) — traces 3 instruction slots through 11 pipeline stages (IFU → IDU decode → IR rename → ROB → AIQ0 → RF → IU → RTU commit → RTU retire) in ~10s.
