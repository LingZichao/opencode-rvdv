# FORCE-RISCV Documentation Library

This is the documentation library for FORCE-RISCV ISG (Instruction Stream Generator).
Use progressive loading: read this index first, then drill into subdirectories as needed.

## Directory Structure

| Directory | Description | When to Read |
|-----------|-------------|--------------|
| [apiDoc/](apiDoc/AGENTS.md) | API reference manual, RISC-V ISA spec, introduction docs | When you need API usage, function signatures, ISA details |
| [config/](config/AGENTS.md) | XML instruction definitions and architecture config | When you need instruction encoding, operand details, or arch config |
| [example/](example/AGENTS.md) | Python test template examples organized by feature | When you need code examples for specific features |

## Standalone Guides

| Guide | Description | When to Read |
|-------|-------------|--------------|
| [memory_operations_guide.md](memory_operations_guide.md) | genVA/genPA/initializeMemory/LSTarget 用法与常见模式 | When working with load/store, address generation, or memory initialization |

## Quick Reference: Common Tasks

### Writing a basic ISG script
1. Read `apiDoc/AGENTS.md` → section on `genInstruction` API
2. Browse `example/APIs/` for basic API usage examples

### Working with specific instruction sets
1. Read `config/AGENTS.md` to find the right XML config
2. Read `example/instructions/AGENTS.md` to find grouped instruction test examples

### Implementing advanced features
| Feature | Doc Location | Example Location |
|---------|-------------|-----------------|
| **Memory operations** | [memory_operations_guide.md](memory_operations_guide.md) | `example/APIs/api_genVA_*.py`, `example/address_solving/` |
| Address solving | `apiDoc/` → User Manual §5.3 | `example/address_solving/` |
| Paging / Virtual Memory | `apiDoc/` → User Manual §5.4 | `example/paging/` |
| Exception handling | `apiDoc/` → User Manual §5.6 | `example/exception_handlers/` |
| Register control | `apiDoc/` → User Manual §5.5 | `example/register/` |
| Branch / BNT | `apiDoc/` → User Manual §5.11 | `example/branch/`, `example/bnt/` |
| State transition | `apiDoc/` → User Manual §5.7 | `example/state_transition/` |
| Privilege switching | `apiDoc/` → Brief Intro §1.1 | `example/privilege_switch/` |
| Multiprocessing | `apiDoc/` → User Manual §3.1 | `example/multiprocessing/` |
| Loop control | `apiDoc/` → User Manual §5.12 | `example/loop/` |
| Vector instructions | `apiDoc/` → ISA Spec Ch.31 | `example/vector/` |
| Floating-point | `apiDoc/` → ISA Spec Ch.21-24 | `example/fsuExamples/` |
| Compressed instructions | `apiDoc/` → ISA Spec Ch.28 | `example/instructions/c_instructions*/` |

### Key APIs (most frequently used)
| API | Purpose |
|-----|---------|
| `genInstruction(name, kwargs)` | Generate a single instruction with optional constraints |
| `genData(pattern)` | Generate data values (INT32, INT64, FP64, etc.) |
| `readRegister / writeRegister` | Read/write register values |
| `initializeRegister` | Set initial register value before generation |
| `reserveRegister / unreserveRegister` | Reserve/release registers from random allocation |
| `getRandomGPR / getRandomRegisters` | Get random available registers |
| `modifyVariable` | Modify generation control variables |
| `genVA(Size, Align, Type, Range)` | Generate valid virtual address for data/instruction |
| `genPA / genVAforPA` | Physical address generation and VA-PA mapping |
| `initializeMemory(addr, bank, size, data)` | Pre-fill memory content before load |
| `LSTarget` (genInstruction param) | Specify load/store target address |
| `modifyOperandChoices` | Constrain operand selection |
