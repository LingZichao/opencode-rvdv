---
name: inst-sampling
description: Trace C910 instruction pipeline events in FSDB waveforms.
compatibility: opencode
---

# Inst Sampling

Build task-specific wave sampling scripts that trace instruction events through the C910 pipeline using wavekit's `Pattern` engine.

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

## Reference Script

[trace.py](trace.py) is a complete 11-stage lifecycle trace — use it as a skeleton, not a template to copy. Each verification task needs its own tailored script.