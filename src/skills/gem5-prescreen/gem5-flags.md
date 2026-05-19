# gem5 Debug & Trace Skill

This document covers gem5 debug mode, debug flags, trace output, and how to run local gem5 for pre-screening. Use this as a reference when analyzing gem5 simulation logs to make architectural judgments.

---

## Debug Flag Selection Matrix

| Goal | First-pass flags | Evidence to inspect |
|---|---|---|
| Instruction stream / target opcode reached | `ExecAll,Faults` | `trace.out`, `stats.txt` |
| Fault, exception, or m5 exit behavior | `ExecAll,Faults,PseudoInst` | `trace.out`, `simout`, `simerr` |
| Branch behavior | `ExecAll,Faults,Branch,BTB,RAS` | `trace.out`, branch-related `stats.txt` keys |
| Load/store, cache, or atomic behavior | `ExecAll,Faults,Cache,LSQ,LSQUnit,LLSC` | `trace.out`, cache/LSQ `stats.txt` keys |
| Address translation, PMP, or CSR behavior | `ExecAll,Faults,TLB,TLBVerbose,PageTableWalker,PMP,RiscvMisc` | `trace.out`, `simerr` |

Use `ExecAll,Faults` as the normal first pass. If `trace.out` becomes too large, narrow the flags or add `--debug-start` / `--debug-end`.

## Version And Flag Checks

Debug flag names and source line numbers can differ between gem5 versions. Treat source locations in this file as hints from the source snapshot used to write the guide. Before relying on optional, compound, or less common flags, verify them with:

```bash
./build/RISCV/gem5.debug --debug-help
```

## gem5 Debug Flags

Debug flags control what internal events gem5 logs. They are enabled via `--debug-flags=Flag1,Flag2` and disabled with `-Flag`.

### Debug CLI Options

| Option | Description |
|---|---|
| `--debug-flags=FLAG[,FLAG]` | Enable debug flags (`-FLAG` disables) |
| `--debug-file=FILE` | Output file (default: cout). Append `.gz` for auto-compression |
| `--debug-start=TICK` | Start debug output at specific tick |
| `--debug-end=TICK` | End debug output at specific tick |
| `--debug-break=TICK[,TICK]` | Create breakpoint(s) at tick(s) |
| `--debug-help` | Print all available debug flags |
| `--debug-activate=EXPR` | Only debug matching sim objects |
| `--debug-ignore=EXPR` | Ignore matching sim objects |

### Exec Flags (Instruction Execution Trace)

The `Exec` family is the most important for instruction-level debugging:

| Flag | Type | Description |
|---|---|---|
| `ExecEnable` | Filter | **Master switch** - no exec tracing without this |
| `ExecOpClass` | Format | Include operand class (e.g., IntAlu, IntMult, MemRead) |
| `ExecThread` | Format | Include thread ID |
| `ExecEffAddr` | Format | Include effective address for memory ops |
| `ExecResult` | Format | Include instruction results |
| `ExecSymbol` | Format | Include symbol names (function names) |
| `ExecMicro` | Filter | Include micro-ops in trace |
| `ExecMacro` | Filter | Include macro-ops in trace |
| `ExecFaulting` | Trace | Trace faulting instructions |
| `ExecUser` | Filter | Trace user-mode instructions only |
| `ExecKernel` | Filter | Trace kernel-mode instructions only |
| `ExecAsid` | Format | Include ASID in trace |
| `ExecCPSeq` | Format | Instruction sequence number |
| `ExecFetchSeq` | Format | Fetch sequence number |
| `ExecRegDelta` | - | Register delta changes |
| `ExecFlags` | Format | Include instruction flags |

**Compound flags:**
- `Exec` = ExecEnable + ExecOpClass + ExecThread + ExecEffAddr + ExecResult + ExecSymbol + ExecMicro + ExecMacro + ExecFaulting + ExecUser + ExecKernel
- `ExecAll` = Exec + ExecCPSeq + ExecFetchSeq + ExecRegDelta + ExecAsid + ExecFlags
- `ExecNoTicks` = Exec + FmtTicksOff (useful for diffing traces)

### CPU Microarchitecture Flags

| Flag | Pipeline Stage | Description |
|---|---|---|
| `Fetch` | Frontend | Instruction fetch |
| `Decode` | Frontend | Instruction decode |
| `Rename` | Frontend | Register renaming |
| `IEW` | Issue/Execute | Issue/Execute/Writeback |
| `Commit` | Backend | Instruction commit |
| `IQ` | Issue | Instruction queue |
| `ROB` | Backend | Reorder buffer |
| `LSQ` | Memory | Load-store queue |
| `LSQUnit` | Memory | LSQ unit details |
| `MemDepUnit` | Memory | Memory dependence unit |
| `StoreSet` | Memory | Store set predictor |
| `FreeList` | Frontend | Physical register free list |
| `DynInst` | - | Dynamic instruction details |
| `O3CPU` | - | O3 CPU top-level events |
| `Activity` | - | CPU activity tracking |
| `Scoreboard` | - | Register scoreboard |
| `Writeback` | Backend | Writeback stage |
| `Branch` | Frontend | Branch prediction |
| `BTB` | Frontend | Branch target buffer |
| `RAS` | Frontend | Return address stack |
| `SimpleCPU` | - | Simple/atomic CPU events |
| `MinorCPU` | - | MinorCPU top-level events |
| `MinorExecute` | - | MinorCPU execute stage |
| `MinorMem` | - | MinorCPU memory access |

**Compound:** `O3CPUAll` = Fetch, Decode, Rename, IEW, Commit, IQ, ROB, FreeList, LSQ, LSQUnit, StoreSet, MemDepUnit, DynInst, O3CPU, Activity, Scoreboard, Writeback

### Branch Predictor Flags

| Flag | Description |
|---|---|
| `Branch` | Branch prediction generic |
| `BTB` | Branch target buffer |
| `RAS` | Return address stack |
| `LTage` | L-TAGE predictor |
| `Tage` | TAGE predictor |
| `TageSCL` | TAGE-SC-L predictor |
| `Predictor` | Generic predictor |
| `Indirect` | Indirect branch predictor |

### Memory System Flags

| Flag | Description |
|---|---|
| `Cache` | Generic cache operations |
| `CacheComp` | Cache compression |
| `CachePort` | Cache port contention |
| `CacheRepl` | Cache replacement policy |
| `CacheTags` | Cache tag lookups |
| `CacheVerbose` | Verbose cache details |
| `MSHR` | Miss status holding registers |
| `HWPrefetch` | Hardware prefetcher |
| `HWPrefetchQueue` | Prefetch queue |
| `DRAM` | DRAM controller |
| `DRAMPower` | DRAM power states |
| `DRAMState` | DRAM state transitions |
| `NVM` | Non-volatile memory |
| `MemCtrl` | Memory controller |
| `MemoryAccess` | General memory access |
| `PacketQueue` | Memory packet queue |
| `MMU` | Memory management unit |
| `TLB` | Translation lookaside buffer |
| `TLBVerbose` | Verbose TLB operations |
| `PageTableWalker` | Page table walker state machine |
| `LLSC` | Load-linked/store-conditional |

**Compound:** `CacheAll` = Cache, CacheComp, CachePort, CacheRepl, CacheVerbose, HWPrefetch, MSHR, PartitionPolicy

### Interconnect / Bus Flags

| Flag | Description |
|---|---|
| `BaseXBar` | Base crossbar |
| `CoherentXBar` | Coherent crossbar |
| `NoncoherentXBar` | Non-coherent crossbar |
| `SnoopFilter` | Snoop filter |
| `Bridge` | Bus bridge |
| `PortTrace` | Port-level tracing |
| `ResponsePort` | Response port |
| `ExternalPort` | External port |
| `TokenPort` | Token port |
| `SysBridge` | System bridge |

**Compound:** `XBar` = BaseXBar, CoherentXBar, NoncoherentXBar, SnoopFilter

### RISC-V Specific Flags

Common RISC-V-specific flags are often defined with `tags=['riscv isa']` in `arch/riscv/SConscript` and `dev/riscv/SConscript`; verify availability with `--debug-help` for the active gem5 build.

| Flag | Source | Description |
|---|---|---|
| `Clint` | `dev/riscv/clint.cc` | Core-local interrupt controller (RISC-V CLINT): tracks PIO read/write, MTIP (machine timer interrupt) post when mtime reaches mtimecmp, MSIP (machine software interrupt) post/clear via msip register |
| `Plic` | `dev/riscv/plic.cc` | Platform-level interrupt controller (RISC-V PLIC): interrupt post/clear per source, priority/threshold/enable register updates, claim/complete handshake, output propagation with timing |
| `PMP` | `arch/riscv/pmp.cc` | Physical memory protection: `pmpCheck()` for every access with VA/PA, PMP config/addr register writes, lock bit enforcement, TOR-mode cascade locking |
| `RiscvMisc` | `arch/riscv/isa.cc:486,681` | All CSR (Control Status Register) access: `readMiscRegNoEffect()` prints CSR name/index/value, `setMiscRegNoEffect()` prints new value being set. High volume: every CSR read/write. |
| `VirtIOMMIO` | `dev/riscv/vio_mmio.cc` | VirtIO MMIO transport layer: MMIO read/write (size, offset, value), kick() callback when guest notifies device to process queue descriptors |
| `Semihosting` | `arch/riscv/semihosting.cc` | RISC-V semihosting: call32/call64 dispatch (operation + args, return code), ebreak semihosting detection (prev/next instruction validation) |
| `LupioBLK/IPI/PIC/RNG/RTC/TMR/TTY/SYS` | `dev/lupio/SConscript` | LupIO RISC-V device family (block, IPI, PIC, RNG, RTC, timer, TTY, SYS). Used in practice with `USE_RISCV_ISA` guard. |

### System / General Flags

| Flag | Description |
|---|---|
| `Interrupt` | Interrupt handling |
| `Faults` | Faults, exceptions, interrupts |
| `Loader` | Binary/ELF loading |
| `PseudoInst` | Pseudo-instructions (m5ops) |
| `SyscallBase` | System call emulation |
| `SyscallVerbose` | Verbose syscall emulation |
| `WorkItems` | Work items tracking |
| `Thread` | Thread context |
| `Context` | CPU context switches |
| `Stack` | Stack operations |
| `Event` | Event queue |
| `Drain` | Drain/checkpoint |
| `Checkpoint` | Checkpoint operations |
| `Config` | Configuration |
| `Timer` | Timer events |
| `ClockDomain` | Clock domain |
| `VoltageDomain` | Voltage domain |
| `PowerDomain` | Power domain |
| `DVFS` | Dynamic voltage/frequency scaling |
| `VtoPhys` | Virtual-to-physical address translation |
| `Vma` | Virtual memory area |
| `GDBAcc/Read/Write/Send/Recv/Misc/Extra` | Remote GDB debugging |

**Compound:** `GDBAll` = All GDB flags
**Compound:** `SyscallAll` = SyscallBase + SyscallVerbose
**Compound:** `Registers` = IntRegs + FloatRegs + VecRegs + VecPredRegs + MatRegs + CCRegs + MiscRegs
**Compound:** `Ruby` = RubyQueue, RubyNetwork, RubyTester, RubyGenerated, RubySlicc, RubySystem, RubyCache, RubyDma, RubyPort, RubySequencer, RubyCacheTrace, RubyPrefetcher, RubyProtocol, RubyHitMiss

### Special Formatting Flags

| Flag | Effect |
|---|---|
| `FmtFlag` | Prefix each message with the flag name that enabled it |
| `FmtStackTrace` | Print a stack trace after every debug message |
| `FmtTicksOff` | Omit tick count prefix from debug messages |
| `FmtVerbose` | More verbose formatting |

### Special Flag: `All`

`All` enables every debug flag. Use with caution: it produces massive output. Always combine with `--debug-start`/`--debug-end` or a narrow `--debug-activate`.

---

## trace.txt / Debug Output

When `--debug-file=trace.txt` is used, gem5 writes all debug output to that file.

### Output Format

Each debug line follows this pattern:
```
TICK: [SimObjectName] [FlagName]: message
```

Example (with `--debug-flags=ExecEnable,ExecOpClass,ExecEffAddr,ExecResult`):
```
500: system.cpu: A0 0x80000000: addi sp, sp, -16 : IntAlu :  D=0x0000003ffffff0
500: system.cpu: A0 0x80000004: sd ra, 8(sp)      : MemWrite :  A=0x3ffffff8 D=0x0000000080000270
```

### Decoding Exec Trace Fields

With full `Exec` flags:
```
TICK: [cpu]: [COMMIT_SEQ] [PC] [DISASM] [OP_CLASS] [EFF_ADDR] [RESULT] [THREAD]
```

| Field | Flag | Example |
|---|---|---|
| PC | (always) | `0x80000000` |
| Disassembly | (always) | `addi sp, sp, -16` |
| Sequence # | ExecCPSeq | `T0 : 42` |
| Op class | ExecOpClass | `IntAlu`, `MemRead`, `MemWrite`, `IntMult`, `FloatAdd` |
| Effective addr | ExecEffAddr | `A=0x3ffffff8` |
| Result | ExecResult | `D=0x0000003ffffff0` |
| Thread ID | ExecThread | `T0` |
| Symbol | ExecSymbol | `main+12`, `printf` |
| Flags | ExecFlags | `[F:1]` |

### Trace File Output Pattern

Debug output is writen to the file specified by `--debug-file`. If not specified, it goes to stdout (cout). If `--debug-file=trace.txt.gz`, output is auto-gzip compressed.

### Using Debug Activate/Ignore to Filter

```bash
# Only show debug for the CPU, not the cache
--debug-flags=Exec --debug-activate=cpu --debug-ignore=cache

# Only show for a specific component
--debug-flags=O3CPUAll --debug-activate='system.cpu'
```

---

## m5out Simulation Output Files

After simulation with `--outdir=<artifact_path>`, `<artifact_path>/` contains:

| File | Description |
|---|---|
| `stats.txt` | **Key file** - All simulation statistics (IPC, CPI, cache misses, branch pred, etc.) |
| `config.ini` | Full system configuration parameters |
| `config.json` | Same as config.ini but in JSON format |
| `config.dot/pdf/svg` | System architecture block diagram |
| `citations.bib` | Paper citations for models used |
| `board.pc.com_1.device` | Terminal output from the simulated system's UART |

### Interpreting stats.txt for Architecture Analysis

stats.txt contains simulation statistics in format:
```
system.cpu.ipc                               0.079110  # IPC: instructions per cycle
system.cpu.cpi                              12.640693  # CPI: cycles per instruction
system.cpu.numCycles                             2920  # Number of cpu cycles simulated
simInsts                                          231  # Number of instructions simulated
hostSeconds                                      0.03  # Real time elapsed on the host
```

Key metrics for architectural analysis:

| Metric | stats.txt Key | What It Tells You |
|---|---|---|
| **IPC/CPI** | `system.cpu.ipc` / `system.cpu.cpi` | Core performance efficiency |
| **Branch mispred rate** | `system.cpu.branchPred.condPredicted` vs `condIncorrect` | Branch predictor accuracy |
| **Cache miss rates** | `system.cpu.dcache.overallMissRate::total` | L1 data cache misses per access |
| **ICache miss rate** | `system.cpu.icache.overallMissRate::total` | L1 instruction cache misses per access |
| **Commit count** | `system.cpu.numCommittedDist` | Distribution of IPC per cycle |
| **ROB occupancy** | `system.cpu.robReadys` | Reorder buffer utilization |
| **Stalled cycles** | Various `StalledCycles` | What causes pipeline stalls |
| **Memory bandwidth** | `system.mem_ctrls.bytesRead/bytesWritten` | DRAM bandwidth utilization |
| **Cache line fills** | `system.cpu.dcache.demandAccesses` | Memory traffic |
| **TLB misses** | `system.cpu.dtlb.hits` / `misses` | TLB effectiveness |

---

## Common Debugging Workflows

### 1. Trace instruction execution
```bash
./build/RISCV/gem5.debug --outdir=<artifact_path> --debug-flags=Exec --debug-file=trace.txt --debug-start=0 --debug-end=100000 config/riscv/fs_bare_metal.py --bare-metal-elf <file>.ELF --mem-start=0x0
```

### 2. Debug pipeline stalls (O3 CPU)
```bash
--debug-flags=O3CPUAll --debug-file=o3_trace.txt
```

### 3. Debug cache behavior
```bash
--debug-flags=CacheAll --debug-file=cache_trace.txt
```

### 4. Debug memory system
```bash
--debug-flags=DRAM,DRAMState,MemCtrl,MemoryAccess,DRAMPower --debug-file=mem_trace.txt
```

### 5. Debug RISC-V interrupts/exceptions
```bash
--debug-flags=Interrupt,Faults,Clint,Plic --debug-file=interrupt_trace.txt
```

### 6. Debug RISC-V address translation (TLB + PTW + PMP)
```bash
--debug-flags=TLB,TLBVerbose,PageTableWalker,PMP --debug-file=tlb_trace.txt
```

### 7. Debug RISC-V CSR access (all CSR reads/writes)
```bash
--debug-flags=RiscvMisc --debug-file=csr_trace.txt
```

### 8. Debug RISC-V LR/SC atomics
```bash
--debug-flags=LLSC --debug-file=llsc_trace.txt
```

### 9. Debug RISC-V VirtIO device interaction
```bash
--debug-flags=VirtIOMMIO,VIO,VIOIface --debug-file=virtio_trace.txt
```

### 10. Diffable trace (no timestamps)
```bash
--debug-flags=ExecNoTicks --debug-file=trace_no_ticks.txt
```

### 11. Comprehensive RISC-V FS debugging
```bash
./build/RISCV/gem5.debug --outdir=<artifact_path> --debug-flags=Exec,TLB,PMP,Interrupt,Faults,Clint,Plic,RiscvMisc --debug-file=full_trace.txt --debug-start=0 --debug-end=500000 config/riscv/fs_bare_metal.py --bare-metal-elf <file>.ELF --mem-start=0x0
```

### 12. Find what flag produced specific output
```bash
--debug-flags=All --debug-flags=FmtFlag --debug-file=trace_with_flags.txt
```

---

## Debug Flag Trigger Conditions

Each debug flag is triggered by specific events/code paths. This section maps flags to their trigger conditions and source locations.

### Exec Flag Triggers

All Exec flags (except ExecFaulting) flow through `src/cpu/exetrace.cc`:

| Flag | Source File | Trigger Condition |
|---|---|---|
| **ExecEnable** | `cpu/exetrace.hh:93` | Checked in `getInstRecord()`. If OFF, returns NULL -> **no tracing at all**. Master gate. |
| **ExecUser** | `cpu/exetrace.cc:66-67` | If ON + thread in user mode -> print. If OFF + user mode -> skip. Filters user-mode traces. |
| **ExecKernel** | `cpu/exetrace.cc:68-69` | If ON + thread in kernel mode -> print. If OFF + kernel mode -> skip. Filters kernel-mode traces. |
| **ExecAsid** | `cpu/exetrace.cc:71-74` | Prints `A<N>` prefix with ASID from `thread->getExecutingAsid()`. Always checked. |
| **ExecThread** | `cpu/exetrace.cc:76-77` | Prints `T<N> : ` prefix with `thread->threadId()`. Always checked. |
| **ExecSymbol** | `cpu/exetrace.cc:83-91` | Looks up PC in `debugSymbolTable`. Prints `@func` or `@func+offset`. Skipped in FS user-mode. |
| **ExecOpClass** | `cpu/exetrace.cc:111-113` | Prints op class (IntAlu/MemRead/FloatAdd/...) when instruction executed (`ran=true`). |
| **ExecResult** | `cpu/exetrace.cc:115-129` | Prints `D=<value>`. If predicated-false -> `Predicated False`. Handles Int/FP/Vector. |
| **ExecEffAddr** | `cpu/exetrace.cc:131-132` | Prints `A=<hex>` when `getMemValid()` is true (memory instruction executed). |
| **ExecFetchSeq** | `cpu/exetrace.cc:134-135` | Prints `FetchSeq=<N>`. Set by O3 commit (commit.cc:1232) and Minor execute (decode.cc:121). |
| **ExecCPSeq** | `cpu/exetrace.cc:137-138` | Prints `CPSeq=<N>`. Set by O3 commit (commit.cc:1233) and Minor execute (execute.cc:882). |
| **ExecFlags** | `cpu/exetrace.cc:140-144` | Prints instruction flags like `flags=(Flag1\|Flag2\|...)`. |
| **ExecMicro** | `cpu/exetrace.cc:175-177` | If ON: each micro-op gets its own trace line. If OFF: micro-ops skipped (except last). |
| **ExecMacro** | `cpu/exetrace.cc:168-174` | If ON + ExecMicro ON: prints macro-op header at first micro-op. If ExecMicro OFF: prints macro-op summary at last micro-op. |
| **ExecFaulting** | `o3/commit.cc:1209`, `minor/execute.cc:982`, `simple/base.cc:264` | If ON: preserves trace data for faulting instructions and dumps them. If OFF: deletes trace data on fault. **TARMAC tracer auto-enables this.** |
| **ExecRegDelta** | `arch/x86/nativetrace.cc:131`, `arch/arm/nativetrace.cc:157` | Not in cpu/ -> used by native execution tracers for register mismatch detection. |

**Exec trace pipeline per CPU model:**

| Model | Trace Record Created | Trace Dumped | ExecFaulting Checked |
|---|---|---|---|
| **O3** | `o3/fetch.cc:1043` | `o3/commit.cc:1234` (after setFetchSeq/setCPSeq) | `o3/commit.cc:1209-1216` |
| **Minor** | `minor/decode.cc:115` | `minor/execute.cc:1401` (after setCPSeq/setPredicate) | `minor/execute.cc:982-985` |
| **Atomic** | `simple/base.cc:386` | `simple/base.cc:483` (after setPredicate) | `simple/base.cc:264` |
| **Timing** | Same as Atomic | Same as Atomic | Same `traceFault()` |

### O3 CPU Pipeline Flag Triggers

#### Fetch (116 DPRINTF sites -> `cpu/o3/fetch.cc`, `cpu/minor/fetch1.cc`, `cpu/minor/fetch2.cc`, `cpu/pred/2bit_local.cc`)

Triggers on:
- **State transitions**: blocked -> squashing -> running -> waiting (cache response / ITLB / trap / quiesce / I-cache retry)
- **ICache/ITLB**: fetching cache line for addr, doing I-cache access, out of MSHRs, translation fault
- **Branch handling**: branch detected at PC, predicted target, unconditional/conditional
- **Squash**: squashing from decode/commit, setting PC, squashing outstanding I-cache miss
- **Instruction creation**: PC created [sn], instruction is: \<disassembly\>
- **Queue management**: fetch queue entry created, sending to decode, adding instructions to decode queue
- **Drain/idle**: no more threads, waiting for drain, no active thread

#### Decode (65 DPRINTF sites -> `cpu/o3/decode.cc`, ISA decoder files)

O3 triggers on:
- **Stall/block**: stall from Rename, blocking/unblocking, skid buffer insertion
- **Squash**: squashing due to incorrect branch prediction, squashing from IEW
- **Processing**: processing [tid], not blocked so running, sending to rename, instruction has fault
- **Activity**: activating/deactivating stage

ISA decoder files trigger on: decoded instruction type, prefix bytes, opcode bytes, modrm/SIB/displacement/immediate collection.

#### Rename (54 DPRINTF sites -> `cpu/o3/rename.cc`, `cpu/o3/rename_map.cc`)

Triggers on:
- **Squash**: squashing instructions, freeing phys regs of misspeculated instructions
- **Resource limits**: cannot rename -> no free LQ/SQ/ROB/IQ entries; stall due to ROB/IQ/LSQ full
- **Serialization**: serialize before/after instruction encountered
- **History**: removing history entry with seq num, removing committed inst from history buffer
- **Register mapping**: renamed reg \<arch\> to physical reg \<idx\>, old mapping was \<old\>
- **Processing**: processing [tid], sending to IEW, processing instruction [lli] with PC

#### IEW (66 DPRINTF sites -> `cpu/o3/iew.cc`, `cpu/o3/regfile.hh`)

Triggers on:
- **Squash**: squashing all instructions, memory violation squashing violator+younger
- **Dispatch**: examining instruction from skid buffer, adding PC to IQ, FU full, IQ full
- **Issue**: issuing instruction PC to FU, memory instruction (store/load) encountered, nop encountered
- **Execute**: executing instructions from IQ, processing PC, calculating address, delayed translation, predicated false, branch mispredicted/correctly predicted
- **Writeback**: current wb cycle, width, numInst, wbActual, inserting [sn] PC into commit insts
- **Stall**: stall from Commit, stall because IQ full, ROB still squashing, bandwidth full
- **RegFile**: access to int/float/vector register, has data/value, setting register to value

#### Commit (34 DPRINTF sites -> `cpu/o3/commit.cc`)

Triggers on:
- **Squash**: squashing due to branch mispred/order violation, redirecting to PC, trap/TC squash
- **Commit**: trying to commit, head inst ready/marks, committing instruction with PC/fault
- **Interrupt**: pending interrupt cleared/handled/detected
- **Barriers**: encountered barrier/non-speculative instruction at ROB head; waiting for all stores to writeback
- **ROB state**: ROB has N insts and N free entries; retiring squashed inst; inserting PC into ROB
- **Drain/flow**: generating trap event, TC squash event, pending interrupt handled

#### IQ (28 DPRINTF sites -> `cpu/o3/inst_queue.cc`)

Triggers on:
- Adding instruction [sn] PC to IQ (also non-speculative)
- Attempting to schedule ready instructions; not able to schedule any
- Issuing instruction PC to FU; completing mem instruction PC
- Waking dependents of completed instruction; dependent instruction PC ready
- Rescheduling mem inst (blocked -> unblocked); marking non-speculative as ready to issue
- Squashing instructions in IQ until seq num
- IQ sharing policy set (Partitioned/Threshold)

#### ROB (11 DPRINTF sites -> `cpu/o3/rob.cc`)

Triggers on:
- Adding inst PC to ROB; now has N instructions
- Retiring head instruction [sn] PC
- Squashing instructions until [sn]; done squashing; starting to squash within ROB
- Reached head of instruction list while squashing; does not need to squash (empty)

#### LSQ / LSQUnit (58 DPRINTF sites -> `cpu/o3/lsq.cc`, `cpu/o3/lsq_unit.cc`)

**LSQ** triggers on:
- LSQ sharing policy set to Dynamic/Threshold/Partitioned
- Error packet received for addr; invalidation received; TLBI Ext Sync
- SingleDataRequest/SplitDataRequest addr, isBlocking; throttle ReadResp
- retryRespEvent scheduled for tick

**LSQUnit** triggers on:
- **Insert**: inserting load/store PC, idx [sn]; LQ/SQ size and occupancy
- **Execute**: executing load/store PC; load not executed from predication; fault on store
- **Commit/Writeback**: committing head load; marking store able to write back; writing back store idx PC to Addr
- **Forward**: store-to-load forwarding, forwarding mismatch
- **Snoop**: got snoop for address; conflicting load; HitExternal Snoop
- **Squash**: squashing until [sn]; load/store instruction squashed
- **Stall**: unstalling/stalling store; cache blocked; strictly ordered load

#### MemDepUnit (27 DPRINTF sites -> `cpu/o3/mem_dep_unit.cc`)

Triggers on:
- Inserted load/store barrier \<type\> SN; outstanding barrier count
- Load searching for producer [sn]; producer found / no dependency for inst PC
- Inserting store/atomic PC [sn]
- Marking registers as ready; instruction has its memory responded; still waiting on response
- Replaying mem instruction; completed mem instruction; barrier completed
- Waking up dependent inst [sn] PC
- Squashing inst [sn]; passing violating PCs to store sets

#### StoreSet (17 DPRINTF sites -> `cpu/o3/store_set.cc`)

Triggers on:
- Neither load nor store had valid store set; load/store had valid store set
- Load/store had smaller store set -> merging them
- Wiping predictor state because N ld/st executed
- Store updated LFST, SSID; inst has no SSID; inst with SSID had no LFST / had LFST entry
- Store invalidated itself in LFST
- Squashing until inum; squashed [sn]

#### Other O3 Flags

| Flag | File | Trigger |
|---|---|---|
| **FreeList** | `o3/free_list.cc:45` | Object construction: "Creating new free list object" |
| **DynInst** | `o3/dyn_inst.cc:84,261` | Constructor: "Instruction created. Instcount = N". Destructor: "Instruction destroyed. Instcount = N" |
| **O3CPU** | `o3/cpu.cc` | Creating O3CPU, tick main, activate/deactivate thread, handle interrupt, switch out, exit thread |
| **Activity** | `cpu/activity.cc`, all O3 stages | Stage activate/deactivate, activity counter changes, waking up CPU, waiting on I-cache |
| **Scoreboard** | `o3/scoreboard.hh:107` | `setReg()` called: "Setting reg \<idx\> (\<class\>) as ready" |
| **Writeback** | `o3/lsq.cc:316` | `LSQ::writebackStores()`: "[tid] Writing back stores. N stores available" |

### SimpleCPU / MinorCPU Flag Triggers

#### SimpleCPU (22 DPRINTF sites -> `cpu/simple/timing.cc`, `cpu/simple/atomic.cc`)

Triggers on:
- Resume/ActivateContext/SuspendContext
- Fetch: translating address, sending fetch for addr (va/pa), pkt addr
- Translation fault: fault occurred, handling; scheduling fetch after Fault
- Complete ICache Fetch; received fetch response
- Received load/store response; received snoop pkt for addr

#### MinorCPU (7 DPRINTF sites -> `cpu/minor/cpu.cc`, `cpu/minor/pipeline.cc`)

Triggers on:
- Startup; switchOut; takeOverFrom
- ActivateContext/SuspendContext thread
- Draining pipeline by halting inst fetches; pipeline undrained stages state

#### MinorExecute (48 DPRINTF sites -> `cpu/minor/execute.cc`)

Triggers on:
- ExecContext setting PC; initiating memRef inst; fault on memory inst
- Trying to issue inst to FU; Issuing to FU; Can't issue (FU busy/not pipelined/not yet)
- Stepping to next inst; wrapping
- Fault inst reached Execute; Fault in early executing/execute
- Can't commit: data barrier not ready / depends on condition / must be at end of line
- Trying to commit mem response; Discarding mem inst (wrong stream)
- Committing no cost inst; Completed inst; Reached inst issue/commit limit

#### MinorMem (55 DPRINTF sites -> `cpu/minor/lsq.cc`, `cpu/minor/execute.cc`)

Triggers on:
- Moving barrier out of store buffer; Pushing store into store buffer; Forwarding from store buffer
- Trying to send request to memory; Request needs retry / still in translation / not at front
- Passing transfer; Moving faulting request into transfers
- Load request with stores still in transfers; Load partly satisfied by store buffer
- Sent data memory request; Received response packet; Received error response
- Has outstanding packets; Completed transfer for barrier
- Found/no matching memory response; Deleting request

### Branch Predictor Flag Triggers

#### Branch (37 DPRINTF sites -> `cpu/pred/bpred_unit.cc`, `cpu/minor/fetch2.cc`, `cpu/minor/execute.cc`)

Triggers on:
- History entry added; predHist.size
- Branch predictor predicted taken/not taken for PC with branch type
- BTB hit/miss info
- Call pushes return address on RAS; return pops from RAS
- Committing branches until; Commit branch: sn, PC, branch type
- Squash: incorrect \<type\> branch; incorrect call/return squash
- Mispredicted: \<branch type\>, PC
- Minor: unpredicted branch / predicted correctly / mis-predicted / wrong target

#### BTB (1 DPRINTF site -> `cpu/pred/simple_btb.cc:56`)

Triggers on: "BTB: Creating BTB object" (construction only).

#### RAS (11 DPRINTF sites -> `cpu/pred/ras.cc`)

Triggers on:
- Create RAS stacks; RAS Reset
- RAS push: "RAS[TOS] <= address. Entries used: N, tid:N"
- RAS pop: "RAS[TOS] => address. Entries used: N, tid:N"
- Incorrect push/pop squash with restore details
- Commit branch/return with correctness indicator

### Memory System Flag Triggers

#### Cache (43 DPRINTF sites -> `mem/cache/base.cc`, `mem/cache/cache.cc`)

Triggers on:
- Packet hit/miss in cache with address, command type, block state
- MSHR handling: allocate, add target, deallocate
- Writeback creation and sending
- Block allocation/deallocation; state transitions
- Clean eviction; prefetch hits in cache; promotion of write to WriteLineReq
- Temporary block usage; blocking/unblocking for ordering
- Snoop hits/misses; deferred snoops; squash of lower-cache packets on writequeue

#### CacheComp (11 DPRINTF sites -> `mem/cache/compressors/base.cc`, `*_compressor*`)

Triggers on:
- Compression of cache line (original vs compressed bit count)
- Decompression of block
- Algorithm-specific: zero-data success/failure, repeated-qwords failure, base-delta failure
- Selection of best compressor from multiple options
- Co-allocation of compressed entries in tags

#### CachePort (6 DPRINTF sites -> `mem/cache/base.cc`, `mem/cache/base.hh`)

Triggers on:
- Scheduling send events at tick; waiting for snoop response before sending
- Blocking new requests (port full); descheduling retries (port still blocked)
- Accepting new requests again (port unblocked); sending retry notifications

#### CacheRepl (2 DPRINTF sites -> `mem/cache/base.cc:1055,1660`)

Triggers on: replacement victim chosen for eviction (during data access and tag lookup), shows victim block details.

#### CacheTags (1 DPRINTF site -> `mem/cache/cache.cc:420`)

Triggers on: cache dumps its current tag state (init/debug inspection).

#### CacheVerbose (12 DPRINTF sites -> `mem/cache/base.cc`, `mem/cache/cache.cc`)

Triggers on:
- Creation of response packets; sending response packets
- Snoop results with block info; packet lookup found block
- Packet flow through eviction; timing write operations
- Invalidation handling; delaying packets for ordering; MSHR target processing

#### MSHR (10 DPRINTF sites -> `mem/cache/mshr.cc`, `mem/cache/mshr_queue.cc`)

Triggers on:
- Allocating new MSHR (shows usage count); deallocating MSHR and its targets
- Adding new target to MSHR with details
- Command type upgrades: UpgradeReq->ReadExReq, SCUpgradeReq->SCUpgradeFailReq
- Dumping target state after allocation

#### HWPrefetch (40 DPRINTF sites -> `mem/cache/prefetch/queued.cc`, `stride.cc`, `bop.cc`, etc.)

Triggers on:
- Stride prefetcher: hits/misses in stride table
- Queued prefetcher: generating/validating/issuing prefetch requests; page-crossing checks
- Address translation results (success/failure); redundant prefetch detection
- Queue-full: eviction of lowest-priority entries
- BOP: finding addresses in RR table, tracking best score
- DCPT/SignaturePath/SMS/STeMS: PC-less request ignoration, prefetch queuing
- Ruby prefetcher proxy: issuing/completing/aborting prefetch requests

#### HWPrefetchQueue (1 DPRINTF site -> `mem/cache/prefetch/queued.cc:136`)

Triggers on: prefetch request dequeued and sent for issue (shows VA and PA).

#### DRAM (24 DPRINTF sites -> `mem/dram_interface.cc`)

Triggers on:
- Packet vs bank/row state check: row buffer hit/miss, seamless hits, prepped hits
- Rank/bank availability; activate commands and timing; bank precharging
- tXAW enforcement (four-activation window); RD/WR burst scheduling; auto-precharge
- DRAM interface setup, capacity, address decoding (rank/bank/row)
- Read/write queue occupancy; self-refresh wakeup during drain; refresh operations

#### DRAMPower (10 DPRINTF sites -> `mem/dram_interface.cc`)

Triggers on: ACT, PRE, PREA, REF, PDN_F_ACT, PDN_F_PRE, SREN, PUP_ACT, PUP_PRE, SREX, RD, WR commands in CSV format: `<tick>,<command>,<rank>,<bank>`.

#### DRAMState (12 DPRINTF sites -> `mem/dram_interface.cc`)

Triggers on:
- Rank unavailability; self-refresh entry/exit
- Power state transitions: active -> precharged
- Sleep state tracking; refresh duration
- Switching to power-down after refresh; all-banks-precharged state
- Bypassing refresh for power state transition; scheduling power/wakeup events

#### NVM (19 DPRINTF sites -> `mem/nvm_interface.cc`)

Triggers on: NVM rank creation, address decoding, bank/rank availability, seamless buffer hits, read timing, controller restart, timing accesses, response readiness, bus turnaround, bus utilization.

#### MemCtrl (60+ DPRINTF sites -> `mem/mem_ctrl.cc`, `mem/hetero_mem_ctrl.cc`, `mem/hbm_ctrl.cc`)

Triggers on:
- Controller setup; receiving timing (recvTimingReq) and atomic requests
- Read/write queue management: adding, queue full, scheduled immediately
- Read/write/response queue dumps; command bus contention detection
- QoS turnaround state selection: read-to-write, write-to-read
- Request-to-rank mapping: free vs busy rank
- Response delivery; burst completion

#### MemoryAccess (5 DPRINTF sites -> `mem/abstract_mem.cc`, GPU coalescer)

Triggers on: read/write access notifications (with data hex dump for reads), cache responding to non-responding address, CleanEvict, write coalescing.

#### PacketQueue (3 DPRINTF sites -> `mem/packet_queue.cc`)

Triggers on: receiving retry from peer, scheduling packet for sending (command type, address, size, tick, ordering), postponing send waiting for retry.

### TLB / MMU Flag Triggers (RISC-V focused)

The RISC-V MMU class (`arch/riscv/mmu.hh`) delegates all translation work to the TLB -> there are no DPRINTF calls in the MMU itself. Use `TLB`, `TLBVerbose`, and `PageTableWalker` for RISC-V address translation debugging.

#### TLB (15 DPRINTF sites in `arch/riscv/tlb.cc`)

Triggers on:

**Insert/Remove/Flush:**
- `TLB::insert()`: `"insert(vpn=%#x, asid=%#x, key=%#x): vaddr=%#x paddr=%#x pte=%#x size=%#x"` -> new TLB entry inserted with full mapping details
- `TLB::demapPage()` (SFENCE.VMA): `"flush(vaddr=%#x, asid=%#x)"` -> partial TLB flush. If both args are zero: `"Flushing all TLB entries"` (full flush)
- `TLB::flushAll()`: `"flushAll()"` -> unconditional full TLB flush
- `TLB::remove(idx)`: `"remove(vpn=%#x, asid=%#x): ppn=%#x pte=%#x size=%#x"` -> entry eviction

**Permission Checks (all raise a page fault):**
- HLVX with no exec permission -> `"HLVX with no exec perm, raising PF"`
- No read permission (and MXR not applicable) -> `"PTE has no read perm, raising PF"`
- No write permission -> `"PTE has no write perm, raising PF"`
- No exec permission -> `"PTE has no exec perm, raising PF"`
- User mode but PTE not user-accessible (U bit not set) -> `"PTE not user accessible, raising PF"`
- Supervisor mode but PTE only user-accessible (U set, SUM=0 or executing) -> `"PTE only user accessible, raising PF"`

**Other:**
- Dirty bit not set on a write -> `"Dirty bit not set, repeating PT walk"` -> triggers page table walk to set dirty bit
- `translateFunctional()` done -> `"Translated (functional) %#x -> %#x."`

#### TLBVerbose (3 DPRINTF sites in `arch/riscv/tlb.cc`)

Triggers on:
- **Every TLB lookup** (`TLB::lookup()`): `"lookup(vpn=%#x, asid=%#x, key=%#x): <hit|miss> ppn=%#x (%#x) <hidden| >"` -> shows hit/miss, PPN, page size, and whether it was a hidden PTW lookup
- **MXR bit bypass**: `"MXR bit on, load from exec page success"` -> MXR allows reading from execute-only pages (hardware enforcement of MXR in RISC-V)
- **Successful translation** (`TLB::translate()`): `"translate(vaddr=%#x, vpn=%#x, asid=%#x): %#x"` -> final VA->PA resolution

#### PageTableWalker (8 DPRINTF sites in `arch/riscv/pagetable_walker.cc`)

Triggers on:
- Concurrent walks queued: `"Walks in progress: %d"` -> existing walk still in progress, new request queued
- Walk squashed (branch mispredict / instruction squash): `"Squashing table walk for address %#x"`
- Stage 1 walk -> each level: `"Got level%d PTE: %#x"` -> PTE value read at current walk level
- Stage 1 leaf found: `"#1 leaf node at level %d, with vpn %#x"`
- SVNAPOT encoding error: `"SVNAPOT PTE has wrong encoding, raising PF"` -> N bit set but PPN0 encoding invalid
- Stage 2 (G-stage / hypervisor) -> each level: `"[GSTAGE]: Got level%d PTE: %#x"`
- Stage 2 leaf found: `"[GSTAGE] #1 leaf node at level %d, with vpn %#x"`

**RISC-V page table walk levels:** Sv39 uses 3 levels (level 2->1->0), Sv48 uses 4 levels (level 3->2->1->0). The walker starts at the highest level and steps down to find a leaf PTE or raise a page fault.

#### LLSC / RISC-V Reservation Handling (6 DPRINTF sites in `arch/riscv/isa.cc`)

Triggers on:
- Snoop hits locked address: `"Locked snoop on address %x."` -> cache coherence snoop on reserved address; reservation is cleared
- Load-Reserved (LR) executed: `"[cid:%d]: Reserved address %x."` -> sets the reservation
- Store-Conditional (SC) starts: `"[cid:%d]: load_reservation_addrs empty? %s."` -> checks if reservation still exists
- SC address check: `"[cid:%d]: addr = %x."` / `"[cid:%d]: last locked addr = %x."` -> compares SC address against reserved address
- SC success: `"[cid:%d]: SC success! Current locked addr = %x."` -> store succeeded atomically

**Key RISC-V LR/SC guarantee:** Reservation is per-context (`cid`). Snoops to the reserved cache line clear the reservation. An SC only succeeds if no intervening snoop or context switch cleared the reservation since the LR.

### System Flag Triggers

| Flag | Key Files | Trigger Condition Summary |
|---|---|---|
| **Interrupt** | `arch/riscv/interrupts.cc:223,234,245`, `dev/*`, `cpu/o3/cpu.cc` | RISC-V: interrupt post/clear/clearAll on local interrupt pending register. Interrupt assertion/clearance, handling, pending detection |
| **Faults** | `arch/riscv/faults.cc:64` (DPRINTFS), ISA fault handlers | RISC-V: `RiscvFault::invoke()` -> central dispatch for ALL faults/exceptions/interrupts. Fault name + exception code + PC at time of trap. Sets cause/epc/tval CSRs, redirects to trap vector |
| **Loader** | `sim/system.cc`, `base/loader/*` | ELF loading: segment placement, entry point, symbol table loading |
| **PseudoInst** | `sim/pseudo_inst.cc` | m5 pseudo-instruction execution (m5exit, m5writefile, m5checkpoint, etc.) |
| **SyscallBase** | `sim/syscall_emul.cc` | System call dispatch: syscall number, arguments, return value |
| **SyscallVerbose** | `sim/syscall_emul.cc` | Verbose syscall details: buffer contents, full argument decode |
| **Thread** | `sim/syscall_emul.cc`, `cpu/*` | Thread state changes: activate, suspend, halt; thread context operations |
| **Context** | `cpu/*/thread_context.*` | CPU context switches: save/restore, thread activation/deactivation |
| **Stack** | `arch/*/process.cc`, `cpu/*` | Stack operations: stack setup, call/return, stack pointer changes |
| **Event** | `sim/eventq.cc` | Event queue scheduling: event creation, service, reschedule, deletion |
| **Drain** | `sim/drain.*` | Drain state machine: drain start, drain complete, resume |
| **Checkpoint** | `sim/serialize.*` | Checkpoint creation/restore: object serialization state |
| **Config** | `sim/config.*` | Configuration parsing: param assignments, SimObject creation |
| **Timer** | `dev/*/timer*` | Timer interrupts, countdown, timer events |
| **ClockDomain** | `sim/clock_domain.*` | Clock domain changes: frequency updates, tick rate |
| **VoltageDomain** | `sim/voltage_domain.*` | Voltage domain state: voltage changes, power state |
| **PowerDomain** | `sim/power/` | Power domain: state transitions, power gating |
| **DVFS** | `sim/clock_domain.*`, DVFS handlers | Frequency/voltage scaling events: transitions, latency |
| **VtoPhys** | `arch/*/vtophys.*`, `mem/` | Virtual-to-physical address translation attempts and results |
| **Vma** | `mem/vma.*` | Virtual memory area operations: allocation, deallocation |
| **GDBAcc/Read/Write/Send/Recv/Misc/Extra** | `base/remote_gdb.cc` | Remote GDB: memory access (R/W), packet send/receive, breakpoints, watchpoints |

### RISC-V Specific Flag Triggers (Detailed)

#### Clint (5 DPRINTF sites -> `dev/riscv/clint.cc`)

CLINT is the RISC-V Core-Local Interrupt Controller. It generates both software interrupts (MSIP) and timer interrupts (MTIP).

| Trigger Condition | Message | Line |
|---|---|---|
| `raiseInterruptPin()` -> mtime == mtimecmp (timer match) | `"MTIP posted - thread: %d, mtime: %d, mtimecmp: %d"` | 95-97 |
| Any CLINT PIO read | `"Read request - addr: %#x, size: %#x, atomic:%d"` | 165-167 |
| Any CLINT PIO write | `"Write request - addr: %#x, size: %#x"` | 185-187 |
| `updateMSIP()` -> msip becomes non-zero (SW interrupt set) | `"MSIP posted - thread: %d"` | 243 |
| `updateMSIP()` -> msip becomes zero (SW interrupt cleared) | `"MSIP cleared - thread: %d"` | 247 |

**Architecture insight:** On each RTC tick, `raiseInterruptPin()` compares mtime against mtimecmp. When mtime reaches (or exceeds) mtimecmp, MTIP is asserted and the hart gets a timer interrupt. MSIP is software-controlled -> other harts (or the same hart) write to memory-mapped MSIP registers to trigger inter-processor interrupts (IPI).

#### Plic (16 DPRINTF sites -> `dev/riscv/plic.cc`)

PLIC is the RISC-V Platform-Level Interrupt Controller. It collects external interrupts from platform devices and routes them to harts.

**Lifecycle of a PLIC interrupt:**

1. **Post/Clear** -> device asserts/clears an interrupt source line
   - `"Int post request - source: %#x, current priority: %#x"` (line 95)
   - `"Int clear request - source: %#x, current priority: %#x"` (line 123)

2. **Configuration via PIO** -> software programs priority, enable, threshold registers
   - `"Read request - addr: %#x, size: %#x, atomic:%d"` (line 136)
   - `"Write request - addr: %#x, size: %#x"` (line 156)
   - `"Priority updated - src: %d, val: %d"` (line 318)
   - `"Enable updated - context: %d, src32: %d, val: %#x"` (line 336)
   - `"Threshold updated - context: %d, val: %d"` (line 347)

3. **Claim/Complete** -> hart claims the highest-priority pending interrupt, then signals completion
   - `"Claim success - context: %d, interrupt ID: %d"` (line 364)
   - `"Claim already cleared - context: %d, interrupt ID: %d"` (race condition, line 371)
   - `"Complete - context: %d, interrupt ID: %d"` (line 394)

4. **Output propagation** -> timed events model PLIC wiring delay
   - `"Update scheduled - tick: %d"` (line 427) -> output event queued
   - `"Update triggered"` (line 468) -> output event fires
   - `"Int posted - thread: %d, int id: %d, pri: %d, thres: %d"` (line 495) -> interrupt delivered to hart (priority > threshold, not already claimed)
   - `"Int filtered - thread: %d, int id: %d, pri: %d, thres: %d"` (line 501) -> interrupt filtered out

**Architecture insight:** PLIC uses a claim/complete handshake -> when a hart reads the claim register, it gets the highest-priority pending interrupt; the PLIC marks it as claimed (no longer pending). The hart must write the completion register after handling to allow the same source to assert again.

#### PMP (10 DPRINTF sites -> `arch/riscv/pmp.cc`)

PMP (Physical Memory Protection) enforces per-mode physical memory access control, checked on every memory access.

**Access checks (`pmpCheck()`):**
- Regular access (VA + PA): `"Checking pmp permissions for va: %#x , pa: %#x"` (line 68)
- Page table walk access (PA only): `"Checking pmp permissions for pa: %#x"` (line 72)

**Configuration register writes (`pmpUpdateCfg()`):**
- Index out of range: `"Can't update pmp entry config %u because..."` (line 155)
- Normal update: `"Update pmp config with %u for pmp entry: %u"` (line 161)
- Locked entry (PMP_LOCK bit set): `"Update pmp entry config %u failed because it locked"` (line 164)

**Address register writes (`pmpUpdateAddr()`):**
- Index out of range / normal update / locked entry similar to config
- TOR-mode cascade lock: `"Update pmp entry %u failed because the entry %u lock bit set and A field is TOR"` (line 257) -> TOR mode entries depend on the next entry's address, so if entry N+1 is locked, entry N is also locked

**Rule update:**
- After `pmpUpdateRule()`, if any locked entry found: `"Find lock entry"` (line 224)

**Architecture insight:** RISC-V PMP has three addressing modes: NAPOT (naturally-aligned power-of-two), TOR (top-of-range -> uses two consecutive PMP entries), and NA4 (4-byte aligned). TOR mode means updating one PMP entry can affect its neighbor. The PMP is checked on every physical memory access, including page table walks.

#### RiscvMisc (2 DPRINTF sites -> `arch/riscv/isa.cc:486,681`)

Tracks ALL Control Status Register (CSR) access. High volume -> every CSR read/write instruction triggers output.

- `readMiscRegNoEffect()`: `"Reading MiscReg %s (%d): %#x."` -> CSR name (from `MiscRegNames[]`), index, current value
- `setMiscRegNoEffect()`: `"Setting MiscReg %s (%d) to %#x."` -> CSR name, index, new value

**Architecture insight:** RISC-V CSRs include: cycle/time/instret counters, mstatus (global status), mtvec (trap vector), mepc (trap PC), mcause (trap cause), mtval (trap value), mie/mip (interrupt enable/pending), pmpcfg/pmpaddr (PMP config/addr), satp (page table root), and many more. Use `RiscvMisc` to see every CSR state change -> invaluable for debugging privilege transitions and trap handling.

#### VirtIOMMIO (5 DPRINTF sites -> `dev/riscv/vio_mmio.cc`)

The MMIO transport layer for VirtIO devices on RISC-V platforms.

- `read()`: `"Reading %u bytes @ 0x%x:"` + `"    value: 0x%x"` -> any MMIO read from VirtIO register space
- `write()`: `"Writing %u bytes @ 0x%x:"` + `"    value: 0x%x"` -> any MMIO write to VirtIO register space
- `kick()`: `"kick(): Sending interrupt..."` -> guest notifies device (writes to QueueNotify register), triggers device-side virtqueue processing and delivers an interrupt to the guest

**Architecture insight:** VirtIO MMIO register layout: Magic/Version/DeviceID/VendorID (device identification), Status (driver/device negotiation), QueueSel/QueueNum/QueueAlign/QueuePFN (virtqueue setup), QueueNotify (kick -> guest->device notification), InterruptStatus/InterruptACK (device->guest notification). The kick mechanism is how the guest tells the device that new descriptors are available in the virtqueue.

#### Semihosting (6 DPRINTF sites -> `arch/riscv/semihosting.cc`)

RISC-V semihosting allows bare-metal/guest code to make host service calls via special ebreak sequences.

- 64-bit call dispatch: `"Semihosting call64: %s"` (line 115) -> `"\t ->: 0x%x, %i"` (line 118)
- 32-bit call dispatch: `"Semihosting call32: %s"` (line 135) -> `"\t ->: 0x%x, %i"` (line 138)
- ebreak semihosting detection failures: cross-page error (line 170), inaccessible surrounding instructions (line 177)
- ebreak verification: `"Checking ebreak for semihosting: Prev=%#x EBreak=%#x Next=%#x"` (line 185) -> checks the 3-instruction sequence: ADDI x0,x0,0x1f + EBREAK + ADDI x0,x0,0x7f

#### Faults (1 DPRINTF site -> `arch/riscv/faults.cc:64`)

Uses `DPRINTFS` (includes CPU scope):
- `RiscvFault::invoke()`: `"Fault (%s, %u) at PC: %s"` -> fault name (e.g., "PageFault", "IllegalInstFault", "InterruptFault"), exception code number, and PC state. This is the central dispatch point for ALL RISC-V faults/exceptions/interrupts.

#### Interrupt (3 DPRINTF sites -> `arch/riscv/interrupts.cc`)

- `post(int_num, index)`: `"Interrupt %d:%d posted"` -> interrupt bit set in pending register
- `clear(int_num, index)`: `"Interrupt %d:%d cleared"` -> interrupt bit cleared
- `clearAll()`: `"All interrupts cleared"` -> all pending interrupts reset (e.g., on CPU state reset)

#### RISC-V Decode (3 DPRINTF sites -> `arch/riscv/decoder.cc`)

- `Decoder::moreBytes()`: `"Requesting bytes 0x%08x from address %#x"` -> raw instruction word fetched
- `Decoder::decode()` entry: `"Decoding instruction 0x%08x at address %#x"` -> instruction before decoding
- `Decoder::decode()` result: `"Decode: Decoded %s instruction: %#x"` -> matched instruction name + encoding

#### RISC-V Stack (6 DPRINTF sites -> `arch/riscv/process.cc`)

All in `argsInit()` -> how the RISC-V process sets up the initial user stack:
- `"Wrote arg \"%s\" to address %p"` (DPRINTFN, line 186) -> each argv string
- `"Wrote env \"%s\" to address %p"` (line 198) -> each envp string
- `"Wrote argc %d to address %#x"` (line 221) -> argument count
- `"Wrote argv pointer %#x to address %#x"` (line 225) -> each argv pointer
- `"Wrote envp pointer %#x to address %#x"` (line 232) -> each envp pointer
- `"Wrote aux key %s to address %#x"` / `"Wrote aux value %x to address %#x"` (lines 249, 252) -> auxiliary vector entries

#### RISC-V Checkpoint (2 DPRINTF sites -> `arch/riscv/isa.cc:981,988`)

- `ISA::serialize()`: `"Serializing Riscv Misc Registers"`
- `ISA::unserialize()`: `"Unserializing Riscv Misc Registers"`

### Interconnect Flag Triggers

| Flag | Key Files | Trigger Condition Summary |
|---|---|---|
| **BaseXBar** | `mem/xbar.cc` | Base crossbar: packet routing, arbitration |
| **CoherentXBar** | `mem/coherent_xbar.cc` | Coherent crossbar: snoop broadcast, snoop filter interaction, coherence routing |
| **NoncoherentXBar** | `mem/noncoherent_xbar.cc` | Non-coherent crossbar: address-based routing |
| **SnoopFilter** | `mem/snoop_filter.cc` | Snoop filter: lookup, register, update, invalidate events |
| **Bridge** | `mem/bridge.cc` | Bus bridge: request forwarding, response matching across clock domains |
| **PortTrace** | `mem/port.*` | Port-level: packet send/receive, retry, port binding |
| **ResponsePort** | `mem/port.*` | Response-side port: response scheduling, send, timing |
| **SysBridge** | `dev/sysbridge.*` | System bridge: MMIO forwarding to system bus |
| **TokenPort** | `mem/token_port.*` | Token-based flow control: token acquire/release |

---

## Build Types

gem5 has different build targets with different debug capabilities:

| Build | Binary | Debug Support | Opt Level |
|---|---|---|---|
| **opt** (default) | `gem5.opt` | Full (debug flags work) | `-O2` |
| **debug** | `gem5.debug` | Full + asserts + extra checks | `-O0 -g` |
| **fast** | `gem5.fast` | Stripped (no debug flags) | `-O3` |

Use `gem5.debug` when you need gdb-level debugging or extra assertions. Use `gem5.opt` for normal debug-flag-based tracing (`TRACING_ON=1` is enabled in opt).

Current setup uses `gem5.debug`.
