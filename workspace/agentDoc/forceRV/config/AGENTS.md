# Configuration Files

XML instruction definitions and architecture configuration for FORCE-RISCV.

## Files

| File | Description | When to Read |
|------|-------------|--------------|
| `riscv_rv64_c910.config` | C910 processor architecture configuration (threads, cores, ISA options) | When configuring FORCE-RISCV for C910 target |
| `g_instructions.xml` | RV32 base integer + M/A/F/D instruction definitions | When checking RV32 instruction names/operands |
| `g_instructions_rv64.xml` | RV64 base integer + M/A/F/D instruction definitions | When checking RV64 instruction names/operands |
| `c_instructions.xml` | RV32 compressed (C extension) instruction definitions | When checking RV32 compressed instruction names |
| `c_instructions_rv64.xml` | RV64 compressed (C extension) instruction definitions | When checking RV64 compressed instruction names |
| `priv_instructions.xml` | Privileged instruction definitions (CSR, ECALL, etc.) | When checking privileged instruction names |
| `zfh_instructions.xml` | RV32 half-precision floating-point (Zfh) instruction definitions | When checking Zfh instruction names |
| `zfh_instructions_rv64.xml` | RV64 half-precision floating-point (Zfh) instruction definitions | When checking RV64 Zfh instruction names |

## Usage Notes
- Instruction names in XML use the `##RISCV` suffix format, e.g. `ADD##RISCV`
- These XML files define instruction encoding, operands, and constraints
- The `.config` file defines the overall architecture parameters for generation
