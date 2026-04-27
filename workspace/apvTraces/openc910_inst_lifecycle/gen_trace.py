#!/usr/bin/env python3
"""Generate trace.yaml with cross-pipe/cross-slot OR-conditions.

Builds on the verified working single-chain YAML, extending to 3 IFU trigger chains
with cross-pipe matching at IDU stages (decode, rename, ROB).

Pipeline stages (verified against original working YAML and C910 RTL):
1. IFU IB dispatch (3 triggers: inst0/1/2)
2. IDU ID decode (cross-pipe: OR match against all id_inst{0,1,2}_data)
3. IDU IR rename (cross-pipe 3x3: OR match against all ir_inst{0,1,2}_data)
4. ROB allocate (cross-slot: OR match against all rob_create{0,1,2,3}_en)
5. IS AIQ0 create (cross-IID: match AIQ0/1 create0/1 IIDs against ROB IIDs)
6. RF pipe0 launch (IID-based match)
7. RF pipe0 decode (IID+func match, original verified pattern)
8. IU pipe0 receive (IID+func+dst_preg match, original verified pattern)
9. IU pipe0 complete (ALU result + cbus match, original verified pattern)
10. RTU commit (cross-slot IID match, original verified pattern)
11. RTU retire (IID match, original verified pattern)
"""

import os

OUTPUT = os.path.join(os.path.dirname(__file__), "trace.yaml")

HEADER = {
    "fsdbFile": "/home/c910/lingzichao/openc910/smart_run/work_force/novas.fsdb",
    "globalClock": "tb.clk",
    "scope": "tb.x_soc.x_cpu_sub_system_axi.x_rv_integration_platform.x_cpu_top.x_ct_top_0.x_ct_core",
    "output": {
        "directory": "workspace/apvTraces/openc910_inst_lifecycle/report",
        "verbose": True,
        "timeout": 100000000,
        "dependency_graph": "deps.png",
    },
    "globalFlush": {
        "condition": [
            "rtu_yy_xx_flush",
            "|| x_ct_ifu_top.rtu_ifu_flush",
            "|| x_ct_idu_top.rtu_idu_flush_fe",
            "|| x_ct_idu_top.rtu_idu_flush_is",
        ]
    },
}


def _dep(task_id, signal):
    return f"$dep.{task_id}.{signal}"


# --------------- Stage builders ---------------

def build_trigger(slot):
    """IFU IB dispatch trigger for inst{slot}."""
    return {
        "id": f"ifu_ib_inst{slot}",
        "name": f"IFU dispatch inst{slot}",
        "matchMode": "first",
        "maxMatch": 1,
        "condition": [
            f"x_ct_ifu_top.ifu_idu_ib_inst{slot}_vld",
            "&& not x_ct_idu_top.idu_ifu_id_stall",
            "&& x_ct_ifu_top.ifdp_ipdp_vpc",
        ],
        "capture": [
            f"x_ct_ifu_top.ifu_idu_ib_inst{s}_data" for s in range(3)
        ] + [
            "x_ct_ifu_top.pcgen_ifctrl_pc",
            "x_ct_ifu_top.ifdp_ipdp_vpc",
        ],
        "logging": [
            f"[IFU{slot}] pc={{pcgen_ifctrl_pc:x}} inst{slot}={{ifu_idu_ib_inst{slot}_data:x}}"
        ],
    }


def build_id_decode(slot):
    """IDU ID decode: cross-pipe OR on instruction data (3 decode pipes)."""
    tid = f"id_decode_inst{slot}"
    parent = f"ifu_ib_inst{slot}"
    dep_data = _dep(parent, f"ifu_idu_ib_inst{slot}_data")

    cond_lines = []
    for p in range(3):
        prefix = "|| " if p > 0 else ""
        cond_lines.append(
            f"{prefix}(x_ct_idu_top.x_ct_idu_id_dp.id_inst{p}_data[31:0] == {dep_data}[31:0])"
        )

    return {
        "id": tid,
        "name": f"IDU ID decode inst{slot}",
        "dependsOn": parent,
        "matchMode": "first",
        "maxMatch": 1,
        "condition": cond_lines,
        "capture": [
            f"x_ct_idu_top.x_ct_idu_id_dp.id_inst{p}_data" for p in range(3)
        ] + [
            f"x_ct_idu_top.x_ct_idu_id_ctrl.id_inst{p}_vld" for p in range(3)
        ] + [
            f"x_ct_idu_top.x_ct_idu_id_ctrl.ctrl_id_pipedown_inst{p}_vld" for p in range(3)
        ],
        "logging": [
            f"[DEC{slot}] id0={{id_inst0_data:x}} id1={{id_inst1_data:x}} id2={{id_inst2_data:x}}"
        ],
    }


def build_ir_rename(slot):
    """IDU IR rename: 3x3 cross-pipe (3 rename pipes x 3 decode data sources)."""
    tid = f"ir_rename_inst{slot}"
    parent = f"id_decode_inst{slot}"

    cond_lines = []
    for r in range(3):
        for d in range(3):
            prefix = "|| " if (r > 0 or d > 0) else ""
            cond_lines.append(
                f"{prefix}(x_ct_idu_top.x_ct_idu_ir_dp.ir_inst{r}_data[31:0]"
                f" == {_dep(parent, f'id_inst{d}_data')}[31:0])"
            )

    return {
        "id": tid,
        "name": f"IDU IR rename inst{slot}",
        "dependsOn": parent,
        "matchMode": "first",
        "maxMatch": 1,
        "condition": cond_lines,
        "capture": [
            f"x_ct_idu_top.x_ct_idu_ir_dp.ir_inst{p}_data" for p in range(3)
        ] + [
            f"x_ct_idu_top.x_ct_idu_ir_ctrl.ir_inst{p}_vld" for p in range(3)
        ] + [
            f"x_ct_idu_top.x_ct_idu_ir_ctrl.ctrl_ir_pipedown_inst{p}_vld" for p in range(3)
        ] + [
            f"rtu_idu_rob_inst{s}_iid" for s in range(4)
        ],
        "logging": [
            f"[IR{slot}] ir0={{ir_inst0_data:x}} ir1={{ir_inst1_data:x}} ir2={{ir_inst2_data:x}}"
        ],
    }


def build_rob_alloc(slot):
    """ROB allocate: cross-slot OR on 4 ROB create enables."""
    tid = f"rob_alloc_inst{slot}"
    parent = f"ir_rename_inst{slot}"

    cond_lines = []
    for s in range(4):
        prefix = "|| " if s > 0 else ""
        cond_lines.append(f"{prefix}idu_rtu_rob_create{s}_en")

    return {
        "id": tid,
        "name": f"ROB alloc inst{slot}",
        "dependsOn": parent,
        "matchMode": "first",
        "maxMatch": 1,
        "condition": cond_lines,
        "capture": [
            f"idu_rtu_rob_create{s}_en" for s in range(4)
        ] + [
            f"rtu_idu_rob_inst{s}_iid" for s in range(4)
        ],
        "logging": [
            f"[ROB{slot}] iid0={{rtu_idu_rob_inst0_iid:x}} iid1={{rtu_idu_rob_inst1_iid:x}} iid2={{rtu_idu_rob_inst2_iid:x}} iid3={{rtu_idu_rob_inst3_iid:x}}"
        ],
    }


def build_is_aiq0_create(slot):
    """IS AIQ0 create: cross-AIQ-slot matching with SPECIFIC ROB IID slot.

    The pipeline is in-order: IFU slot N maps to ROB create slot N.
    We match against the specific rob_inst{slot}_iid, not all 4.
    Cross-AIQ-slot OR (AIQ0/1, create0/1) covers unknown AIQ assignment.
    """
    tid = f"is_aiq0_inst{slot}"
    parent = f"rob_alloc_inst{slot}"
    rob_iid = _dep(parent, f"rtu_idu_rob_inst{slot}_iid")

    cond_lines = [
        "x_ct_idu_top.x_ct_idu_is_aiq0.ctrl_aiq0_create0_dp_en",
        "&& x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_xx_issue_en",
        "&& x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_bypass_en",
        "&& x_ct_idu_top.x_ct_idu_is_aiq0.x_ct_idu_is_aiq0_entry0.x_create_dp_en",
        "&& x_ct_idu_top.x_ct_idu_is_aiq0.x_ct_idu_is_aiq0_entry0.x_create_en == x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_entry_create0_in",
    ]

    # Cross-AIQ-slot: match if any AIQ slot carries the specific instruction IID
    for aiq in range(2):
        for c in range(2):
            prefix = "&& ((" if (aiq == 0 and c == 0) else "|| ("
            cond_lines.append(
                f"{prefix}x_ct_idu_top.x_ct_idu_is_ctrl.is_dis_aiq{aiq}_create{c}_en && "
                f"(x_ct_idu_top.x_ct_idu_is_dp.is_aiq{aiq}_create{c}_iid == {rob_iid}))"
            )
    cond_lines[-1] = cond_lines[-1] + ")"

    return {
        "id": tid,
        "name": f"IS AIQ0 create inst{slot}",
        "dependsOn": parent,
        "matchMode": "first",
        "maxMatch": 1,
        "condition": cond_lines,
        "capture": [
            f"x_ct_idu_top.x_ct_idu_is_ctrl.is_dis_aiq{q}_create{c}_en"
            for q in range(2) for c in range(2)
        ] + [
            f"x_ct_idu_top.x_ct_idu_is_dp.is_aiq{q}_create{c}_iid"
            for q in range(2) for c in range(2)
        ] + [
            "x_ct_idu_top.x_ct_idu_is_aiq0.ctrl_aiq0_create0_dp_en",
            "x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_entry_create0_in",
            "x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_dp_issue_read_data",
            "x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_bypass_en",
            "x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_xx_issue_en",
            "x_ct_idu_top.x_ct_idu_is_aiq0.x_ct_idu_is_aiq0_entry0.x_create_en",
            "x_ct_idu_top.x_ct_idu_is_aiq0.x_ct_idu_is_aiq0_entry0.x_create_dp_en",
        ],
        "logging": [
            f"[AIQ0_{slot}] c0={{is_dis_aiq0_create0_en}}:{{is_aiq0_create0_iid:x}} c1={{is_dis_aiq0_create1_en}}:{{is_aiq0_create1_iid:x}}"
        ],
    }


def build_rf_pipe0_launch(slot):
    """RF pipe0 launch: match pipe0 IID directly against the instruction's ROB IID.

    Uses the ROB IID as the identity anchor, bypassing AIQ-captured IIDs.
    The dependsOn (AIQ) still provides correct temporal ordering.
    """
    tid = f"rf_pipe0_inst{slot}"
    parent = f"is_aiq0_inst{slot}"
    rob_iid = _dep(f"rob_alloc_inst{slot}", f"rtu_idu_rob_inst{slot}_iid")

    return {
        "id": tid,
        "name": f"RF pipe0 launch inst{slot}",
        "dependsOn": parent,
        "matchMode": "first",
        "maxMatch": 1,
        "condition": [
            "x_ct_idu_top.x_ct_idu_rf_ctrl.rf_pipe0_inst_vld",
            "&& x_ct_idu_top.x_ct_idu_rf_ctrl.ctrl_rf_pipe0_pipedown_vld",
            "&& x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_dst_vld",
            f"&& x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_iid == {rob_iid}",
        ],
        "capture": [
            "x_ct_idu_top.x_ct_idu_rf_ctrl.rf_pipe0_inst_vld",
            "x_ct_idu_top.x_ct_idu_rf_ctrl.ctrl_rf_pipe0_pipedown_vld",
            "x_ct_idu_top.x_ct_idu_rf_ctrl.ctrl_aiq0_rf_pop_vld",
            "x_ct_idu_top.x_ct_idu_rf_ctrl.idu_iu_rf_pipe0_sel",
            "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_iid",
            "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_func",
            "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_dst_preg",
            "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_dst_vld",
            "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_src0",
            "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_src1",
        ],
        "logging": [
            f"[RF0_{slot}] iid={{idu_iu_rf_pipe0_iid:x}} func={{idu_iu_rf_pipe0_func:x}} dst={{idu_iu_rf_pipe0_dst_preg:x}}"
        ],
    }


def build_rf_pipe0_decode(slot):
    """RF pipe0 decode: verified condition (IID + func match, no exception)."""
    tid = f"rf_decode_inst{slot}"
    parent = f"rf_pipe0_inst{slot}"

    return {
        "id": tid,
        "name": f"RF pipe0 decode inst{slot}",
        "dependsOn": parent,
        "matchMode": "first",
        "maxMatch": 1,
        "condition": [
            f"x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_iid == {_dep(parent, 'idu_iu_rf_pipe0_iid')}",
            f"&& x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_func == {_dep(parent, 'idu_iu_rf_pipe0_func')}",
            "&& not x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_expt_vld",
        ],
        "capture": [
            "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_iid",
            "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_func",
            "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_dst_preg",
            "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_eu_sel",
            "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_expt_vld",
            "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_func",
            "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_sel",
            "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_opcode",
        ],
        "logging": [
            f"[RFDC{slot}] iid={{idu_iu_rf_pipe0_iid:x}} func={{pipe0_decd_func:x}} eu={{pipe0_decd_eu_sel:x}} opcode={{pipe0_decd_opcode:x}}"
        ],
    }


def build_iu_pipe0_receive(slot):
    """IU pipe0 receive: verified condition (sel + IID + func + dst_preg match)."""
    tid = f"iu_pipe0_recv_inst{slot}"
    parent = f"rf_decode_inst{slot}"

    return {
        "id": tid,
        "name": f"IU pipe0 receive inst{slot}",
        "dependsOn": parent,
        "matchMode": "first",
        "maxMatch": 1,
        "condition": [
            "x_ct_iu_top.idu_iu_rf_pipe0_sel",
            f"&& x_ct_iu_top.idu_iu_rf_pipe0_iid == {_dep(parent, 'idu_iu_rf_pipe0_iid')}",
            f"&& x_ct_iu_top.idu_iu_rf_pipe0_func == {_dep(parent, 'idu_iu_rf_pipe0_func')}",
            f"&& x_ct_iu_top.idu_iu_rf_pipe0_dst_preg == {_dep(parent, 'idu_iu_rf_pipe0_dst_preg')}",
        ],
        "capture": [
            "x_ct_iu_top.idu_iu_rf_pipe0_sel",
            "x_ct_iu_top.idu_iu_rf_pipe0_gateclk_sel",
            "x_ct_iu_top.idu_iu_rf_pipe0_iid",
            "x_ct_iu_top.idu_iu_rf_pipe0_opcode",
            "x_ct_iu_top.idu_iu_rf_pipe0_func",
            "x_ct_iu_top.idu_iu_rf_pipe0_dst_preg",
            "x_ct_iu_top.idu_iu_rf_pipe0_dst_vld",
            "x_ct_iu_top.idu_iu_rf_pipe0_src0",
            "x_ct_iu_top.idu_iu_rf_pipe0_src1",
        ],
        "logging": [
            f"[IU_RECV{slot}] iid={{idu_iu_rf_pipe0_iid:x}} opcode={{idu_iu_rf_pipe0_opcode:x}} func={{idu_iu_rf_pipe0_func:x}} dst={{idu_iu_rf_pipe0_dst_preg:x}}"
        ],
    }


def build_iu_pipe0_complete(slot):
    """IU pipe0 complete: verified condition (ALU result + cbus IID match)."""
    tid = f"iu_pipe0_cmplt_inst{slot}"
    parent = f"iu_pipe0_recv_inst{slot}"

    return {
        "id": tid,
        "name": f"IU pipe0 complete inst{slot}",
        "dependsOn": parent,
        "matchMode": "first",
        "maxMatch": 1,
        "condition": [
            "x_ct_iu_top.x_ct_iu_alu0.alu_rbus_ex1_pipex_data_vld",
            f"&& x_ct_iu_top.x_ct_iu_alu0.alu_rbus_ex1_pipex_preg == {_dep(parent, 'idu_iu_rf_pipe0_dst_preg')}",
            "&& x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe0_cmplt",
            f"&& x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe0_iid == {_dep(parent, 'idu_iu_rf_pipe0_iid')}",
        ],
        "capture": [
            "x_ct_iu_top.x_ct_iu_alu0.idu_iu_rf_pipex_gateclk_sel",
            "x_ct_iu_top.x_ct_iu_alu0.idu_iu_rf_pipex_dst_preg",
            "x_ct_iu_top.x_ct_iu_alu0.idu_iu_rf_pipex_dst_vld",
            "x_ct_iu_top.x_ct_iu_alu0.idu_iu_rf_pipex_func",
            "x_ct_iu_top.x_ct_iu_alu0.alu_rbus_ex1_pipex_data_vld",
            "x_ct_iu_top.x_ct_iu_alu0.alu_rbus_ex1_pipex_data",
            "x_ct_iu_top.x_ct_iu_alu0.alu_rbus_ex1_pipex_preg",
            "x_ct_iu_top.x_ct_iu_rbus.alu_rbus_ex1_pipe0_data_vld",
            "x_ct_iu_top.x_ct_iu_rbus.alu_rbus_ex1_pipe0_preg",
            "x_ct_iu_top.x_ct_iu_rbus.rbus_pipe0_rslt_vld",
            "x_ct_iu_top.x_ct_iu_rbus.rbus_pipe0_wb_preg_dup5",
            "x_ct_iu_top.x_ct_iu_rbus.rbus_pipe0_wb_vld",
            "x_ct_iu_top.x_ct_iu_rbus.rbus_pipe0_wb_data",
            "x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe0_cmplt",
            "x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe0_iid",
            "x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe0_abnormal",
            "x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe0_expt_vld",
            "iu_rtu_pipe0_cmplt",
            "iu_rtu_pipe0_iid",
            "iu_rtu_pipe0_abnormal",
            "iu_rtu_pipe0_expt_vld",
            "iu_rtu_pipe0_expt_vec",
        ],
        "logging": [
            f"[IU_CMPLT{slot}] iid={{iu_rtu_pipe0_iid:x}} cmplt={{iu_rtu_pipe0_cmplt}} abnormal={{iu_rtu_pipe0_abnormal}}"
        ],
    }


def build_rtu_commit(slot):
    """RTU commit: verified cross-slot IID matching (3 commit slots)."""
    tid = f"rtu_commit_inst{slot}"
    parent = f"iu_pipe0_cmplt_inst{slot}"

    cond_lines = []
    for c in range(3):
        prefix = "" if c == 0 else "|| "
        cond_lines.append(
            f"{prefix}(x_ct_rtu_top.rtu_yy_xx_commit{c}"
            f" && x_ct_rtu_top.rtu_yy_xx_commit{c}_iid"
            f" == {_dep(parent, 'iu_rtu_pipe0_iid')})"
        )

    return {
        "id": tid,
        "name": f"RTU commit inst{slot}",
        "dependsOn": parent,
        "matchMode": "first",
        "maxMatch": 1,
        "condition": cond_lines,
        "capture": [
            f"x_ct_rtu_top.rtu_yy_xx_commit{c}" for c in range(3)
        ] + [
            f"x_ct_rtu_top.rtu_yy_xx_commit{c}_iid" for c in range(3)
        ] + [
            "x_ct_rtu_top.rtu_pad_retire0_pc",
            "x_ct_rtu_top.rtu_pad_retire1_pc",
            "x_ct_rtu_top.rtu_pad_retire2_pc",
            "x_ct_rtu_top.rtu_yy_xx_retire0",
            "x_ct_rtu_top.rob_retire_inst0_cur_pc",
            "x_ct_rtu_top.rob_retire_inst0_iid",
            "x_ct_rtu_top.rob_retire_inst0_vld",
        ],
        "logging": [
            f"[CMT{slot}] c0={{rtu_yy_xx_commit0}}:{{rtu_yy_xx_commit0_iid:x}} retire0={{rtu_yy_xx_retire0}} retire_pc={{rtu_pad_retire0_pc:x}}"
        ],
    }


def build_rtu_retire(slot):
    """RTU retire: verified condition (IID match at retire boundary)."""
    tid = f"rtu_retire_inst{slot}"
    parent = f"rtu_commit_inst{slot}"

    return {
        "id": tid,
        "name": f"RTU retire inst{slot}",
        "dependsOn": parent,
        "matchMode": "first",
        "maxMatch": 1,
        "condition": [
            "x_ct_rtu_top.rtu_pad_retire0",
            "&& x_ct_rtu_top.rtu_yy_xx_retire0",
            f"&& x_ct_rtu_top.rob_retire_inst0_iid == {_dep(parent, 'rtu_yy_xx_commit0_iid')}",
        ],
        "capture": [
            "x_ct_rtu_top.rtu_pad_retire0",
            "x_ct_rtu_top.rtu_pad_retire0_pc",
            "x_ct_rtu_top.rtu_yy_xx_retire0",
            "x_ct_rtu_top.rtu_yy_xx_commit0",
            "x_ct_rtu_top.rtu_yy_xx_commit0_iid",
            "x_ct_rtu_top.rob_retire_inst0_iid",
            "x_ct_rtu_top.rob_retire_inst0_vld",
            "x_ct_rtu_top.rob_retire_inst0_cur_pc",
        ],
        "logging": [
            f"[RET{slot}] iid={{rob_retire_inst0_iid:x}} pc={{rtu_pad_retire0_pc:x}} retire0={{rtu_yy_xx_retire0}}"
        ],
    }


# --------------- main ---------------

def main():
    tasks = []

    # 1. 3 IFU triggers
    for slot in range(3):
        tasks.append(build_trigger(slot))
    # 2. IDU ID decode (cross-pipe)
    for slot in range(3):
        tasks.append(build_id_decode(slot))
    # 3. IDU IR rename (cross-pipe 3x3)
    for slot in range(3):
        tasks.append(build_ir_rename(slot))
    # 4. ROB allocate (cross-slot)
    for slot in range(3):
        tasks.append(build_rob_alloc(slot))
    # 5. IS AIQ0 create (cross-IID)
    for slot in range(3):
        tasks.append(build_is_aiq0_create(slot))
    # 6. RF pipe0 launch
    for slot in range(3):
        tasks.append(build_rf_pipe0_launch(slot))
    # 7. RF pipe0 decode
    for slot in range(3):
        tasks.append(build_rf_pipe0_decode(slot))
    # 8. IU pipe0 receive
    for slot in range(3):
        tasks.append(build_iu_pipe0_receive(slot))
    # 9. IU pipe0 complete
    for slot in range(3):
        tasks.append(build_iu_pipe0_complete(slot))
    # 10. RTU commit (cross-slot)
    for slot in range(3):
        tasks.append(build_rtu_commit(slot))
    # 11. RTU retire
    for slot in range(3):
        tasks.append(build_rtu_retire(slot))

    # Write YAML
    with open(OUTPUT, "w") as f:
        f.write(f"fsdbFile: {HEADER['fsdbFile']}\n")
        f.write(f"globalClock: {HEADER['globalClock']}\n")
        f.write(f"scope: {HEADER['scope']}\n")
        f.write("\n")
        f.write("output:\n")
        f.write(f"  directory: {HEADER['output']['directory']}\n")
        f.write(f"  verbose: {str(HEADER['output']['verbose']).lower()}\n")
        f.write(f"  timeout: {HEADER['output']['timeout']}\n")
        f.write(f"  dependency_graph: {HEADER['output']['dependency_graph']}\n")
        f.write("\n")
        f.write("globalFlush:\n")
        f.write("  condition:\n")
        for line in HEADER["globalFlush"]["condition"]:
            f.write(f'    - "{line}"\n')
        f.write("\n")
        f.write("tasks:\n")

        for task in tasks:
            f.write(f"  - id: {task['id']}\n")
            f.write(f"    name: \"{task['name']}\"\n")
            if "dependsOn" in task:
                f.write(f"    dependsOn: {task['dependsOn']}\n")
            f.write(f"    matchMode: {task['matchMode']}\n")
            f.write(f"    maxMatch: {task['maxMatch']}\n")
            f.write("    condition:\n")
            for line in task["condition"]:
                f.write(f'      - "{line}"\n')
            f.write("    capture:\n")
            for sig in task["capture"]:
                f.write(f"      - {sig}\n")
            f.write("    logging:\n")
            for log in task["logging"]:
                f.write(f'      - "{log}"\n')
            f.write("\n")

    print(f"Generated {OUTPUT} with {len(tasks)} tasks (3 chains x 11 stages).")


if __name__ == "__main__":
    main()
