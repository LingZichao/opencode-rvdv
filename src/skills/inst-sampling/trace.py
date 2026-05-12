#!/usr/bin/env python3
"""Wavekit trace: OpenC910 instruction lifecycle

Tracks an instruction through all pipeline stages from pcgen to retire,
correctly handling crossbar routing at every stage.

Pipeline stages:
  0. PCGEN    - PC generation (instruction fetch initiated)
  1. IFU_IB   - Instruction buffer output to ID stage
  2. IDU_ID   - Instruction decode (3-wide)
  3. IDU_IR   - Rename / pre-decode (4-wide, expansion of compressed insts)
  4. IS_DISP  - Issue stage dispatch (crossbar: any IS inst -> any AIQ port)
  5. ROB_ALLOC- ROB entry allocation + IID assignment
  6. AIQ_CREATE - Issue queue entry creation with IID
  7. RF_ISSUE - Register file read + issue to execution pipe
  8. IU_EXEC  - Execution pipe receive
  9. IU_CMPLT - Execution complete, writeback to ROB
  10. RTU_COMMIT - ROB commit (in-order)
  11. RTU_RETIRE - Architectural state update

Key cross-points where slot positions are NOT preserved:
  - ID(3 insts) -> IR(4 insts): compressed instruction expansion
  - IR -> IS: pipedown2/pipedown4 mode changes IS inst positions
  - IS -> AIQ: any IS inst can go to any AIQ create port via sel signals
  - IS -> ROB: ROB create0 always from IS inst0; creates 1-3 use sel signals
  - AIQ -> RF pipes: AIQ0 can issue to pipe0 or pipe1

Strategy: track by (pc15, instruction word) through front-end crossbars,
then by selected AIQ port plus (IID, instruction word) through RF/execution.

Usage:
  .venv/bin/python src/skills/inst-sampling/trace.py
"""

import os
import time
import json

import numpy as np

from wavekit import FsdbReader, MatchStatus, Pattern

FSDB = "/home/c910/openc910/smart_run/work_force/novas.fsdb"
CLOCK = "tb.clk"
SCOPE = (
    "tb.x_soc.x_cpu_sub_system_axi.x_rv_integration_platform"
    ".x_cpu_top.x_ct_top_0.x_ct_core"
)
OUTPUT = "workspace/instTraces/openc910_inst_lifecycle/report"
TIMEOUT = 500
END_CYCLE = 5000

# Pipeline stage order for per-stage timing
# Each stage name matches the cycle_<name> capture key suffix
STAGE_ORDER = [
    "pcgen_ib",    # PCGEN + IFU IB trigger
    "id_decode",   # IDU ID decode
    "ir_rename",   # IDU IR rename / expansion
    "rob_alloc",   # ROB entry allocation
    "aiq_create",  # AIQ entry creation
    "rf_issue",    # RF pipe0 issue
    "rf_decode",   # RF pipe0 decode
    "iu_exec",     # IU pipe0 receive
    "iu_cmplt",    # IU pipe0 complete
    "rtu_commit",  # RTU commit
    "rtu_retire",  # RTU retire
]


def _s(name: str) -> str:
    """Resolve relative signal path to absolute."""
    return f"{SCOPE}.{name}"


def _load(reader, name: str):
    """Load a clock-sampled waveform."""
    return reader.load_waveform(_s(name), clock=CLOCK, sample_on_posedge=True)


def build_trace(reader, slot: int) -> Pattern:
    """Build a 12-stage instruction trace using wavekit's native Pattern API.

    The pattern tries both AIQ0 and AIQ1 at the dispatch point and
    automatically follows whichever execution pipe the instruction takes.

    Args:
        slot: IB output position (0, 1, or 2) to trigger on.
    """

    # ================================================================
    #  Pre-load all waveforms
    # ================================================================

    # ---- Stage 0: PCGEN (captured alongside IB trigger for reference) ----
    pcgen_pc = _load(reader, "x_ct_ifu_top.x_ct_ifu_pcgen.pcgen_ifdp_pc[38:0]")

    # ---- Stage 1: IFU IB (3 slots) ----
    inst_data = [_load(reader, f"x_ct_ifu_top.ifu_idu_ib_inst{i}_data[31:0]") for i in range(3)]
    inst_pc = [_load(reader, f"x_ct_ifu_top.ifu_idu_ib_inst{i}_data[63:49]") for i in range(3)]
    inst_vld = [_load(reader, f"x_ct_ifu_top.ifu_idu_ib_inst{i}_vld") for i in range(3)]

    # ---- Stage 2: IDU ID (3 pipeline positions) ----
    id_data = [_load(reader, f"x_ct_idu_top.x_ct_idu_id_dp.id_inst{i}_data[31:0]") for i in range(3)]
    id_pc = [_load(reader, f"x_ct_idu_top.x_ct_idu_id_dp.id_inst{i}_data[63:49]") for i in range(3)]
    id_vld = [_load(reader, f"x_ct_idu_top.x_ct_idu_id_ctrl.ctrl_top_id_inst{i}_vld") for i in range(3)]
    id_stall = _load(reader, "x_ct_idu_top.idu_ifu_id_stall")

    # ---- Stage 3: IDU IR (4 pipeline positions — 3-to-4 expansion) ----
    ir_data = [_load(reader, f"x_ct_idu_top.x_ct_idu_ir_dp.ir_inst{i}_data[31:0]") for i in range(4)]
    ir_pc = [_load(reader, f"x_ct_idu_top.x_ct_idu_ir_dp.ir_inst{i}_data[167:153]") for i in range(4)]
    ir_vld = [_load(reader, f"x_ct_idu_top.x_ct_idu_ir_ctrl.ctrl_ir_pipedown_inst{i}_vld") for i in range(4)]

    # ---- Stage 4+5: ROB create (4 ports) + IIDs ----
    rob_iids = [_load(reader, f"rtu_idu_rob_inst{i}_iid[6:0]") for i in range(4)]
    rob_creates = [_load(reader, f"idu_rtu_rob_create{i}_en") for i in range(4)]
    is_data = [_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.is_inst{i}_read_data[31:0]") for i in range(4)]
    is_pc = [_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.is_inst{i}_read_data[199:185]") for i in range(4)]
    is_vld = [_load(reader, f"x_ct_idu_top.ctrl_top_is_inst{i}_vld") for i in range(4)]

    # ---- Stage 6: AIQ create entries + IS dispatch IIDs ----
    aiq_ens = [[_load(reader, f"x_ct_idu_top.x_ct_idu_is_ctrl.is_dis_aiq{q}_create{c}_en") for c in range(2)] for q in range(2)]
    aiq_iids = [[_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.is_aiq{q}_create{c}_iid[6:0]") for c in range(2)] for q in range(2)]
    # AIQ entry instruction word for crossbar disambiguation
    aiq_c_data = [
        [_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.dp_aiq{q}_create{c}_data[31:0]") for c in range(2)]
        for q in range(2)
    ]
    aiq_c_pc = [
        [_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.is_aiq{q}_create{c}_data[199:185]") for c in range(2)]
        for q in range(2)
    ]

    # ---- Stages 7-10: RF pipe, decode, IU receive, IU complete (per-pipe) ----
    # Pipe0 has full signal set; pipe1 lacks opcode, expt_vld and decd_expt_vld
    # (C910 architecture: all exception handling goes through pipe0 only).
    rf_iid = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe{p}_iid[6:0]") for p in range(2)]
    rf_func = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe{p}_func") for p in range(2)]
    rf_dst = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe{p}_dst_preg[6:0]") for p in range(2)]
    rf_vld = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_ctrl.rf_pipe{p}_inst_vld") for p in range(2)]
    rf_pd_vld = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_ctrl.ctrl_rf_pipe{p}_pipedown_vld") for p in range(2)]
    rf_dst_vld = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe{p}_dst_vld") for p in range(2)]
    # Pipe0-only signals (pipe1 = None — these signals do not exist in RTL)
    rf_opcode = [
        _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_opcode[31:0]"),
        None,
    ]
    rf_expt_vld = [
        _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_expt_vld"),
        None,
    ]
    decd_expt = [
        _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_expt_vld"),
        None,
    ]
    decd_func = [
        _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_func"),
        _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.pipe1_decd_func"),
    ]

    iu_sel = [_load(reader, f"x_ct_iu_top.idu_iu_rf_pipe{p}_sel") for p in range(2)]
    iu_iid = [_load(reader, f"x_ct_iu_top.idu_iu_rf_pipe{p}_iid[6:0]") for p in range(2)]
    iu_func = [_load(reader, f"x_ct_iu_top.idu_iu_rf_pipe{p}_func") for p in range(2)]
    iu_dst = [_load(reader, f"x_ct_iu_top.idu_iu_rf_pipe{p}_dst_preg[6:0]") for p in range(2)]

    alu_vld = [_load(reader, f"x_ct_iu_top.x_ct_iu_alu{p}.alu_rbus_ex1_pipex_data_vld") for p in range(2)]
    alu_preg = [_load(reader, f"x_ct_iu_top.x_ct_iu_alu{p}.alu_rbus_ex1_pipex_preg[6:0]") for p in range(2)]
    cbus_cmplt = [_load(reader, f"x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe{p}_cmplt") for p in range(2)]
    cbus_iid = [_load(reader, f"x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe{p}_iid[6:0]") for p in range(2)]
    rt_iid = [_load(reader, f"iu_rtu_pipe{p}_iid[6:0]") for p in range(2)]

    # ---- Stage 11: RTU commit (3 commit slots) ----
    commits = [_load(reader, f"x_ct_rtu_top.rtu_yy_xx_commit{i}") for i in range(3)]
    commit_iids = [_load(reader, f"x_ct_rtu_top.rtu_yy_xx_commit{i}_iid[6:0]") for i in range(3)]

    # ---- Stage 12: RTU retire ----
    retires = [_load(reader, f"x_ct_rtu_top.rtu_pad_retire{i}") for i in range(3)]
    retire_vlds = [_load(reader, f"x_ct_rtu_top.rtu_yy_xx_retire{i}") for i in range(3)]
    retire_pcs = [_load(reader, f"x_ct_rtu_top.rtu_pad_retire{i}_pc[39:0]") for i in range(3)]
    retire_iids = [
        _load(reader, "x_ct_rtu_top.rob_retire_inst0_iid[6:0]"),
        _load(reader, "x_ct_rtu_top.x_ct_rtu_rob.x_ct_rtu_rob_rt.retire_inst1_iid[6:0]"),
        _load(reader, "x_ct_rtu_top.x_ct_rtu_rob.x_ct_rtu_rob_rt.retire_inst2_iid[6:0]"),
    ]

    # ---- Flush guard ----
    # While an instruction is in-flight, any flush invalidates this trace
    # instance instead of letting it keep waiting and potentially reconnect
    # to a later instruction with the same word/IID.
    flush_ok = reader.eval(
        f"({_s('rtu_yy_xx_flush')} == 0)"
        f" and ({_s('x_ct_ifu_top.rtu_ifu_flush')} == 0)"
        f" and ({_s('x_ct_idu_top.rtu_idu_flush_fe')} == 0)"
        f" and ({_s('x_ct_idu_top.rtu_idu_flush_is')} == 0)",
        clock=CLOCK, sample_on_posedge=True,
    )

    # ---- Synthetic cycle counter for per-stage timing ----
    # Use vectorized_map to create a waveform whose value == cycle index.
    # Since we sample on posedge from start_cycle=0, value[i] == absolute cycle.
    cycle_cnt = pcgen_pc.vectorized_map(
        lambda v: np.arange(len(v), dtype=np.int64), width=64, signed=False,
    )

    # ================================================================
    #  Build Pattern
    # ================================================================
    pat = Pattern()

    # ---- Stage 0+1: PCGEN + IFU IB dispatch ----
    # Capture pcgen PC at the trigger cycle as reference context.
    # Note: due to IF->IB pipeline latency, the pcgen PC at this cycle
    # may not directly correspond to the traced instruction's PC.
    # The instruction identity is tracked as (pc15, opcode) through the
    # front-end crossbar stages, then by IID after AIQ creation.
    vpc_wf = _load(reader, "x_ct_ifu_top.ifdp_ipdp_vpc")

    # Wait for a new accepted token at IB output.  The valid signals are
    # level-like in practice, so suppress duplicate forks while the same
    # (pc15, opcode) remains visible without a stall/flush boundary.
    def trigger_ib(idx, _caps):
        active = (int(inst_vld[slot].value[idx]) != 0
                  and int(id_stall.value[idx]) == 0
                  and int(vpc_wf.value[idx]) != 0
                  and int(flush_ok.value[idx]) != 0)
        if not active:
            return False
        if idx == 0:
            return True
        prev_active = (int(inst_vld[slot].value[idx - 1]) != 0
                       and int(id_stall.value[idx - 1]) == 0
                       and int(vpc_wf.value[idx - 1]) != 0
                       and int(flush_ok.value[idx - 1]) != 0)
        if not prev_active:
            return True
        return (int(inst_data[slot].value[idx]) != int(inst_data[slot].value[idx - 1])
                or int(inst_pc[slot].value[idx]) != int(inst_pc[slot].value[idx - 1]))

    pat.wait(trigger_ib)
    pat.capture("ifu_ib.inst", inst_data[slot])
    pat.capture("ifu_ib.pc15", inst_pc[slot])
    pat.capture("pcgen.pc", pcgen_pc)
    pat.capture("pcgen.vpc", vpc_wf)
    pat.capture("cycle_pcgen_ib", cycle_cnt)

    def _selected_value(waves, lane_key):
        def capture_selected(idx, caps):
            lane = int(caps[lane_key])
            return int(waves[lane].value[idx]) if lane >= 0 else -1
        return capture_selected

    # ---- Stage 2: IDU ID decode (3-wide, cross-pipe match) ----
    def _id_match_lane(idx, caps):
        inst = caps["ifu_ib.inst"]
        pc15 = caps["ifu_ib.pc15"]
        for i in range(3):
            if (int(id_vld[i].value[idx]) != 0
                    and int(id_data[i].value[idx]) == inst
                    and int(id_pc[i].value[idx]) == pc15):
                return i
        return -1

    def wait_id_decode(idx, caps):
        return _id_match_lane(idx, caps) >= 0
    pat.wait(wait_id_decode, guard=flush_ok)
    pat.capture("id_decode.lane", _id_match_lane)
    pat.capture("id_decode.inst", _selected_value(id_data, "id_decode.lane"))
    pat.capture("id_decode.pc15", _selected_value(id_pc, "id_decode.lane"))
    pat.capture("cycle_id_decode", cycle_cnt)

    # ---- Stage 3: IDU IR rename (4-wide after 3→4 expansion, cross-pipe) ----
    # Match by pc15 only — instruction word changes at IR because 16-bit
    # compressed instructions (RVC) are expanded to their 32-bit equivalents.
    def _ir_match_lane(idx, caps):
        pc15 = caps["id_decode.pc15"]
        for i in range(4):
            if (int(ir_vld[i].value[idx]) != 0
                    and int(ir_pc[i].value[idx]) == pc15):
                return i
        return -1

    def wait_ir_rename(idx, caps):
        return _ir_match_lane(idx, caps) >= 0
    pat.wait(wait_ir_rename, guard=flush_ok)
    pat.capture("ir_rename.lane", _ir_match_lane)
    pat.capture("ir_rename.inst", _selected_value(ir_data, "ir_rename.lane"))
    pat.capture("ir_rename.pc15", _selected_value(ir_pc, "ir_rename.lane"))
    pat.capture("cycle_ir_rename", cycle_cnt)

    def _is_match_lane(idx, caps):
        inst = caps["ir_rename.inst"]
        pc15 = caps["ir_rename.pc15"]
        for i in range(4):
            if (int(is_vld[i].value[idx]) != 0
                    and int(is_data[i].value[idx]) == inst
                    and int(is_pc[i].value[idx]) == pc15):
                return i
        return -1

    # ---- Stage 4+5: ROB allocate + AIQ create (try both AIQ0 and AIQ1) ----
    # Scan all 4 AIQ create ports (AIQ0×2 + AIQ1×2) to find which pipe the
    # instruction was dispatched to.  Returns (queue, port) or (-1, -1).
    def _aiq_match_queue_port(idx, caps):
        pc15 = caps["ifu_ib.pc15"]
        inst = caps.get("ir_rename.inst", caps["ifu_ib.inst"])
        for q in range(2):
            for c in range(2):
                if int(aiq_ens[q][c].value[idx]) != 0:
                    if (int(aiq_c_data[q][c].value[idx]) == inst
                            and int(aiq_c_pc[q][c].value[idx]) == pc15):
                        return (q, c)
        return (-1, -1)

    def aiq_matches(idx, caps):
        q, _c = _aiq_match_queue_port(idx, caps)
        return q >= 0

    def _aiq_match_queue(idx, caps):
        q, _c = _aiq_match_queue_port(idx, caps)
        return q

    def _aiq_match_port(idx, caps):
        _q, c = _aiq_match_queue_port(idx, caps)
        return c

    def _aiq_match_iid(idx, caps):
        q, c = _aiq_match_queue_port(idx, caps)
        if q < 0:
            return -1
        return int(aiq_iids[q][c].value[idx])

    def _aiq_match_opcode(idx, caps):
        q, c = _aiq_match_queue_port(idx, caps)
        if q < 0:
            return -1
        return int(aiq_c_data[q][c].value[idx])

    def _aiq_match_pc15(idx, caps):
        q, c = _aiq_match_queue_port(idx, caps)
        if q < 0:
            return -1
        return int(aiq_c_pc[q][c].value[idx])

    def wait_is_dispatch(idx, caps):
        return (_is_match_lane(idx, caps) >= 0
                and any(int(rob_creates[i].value[idx]) != 0 for i in range(4))
                and aiq_matches(idx, caps))

    def _rob_create_mask(idx, _caps):
        mask = 0
        for i in range(4):
            mask |= (int(rob_creates[i].value[idx]) != 0) << i
        return mask

    pat.wait(wait_is_dispatch, guard=flush_ok)
    pat.capture("is_stage.lane", _is_match_lane)
    pat.capture("is_stage.inst", _selected_value(is_data, "is_stage.lane"))
    pat.capture("is_stage.pc15", _selected_value(is_pc, "is_stage.lane"))
    pat.capture("rob_alloc.create_mask", _rob_create_mask)
    pat.capture("rob_alloc.iid", _aiq_match_iid)
    pat.capture("cycle_rob_alloc", cycle_cnt)
    pat.capture("aiq.queue", _aiq_match_queue)
    pat.capture("aiq.port", _aiq_match_port)
    pat.capture("aiq.iid", _aiq_match_iid)
    pat.capture("aiq.opcode", _aiq_match_opcode)
    pat.capture("aiq.pc15", _aiq_match_pc15)
    pat.capture("cycle_aiq_create", cycle_cnt)

    # ---- Stage 6+7+8: RF pipe launch + decode + IU receive ----
    # Use captured aiq.queue to select the correct pipe's signals.
    # Pipe1 lacks opcode/expt_vld/decd_expt_vld — skip those checks.
    def _q(caps):
        return int(caps["aiq.queue"])

    def wait_rf_pipe_iu(idx, caps):
        q = _q(caps)
        if not (int(rf_vld[q].value[idx]) != 0 and int(rf_pd_vld[q].value[idx]) != 0):
            return False
        if int(rf_iid[q].value[idx]) != caps["aiq.iid"]:
            return False
        if rf_opcode[q] is not None:
            if int(rf_opcode[q].value[idx]) != caps["aiq.opcode"]:
                return False
        if rf_expt_vld[q] is not None:
            if int(rf_expt_vld[q].value[idx]) != 0:
                return False
        if decd_expt[q] is not None:
            if int(decd_expt[q].value[idx]) != 0:
                return False
        return (int(iu_sel[q].value[idx]) != 0
                and int(iu_iid[q].value[idx]) == int(rf_iid[q].value[idx])
                and int(iu_func[q].value[idx]) == int(rf_func[q].value[idx])
                and int(iu_dst[q].value[idx]) == int(rf_dst[q].value[idx]))
    pat.wait(wait_rf_pipe_iu, guard=flush_ok)
    # Use lambdas for pipe-specific captures — resolve signal from captured queue
    pat.capture("rf_pipe.iid", lambda idx, caps: int(rf_iid[_q(caps)].value[idx]))
    pat.capture("rf_pipe.opcode", lambda idx, caps: int(rf_opcode[_q(caps)].value[idx]) if rf_opcode[_q(caps)] is not None else -1)
    pat.capture("rf_pipe.func", lambda idx, caps: int(rf_func[_q(caps)].value[idx]))
    pat.capture("rf_pipe.dst_vld", lambda idx, caps: int(rf_dst_vld[_q(caps)].value[idx]))
    pat.capture("rf_pipe.dst_preg", lambda idx, caps: int(rf_dst[_q(caps)].value[idx]))
    pat.capture("cycle_rf_issue", cycle_cnt)
    pat.capture("rf_decode.iid", lambda idx, caps: int(rf_iid[_q(caps)].value[idx]))
    pat.capture("rf_decode.opcode", lambda idx, caps: int(rf_opcode[_q(caps)].value[idx]) if rf_opcode[_q(caps)] is not None else -1)
    pat.capture("rf_decode.func", lambda idx, caps: int(decd_func[_q(caps)].value[idx]))
    pat.capture("cycle_rf_decode", cycle_cnt)
    pat.capture("iu_recv.iid", lambda idx, caps: int(iu_iid[_q(caps)].value[idx]))
    pat.capture("iu_recv.func", lambda idx, caps: int(iu_func[_q(caps)].value[idx]))
    pat.capture("iu_recv.dst_preg", lambda idx, caps: int(iu_dst[_q(caps)].value[idx]))
    pat.capture("cycle_iu_exec", cycle_cnt)

    # ---- Stage 9: IU pipe complete ----
    def wait_iu_cmplt(idx, caps):
        q = _q(caps)
        if not (int(cbus_cmplt[q].value[idx]) != 0
                and int(cbus_iid[q].value[idx]) == caps["iu_recv.iid"]):
            return False
        if caps["rf_pipe.dst_vld"] == 0:
            return True
        return int(alu_vld[q].value[idx]) != 0 and int(alu_preg[q].value[idx]) == caps["iu_recv.dst_preg"]
    pat.wait(wait_iu_cmplt, guard=flush_ok)
    pat.capture("iu_cmplt.rt_iid", lambda idx, caps: int(rt_iid[_q(caps)].value[idx]))
    pat.capture("cycle_iu_cmplt", cycle_cnt)

    def _commit_matches(idx, caps):
        rt = caps["iu_cmplt.rt_iid"]
        piped_iid = caps["rf_pipe.iid"]
        if rt != piped_iid:
            return -1
        for i in range(3):
            if int(commits[i].value[idx]) != 0 and int(commit_iids[i].value[idx]) == rt:
                return i
        return -1

    def _retire_matches(idx, caps):
        iid = caps["rf_pipe.iid"]
        for i in range(3):
            if ((int(retires[i].value[idx]) != 0 or int(retire_vlds[i].value[idx]) != 0)
                    and int(retire_iids[i].value[idx]) == iid):
                return i
        return -1

    # ---- Stage 10+11: RTU commit + retire ----
    # Commit and architectural retire can appear in the same sampled cycle.
    def wait_rtu_commit_retire(idx, caps):
        return _commit_matches(idx, caps) >= 0 and _retire_matches(idx, caps) >= 0

    def _commit_iid(idx, caps):
        commit_slot = _commit_matches(idx, caps)
        return int(commit_iids[commit_slot].value[idx]) if commit_slot >= 0 else -1

    def _retire_iid(idx, caps):
        retire_slot = _retire_matches(idx, caps)
        return int(retire_iids[retire_slot].value[idx]) if retire_slot >= 0 else -1

    def _retire_entry_pc(idx, caps):
        retire_slot = _retire_matches(idx, caps)
        return int(retire_pcs[retire_slot].value[idx]) if retire_slot >= 0 else -1

    def _retire_entry_pc15(idx, caps):
        entry_pc = _retire_entry_pc(idx, caps)
        return (entry_pc >> 1) & 0x7fff if entry_pc >= 0 else -1

    def _retire_target_pc(_idx, caps):
        return int(caps["ifu_ib.pc15"]) << 1

    def _retire_target_offset(idx, caps):
        entry_pc15 = _retire_entry_pc15(idx, caps)
        return int(caps["ifu_ib.pc15"]) - entry_pc15 if entry_pc15 >= 0 else -1

    pat.wait(wait_rtu_commit_retire, guard=flush_ok)
    pat.capture("rtu_commit.slot", _commit_matches)
    pat.capture("rtu_commit.iid", _commit_iid)
    pat.capture("cycle_rtu_commit", cycle_cnt)
    pat.capture("rtu_retire.slot", _retire_matches)
    pat.capture("rtu_retire.iid", _retire_iid)
    pat.capture("rtu_retire.entry_pc", _retire_entry_pc)
    pat.capture("rtu_retire.entry_pc15", _retire_entry_pc15)
    pat.capture("rtu_retire.target_pc", _retire_target_pc)
    pat.capture("rtu_retire.target_offset_pc15", _retire_target_offset)
    pat.capture("cycle_rtu_retire", cycle_cnt)

    pat.timeout(TIMEOUT)
    return pat


def compute_stage_timing(result, match_idx):
    """Extract per-stage cycle numbers and compute delta from previous stage.

    Returns list of dicts: [{"stage": name, "cycle": int, "delta": int}, ...]
    Delta is cycles since the previous stage (first stage delta = 0).
    """
    timing = []
    prev_cycle = None
    for stage in STAGE_ORDER:
        key = f"cycle_{stage}"
        if key not in result.captures:
            continue
        val = result.captures[key].value[match_idx]
        if val is None:
            break
        cycle = int(val)
        delta = cycle - prev_cycle if prev_cycle is not None else 0
        timing.append({"stage": stage, "cycle": cycle, "delta": delta})
        prev_cycle = cycle
    return timing


def _json_value(val):
    """Convert numpy scalar capture values to JSON-friendly Python values."""
    if val is None:
        return None
    if isinstance(val, np.generic):
        return val.item()
    if isinstance(val, list):
        return [_json_value(v) for v in val]
    try:
        return int(val)
    except (TypeError, ValueError, OverflowError):
        return str(val)


def build_match_record(result, i, slot):
    """Build one flattened match record with slot kept as metadata."""
    stage_timing = compute_stage_timing(result, i)
    captures = {
        name: _json_value(wf.value[i])
        for name, wf in result.captures.items()
    }
    pipe = captures.get("aiq.queue", -1)
    return {
        "id": None,
        "entry_slot": slot,
        "pipe": pipe,
        "local_match_id": i,
        "start_cycle": int(result.start.value[i]),
        "end_cycle": int(result.end.value[i]),
        "duration": int(result.duration.value[i]),
        "status": MatchStatus(result.status.value[i]).name,
        "captures": captures,
        "stage_timing": stage_timing,
    }


def sort_match_key(match):
    """Sort by traced entry point first, then slot/pipe for deterministic ties."""
    entry_cycle = match["captures"].get("cycle_pcgen_ib")
    if entry_cycle is None:
        entry_cycle = match["start_cycle"]
    return (int(entry_cycle), match["entry_slot"], match["pipe"], match["local_match_id"])


def compute_flat_stage_stats(matches):
    """Compute stage timing statistics across all flattened OK matches."""
    stats = {}
    ok_matches = [m for m in matches if m["status"] == "OK"]
    for stage in STAGE_ORDER:
        rows = [
            t for m in ok_matches for t in m["stage_timing"]
            if t["stage"] == stage
        ]
        if not rows:
            continue
        cycles = [int(t["cycle"]) for t in rows]
        deltas = [int(t["delta"]) for t in rows]
        stats[stage] = {
            "cycle_avg": sum(cycles) / len(cycles),
            "cycle_min": min(cycles),
            "cycle_max": max(cycles),
            "delta_avg": sum(deltas) / len(deltas),
            "delta_min": min(deltas),
            "delta_max": max(deltas),
        }
    return stats


def compute_status_stage_counts(matches, filter_pipe=None):
    """Count terminal stage by match status for timeout/debug triage.

    Args:
        filter_pipe: if set, only count matches for this pipe.
    """
    counts = {}
    for match in matches:
        if filter_pipe is not None and match["pipe"] != filter_pipe:
            continue
        status = match["status"]
        stage = match["stage_timing"][-1]["stage"] if match["stage_timing"] else "none"
        counts.setdefault(status, {})
        counts[status][stage] = counts[status].get(stage, 0) + 1
    return counts


def format_match(result, i, slot):
    """Format a single match for text output with per-stage timing."""
    status = MatchStatus(result.status.value[i]).name
    start = result.start.value[i]
    end = result.end.value[i]
    dur = result.duration.value[i]
    lines = [f"  Match #{i} [{status}]  slot={slot}  cycles {start}->{end}  dur={dur}"]

    # Per-stage timing header
    stage_timing = compute_stage_timing(result, i)
    if stage_timing:
        header = "    Stage timing (cycle / delta):"
        items = []
        for st in stage_timing:
            items.append(f"{st['stage']}={st['cycle']}(+{st['delta']})")
        lines.append(header)
        lines.append("      " + " | ".join(items))

    # Signal captures (skip cycle_* keys, already shown above)
    for name, wf in result.captures.items():
        if name.startswith("cycle_"):
            continue
        val = wf.value[i]
        lines.append(f"    {name} = 0x{int(val):x}")
    return "\n".join(lines)


def format_flat_match(match):
    """Format one flattened match for text output."""
    lines = [
        f"  Match #{match['id']} [{match['status']}]"
        f"  slot={match['entry_slot']} pipe={match['pipe']}"
        f"  local={match['local_match_id']}"
        f"  cycles {match['start_cycle']}->{match['end_cycle']}"
        f"  dur={match['duration']}"
    ]

    if match["stage_timing"]:
        items = [
            f"{st['stage']}={st['cycle']}(+{st['delta']})"
            for st in match["stage_timing"]
        ]
        lines.append("    Stage timing (cycle / delta):")
        lines.append("      " + " | ".join(items))

    for name, val in match["captures"].items():
        if name.startswith("cycle_"):
            continue
        if val is None:
            continue
        if isinstance(val, int):
            lines.append(f"    {name} = 0x{val:x}")
        else:
            lines.append(f"    {name} = {val}")
    return "\n".join(lines)


def main():
    with FsdbReader(FSDB) as reader:
        print(f"[INFO] Opened {FSDB}")

        all_results = {}
        for slot in range(3):
            label = f"inst{slot}"
            print(f"\n[INFO] Building trace: {label}")
            pat = build_trace(reader, slot)

            print(f"[INFO] Running trace: {label} (cycles 0-{END_CYCLE})...")
            start = time.time()
            result = pat.match(start_cycle=0, end_cycle=END_CYCLE)
            elapsed = time.time() - start

            ok = int(np.sum(result.status.value == MatchStatus.OK))
            to = int(np.sum(result.status.value == MatchStatus.TIMEOUT))
            rv = int(np.sum(result.status.value == MatchStatus.REQUIRE_VIOLATED))
            print(f"[INFO] {label}: {len(result.start.value)} matches"
                  f" (OK={ok} TIMEOUT={to} REQ_VIOL={rv})"
                  f" in {elapsed:.1f}s")

            # Print first few OK matches
            ok_idx = np.where(result.status.value == MatchStatus.OK)[0]
            for j in ok_idx[:3]:
                print(format_match(result, j, slot))

            all_results[label] = result

    # Save flattened reports
    os.makedirs(OUTPUT, exist_ok=True)

    matches = []
    for label, result in all_results.items():
        slot = int(label[4:])
        for i in range(len(result.start.value)):
            matches.append(build_match_record(result, i, slot))

    matches.sort(key=sort_match_key)
    for i, match in enumerate(matches):
        match["id"] = i

    status_counts = {
        status.name: sum(1 for m in matches if m["status"] == status.name)
        for status in MatchStatus
    }
    stage_stats = compute_flat_stage_stats(matches)
    status_stage_counts = compute_status_stage_counts(matches)

    trace = {
        "trace_name": "openc910_inst_lifecycle",
        "layout": "flattened_by_entry_cycle",
        "slots": 3,
        "pipes": 2,
        "start_cycle": 0,
        "end_cycle": END_CYCLE,
        "status_counts": status_counts,
        "status_stage_counts": status_stage_counts,
        "stage_stats": stage_stats,
        "matches": matches,
    }
    with open(f"{OUTPUT}/inst_trace.json", "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2)

    lines = [
        "Trace: openc910_inst_lifecycle",
        "  Layout: flattened by cycle_pcgen_ib, slot/pipe kept as metadata",
        "  Stages: pcgen -> ifu_ib -> id_decode -> ir_rename -> rob_alloc",
        "          -> is_aiq -> rf_pipe -> rf_decode -> iu_recv",
        "          -> iu_cmplt -> rtu_commit -> rtu_retire",
        f"  Results: {len(matches)} total",
        f"    OK: {status_counts['OK']}, TIMEOUT: {status_counts['TIMEOUT']}, "
        f"REQUIRE_VIOLATED: {status_counts['REQUIRE_VIOLATED']}",
        "",
    ]
    # Per-pipe breakdown
    for p in range(2):
        pm = [m for m in matches if m["pipe"] == p]
        pok = sum(1 for m in pm if m["status"] == "OK")
        pto = sum(1 for m in pm if m["status"] == "TIMEOUT")
        prv = sum(1 for m in pm if m["status"] == "REQUIRE_VIOLATED")
        lines.append(f"  pipe{p}: {len(pm)} matches (OK={pok} TIMEOUT={pto} REQ_VIOL={prv})")
    lines.append("")
    for status in ("TIMEOUT", "REQUIRE_VIOLATED"):
        stage_counts = status_stage_counts.get(status, {})
        if not stage_counts:
            continue
        lines.append(f"  {status} terminal stage counts (all pipes):")
        for stage, count in sorted(stage_counts.items(), key=lambda item: (-item[1], item[0])):
            # Show per-pipe breakdown
            p0 = compute_status_stage_counts(matches, filter_pipe=0).get(status, {}).get(stage, 0)
            p1 = compute_status_stage_counts(matches, filter_pipe=1).get(status, {}).get(stage, 0)
            lines.append(f"    {stage:14s}  {count} (p0={p0} p1={p1})")
        lines.append("")

    if stage_stats:
        lines.append("  Stage timing summary (cycle [min..max] / delta [min..max]):")
        for stage, stats in stage_stats.items():
            lines.append(
                f"    {stage:14s}  cy={stats['cycle_avg']:6.1f} [{stats['cycle_min']}..{stats['cycle_max']}]"
                f"  d={stats['delta_avg']:5.1f} [{stats['delta_min']}..{stats['delta_max']}]"
            )
        lines.append("")

    ok_matches = [m for m in matches if m["status"] == "OK"]
    for match in ok_matches:
        lines.append(format_flat_match(match))
        lines.append("")

    with open(f"{OUTPUT}/inst_trace.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[INFO] Saved {OUTPUT}/inst_trace.json and inst_trace.txt")

    print("\n[INFO] Done.")


if __name__ == "__main__":
    main()
