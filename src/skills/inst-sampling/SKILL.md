---
name: inst-sampling
description: Trace RISC-V instruction pipeline events in FSDB waveforms with wavekit.
compatibility: opencode
---

# Inst Sampling

Build task-specific wave sampling scripts that trace RISC-V instruction events through a design pipeline using wavekit's `Pattern` engine.

## Project Defaults

```python
FSDB = "<task-provided FSDB path>"
CLOCK = "<task-provided or discovered clock>"
SCOPE = "<task-provided or discovered design scope>"
```

Use task-provided Columbus or RTL simulation artifacts when available. Do not assume legacy `smart_run` paths or scopes unless the task explicitly points to that environment.

## Workspace

- Trace script: `workspace/instTraces/<task_name>/trace.py`
- Output: `workspace/instTraces/<task_name>/report/`

## API Reference

See the `wavekit` skill for full Pattern API, waveform operations, and viewer usage.

## Reference Script

[trace.py](trace.py) is a complete historical lifecycle trace example — use its stage structure as a skeleton, not as a signal/path template. Each verification task needs its own tailored script, FSDB path, clock, scope, and signal mapping.

## Reusable Patterns

### 1. Establish identity keys

Pick the earliest observation point where an instruction can be *uniquely captured* and extract its identity anchor. The anchor must satisfy:

- **Architectural uniqueness**: the fields distinguish this instruction from any other in the window. PC alone is insufficient if the same PC executes in a loop; pair it with a sequence marker (`vpc` transition, `inst_word`, etc.).
- **Timing uniqueness**: the key must not collide with any other in-flight instruction at a different pipeline stage — it is the invariant used to disambiguate across every downstream crossbar match.

Pipelines assign a unique tag (ROB index, IID) at some mid-pipeline stage:

- **Before tag assignment**: match by architectural attributes — `(PC, inst_word)` at minimum. When decode changes the payload (RVC expansion, fusion), drop the changed field; match on what survives.
- **After tag assignment**: match by the tag alone.

For a concrete design, choose the earliest stable frontend identity tuple, then switch to the pipeline tag once the design assigns one, for example an `IID`, ROB index, or equivalent internal tag.

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
