# APV Examples

## Minimal IFU Fetch to IDU Lane

This example keeps the identity chain explicit: fetch captures PC and packed instruction data; IFDP ties current VPC to the captured PC; IDU lane selection uses a pattern variable and split membership against captured packed data.

```yaml
fsdbFile: /abs/path/to/novas.fsdb
globalClock: tb.clk
scope: tb.x_soc.x_cpu_sub_system_axi.x_rv_integration_platform.x_cpu_top.x_ct_top_0.x_ct_core.x_ct_ifu_top

output:
  directory: workspace/apvReports/ifu_to_idu
  verbose: true
  timeout: 10000000

globalFlush:
  condition:
    - "rtu_ifu_flush == 1'b1"
    - "|| rtu_ifu_xx_expt_vld == 1'b1"

tasks:
  - id: fetch_complete
    name: "IF pipedown"
    matchMode: first
    condition:
      - "ifctrl_ifdp_pipedown == 1'b1"
    capture:
      - pcgen_ifctrl_pc
    logging:
      - "[FETCH] pc={pcgen_ifctrl_pc:x}"

  - id: ifdp_entry
    name: "IFDP entry"
    dependsOn: fetch_complete
    matchMode: first
    condition:
      - "ifctrl_ifdp_pipedown == 1'b1"
      - "&& ifdp_ipdp_vpc == $dep.fetch_complete.pcgen_ifctrl_pc"
    capture:
      - ifdp_ipdp_vpc
      - x_ct_ifu_ifdp.ifdp_inst_data0
      - x_ct_ifu_ifdp.ifdp_inst_data1
    logging:
      - "[IFDP] vpc={ifdp_ipdp_vpc:x}"

  - id: idu_lane_from_way0
    name: "IDU lane from IFDP way0"
    dependsOn: ifdp_entry
    matchMode: unique_per_var
    maxMatch: 4
    condition:
      - "ifu_idu_ib_inst{idx}_vld == 1'b1"
      - "&& ifu_idu_ib_inst{idx}_data[15:0] <@ $dep.ifdp_entry.x_ct_ifu_ifdp.ifdp_inst_data0.$split(8)"
    capture:
      - ifu_idu_ib_inst{idx}_data
    logging:
      - "[IDU_LANE_WAY0] lane={idx} inst={ifu_idu_ib_inst{idx}_data:x}"
```

## Explicit Sibling Handoffs

Use sibling tasks when each terminal path needs a distinct condition. Do not collapse these to one pipe unless local evidence proves only one pipe can carry the instruction.

```yaml
tasks:
  - id: decode_entry
    name: "Decode entry"
    matchMode: first
    condition:
      - "id_inst0_vld == 1'b1"
      - "&& id_inst0_data[31:0] == 32'h00a58533"
    capture:
      - id_inst0_data
      - id_inst0_pc
    logging:
      - "[DECODE] pc={id_inst0_pc:x} inst={id_inst0_data:x}"

  - id: pipe0_accept
    name: "Pipe0 accepts decode inst"
    dependsOn: decode_entry
    matchMode: first
    maxMatch: 1
    condition:
      - "pipe0_vld == 1'b1"
      - "&& pipe0_inst[31:0] == $dep.decode_entry.id_inst0_data[31:0]"
    capture:
      - pipe0_inst
      - pipe0_iid
    logging:
      - "[PIPE0] iid={pipe0_iid} inst={pipe0_inst:x}"

  - id: pipe1_accept
    name: "Pipe1 accepts decode inst"
    dependsOn: decode_entry
    matchMode: first
    maxMatch: 1
    condition:
      - "pipe1_vld == 1'b1"
      - "&& pipe1_inst[31:0] == $dep.decode_entry.id_inst0_data[31:0]"
    capture:
      - pipe1_inst
      - pipe1_iid
    logging:
      - "[PIPE1] iid={pipe1_iid} inst={pipe1_inst:x}"
```

## IDU Rename to Issue by IID

```yaml
tasks:
  - id: id_inst0
    name: "ID inst0"
    condition:
      - "x_ct_idu_top.x_ct_idu_id_dp.id_inst0_data[31:0] == 32'h00000013"
    capture:
      - x_ct_idu_top.x_ct_idu_id_dp.id_inst0_data
      - x_ct_idu_top.idu_iu_rf_pipe0_iid
    logging:
      - "[ID0] iid={x_ct_idu_top.idu_iu_rf_pipe0_iid} inst={x_ct_idu_top.x_ct_idu_id_dp.id_inst0_data:x}"

  - id: issue_aiq0_create0
    name: "Issue to AIQ0 create0"
    dependsOn: id_inst0
    matchMode: first
    condition:
      - "x_ct_idu_top.x_ct_idu_is_ctrl.is_dis_aiq0_create0_en == 1'b1"
      - "&& x_ct_idu_top.x_ct_idu_is_dp.is_aiq0_create0_iid == $dep.id_inst0.x_ct_idu_top.idu_iu_rf_pipe0_iid"
    capture:
      - x_ct_idu_top.x_ct_idu_is_ctrl.is_dis_aiq0_create0_en
      - x_ct_idu_top.x_ct_idu_is_dp.is_aiq0_create0_iid
    logging:
      - "[ISSUE_AIQ0] iid={x_ct_idu_top.x_ct_idu_is_dp.is_aiq0_create0_iid}"
```

## RTU Completion by IID

```yaml
tasks:
  - id: rob_create0
    name: "ROB create0"
    condition:
      - "idu_rtu_rob_create0_en == 1'b1"
    capture:
      - rtu_idu_rob_inst0_iid
      - idu_rtu_rob_create0_data
    logging:
      - "[ROB_CREATE0] iid={rtu_idu_rob_inst0_iid}"

  - id: exec_complete
    name: "Execution complete by IID"
    dependsOn: rob_create0
    matchMode: first
    condition:
      - "(iu_rtu_pipe0_cmplt == 1'b1 && iu_rtu_pipe0_iid == $dep.rob_create0.rtu_idu_rob_inst0_iid)"
      - "|| (lsu_rtu_wb_pipe3_cmplt == 1'b1 && lsu_rtu_wb_pipe3_iid == $dep.rob_create0.rtu_idu_rob_inst0_iid)"
    capture:
      - iu_rtu_pipe0_cmplt
      - iu_rtu_pipe0_iid
      - lsu_rtu_wb_pipe3_cmplt
      - lsu_rtu_wb_pipe3_iid
    logging:
      - "[EXEC_COMPLETE] iid={$dep.rob_create0.rtu_idu_rob_inst0_iid}"
```

## Conservative Partial Pattern

When only a valid gate is visible and the local route has stronger-but-unavailable identity signals, keep the YAML exploratory and report the result as partial.

```yaml
tasks:
  - id: weak_handoff_probe
    name: "Weak handoff probe"
    dependsOn: decode_entry
    matchMode: first
    maxMatch: 1
    condition:
      - "handoff_vld == 1'b1"
      - "&& !local_stall"
    capture:
      - handoff_vld
      - local_stall
    logging:
      - "[WEAK_HANDOFF] vld={handoff_vld} stall={local_stall}"
```

Report note: this proves a local handoff event, not same-instruction identity. Add PC, instruction bits, data slice, IID, ROB id, queue id, or tag equality before calling the route complete.
