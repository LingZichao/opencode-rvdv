# API Documentation

This directory contains the core reference documentation for FORCE-RISCV and RISC-V ISA.

## Documents

| Document | Size | Description | When to Read |
|----------|------|-------------|--------------|
| [FORCE-RISCV_brief_introduction.md](FORCE-RISCV_brief_introduction.md) | Short | Architecture overview, components, execution flow | First read for understanding FORCE-RISCV basics |
| [FORCE-RISCV_User_Manual-v0.8.md](FORCE-RISCV_User_Manual-v0.8.md) | Large | Complete API reference with all function signatures | When you need specific API details |
| [RISC-V_Unprivileged_ISA.md](RISC-V_Unprivileged_ISA.md) | Large | Full RISC-V ISA specification | When you need instruction encoding/semantics |
| [README.md](README.md) | Medium | Quick start guide, build instructions, project overview | For setup and running FORCE-RISCV |
| [INDEX.md](INDEX.md) | Medium | Detailed table of contents with section links | To navigate large docs by section |

## Progressive Loading Guide

### Level 1: Start here
Read `FORCE-RISCV_brief_introduction.md` for:
- Basic components (Config, Arch, Memory, Virtual Memory, State Transition)
- Program execution flow (boot → template → end-of-test)

### Level 2: API Reference (read sections as needed)
The User Manual (`FORCE-RISCV_User_Manual-v0.8.md`) is large. Use `INDEX.md` to locate the right section:

| Need | Section to Read |
|------|----------------|
| Instruction generation | §5.1 `genInstruction`, `queryInstructionRecord` |
| Sequence patterns | §5.2, §6.1-6.7 (sequence examples) |
| Address/page APIs | §5.3 (address), §5.4 (page) |
| Register control | §5.5 (all register APIs) |
| Exception handling | §5.6 (exception APIs) |
| PE state control | §5.7 `getPEstate`, `setPEstate` |
| Memory control | §5.8 `initializeMemory` |
| Choices modification | §5.9 (operand/paging/general choices) |
| Variables/knobs | §5.10 `modifyVariable`, `getVariable` |
| BNT (branch not taken) | §5.11 `setBntHook`, `revertBntHook` |
| Utility functions | §5.12 (`pickWeighted`, `sample`, `random32/64`, `genData`, etc.) |
| Test template structure | §4 (template format, control files) |
| Choices & variables ref | §7 (dependency, reloading, page table controls) |

### Level 3: RISC-V ISA Specification (read chapters as needed)
The ISA spec (`RISC-V_Unprivileged_ISA.md`) covers instruction semantics. Key chapters:

| Extension | Chapters |
|-----------|----------|
| RV32I/RV64I base | Ch.2, Ch.4 |
| M (mul/div) | Ch.12 |
| A (atomic) | Ch.13-17 |
| F/D/Q (float) | Ch.21-23 |
| Zfh (half-float) | Ch.24 |
| C (compressed) | Ch.28 |
| B (bit manipulation) | Ch.30 |
| V (vector) | Ch.31 |
| Memory model | Ch.18 |
| CSR | Ch.6 |
