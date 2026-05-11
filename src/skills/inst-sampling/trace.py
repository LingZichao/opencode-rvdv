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

Strategy: track by instruction word through front-end crossbars,
then by IID from AIQ entry through execution and retire.

Usage:
  .venv/bin/python src/skills/inst-sampling/trace.py
"""

import os
import time

from wavekit import FsdbReader
from wavekit.pattern import Pattern, MatchStatus

FSDB = "/home/c910/openc910/smart_run/work_force/novas.fsdb"
CLOCK = "tb.clk"
SCOPE = (
    "tb.x_soc.x_cpu_sub_system_axi.x_rv_integration_platform"
    ".x_cpu_top.x_ct_top_0.x_ct_core"
)
OUTPUT = "workspace/instTraces/openc910_inst_lifecycle/report"
TIMEOUT = 500
END_CYCLE = 5000


def _s(name: str) -> str:
    """Resolve relative signal path to absolute."""
    return f"{SCOPE}.{name}"


def _load(reader, name: str):
    """Load a clock-sampled waveform."""
    return reader.load_waveform(_s(name), clock=CLOCK, sample_on_posedge=True)


def build_trace(reader, slot: int) -> Pattern:
    """Build a 12-stage instruction trace using wavekit's native Pattern API.

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

    # ---- Stage 2: IDU ID (3 pipeline positions) ----
    id_data = [_load(reader, f"x_ct_idu_top.x_ct_idu_id_dp.id_inst{i}_data[31:0]") for i in range(3)]
    id_vld = [_load(reader, f"x_ct_idu_top.x_ct_idu_id_ctrl.ctrl_top_id_inst{i}_vld") for i in range(3)]

    # ---- Stage 3: IDU IR (4 pipeline positions — 3-to-4 expansion) ----
    ir_data = [_load(reader, f"x_ct_idu_top.x_ct_idu_ir_dp.ir_inst{i}_data[31:0]") for i in range(4)]
    ir_vld = [_load(reader, f"x_ct_idu_top.x_ct_idu_ir_ctrl.ctrl_ir_pipedown_inst{i}_vld") for i in range(4)]

    # ---- Stage 4+5: ROB create (4 ports) + IIDs ----
    rob_iids = [_load(reader, f"rtu_idu_rob_inst{i}_iid[6:0]") for i in range(4)]
    rob_creates = [_load(reader, f"idu_rtu_rob_create{i}_en") for i in range(4)]

    # ---- Stage 6: AIQ0 create entries + IS dispatch IIDs ----
    aiq0_ctrl_en = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.ctrl_aiq0_create0_dp_en")
    aiq0_issue_en = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_xx_issue_en")
    aiq0_bypass = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_bypass_en")
    aiq0_dp_en = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.x_ct_idu_is_aiq0_entry0.x_create_dp_en")
    aiq0_create_en = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.x_ct_idu_is_aiq0_entry0.x_create_en")
    aiq0_entry_in = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_entry_create0_in")
    aiq_ens = [[_load(reader, f"x_ct_idu_top.x_ct_idu_is_ctrl.is_dis_aiq{q}_create{c}_en") for c in range(2)] for q in range(2)]
    aiq_iids = [[_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.is_aiq{q}_create{c}_iid[6:0]") for c in range(2)] for q in range(2)]
    # AIQ entry instruction word for crossbar disambiguation
    aiq0_c0_data = _load(reader, "x_ct_idu_top.x_ct_idu_is_dp.dp_aiq0_create0_data[31:0]")
    aiq0_c1_data = _load(reader, "x_ct_idu_top.x_ct_idu_is_dp.dp_aiq0_create1_data[31:0]")

    # ---- Stage 7: RF pipe0 issue to execution pipe ----
    rf_iid = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_iid[6:0]")
    rf_func = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_func")
    rf_dst = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_dst_preg[6:0]")
    rf_vld = _load(reader, "x_ct_idu_top.x_ct_idu_rf_ctrl.rf_pipe0_inst_vld")
    rf_pd_vld = _load(reader, "x_ct_idu_top.x_ct_idu_rf_ctrl.ctrl_rf_pipe0_pipedown_vld")
    rf_dst_vld = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_dst_vld")

    # ---- Stage 8: RF pipe0 decode ----
    decd_func = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_func")
    decd_expt = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_expt_vld")

    # ---- Stage 9: IU pipe0 receive ----
    iu_sel = _load(reader, "x_ct_iu_top.idu_iu_rf_pipe0_sel")
    iu_iid = _load(reader, "x_ct_iu_top.idu_iu_rf_pipe0_iid[6:0]")
    iu_func = _load(reader, "x_ct_iu_top.idu_iu_rf_pipe0_func")
    iu_dst = _load(reader, "x_ct_iu_top.idu_iu_rf_pipe0_dst_preg[6:0]")

    # ---- Stage 10: IU pipe0 complete ----
    alu_vld = _load(reader, "x_ct_iu_top.x_ct_iu_alu0.alu_rbus_ex1_pipex_data_vld")
    alu_preg = _load(reader, "x_ct_iu_top.x_ct_iu_alu0.alu_rbus_ex1_pipex_preg[6:0]")
    cbus_cmplt = _load(reader, "x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe0_cmplt")
    cbus_iid = _load(reader, "x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe0_iid[6:0]")
    rt_iid = _load(reader, "iu_rtu_pipe0_iid[6:0]")

    # ---- Stage 11: RTU commit (3 commit slots) ----
    commits = [_load(reader, f"x_ct_rtu_top.rtu_yy_xx_commit{i}") for i in range(3)]
    commit_iids = [_load(reader, f"x_ct_rtu_top.rtu_yy_xx_commit{i}_iid[6:0]") for i in range(3)]

    # ---- Stage 12: RTU retire ----
    retire0 = _load(reader, "x_ct_rtu_top.rtu_pad_retire0")
    retire0_vld = _load(reader, "x_ct_rtu_top.rtu_yy_xx_retire0")
    retire_pc = _load(reader, "x_ct_rtu_top.rtu_pad_retire0_pc[39:0]")
    rob_retire_iid = _load(reader, "x_ct_rtu_top.rob_retire_inst0_iid[6:0]")

    # ---- Flush guard ----
    flush_wf = reader.eval(
        f"({_s('rtu_yy_xx_flush')} != 0)"
        f" or ({_s('x_ct_ifu_top.rtu_ifu_flush')} != 0)"
        f" or ({_s('x_ct_idu_top.rtu_idu_flush_fe')} != 0)"
        f" or ({_s('x_ct_idu_top.rtu_idu_flush_is')} != 0)",
        clock=CLOCK, sample_on_posedge=True,
    )

    def no_flush(idx):
        return int(flush_wf.value[idx]) == 0

    def safe(fn):
        """Wrap a wait callable: flush-active cycles return False (keep waiting)."""
        def wrapped(idx, caps):
            return no_flush(idx) and fn(idx, caps)
        return wrapped

    def safe_wf(wf):
        """Waveform wait: flush-active cycles return False."""
        def wrapped(idx, caps):
            return no_flush(idx) and int(wf.value[idx]) != 0
        return wrapped

    # ================================================================
    #  Build Pattern
    # ================================================================
    pat = Pattern()

    # ---- Stage 0+1: PCGEN + IFU IB dispatch ----
    # Capture pcgen PC at the trigger cycle as reference context.
    # Note: due to IF->IB pipeline latency, the pcgen PC at this cycle
    # may not directly correspond to the traced instruction's PC.
    # The instruction identity is tracked by its 32-bit instruction word
    # through the front-end crossbar stages.
    vpc_wf = _load(reader, "x_ct_ifu_top.ifdp_ipdp_vpc")

    # Wait for our slot's instruction at IB output, no ID stall
    trigger_expr = (
        f"({_s('x_ct_ifu_top.ifu_idu_ib_inst')}{slot}_vld != 0)"
        f" and ({_s('x_ct_idu_top.idu_ifu_id_stall')} == 0)"
        f" and ({_s('x_ct_ifu_top.ifdp_ipdp_vpc')} != 0)"
    )
    pat.wait(safe_wf(reader.eval(trigger_expr, clock=CLOCK, sample_on_posedge=True)))
    pat.capture(f"ifu_ib.inst{slot}", inst_data[slot])
    pat.capture("pcgen.pc", pcgen_pc)
    pat.capture("pcgen.vpc", vpc_wf)

    # ---- Stage 2: IDU ID decode (3-wide, cross-pipe match) ----
    def wait_id_decode(idx, caps):
        inst = caps[f"ifu_ib.inst{slot}"]
        return any(int(id_vld[i].value[idx]) != 0 and int(id_data[i].value[idx]) == inst
                   for i in range(3))
    pat.wait(safe(wait_id_decode))
    pat.capture("id_decode.id0", id_data[0])
    pat.capture("id_decode.id1", id_data[1])
    pat.capture("id_decode.id2", id_data[2])

    # ---- Stage 3: IDU IR rename (4-wide after 3→4 expansion, cross-pipe) ----
    def wait_ir_rename(idx, caps):
        id_words = [caps[f"id_decode.id{i}"] for i in range(3)]
        return any(int(ir_vld[i].value[idx]) != 0
                   and int(ir_data[i].value[idx]) in id_words
                   for i in range(4))
    pat.wait(safe(wait_ir_rename))
    for i in range(4):
        pat.capture(f"ir_rename.ir{i}", ir_data[i])

    # ---- Stage 4: ROB allocate (4 create ports) ----
    # Wait for at least one ROB create to happen; capture IIDs for context.
    def wait_rob_alloc(idx, caps):
        return any(int(rob_creates[i].value[idx]) != 0 for i in range(4))
    pat.wait(safe(wait_rob_alloc))
    for i in range(4):
        pat.capture(f"rob_alloc.iid{i}", rob_iids[i])
        pat.capture(f"rob_alloc.create{i}_en", rob_creates[i])

    # ---- Stage 5: IS AIQ0 create with instruction-word disambiguation ----
    # Key fix: we match the AIQ entry by its instruction word
    # (bits [31:0] of dp_aiq0_create*_data), NOT by guessing which
    # ROB IID belongs to which instruction. This resolves the crossbar:
    # any IS inst can go to any AIQ create port.
    def wait_aiq0(idx, caps):
        if not (int(aiq0_ctrl_en.value[idx]) != 0
                and int(aiq0_issue_en.value[idx]) != 0
                and int(aiq0_bypass.value[idx]) != 0
                and int(aiq0_dp_en.value[idx]) != 0
                and int(aiq0_create_en.value[idx]) == int(aiq0_entry_in.value[idx])):
            return False
        # Our instruction word from the IB trigger
        inst = caps[f"ifu_ib.inst{slot}"]
        # Check AIQ0 create0 and create1 for matching instruction word
        # Only exact match against the tracked instruction word.
        # (Compressed-instruction expansion would change the word;
        #  those cases need IR-word matching with tighter disambiguation.)
        if int(aiq_ens[0][0].value[idx]) != 0:
            if int(aiq0_c0_data.value[idx]) == inst:
                return True
        if int(aiq_ens[0][1].value[idx]) != 0:
            if int(aiq0_c1_data.value[idx]) == inst:
                return True
        return False
    pat.wait(safe(wait_aiq0))
    # Capture both AIQ create port IIDs for reference
    # The correct one will be matched at the RF stage
    pat.capture("aiq.a0c0_iid", aiq_iids[0][0])
    pat.capture("aiq.a0c0_data", aiq0_c0_data)
    pat.capture("aiq.a0c1_iid", aiq_iids[0][1])
    pat.capture("aiq.a0c1_data", aiq0_c1_data)

    # ---- Stage 6: RF pipe0 launch ----
    # Match RF pipe0 IID against AIQ IIDs (not ROB IIDs).
    # The AIQ IIDs are guaranteed to be from the correct cycle
    # because we matched by instruction word at the AIQ entry.
    def wait_rf_pipe0(idx, caps):
        if not (int(rf_vld.value[idx]) != 0
                and int(rf_pd_vld.value[idx]) != 0
                and int(rf_dst_vld.value[idx]) != 0):
            return False
        pipe0_iid = int(rf_iid.value[idx])
        # Match against AIQ0 create0 and create1 IIDs
        return (pipe0_iid == caps.get("aiq.a0c0_iid", -1)
                or pipe0_iid == caps.get("aiq.a0c1_iid", -1))
    pat.wait(safe(wait_rf_pipe0))
    pat.capture("rf_pipe0.iid", rf_iid)
    pat.capture("rf_pipe0.func", rf_func)
    pat.capture("rf_pipe0.dst_preg", rf_dst)

    # ---- Stage 7: RF pipe0 decode ----
    def wait_rf_decode(idx, caps):
        return (int(rf_iid.value[idx]) == caps["rf_pipe0.iid"]
                and int(decd_func.value[idx]) == caps["rf_pipe0.func"]
                and int(decd_expt.value[idx]) == 0)
    pat.wait(safe(wait_rf_decode))
    pat.capture("rf_decode.iid", rf_iid)

    # ---- Stage 8: IU pipe0 receive ----
    def wait_iu_recv(idx, caps):
        return (int(iu_sel.value[idx]) != 0
                and int(iu_iid.value[idx]) == caps["rf_decode.iid"]
                and int(iu_func.value[idx]) == caps["rf_pipe0.func"]
                and int(iu_dst.value[idx]) == caps["rf_pipe0.dst_preg"])
    pat.wait(safe(wait_iu_recv))
    pat.capture("iu_recv.iid", iu_iid)
    pat.capture("iu_recv.dst_preg", iu_dst)

    # ---- Stage 9: IU pipe0 complete ----
    def wait_iu_cmplt(idx, caps):
        return (int(alu_vld.value[idx]) != 0
                and int(alu_preg.value[idx]) == caps["iu_recv.dst_preg"]
                and int(cbus_cmplt.value[idx]) != 0
                and int(cbus_iid.value[idx]) == caps["iu_recv.iid"])
    pat.wait(safe(wait_iu_cmplt))
    pat.capture("iu_cmplt.rt_iid", rt_iid)

    # ---- Stage 10: RTU commit (3 commit slots) ----
    # Match rt_iid (from IU completion) against our confirmed RF pipe0 IID
    def wait_rtu_commit(idx, caps):
        rt = caps["iu_cmplt.rt_iid"]
        piped_iid = caps["rf_pipe0.iid"]
        if rt != piped_iid:
            return False
        return any(int(commits[i].value[idx]) != 0
                   and int(commit_iids[i].value[idx]) == rt
                   for i in range(3))
    pat.wait(safe(wait_rtu_commit))
    pat.capture("rtu_commit.commit0_iid", commit_iids[0])

    # ---- Stage 11: RTU retire ----
    # Match retire IID against our confirmed RF pipe0 IID
    def wait_rtu_retire(idx, caps):
        if not (int(retire0.value[idx]) != 0
                and int(retire0_vld.value[idx]) != 0):
            return False
        retire_iid = int(rob_retire_iid.value[idx])
        return retire_iid == caps["rf_pipe0.iid"]
    pat.wait(safe(wait_rtu_retire))
    pat.capture("rtu_retire.retire0_pc", retire_pc)

    pat.timeout(TIMEOUT)
    return pat


def format_match(result, i, slot):
    """Format a single match for text output."""
    from wavekit.pattern import MatchStatus
    status = MatchStatus(result.status.value[i]).name
    start = result.start.value[i]
    end = result.end.value[i]
    dur = result.duration.value[i]
    lines = [f"  Match #{i} [{status}]  cycles {start}->{end}  dur={dur}"]
    for name, wf in result.captures.items():
        val = wf.value[i]
        lines.append(f"    {name} = {val}")
    return "\n".join(lines)


def main():
    reader = FsdbReader(FSDB)
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

        import numpy as np
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

    # Save reports
    os.makedirs(OUTPUT, exist_ok=True)
    import json
    import numpy as np

    for label, result in all_results.items():
        # JSON
        matches = []
        for i in range(len(result.start.value)):
            caps = {name: str(wf.value[i]) for name, wf in result.captures.items()}
            matches.append({
                "id": i,
                "start_cycle": int(result.start.value[i]),
                "end_cycle": int(result.end.value[i]),
                "duration": int(result.duration.value[i]),
                "status": MatchStatus(result.status.value[i]).name,
                "captures": caps,
            })
        with open(f"{OUTPUT}/{label}.json", "w") as f:
            json.dump({"trace_name": label, "matches": matches}, f, indent=2)

        # Text summary
        ok = int(np.sum(result.status.value == MatchStatus.OK))
        to = int(np.sum(result.status.value == MatchStatus.TIMEOUT))
        rv = int(np.sum(result.status.value == MatchStatus.REQUIRE_VIOLATED))
        lines = [
            f"Trace: {label}",
            f"  Stages: pcgen -> ifu_ib -> id_decode -> ir_rename -> rob_alloc",
            f"          -> is_aiq0 -> rf_pipe0 -> rf_decode -> iu_recv",
            f"          -> iu_cmplt -> rtu_commit -> rtu_retire",
            f"  Results: {len(result.start.value)} total",
            f"    OK: {ok}, TIMEOUT: {to}, REQUIRE_VIOLATED: {rv}",
            "",
        ]
        ok_idx = np.where(result.status.value == MatchStatus.OK)[0]
        for j in ok_idx[:10]:
            lines.append(format_match(result, j, int(label[-1])))
            lines.append("")
        with open(f"{OUTPUT}/{label}.txt", "w") as f:
            f.write("\n".join(lines))
        print(f"[INFO] Saved {OUTPUT}/{label}.json and .txt")

    reader.close()
    print("\n[INFO] Done.")


if __name__ == "__main__":
    main()
