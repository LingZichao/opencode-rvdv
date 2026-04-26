# APV Examples

## Minimal IFU Fetch to IDU Lane

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
