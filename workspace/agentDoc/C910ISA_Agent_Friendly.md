# C910 Instruction Set Architecture (ISA) Reference

## Overview
C910 implements two main instruction set categories:
1. **RV Base Instruction Sets** (RISC-V standard) RV64GC(RV64IMAFDC)
2. **XuanTie Extended Instruction Sets** (Custom extensions)

Note:
1. Vector Extension (V) is not supported, VADD,VSUB .etc are not supported.
2. **XuanTie Extended Instruction Sets Instructions** (Custom extensions),are not supported to generate in force-riscv

---

## Table of Contents
1. [RV64I - Integer Base Instructions](#311-rv64i-integer-instructions)
2. [RV64M - Multiply/Divide Instructions](#312-rv64m-multiplydivide-instructions)
3. [RV64A - Atomic Instructions](#313-rv64a-atomic-instructions)
4. [RV64F - Single-Precision Floating Point](#314-rv64f-single-precision-floating-point)
5. [RV64D - Double-Precision Floating Point](#315-rv64d-double-precision-floating-point)
6. [RV64C - Compressed Instructions](#316-rv64c-compressed-instructions)

---

## 3.1.1 RV64I - Integer Instructions

### Categories
| Category | Description |
|----------|-------------|
| Arithmetic | ADD, SUB, ADDI, etc. |
| Logical | AND, OR, XOR, etc. |
| Shift | SLL, SRL, SRA, etc. |
| Compare | SLT, SLTU, SLTI, etc. |
| Data Transfer | LUI, AUIPC |
| Branch/Jump | BEQ, BNE, JAL, JALR, etc. |
| Memory Access | LB, LH, LW, LD, SB, SH, SW, SD |
| CSR Operations | CSRRW, CSRRS, CSRRC, etc. |
| Low Power | WFI |
| Exception Return | MRET, SRET |
| Special | FENCE, ECALL, EBREAK |

### Instruction Latency Table

#### Arithmetic Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| ADD | Signed add | 1 |
| ADDW | Low 32-bit signed add | 1 |
| ADDI | Signed immediate add | 1 |
| ADDIW | Low 32-bit signed immediate add | 1 |
| SUB | Signed subtract | 1 |
| SUBW | Low 32-bit signed subtract | 1 |

#### Logical Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| AND | Bitwise AND | 1 |
| ANDI | Immediate bitwise AND | 1 |
| OR | Bitwise OR | 1 |
| ORI | Immediate bitwise OR | 1 |
| XOR | Bitwise XOR | 1 |
| XORI | Immediate bitwise XOR | 1 |

#### Shift Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| SLL | Logical left shift | 1 |
| SLLW | Low 32-bit logical left shift | 1 |
| SLLI | Immediate logical left shift | 1 |
| SLLIW | Low 32-bit immediate logical left shift | 1 |
| SRL | Logical right shift | 1 |
| SRLW | Low 32-bit logical right shift | 1 |
| SRLI | Immediate logical right shift | 1 |
| SRLIW | Low 32-bit immediate logical right shift | 1 |
| SRA | Arithmetic right shift | 1 |
| SRAW | Low 32-bit arithmetic right shift | 1 |
| SRAI | Immediate arithmetic right shift | 1 |
| SRAIW | Low 32-bit immediate arithmetic right shift | 1 |

#### Compare Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| SLT | Signed compare less than | 1 |
| SLTU | Unsigned compare less than | 1 |
| SLTI | Signed immediate compare less than | 1 |
| SLTIU | Unsigned immediate compare less than | 1 |

#### Data Transfer Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| LUI | Load upper immediate | 1 |
| AUIPC | Add upper immediate to PC | 1 |

#### Branch/Jump Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| BEQ | Branch if equal | 1 |
| BNE | Branch if not equal | 1 |
| BLT | Branch if signed less than | 1 |
| BGE | Branch if signed greater or equal | 1 |
| BLTU | Branch if unsigned less than | 1 |
| BGEU | Branch if unsigned greater or equal | 1 |
| JAL | Jump and link | 1 |
| JALR | Jump register and link | 1 |

#### Memory Access Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| LB | Load byte (sign-extended) | WEAK: ≥3 / STRONG: variable |
| LBU | Load byte (zero-extended) | WEAK: ≥3 / STRONG: variable |
| LH | Load halfword (sign-extended) | WEAK: ≥3 / STRONG: variable |
| LHU | Load halfword (zero-extended) | WEAK: ≥3 / STRONG: variable |
| LW | Load word (sign-extended) | WEAK: ≥3 / STRONG: variable |
| LWU | Load word (zero-extended) | WEAK: ≥3 / STRONG: variable |
| LD | Load doubleword | WEAK: ≥3 / STRONG: variable |
| SB | Store byte | WEAK: 1 / STRONG: variable |
| SH | Store halfword | WEAK: 1 / STRONG: variable |
| SW | Store word | WEAK: 1 / STRONG: variable |
| SD | Store doubleword | WEAK: 1 / STRONG: variable |

#### CSR Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| CSRRW | CSR read/write | Blocked / variable |
| CSRRS | CSR set bits | Blocked / variable |
| CSRRC | CSR clear bits | Blocked / variable |
| CSRRWI | CSR immediate read/write | Blocked / variable |
| CSRRSI | CSR immediate set bits | Blocked / variable |
| CSRRCI | CSR immediate clear bits | Blocked / variable |

#### Special Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| WFI | Wait for interrupt | variable |
| MRET | Machine mode exception return | Blocked / variable |
| SRET | Supervisor mode exception return | Blocked / variable |
| FENCE | Memory fence | variable |
| FENCE.I | Instruction fence | Blocked / variable |
| SFENCE.VMA | Virtual memory fence | Blocked / variable |
| ECALL | Environment call | 1 |
| EBREAK | Breakpoint | 1 |

> **Reference:** Appendix A-1 for I instruction terminology

---

## 3.1.2 RV64M - Multiply/Divide Instructions

| Instruction | Description | Latency |
|-------------|-------------|---------|
| MUL | Signed multiply | 4 |
| MULW | Low 32-bit signed multiply | 4 |
| MULH | Signed multiply high bits | 4 |
| MULHS | Signed/unsigned multiply high | 4 |
| MULHU | Unsigned multiply high | 4 |
| DIV | Signed divide | 3-20 |
| DIVW | Low 32-bit signed divide | 3-12 |
| DIVU | Unsigned divide | 3-20 |
| DIVUW | Low 32-bit unsigned divide | 3-12 |
| REM | Signed remainder | 3-20 |
| REMW | Low 32-bit signed remainder | 3-12 |
| REMU | Unsigned remainder | 3-20 |
| REMUW | Low 32-bit unsigned remainder | 3-12 |

> **Reference:** Appendix A-2 for M instruction terminology

---

## 3.1.3 RV64A - Atomic Instructions

| Instruction | Description | Latency |
|-------------|-------------|---------|
| LR.W | Load reserved word | Split into multiple atomic ops |
| LR.D | Load reserved doubleword | Split into multiple atomic ops |
| SC.W | Store conditional word | Split into multiple atomic ops |
| SC.D | Store conditional doubleword | Split into multiple atomic ops |
| AMOSWAP.W | Atomic swap word | Split into multiple atomic ops |
| AMOSWAP.D | Atomic swap doubleword | Split into multiple atomic ops |
| AMOADD.W | Atomic add word | Split into multiple atomic ops |
| AMOADD.D | Atomic add doubleword | Split into multiple atomic ops |
| AMOXOR.W | Atomic XOR word | Split into multiple atomic ops |
| AMOXOR.D | Atomic XOR doubleword | Split into multiple atomic ops |
| AMOAND.W | Atomic AND word | Split into multiple atomic ops |
| AMOAND.D | Atomic AND doubleword | Split into multiple atomic ops |
| AMOOR.W | Atomic OR word | Split into multiple atomic ops |
| AMOOR.D | Atomic OR doubleword | Split into multiple atomic ops |
| AMOMIN.W | Atomic min (signed) word | Split into multiple atomic ops |
| AMOMIN.D | Atomic min (signed) doubleword | Split into multiple atomic ops |
| AMOMAX.W | Atomic max (signed) word | Split into multiple atomic ops |
| AMOMAX.D | Atomic max (signed) doubleword | Split into multiple atomic ops |
| AMOMINU.W | Atomic min (unsigned) word | Split into multiple atomic ops |
| AMOMINU.D | Atomic min (unsigned) doubleword | Split into multiple atomic ops |
| AMOMAXU.W | Atomic max (unsigned) word | Split into multiple atomic ops |
| AMOMAXU.D | Atomic max (unsigned) doubleword | Split into multiple atomic ops |

**Note:** Atomic instructions may be split into multiple operations with blocked execution. Latency is unpredictable.

> **Reference:** Appendix A-3 for A instruction terminology

---

## 3.1.4 RV64F - Single-Precision Floating Point

### Categories
| Category | Instructions |
|----------|-------------|
| Arithmetic | FADD.S, FSUB.S, FMUL.S, FMADD.S, etc. |
| Sign Injection | FSGNJ.S, FSGNJN.S, FSGNJX.S |
| Data Transfer | FMV.X.W, FMV.W.X |
| Compare | FMIN.S, FMAX.S, FEQ.S, FLT.S, FLE.S |
| Type Conversion | FCVT.*.S, FCVT.S.* |
| Memory | FLW, FSW |
| Classification | FCLASS.S |

### Instruction Latency Table

#### Arithmetic Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FADD.S | Single-precision add | 3 |
| FSUB.S | Single-precision subtract | 3 |
| FMUL.S | Single-precision multiply | 4 |
| FMADD.S | Single-precision multiply-add | 5 |
| FMSUB.S | Single-precision multiply-subtract | 5 |
| FNMADD.S | Single-precision multiply-add negate | 5 |
| FNMSUB.S | Single-precision multiply-subtract negate | 5 |
| FDIV.S | Single-precision divide | 4-10 |
| FSQRT.S | Single-precision square root | 4-10 |

#### Sign Injection Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FSGNJ.S | Sign injection | 3 |
| FSGNJN.S | Sign negate injection | 3 |
| FSGNJX.S | Sign XOR injection | 3 |

#### Data Transfer Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FMV.X.W | Float to int transfer | Split: 1+1 |
| FMV.W.X | Int to float transfer | Split: 1+1 |

#### Compare Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FMIN.S | Float minimum | 3 |
| FMAX.S | Float maximum | 3 |
| FEQ.S | Float equal compare | Split: 3+1 |
| FLT.S | Float less than compare | Split: 3+1 |
| FLE.S | Float less-or-equal compare | Split: 3+1 |

#### Type Conversion Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FCVT.W.S | Float to signed int | Split: 3+1 |
| FCVT.WU.S | Float to unsigned int | Split: 3+1 |
| FCVT.S.W | Signed int to float | Split: 3+1 |
| FCVT.S.WU | Unsigned int to float | Split: 3+1 |
| FCVT.L.S | Float to signed long | Split: 3+1 |
| FCVT.LU.S | Float to unsigned long | Split: 3+1 |
| FCVT.S.L | Signed long to float | Split: 1+3 |
| FCVT.S.LU | Unsigned long to float | Split: 1+3 |

#### Memory Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FLW | Float load word | WEAK: ≥3 / STRONG: variable |
| FSW | Float store word | WEAK: 1 / STRONG: variable |

#### Classification Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FCLASS.S | Float classify | Split: 1+1 |

> **Reference:** Appendix A-4 for F instruction terminology

---

## 3.1.5 RV64D - Double-Precision Floating Point

### Categories
| Category | Instructions |
|----------|-------------|
| Arithmetic | FADD.D, FSUB.D, FMUL.D, FMADD.D, etc. |
| Sign Injection | FSGNJ.D, FSGNJN.D, FSGNJX.D |
| Data Transfer | FMV.X.D, FMV.D.X |
| Compare | FMIN.D, FMAX.D, FEQ.D, FLT.D, FLE.D |
| Type Conversion | FCVT.*.D, FCVT.D.* |
| Memory | FLD, FSD |
| Classification | FCLASS.D |

### Instruction Latency Table

#### Arithmetic Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FADD.D | Double-precision add | 3 |
| FSUB.D | Double-precision subtract | 3 |
| FMUL.D | Double-precision multiply | 4 |
| FMADD.D | Double-precision multiply-add | 5 |
| FMSUB.D | Double-precision multiply-subtract | 5 |
| FNMSUB.D | Double-precision multiply-add negate | 5 |
| FNMADD.D | Double-precision multiply-subtract negate | 5 |
| FDIV.D | Double-precision divide | 4-17 |
| FSQRT.D | Double-precision square root | 4-17 |

#### Sign Injection Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FSGNJ.D | Sign injection | 3 |
| FSGNJN.D | Sign negate injection | 3 |
| FSGNJX.D | Sign XOR injection | 3 |

#### Data Transfer Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FMV.X.D | Double to int transfer | Split: 1+1 |
| FMV.D.X | Int to double transfer | Split: 1+1 |

#### Compare Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FMIN.D | Double minimum | 3 |
| FMAX.D | Double maximum | 3 |
| FEQ.D | Double equal compare | Split: 3+1 |
| FLT.D | Double less than compare | Split: 3+1 |
| FLE.D | Double less-or-equal compare | Split: 3+1 |

#### Type Conversion Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FCVT.S.D | Double to single | 3 |
| FCVT.D.S | Single to double | 3 |
| FCVT.W.D | Double to signed int | Split: 3+1 |
| FCVT.WU.D | Double to unsigned int | Split: 3+1 |
| FCVT.D.W | Signed int to double | Split: 3+1 |
| FCVT.D.WU | Unsigned int to double | Split: 3+1 |
| FCVT.L.D | Double to signed long | Split: 3+1 |
| FCVT.LU.D | Double to unsigned long | Split: 3+1 |
| FCVT.D.L | Signed long to double | Split: 3+1 |
| FCVT.D.LU | Unsigned long to double | Split: 3+1 |

#### Memory Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FLD | Double load | WEAK: ≥3 / STRONG: variable |
| FSD | Double store | WEAK: 1 / STRONG: variable |

#### Classification Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| FCLASS.D | Double classify | Split: 1+1 |

> **Reference:** Appendix A-5 for D instruction terminology

---

## 3.1.6 RV64C - Compressed Instructions

### Categories
| Category | Instructions |
|----------|-------------|
| Arithmetic | C.ADD, C.SUB, C.ADDI, etc. |
| Logical | C.AND, C.ANDI, C.OR, C.XOR |
| Shift | C.SLLI, C.SRLI, C.SRAI |
| Data Transfer | C.MV, C.LI, C.LUI |
| Branch/Jump | C.BEQZ, C.BNEZ, C.J, C.JR, C.JALR |
| Memory Access | C.LW, C.SW, C.LD, C.SD, etc. |
| Special | C.NOP, C.EBREAK |

### Instruction Latency Table

#### Arithmetic Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| C.ADD | Signed add | 1 |
| C.ADDW | Low 32-bit signed add | 1 |
| C.ADDI | Signed immediate add | 1 |
| C.ADDIW | Low 32-bit signed immediate add | 1 |
| C.SUB | Signed subtract | 1 |
| C.SUBW | Low 32-bit signed subtract | 1 |
| C.ADDI16SP | Add 16x immediate to SP | 1 |
| C.ADDI4SPN | Add 4x immediate to SP | 1 |

#### Logical Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| C.AND | Bitwise AND | 1 |
| C.ANDI | Immediate bitwise AND | 1 |
| C.OR | Bitwise OR | 1 |
| C.XOR | Bitwise XOR | 1 |

#### Shift Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| C.SLLI | Immediate logical left shift | 1 |
| C.SRLI | Immediate logical right shift | 1 |
| C.SRAI | Immediate arithmetic right shift | 1 |

#### Data Transfer Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| C.MV | Data move | 1 |
| C.LI | Load immediate | 1 |
| C.LUI | Load upper immediate | 1 |

#### Branch/Jump Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| C.BEQZ | Branch if equal to zero | 1 |
| C.BNEZ | Branch if not equal to zero | 1 |
| C.J | Unconditional jump | 1 |
| C.JR | Jump register | 1 |
| C.JALR | Jump register and link | 1 |

#### Memory Access Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| C.LW | Load word | WEAK: ≥3 / STRONG: variable |
| C.SW | Store word | WEAK: 1 / STRONG: variable |
| C.LWSP | Load word from SP | WEAK: ≥3 / STRONG: variable |
| C.SWSP | Store word to SP | WEAK: 1 / STRONG: variable |
| C.LD | Load doubleword | WEAK: ≥3 / STRONG: variable |
| C.SD | Store doubleword | WEAK: 1 / STRONG: variable |
| C.LDSP | Load doubleword from SP | WEAK: ≥3 / STRONG: variable |
| C.SDSP | Store doubleword to SP | WEAK: 1 / STRONG: variable |
| C.FLD | Float load double | WEAK: ≥3 / STRONG: variable |
| C.FSD | Float store double | WEAK: 1 / STRONG: variable |
| C.FLDSP | Float load double from SP | WEAK: ≥3 / STRONG: variable |
| C.FSDSP | Float store double to SP | WEAK: 1 / STRONG: variable |

#### Special Instructions
| Instruction | Description | Latency |
|-------------|-------------|---------|
| C.NOP | No operation | 1 |
| C.EBREAK | Breakpoint | 1 |

---

## Quick Reference: Latency Categories

| Latency | Instructions |
|---------|-------------|
| **1 cycle** | Most integer, logical, shift, compare, branch, compressed |
| **3-5 cycles** | Float multiply/add, float sign injection |
| **4-10/17 cycles** | Float divide/square root (variable) |
| **3-20 cycles** | Integer divide/remainder (variable) |
| **≥3 cycles** | Memory loads (WEAK order) |
| **Variable** | Memory stores, CSR ops, fences, atomics |
| **Blocked** | Exception returns, some CSR ops, fences |

---

## Memory Ordering Models

| Model | Load Latency | Store Latency |
|-------|-------------|---------------|
| **WEAK ORDER** | ≥3 cycles | 1 cycle |
| **STRONG ORDER** | Variable (unpredictable) | Variable (unpredictable) |

---

*Document generated for Agent-friendly reference. Original source: C910 User Manual Chapter 3*
