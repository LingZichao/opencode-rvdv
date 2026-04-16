# Example Test Templates

Python test template examples organized by feature area. Each subdirectory contains `*_force.py` test templates and `*_fctrl.py` control files.

## Control File Convention
- `_def_fctrl.py` — Default control config (lists test files + generator options like `--cfg riscv_rv64.config`)
- `_noiss_fctrl.py` — Run without ISS (no instruction set simulator)
- `_perf_fctrl.py` — Performance testing config
- `_rv32_fctrl.py` — RV32-specific config

## Example Categories

| Directory | Files | Description | When to Read |
|-----------|-------|-------------|--------------|
| [APIs/](APIs/) | 36 | Core API usage: register mgmt, constraints, VA/PA gen, random values, CSR, state | Need examples of specific FORCE-RISCV API calls |
| [address_solving/](address_solving/) | 6 | Address resolution for load/store, address reuse, compressed instr, misalignment | Working with load/store address constraints |
| [bnt/](bnt/) | 2 | Branch-not-taken (BNT) speculative sequence generation | Implementing BNT hooks |
| [branch/](branch/) | 5 | PC-relative conditional/unconditional branches, register-indirect branches | Generating branch instructions |
| [exception_handlers/](exception_handlers/) | 9 | Exception/trap handling: ecall/ebreak, CSR access, stack, privileged traps | Implementing exception handling |
| [fsuExamples/](fsuExamples/) | 5 | Floating-point & multiply-divide with data constraints, NaN boxing | Working with FP instructions |
| [instructions/](instructions/AGENTS.md) | 150 | Instruction set coverage tests grouped by ISA extension | Need instruction-specific test patterns |
| [loop/](loop/) | 8 | Loop control: basic loops, reconvergence, conditional branches in loops | Implementing loop sequences |
| [masterRun/](masterRun/) | 4 | Test harness integration and command-line options | Understanding test execution flow |
| [multiprocessing/](multiprocessing/) | 8 | Multi-thread: fence, semaphore, thread locking, context management | Multi-threaded test generation |
| [paging/](paging/) | 18 | Virtual memory: page faults on branch/load/store, memory attributes | Virtual memory and paging tests |
| [privilege_switch/](privilege_switch/) | 7 | Privilege level transitions via system calls and exception returns | Privilege mode switching |
| [register/](register/) | 3 | System register (CSR) operations, read-only register access | CSR read/write testing |
| [rv32/](rv32/) | 2 | RV32I instruction set coverage | RV32-specific tests |
| [rv64/](rv64/) | 4 | RV64 instructions, invalid address handling, exception counting | RV64-specific tests |
| [state_transition/](state_transition/) | 21 | CPU state management: boot state, GPR/FPR/CSR init, transition modes | State setup and transitions |
| [thread_group/](thread_group/) | 6 | Thread grouping and partitioning across hardware configs | Thread group management |
| [vector/](vector/) | 25 | RV-V vector: add, load/store (unit-stride/strided/indexed/segment), mask, vsetvl | Vector extension tests |

## Key Example Files (Start Here)

For learning FORCE-RISCV, read these examples in order:

1. **APIs/GenData_test_force.py** — `genData()` API for generating typed data values
2. **APIs/InitializeRegisterTest_force.py** — Register initialization
3. **APIs/ReserveRegisterTest_force.py** — Register reservation
4. **APIs/Constraint_force.py** — Applying constraints to generation
5. **APIs/api_genVA_01_force.py** — Virtual address generation
6. **branch/branch_pc_relative_conditional_force.py** — Branch instruction generation
7. **paging/paging_force.py** — Basic paging setup
8. **vector/vector_simple_add_force.py** — Simple vector instruction
