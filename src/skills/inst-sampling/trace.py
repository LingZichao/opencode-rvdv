#!/usr/bin/env python3
"""Wavekit trace: OpenC910 instruction lifecycle 

Usage:
  .venv/bin/python src/skills/inst-sampling/trace.py
"""

import os
import time

from wavekit import FsdbReader
from wavekit.pattern import Pattern, MatchStatus

FSDB = "openc910/smart_run/work_force/novas.fsdb"
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
    """Build an 11-stage instruction trace using wavekit's native Pattern API."""

    # ---- Pre-load all waveforms ----
    inst_data = [_load(reader, f"x_ct_ifu_top.ifu_idu_ib_inst{i}_data[31:0]") for i in range(3)]
    id_data = [_load(reader, f"x_ct_idu_top.x_ct_idu_id_dp.id_inst{i}_data[31:0]") for i in range(3)]
    ir_data = [_load(reader, f"x_ct_idu_top.x_ct_idu_ir_dp.ir_inst{i}_data[31:0]") for i in range(3)]
    rob_iids = [_load(reader, f"rtu_idu_rob_inst{i}_iid[6:0]") for i in range(4)]
    rob_creates = [_load(reader, f"idu_rtu_rob_create{i}_en") for i in range(4)]
    rf_iid = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_iid[6:0]")
    rf_func = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_func")
    rf_dst = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_dst_preg[6:0]")
    rf_vld = _load(reader, "x_ct_idu_top.x_ct_idu_rf_ctrl.rf_pipe0_inst_vld")
    rf_pd_vld = _load(reader, "x_ct_idu_top.x_ct_idu_rf_ctrl.ctrl_rf_pipe0_pipedown_vld")
    rf_dst_vld = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.idu_iu_rf_pipe0_dst_vld")
    decd_func = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_func")
    decd_expt = _load(reader, "x_ct_idu_top.x_ct_idu_rf_dp.x_ct_idu_rf_pipe0_decd.pipe0_decd_expt_vld")
    iu_sel = _load(reader, "x_ct_iu_top.idu_iu_rf_pipe0_sel")
    iu_iid = _load(reader, "x_ct_iu_top.idu_iu_rf_pipe0_iid[6:0]")
    iu_func = _load(reader, "x_ct_iu_top.idu_iu_rf_pipe0_func")
    iu_dst = _load(reader, "x_ct_iu_top.idu_iu_rf_pipe0_dst_preg[6:0]")
    alu_vld = _load(reader, "x_ct_iu_top.x_ct_iu_alu0.alu_rbus_ex1_pipex_data_vld")
    alu_preg = _load(reader, "x_ct_iu_top.x_ct_iu_alu0.alu_rbus_ex1_pipex_preg[6:0]")
    cbus_cmplt = _load(reader, "x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe0_cmplt")
    cbus_iid = _load(reader, "x_ct_iu_top.x_ct_iu_cbus.iu_rtu_pipe0_iid[6:0]")
    rt_iid = _load(reader, "iu_rtu_pipe0_iid[6:0]")
    commits = [_load(reader, f"x_ct_rtu_top.rtu_yy_xx_commit{i}") for i in range(3)]
    commit_iids = [_load(reader, f"x_ct_rtu_top.rtu_yy_xx_commit{i}_iid[6:0]") for i in range(3)]
    retire0 = _load(reader, "x_ct_rtu_top.rtu_pad_retire0")
    retire0_vld = _load(reader, "x_ct_rtu_top.rtu_yy_xx_retire0")
    retire_pc = _load(reader, "x_ct_rtu_top.rtu_pad_retire0_pc[39:0]")
    rob_retire_iid = _load(reader, "x_ct_rtu_top.rob_retire_inst0_iid[6:0]")

    # AIQ0 signals
    aiq0_ctrl_en = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.ctrl_aiq0_create0_dp_en")
    aiq0_issue_en = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_xx_issue_en")
    aiq0_bypass = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_bypass_en")
    aiq0_dp_en = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.x_ct_idu_is_aiq0_entry0.x_create_dp_en")
    aiq0_create_en = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.x_ct_idu_is_aiq0_entry0.x_create_en")
    aiq0_entry_in = _load(reader, "x_ct_idu_top.x_ct_idu_is_aiq0.aiq0_entry_create0_in")
    aiq_ens = [[_load(reader, f"x_ct_idu_top.x_ct_idu_is_ctrl.is_dis_aiq{q}_create{c}_en") for c in range(2)] for q in range(2)]
    aiq_iids = [[_load(reader, f"x_ct_idu_top.x_ct_idu_is_dp.is_aiq{q}_create{c}_iid[6:0]") for c in range(2)] for q in range(2)]

    # Flush guard waveform — embed in wait conditions, NOT as .wait() guard
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

    # ---- Build Pattern ----
    pat = Pattern()

    # Stage 1: IFU IB dispatch trigger
    trigger_expr = (
        f"({_s('x_ct_ifu_top.ifu_idu_ib_inst')}{slot}_vld != 0)"
        f" and ({_s('x_ct_idu_top.idu_ifu_id_stall')} == 0)"
        f" and ({_s('x_ct_ifu_top.ifdp_ipdp_vpc')} != 0)"
    )
    pat.wait(safe_wf(reader.eval(trigger_expr, clock=CLOCK, sample_on_posedge=True)))
    pat.capture(f"ifu_ib.inst{slot}", inst_data[slot])

    # Stage 2: IDU ID decode — cross-pipe OR on instruction word
    def wait_id_decode(idx, caps):
        inst = caps[f"ifu_ib.inst{slot}"]
        return (int(id_data[0].value[idx]) == inst
                or int(id_data[1].value[idx]) == inst
                or int(id_data[2].value[idx]) == inst)
    pat.wait(safe(wait_id_decode))
    pat.capture("id_decode.id0", id_data[0])
    pat.capture("id_decode.id1", id_data[1])
    pat.capture("id_decode.id2", id_data[2])

    # Stage 3: IDU IR rename — 3x3 cross-pipe
    def wait_ir_rename(idx, caps):
        id0 = caps["id_decode.id0"]
        id1 = caps["id_decode.id1"]
        id2 = caps["id_decode.id2"]
        v0 = int(ir_data[0].value[idx])
        v1 = int(ir_data[1].value[idx])
        v2 = int(ir_data[2].value[idx])
        return (v0 in (id0, id1, id2)
                or v1 in (id0, id1, id2)
                or v2 in (id0, id1, id2))
    pat.wait(safe(wait_ir_rename))
    for i in range(4):
        pat.capture(f"ir_rename.rob_iid{i}", rob_iids[i])

    # Stage 4: ROB allocate — cross-slot OR
    def wait_rob_alloc(idx, caps):
        return any(int(rob_creates[i].value[idx]) != 0 for i in range(4))
    pat.wait(safe(wait_rob_alloc))
    for i in range(4):
        pat.capture(f"rob_alloc.iid{i}", rob_iids[i])

    # Stage 5: IS AIQ0 create — cross-AIQ IID match
    def wait_aiq0(idx, caps, s=slot):
        if not (int(aiq0_ctrl_en.value[idx]) != 0
                and int(aiq0_issue_en.value[idx]) != 0
                and int(aiq0_bypass.value[idx]) != 0
                and int(aiq0_dp_en.value[idx]) != 0
                and int(aiq0_create_en.value[idx]) == int(aiq0_entry_in.value[idx])):
            return False
        iid = caps[f"rob_alloc.iid{s}"]
        for q in range(2):
            for c in range(2):
                if (int(aiq_ens[q][c].value[idx]) != 0
                        and int(aiq_iids[q][c].value[idx]) == iid):
                    return True
        return False
    pat.wait(safe(wait_aiq0))

    # Stage 6: RF pipe0 launch — IID match against ROB IID
    def wait_rf_pipe0(idx, caps, s=slot):
        return (int(rf_vld.value[idx]) != 0
                and int(rf_pd_vld.value[idx]) != 0
                and int(rf_dst_vld.value[idx]) != 0
                and int(rf_iid.value[idx]) == caps[f"rob_alloc.iid{s}"])
    pat.wait(safe(wait_rf_pipe0))
    pat.capture("rf_pipe0.iid", rf_iid)
    pat.capture("rf_pipe0.func", rf_func)
    pat.capture("rf_pipe0.dst_preg", rf_dst)

    # Stage 7: RF pipe0 decode — IID + func, no exception
    def wait_rf_decode(idx, caps):
        return (int(rf_iid.value[idx]) == caps["rf_pipe0.iid"]
                and int(decd_func.value[idx]) == caps["rf_pipe0.func"]
                and int(decd_expt.value[idx]) == 0)
    pat.wait(safe(wait_rf_decode))
    pat.capture("rf_decode.iid", rf_iid)

    # Stage 8: IU pipe0 receive — sel + IID + func + dst_preg
    def wait_iu_recv(idx, caps):
        return (int(iu_sel.value[idx]) != 0
                and int(iu_iid.value[idx]) == caps["rf_decode.iid"]
                and int(iu_func.value[idx]) == caps["rf_pipe0.func"]
                and int(iu_dst.value[idx]) == caps["rf_pipe0.dst_preg"])
    pat.wait(safe(wait_iu_recv))
    pat.capture("iu_recv.iid", iu_iid)
    pat.capture("iu_recv.dst_preg", iu_dst)

    # Stage 9: IU pipe0 complete — ALU result + cbus
    def wait_iu_cmplt(idx, caps):
        return (int(alu_vld.value[idx]) != 0
                and int(alu_preg.value[idx]) == caps["iu_recv.dst_preg"]
                and int(cbus_cmplt.value[idx]) != 0
                and int(cbus_iid.value[idx]) == caps["iu_recv.iid"])
    pat.wait(safe(wait_iu_cmplt))
    pat.capture("iu_cmplt.rt_iid", rt_iid)

    # Stage 10: RTU commit — cross-slot IID (3 commit slots)
    def wait_rtu_commit(idx, caps):
        rt = caps["iu_cmplt.rt_iid"]
        for i in range(3):
            if (int(commits[i].value[idx]) != 0
                    and int(commit_iids[i].value[idx]) == rt):
                return True
        return False
    pat.wait(safe(wait_rtu_commit))
    pat.capture("rtu_commit.commit0_iid", commit_iids[0])

    # Stage 11: RTU retire
    def wait_rtu_retire(idx, caps):
        return (int(retire0.value[idx]) != 0
                and int(retire0_vld.value[idx]) != 0
                and int(rob_retire_iid.value[idx]) == caps["rtu_commit.commit0_iid"])
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
            f"  Stages: ifu_ib -> id_decode -> ir_rename -> rob_alloc -> is_aiq0",
            f"          -> rf_pipe0 -> rf_decode -> iu_recv -> iu_cmplt",
            f"          -> rtu_commit -> rtu_retire",
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
