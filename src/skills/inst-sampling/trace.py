#!/usr/bin/env python3
"""Wavekit trace: OpenC910 instruction lifecycle.

Tracks an instruction through all pipeline stages from fetch to retirement,
correctly handling crossbar routing at every width-change point.

  OpenC910 Pipeline
  =================

    IFU                       IDU                            IU                  RTU
    ===                       ===                            ==                  ===
    PCGEN → IB ─→ ID ─→ IR ─→ IS ─→ ROB ─→ AIQ ─→ RF ─→ EXEC ─→ CMPLT ─→ COMMIT ─→ RETIRE
    (pc)   [3]   [3]   [4]   [4]   [4]     [2×2]   [2]    [2]     [2]      [3]       [3]

  Slot-losing crossbars:
    ID(3) → IR(4)   RVC expansion (16→32 bit) changes width and pipeline position
    IR → IS         pipedown2/4 mode shuffles positions
    IS → AIQ        4 IS slots → 2 AIQs × 2 ports via crossbar sel signals
    IS → ROB        create0 fixed from IS0; creates1-3 through sel priority
    AIQ → RF        AIQ0 can issue to pipe0 or pipe1

  Tracking strategy:
    • Front-end (before IID): match by (pc15, instruction word)
    • Back-end (after IID):   match by IID assigned at AIQ creation

Usage:
  .venv/bin/python src/skills/inst-sampling/trace.py
"""

import json
import os
import time

import numpy as np

from wavekit import FsdbReader, MatchStatus, Pattern

# =============================================================================
# Configuration
# =============================================================================

FSDB = "/home/c910/lingzichao/opencode-rvdv/workspace/openc910/smart_run/work_force/novas.fsdb"
CLOCK = "tb.clk"
SCOPE = (
    "tb.x_soc.x_cpu_sub_system_axi.x_rv_integration_platform"
    ".x_cpu_top.x_ct_top_0.x_ct_core"
)
OUTPUT = "workspace/instTraces/openc910_inst_lifecycle/report"
TIMEOUT = 500
END_CYCLE = 5000

# Ordered pipeline stage names (keys match cycle_<name> captures below)
STAGE_ORDER = [
    "pcgen_ib",
    "id_decode",
    "ir_rename",
    "rob_alloc",
    "aiq_create",
    "rf_issue",
    "rf_decode",
    "iu_exec",
    "iu_cmplt",
    "rtu_commit",
    "rtu_retire",
]


# =============================================================================
# Helpers
# =============================================================================

def _s(name: str) -> str:
    """Resolve relative signal path to absolute scope."""
    return f"{SCOPE}.{name}"


def _load(reader, name: str):
    """Load a waveform sampled on posedge of CLOCK."""
    return reader.load_waveform(_s(name), clock=CLOCK, sample_on_posedge=True)


def _json_value(val):
    """Convert numpy scalars to JSON-native Python types."""
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


# =============================================================================
# Trace builder
# =============================================================================

def build_trace(reader, slot: int) -> Pattern:
    """Build a full instruction-lifecycle Pattern for one IB output slot.

    Args:
        slot: IB slot index (0–2) to trigger on.
    """

    # =========================================================================
    # Waveform loading — grouped by pipeline unit
    # =========================================================================

    # -- IFU: PC generation & instruction buffer (3 slots) --------------------

    pcgen_pc   = _load(reader, "x_ct_ifu_top.x_ct_ifu_pcgen.pcgen_ifdp_pc[38:0]")
    vpc        = _load(reader, "x_ct_ifu_top.ifdp_ipdp_vpc")

    inst_data  = [_load(reader, f"x_ct_ifu_top.ifu_idu_ib_inst{i}_data[31:0]")   for i in range(3)]
    inst_pc    = [_load(reader, f"x_ct_ifu_top.ifu_idu_ib_inst{i}_data[63:49]")   for i in range(3)]
    inst_vld   = [_load(reader, f"x_ct_ifu_top.ifu_idu_ib_inst{i}_vld")            for i in range(3)]

    # -- IDU: ID stage — decode (3-wide) --------------------------------------

    id_data  = [_load(reader, f"x_ct_idu_top.x_ct_idu_id_dp.id_inst{i}_data[31:0]")        for i in range(3)]
    id_pc    = [_load(reader, f"x_ct_idu_top.x_ct_idu_id_dp.id_inst{i}_data[63:49]")        for i in range(3)]
    id_vld   = [_load(reader, f"x_ct_idu_top.x_ct_idu_id_ctrl.ctrl_top_id_inst{i}_vld")     for i in range(3)]
    id_stall = _load(reader, "x_ct_idu_top.idu_ifu_id_stall")

    # -- IDU: IR stage — rename / pre-decode (4-wide, 16→32 expansion) --------

    ir_data = [_load(reader, f"x_ct_idu_top.x_ct_idu_ir_dp.ir_inst{i}_data[31:0]")          for i in range(4)]
    ir_pc   = [_load(reader, f"x_ct_idu_top.x_ct_idu_ir_dp.ir_inst{i}_data[167:153]")       for i in range(4)]
    ir_vld  = [_load(reader, f"x_ct_idu_top.x_ct_idu_ir_ctrl.ctrl_ir_pipedown_inst{i}_vld") for i in range(4)]

    # -- IDU: IS stage — issue / dispatch (4 slots) ----------------------------

    is_data = [_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.is_inst{i}_read_data[31:0]")    for i in range(4)]
    is_pc   = [_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.is_inst{i}_read_data[199:185]")  for i in range(4)]
    is_vld  = [_load(reader, f"x_ct_idu_top.ctrl_top_is_inst{i}_vld")                        for i in range(4)]

    # -- ROB: entry allocation (4 create ports) --------------------------------

    rob_creates = [_load(reader, f"idu_rtu_rob_create{i}_en")            for i in range(4)]
    rob_iids    = [_load(reader, f"rtu_idu_rob_inst{i}_iid[6:0]")        for i in range(4)]

    # -- AIQ: issue queue entry creation (2 queues × 2 ports each) ------------

    aiq_ens   = [[_load(reader, f"x_ct_idu_top.x_ct_idu_is_ctrl.is_dis_aiq{q}_create{c}_en")       for c in range(2)] for q in range(2)]
    aiq_iids  = [[_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.is_aiq{q}_create{c}_iid[6:0]")       for c in range(2)] for q in range(2)]
    aiq_data  = [[_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.dp_aiq{q}_create{c}_data[31:0]")     for c in range(2)] for q in range(2)]
    aiq_pc    = [[_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.is_aiq{q}_create{c}_data[199:185]")  for c in range(2)] for q in range(2)]

    # -- RF: register file read + issue (2 pipes) -----------------------------
    # Pipe1 lacks opcode, expt_vld, decd_expt_vld — exception handling is pipe0 only.

    rf_iid     = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe{p}_iid[6:0]")   for p in range(2)]
    rf_func    = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe{p}_func")        for p in range(2)]
    rf_dst     = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe{p}_dst_preg[6:0]") for p in range(2)]
    rf_vld     = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_ctrl.rf_pipe{p}_inst_vld")          for p in range(2)]
    rf_pd_vld  = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_ctrl.ctrl_rf_pipe{p}_pipedown_vld") for p in range(2)]
    rf_dst_vld = [_load(reader, f"x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe{p}_dst_vld")     for p in range(2)]

    rf_opcode    = [_load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_opcode[31:0]"), None]
    rf_expt_vld  = [_load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_expt_vld"),     None]
    decd_expt    = [_load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_expt_vld"), None]
    decd_func    = [
        _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_func"),
        _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.pipe1_decd_func"),
    ]

    # -- IU: execution unit (2 pipes) -----------------------------------------

    iu_sel  = [_load(reader, f"x_ct_iu_top.idu_iu_rf_pipe{p}_sel")          for p in range(2)]
    iu_iid  = [_load(reader, f"x_ct_iu_top.idu_iu_rf_pipe{p}_iid[6:0]")    for p in range(2)]
    iu_func = [_load(reader, f"x_ct_iu_top.idu_iu_rf_pipe{p}_func")         for p in range(2)]
    iu_dst  = [_load(reader, f"x_ct_iu_top.idu_iu_rf_pipe{p}_dst_preg[6:0]") for p in range(2)]

    alu_vld  = [_load(reader, f"x_ct_iu_top.x_ct_iu_alu{p}.alu_rbus_ex1_pipex_data_vld") for p in range(2)]
    alu_preg = [_load(reader, f"x_ct_iu_top.x_ct_iu_alu{p}.alu_rbus_ex1_pipex_preg[6:0]") for p in range(2)]

    cbus_cmplt = [_load(reader, f"x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe{p}_cmplt")     for p in range(2)]
    cbus_iid   = [_load(reader, f"x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe{p}_iid[6:0]")  for p in range(2)]
    rt_iid     = [_load(reader, f"iu_rtu_pipe{p}_iid[6:0]")                              for p in range(2)]

    # -- RTU: commit (3 slots) + retire (3 slots) -----------------------------

    commits     = [_load(reader, f"x_ct_rtu_top.rtu_yy_xx_commit{i}")            for i in range(3)]
    commit_iids = [_load(reader, f"x_ct_rtu_top.rtu_yy_xx_commit{i}_iid[6:0]")   for i in range(3)]

    retires     = [_load(reader, f"x_ct_rtu_top.rtu_pad_retire{i}")              for i in range(3)]
    retire_vlds = [_load(reader, f"x_ct_rtu_top.rtu_yy_xx_retire{i}")            for i in range(3)]
    retire_pcs  = [_load(reader, f"x_ct_rtu_top.rtu_pad_retire{i}_pc[39:0]")     for i in range(3)]
    retire_iids = [
        _load(reader, "x_ct_rtu_top.rob_retire_inst0_iid[6:0]"),
        _load(reader, "x_ct_rtu_top.x_ct_rtu_rob.x_ct_rtu_rob_rt.retire_inst1_iid[6:0]"),
        _load(reader, "x_ct_rtu_top.x_ct_rtu_rob.x_ct_rtu_rob_rt.retire_inst2_iid[6:0]"),
    ]

    # -- Flush guard ----------------------------------------------------------
    # If any flush asserts while the trace is in-flight, kill this instance
    # rather than letting it reconnect to a later instruction with the same word/IID.

    flush_ok = reader.eval(
        f"({_s('rtu_yy_xx_flush')} == 0)"
        f" and ({_s('x_ct_ifu_top.rtu_ifu_flush')} == 0)"
        f" and ({_s('x_ct_idu_top.rtu_idu_flush_fe')} == 0)"
        f" and ({_s('x_ct_idu_top.rtu_idu_flush_is')} == 0)",
        clock=CLOCK, sample_on_posedge=True,
    )

    # -- Synthetic cycle counter -----------------------------------------------

    cycle_cnt = pcgen_pc.vectorized_map(
        lambda v: np.arange(len(v), dtype=np.int64), width=64, signed=False,
    )

    # =========================================================================
    # Pattern definition — one stage group at a time
    # =========================================================================
    pat = Pattern()

    # ---- IFU: PCGEN + IB trigger --------------------------------------------

    def _ib_active(idx):
        return (int(inst_vld[slot].value[idx]) != 0
                and int(id_stall.value[idx]) == 0
                and int(vpc.value[idx]) != 0
                and int(flush_ok.value[idx]) != 0)

    def _trigger_ib(idx, _caps):
        if not _ib_active(idx):
            return False
        if idx == 0:
            return True
        # Suppress duplicate forks while same (pc15, opcode) sits at IB output
        # without an intervening stall/flush edge.
        if not _ib_active(idx - 1):
            return True
        return (int(inst_data[slot].value[idx]) != int(inst_data[slot].value[idx - 1])
                or int(inst_pc[slot].value[idx]) != int(inst_pc[slot].value[idx - 1]))

    pat.wait(_trigger_ib)
    pat.capture("ifu_ib.inst",    inst_data[slot])
    pat.capture("ifu_ib.pc15",    inst_pc[slot])
    pat.capture("pcgen.pc",       pcgen_pc)
    pat.capture("pcgen.vpc",      vpc)
    pat.capture("cycle_pcgen_ib", cycle_cnt)

    # -- Helper: pick the matched lane from a list of waveforms ----------------

    def _lane_value(waves, lane_key):
        def pick(idx, caps):
            lane = int(caps[lane_key])
            return int(waves[lane].value[idx]) if lane >= 0 else -1
        return pick

    # ---- IDU ID: decode (3-wide) — match by (inst, pc15) --------------------

    def _match_id(idx, caps):
        inst, pc15 = caps["ifu_ib.inst"], caps["ifu_ib.pc15"]
        for i in range(3):
            if (int(id_vld[i].value[idx]) != 0
                    and int(id_data[i].value[idx]) == inst
                    and int(id_pc[i].value[idx]) == pc15):
                return i
        return -1

    pat.wait(lambda idx, caps: _match_id(idx, caps) >= 0, guard=flush_ok)
    pat.capture("id_decode.lane", _match_id)
    pat.capture("id_decode.inst", _lane_value(id_data, "id_decode.lane"))
    pat.capture("id_decode.pc15", _lane_value(id_pc,   "id_decode.lane"))
    pat.capture("cycle_id_decode", cycle_cnt)

    # ---- IDU IR: rename (4-wide) — match by pc15 only (RVC expansion) --------

    def _match_ir(idx, caps):
        pc15 = caps["id_decode.pc15"]
        for i in range(4):
            if int(ir_vld[i].value[idx]) != 0 and int(ir_pc[i].value[idx]) == pc15:
                return i
        return -1

    pat.wait(lambda idx, caps: _match_ir(idx, caps) >= 0, guard=flush_ok)
    pat.capture("ir_rename.lane", _match_ir)
    pat.capture("ir_rename.inst", _lane_value(ir_data, "ir_rename.lane"))
    pat.capture("ir_rename.pc15", _lane_value(ir_pc,   "ir_rename.lane"))
    pat.capture("cycle_ir_rename", cycle_cnt)

    # ---- IDU IS: dispatch (4 slots) — match by (inst, pc15) ------------------

    def _match_is(idx, caps):
        inst, pc15 = caps["ir_rename.inst"], caps["ir_rename.pc15"]
        for i in range(4):
            if (int(is_vld[i].value[idx]) != 0
                    and int(is_data[i].value[idx]) == inst
                    and int(is_pc[i].value[idx]) == pc15):
                return i
        return -1

    # ---- ROB + AIQ: allocation + issue queue entry --------------------------
    # Try all 4 AIQ create ports (AIQ0×2 + AIQ1×2); capture the matched queue/port.
    # From this point forward the instruction identity is carried by IID.

    def _match_aiq(idx, caps):
        inst, pc15 = caps.get("ir_rename.inst", caps["ifu_ib.inst"]), caps["ifu_ib.pc15"]
        for q in range(2):
            for c in range(2):
                if (int(aiq_ens[q][c].value[idx]) != 0
                        and int(aiq_data[q][c].value[idx]) == inst
                        and int(aiq_pc[q][c].value[idx]) == pc15):
                    return (q, c)
        return (-1, -1)

    def _rob_mask(idx, _caps):
        return sum((int(rob_creates[i].value[idx]) != 0) << i for i in range(4))

    def _wait_is_rob_aiq(idx, caps):
        return (_match_is(idx, caps) >= 0
                and any(int(rob_creates[i].value[idx]) != 0 for i in range(4))
                and _match_aiq(idx, caps)[0] >= 0)

    pat.wait(_wait_is_rob_aiq, guard=flush_ok)
    pat.capture("is_stage.lane",   _match_is)
    pat.capture("is_stage.inst",   _lane_value(is_data, "is_stage.lane"))
    pat.capture("is_stage.pc15",   _lane_value(is_pc,   "is_stage.lane"))
    pat.capture("rob_alloc.create_mask", _rob_mask)
    pat.capture("rob_alloc.iid",   lambda idx, caps: int(aiq_iids[_match_aiq(idx, caps)[0]][_match_aiq(idx, caps)[1]].value[idx]))
    pat.capture("cycle_rob_alloc", cycle_cnt)
    pat.capture("aiq.queue",       lambda idx, caps: _match_aiq(idx, caps)[0])
    pat.capture("aiq.port",        lambda idx, caps: _match_aiq(idx, caps)[1])
    pat.capture("aiq.iid",         lambda idx, caps: int(aiq_iids[_match_aiq(idx, caps)[0]][_match_aiq(idx, caps)[1]].value[idx]))
    pat.capture("aiq.opcode",      lambda idx, caps: int(aiq_data[_match_aiq(idx, caps)[0]][_match_aiq(idx, caps)[1]].value[idx]))
    pat.capture("aiq.pc15",        lambda idx, caps: int(aiq_pc[_match_aiq(idx, caps)[0]][_match_aiq(idx, caps)[1]].value[idx]))
    pat.capture("cycle_aiq_create", cycle_cnt)

    # ---- RF → IU: pipe issue, decode, IU receive ----------------------------
    # Use captured aiq.queue to index the correct pipe's signals.

    def _q(caps):
        return int(caps["aiq.queue"])

    def _wait_rf_iu(idx, caps):
        q = _q(caps)
        if not (int(rf_vld[q].value[idx]) != 0 and int(rf_pd_vld[q].value[idx]) != 0):
            return False
        if int(rf_iid[q].value[idx]) != caps["aiq.iid"]:
            return False
        if rf_opcode[q] is not None and int(rf_opcode[q].value[idx]) != caps["aiq.opcode"]:
            return False
        if rf_expt_vld[q] is not None and int(rf_expt_vld[q].value[idx]) != 0:
            return False
        if decd_expt[q] is not None and int(decd_expt[q].value[idx]) != 0:
            return False
        return (int(iu_sel[q].value[idx]) != 0
                and int(iu_iid[q].value[idx]) == int(rf_iid[q].value[idx])
                and int(iu_func[q].value[idx]) == int(rf_func[q].value[idx])
                and int(iu_dst[q].value[idx]) == int(rf_dst[q].value[idx]))

    def _pipe_cap(wf):
        """Factory: capture pipe-indexed waveform value."""
        return lambda idx, caps: int(wf[_q(caps)].value[idx])

    def _opt_pipe_cap(wf, default=-1):
        """Factory: capture optional pipe-indexed waveform (None → default)."""
        return lambda idx, caps: int(wf[_q(caps)].value[idx]) if wf[_q(caps)] is not None else default

    pat.wait(_wait_rf_iu, guard=flush_ok)
    # RF pipe (issue)
    pat.capture("rf_pipe.iid",      _pipe_cap(rf_iid))
    pat.capture("rf_pipe.opcode",   _opt_pipe_cap(rf_opcode))
    pat.capture("rf_pipe.func",     _pipe_cap(rf_func))
    pat.capture("rf_pipe.dst_vld",  _pipe_cap(rf_dst_vld))
    pat.capture("rf_pipe.dst_preg", _pipe_cap(rf_dst))
    pat.capture("cycle_rf_issue",   cycle_cnt)
    # RF decode (1 cycle later in same pipe)
    pat.capture("rf_decode.iid",    _pipe_cap(rf_iid))
    pat.capture("rf_decode.opcode", _opt_pipe_cap(rf_opcode))
    pat.capture("rf_decode.func",   _pipe_cap(decd_func))
    pat.capture("cycle_rf_decode",  cycle_cnt)
    # IU receive
    pat.capture("iu_recv.iid",      _pipe_cap(iu_iid))
    pat.capture("iu_recv.func",     _pipe_cap(iu_func))
    pat.capture("iu_recv.dst_preg", _pipe_cap(iu_dst))
    pat.capture("cycle_iu_exec",    cycle_cnt)

    # ---- IU: execution complete ---------------------------------------------

    def _wait_iu_cmplt(idx, caps):
        q = _q(caps)
        if not (int(cbus_cmplt[q].value[idx]) != 0
                and int(cbus_iid[q].value[idx]) == caps["iu_recv.iid"]):
            return False
        if caps["rf_pipe.dst_vld"] == 0:
            return True
        return int(alu_vld[q].value[idx]) != 0 and int(alu_preg[q].value[idx]) == caps["iu_recv.dst_preg"]

    pat.wait(_wait_iu_cmplt, guard=flush_ok)
    pat.capture("iu_cmplt.rt_iid", _pipe_cap(rt_iid))
    pat.capture("cycle_iu_cmplt",  cycle_cnt)

    # ---- RTU: commit + retire (3 slots each) --------------------------------

    def _match_commit(idx, caps):
        rt = caps["iu_cmplt.rt_iid"]
        if rt != caps["rf_pipe.iid"]:
            return -1
        for i in range(3):
            if int(commits[i].value[idx]) != 0 and int(commit_iids[i].value[idx]) == rt:
                return i
        return -1

    def _match_retire(idx, caps):
        iid = caps["rf_pipe.iid"]
        for i in range(3):
            if ((int(retires[i].value[idx]) != 0 or int(retire_vlds[i].value[idx]) != 0)
                    and int(retire_iids[i].value[idx]) == iid):
                return i
        return -1

    pat.wait(lambda idx, caps: _match_commit(idx, caps) >= 0 and _match_retire(idx, caps) >= 0,
             guard=flush_ok)
    pat.capture("rtu_commit.slot",               _match_commit)
    pat.capture("rtu_commit.iid",                lambda idx, caps: int(commit_iids[_match_commit(idx, caps)].value[idx]))
    pat.capture("cycle_rtu_commit",              cycle_cnt)
    pat.capture("rtu_retire.slot",               _match_retire)
    pat.capture("rtu_retire.iid",                lambda idx, caps: int(retire_iids[_match_retire(idx, caps)].value[idx]))
    pat.capture("rtu_retire.entry_pc",           lambda idx, caps: int(retire_pcs[_match_retire(idx, caps)].value[idx]))
    pat.capture("rtu_retire.entry_pc15",         lambda idx, caps: (int(retire_pcs[_match_retire(idx, caps)].value[idx]) >> 1) & 0x7fff)
    pat.capture("rtu_retire.target_pc",          lambda _idx, caps: int(caps["ifu_ib.pc15"]) << 1)
    pat.capture("rtu_retire.target_offset_pc15", lambda idx, caps: int(caps["ifu_ib.pc15"]) - ((int(retire_pcs[_match_retire(idx, caps)].value[idx]) >> 1) & 0x7fff))
    pat.capture("cycle_rtu_retire",              cycle_cnt)

    pat.timeout(TIMEOUT)
    return pat


# =============================================================================
# Output formatting
# =============================================================================

def compute_stage_timing(result, match_idx):
    """Extract per-stage cycle numbers and inter-stage deltas."""
    timing = []
    prev = None
    for stage in STAGE_ORDER:
        key = f"cycle_{stage}"
        if key not in result.captures:
            continue
        val = result.captures[key].value[match_idx]
        if val is None:
            break
        cyc = int(val)
        timing.append({"stage": stage, "cycle": cyc, "delta": cyc - prev if prev is not None else 0})
        prev = cyc
    return timing


def build_match_record(result, i, slot):
    """Build one flattened match record from a Pattern result entry."""
    stage_timing = compute_stage_timing(result, i)
    captures = {name: _json_value(wf.value[i]) for name, wf in result.captures.items()}
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
    """Sort by entry cycle, then slot/pipe for deterministic ordering."""
    entry = match["captures"].get("cycle_pcgen_ib", match["start_cycle"])
    return (int(entry), match["entry_slot"], match["pipe"], match["local_match_id"])


def compute_flat_stage_stats(matches):
    """Aggregate stage timing statistics across all OK matches."""
    stats = {}
    for stage in STAGE_ORDER:
        rows = [t for m in matches if m["status"] == "OK"
                for t in m["stage_timing"] if t["stage"] == stage]
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
    """Count terminal stage by match status, optionally filtered to one pipe."""
    counts = {}
    for m in matches:
        if filter_pipe is not None and m["pipe"] != filter_pipe:
            continue
        status = m["status"]
        stage = m["stage_timing"][-1]["stage"] if m["stage_timing"] else "none"
        counts.setdefault(status, {})
        counts[status][stage] = counts[status].get(stage, 0) + 1
    return counts


def format_flat_match(match):
    """Format one flattened match for text report output."""
    lines = [
        f"  Match #{match['id']} [{match['status']}]"
        f"  slot={match['entry_slot']} pipe={match['pipe']}"
        f"  local={match['local_match_id']}"
        f"  cycles {match['start_cycle']}->{match['end_cycle']}"
        f"  dur={match['duration']}"
    ]
    if match["stage_timing"]:
        items = [f"{st['stage']}={st['cycle']}(+{st['delta']})" for st in match["stage_timing"]]
        lines.append("    Stage timing (cycle / delta):")
        lines.append("      " + " | ".join(items))
    for name, val in match["captures"].items():
        if name.startswith("cycle_"):
            continue
        if val is None:
            continue
        fmt = f"0x{val:x}" if isinstance(val, int) else f"{val}"
        lines.append(f"    {name} = {fmt}")
    return "\n".join(lines)


def format_match(result, i, slot):
    """Format a single raw Pattern match for console output with stage timing."""
    status = MatchStatus(result.status.value[i]).name
    lines = [f"  Match #{i} [{status}]  slot={slot}  cycles {result.start.value[i]}->{result.end.value[i]}  dur={result.duration.value[i]}"]
    stage_timing = compute_stage_timing(result, i)
    if stage_timing:
        items = [f"{st['stage']}={st['cycle']}(+{st['delta']})" for st in stage_timing]
        lines.append("    Stage timing (cycle / delta):")
        lines.append("      " + " | ".join(items))
    for name, wf in result.captures.items():
        if name.startswith("cycle_"):
            continue
        lines.append(f"    {name} = 0x{int(wf.value[i]):x}")
    return "\n".join(lines)


# =============================================================================
# Main
# =============================================================================

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

            ok_idx = np.where(result.status.value == MatchStatus.OK)[0]
            for j in ok_idx[:3]:
                print(format_match(result, j, slot))

            all_results[label] = result

    os.makedirs(OUTPUT, exist_ok=True)

    # Flatten and sort all matches
    matches = []
    for label, result in all_results.items():
        slot = int(label[4:])
        for i in range(len(result.start.value)):
            matches.append(build_match_record(result, i, slot))

    matches.sort(key=sort_match_key)
    for i, m in enumerate(matches):
        m["id"] = i

    # Aggregate statistics
    status_counts = {s.name: sum(1 for m in matches if m["status"] == s.name) for s in MatchStatus}
    stage_stats = compute_flat_stage_stats(matches)
    status_stage_counts = compute_status_stage_counts(matches)

    # JSON output
    trace = {
        "trace_name": "openc910_inst_lifecycle",
        "layout": "flattened_by_entry_cycle",
        "slots": 3, "pipes": 2,
        "start_cycle": 0, "end_cycle": END_CYCLE,
        "status_counts": status_counts,
        "status_stage_counts": status_stage_counts,
        "stage_stats": stage_stats,
        "matches": matches,
    }
    with open(f"{OUTPUT}/inst_trace.json", "w", encoding="utf-8") as f:
        json.dump(trace, f, indent=2)

    # Text report
    lines = [
        "Trace: openc910_inst_lifecycle",
        "  Layout: flattened by cycle_pcgen_ib, slot/pipe kept as metadata",
        "  Stages: IFU(PCGEN→IB) → IDU(ID→IR→IS) → ROB → AIQ → RF → IU(EXEC→CMPLT) → RTU(COMMIT→RETIRE)",
        f"  Results: {len(matches)} total",
        f"    OK: {status_counts['OK']}, TIMEOUT: {status_counts['TIMEOUT']}, "
        f"REQUIRE_VIOLATED: {status_counts['REQUIRE_VIOLATED']}",
        "",
    ]
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
        for stage, count in sorted(stage_counts.items(), key=lambda x: (-x[1], x[0])):
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

    for m in (m for m in matches if m["status"] == "OK"):
        lines.append(format_flat_match(m))
        lines.append("")

    with open(f"{OUTPUT}/inst_trace.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"[INFO] Saved {OUTPUT}/inst_trace.json and inst_trace.txt")

    print("\n[INFO] Done.")


if __name__ == "__main__":
    main()
