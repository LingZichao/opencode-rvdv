---
name: inst-sampling
description: Trace C910 instruction pipeline events in FSDB waveforms.
compatibility: opencode
---

# Inst Sampling

Build task-specific wave sampling scripts that trace instruction events through the C910 pipeline using wavekit's `Pattern` engine.

## Project Defaults

```python
FSDB = "<workspace>/openc910/smart_run/work_force/novas.fsdb"
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

## Reusable Patterns

### 1. Establish identity keys

Pick the earliest observation point where an instruction can be *uniquely captured* and extract its identity anchor. The anchor must satisfy:

- **Architectural uniqueness**: the fields distinguish this instruction from any other in the window. PC alone is insufficient if the same PC executes in a loop; pair it with a sequence marker (`vpc` transition, `inst_word`, etc.).
- **Timing uniqueness**: the key must not collide with any other in-flight instruction at a different pipeline stage — it is the invariant used to disambiguate across every downstream crossbar match.

Pipelines assign a unique tag (ROB index, IID) at some mid-pipeline stage:

- **Before tag assignment**: match by architectural attributes — `(PC, inst_word)` at minimum. When decode changes the payload (RVC expansion, fusion), drop the changed field; match on what survives.
- **After tag assignment**: match by the tag alone.

For C910 example, the anchor is `(vpc, pc15, inst_word)` at IFU IB output. After AIQ create, the key switches to `IID`.

### 2. Guard all waits with a global kill condition

Any pipeline cancellation (flush, exception, replay) invalidates in-flight traces. A single guard expression evaluated once and passed to every `wait()` prevents false reconnects:

```python
guard_ok = reader.eval("(flush_fe == 0) and (flush_pipe == 0) and ...", ...)
pat.wait(..., guard=guard_ok)
```

Without this, a cancelled entity's identity key or tag may be reassigned, producing a false-positive match that stitches unrelated events together.

### 3. Standard stage structure

Every pipeline stage in a Pattern follows the same shape:

```python
# -- Stage N: <name> --------------------------------------------------
def _match_N(idx, caps):
    # return lane/port index (≥0) or -1 for no match
    ...

pat.wait(lambda idx, caps: _match_N(idx, caps) >= 0, guard=guard_ok)
pat.capture("N.lane",  _match_N)
pat.capture("N.field", _cap(signal_list))
pat.capture("cycle_N", cycle)
```

Keep match functions close to their wait/capture group — not at the top of the file.