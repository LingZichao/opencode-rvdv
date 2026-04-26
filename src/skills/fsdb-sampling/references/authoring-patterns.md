# APV Authoring Patterns

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

## Match Mode Selection

- `first`: ordinary pipeline progress from one stage to the next.
- `all`: repeated events, broadcast, or multiple completions that must be inspected.
- `unique_per_var`: lane/slot/way pattern matching where each variable value should appear once.

Use `maxMatch` whenever the hardware bound is known.

## Failure Interpretation

- No root matches: trigger condition or FSDB/scope may be wrong.
- No dependent matches: identity relation may be too strict, timeout too short, or trace crossed `globalFlush`.
- Duplicate matches: condition is under-constrained or multiple upstream traces are aliasing the same row.
