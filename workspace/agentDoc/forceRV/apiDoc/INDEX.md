# API Documentation Index

This index provides a progressive loading guide for the API documentation in this directory.

---

## Documents Overview

| Document | Description |
|----------|-------------|
| [FORCE-RISCV_brief_introduction.md](./FORCE-RISCV_brief_introduction.md) | Basic introduction to FORCE-RISCV components and execution flow |
| [FORCE-RISCV_User_Manual-v0.8.md](./FORCE-RISCV_User_Manual-v0.8.md) | Complete user manual with API reference |
| [RISC-V_Unprivileged_ISA.md](./RISC-V_Unprivileged_ISA.md) | RISC-V Unprivileged ISA Specification |

---

## 1. FORCE-RISCV Brief Introduction

### 1.1 Basic Components
- Config
- Arch
- Memory
- Virtual Memory
- State Transition/Privilege Switch
- Dependency
- ReExe/Bnt

### 1.2 Program Execution Flow
- Boot sequence
- Template execution
- End-of-test handling

---

## 2. FORCE-RISCV User Manual (v0.8)

### Table of Contents

#### Introduction & Getting Started
- [Introduction](./FORCE-RISCV_User_Manual-v0.8.md#introduction)
- [Getting Started](./FORCE-RISCV_User_Manual-v0.8.md#getting-started)
  - [2.1 Building the code](./FORCE-RISCV_User_Manual-v0.8.md#21-building-the-code)
  - [2.2 Running the program](./FORCE-RISCV_User_Manual-v0.8.md#22-running-the-program)
  - [2.3 Command line arguments](./FORCE-RISCV_User_Manual-v0.8.md#23-command-line-arguments)
  - [2.4 Back-End Generator Options](./FORCE-RISCV_User_Manual-v0.8.md#24-back-end-generator-options)
  - [2.5 Front-End Generator Options](./FORCE-RISCV_User_Manual-v0.8.md#25-front-end-generator-options)

#### FORCE-RISCV ISG
- [3.1 Front-end interface](./FORCE-RISCV_User_Manual-v0.8.md#31-front-end-interface)
  - [3.1.1 Variables and flow control](./FORCE-RISCV_User_Manual-v0.8.md#311-variables-and-flow-control)
  - [3.1.2 Sequence](./FORCE-RISCV_User_Manual-v0.8.md#312-sequence)
  - [3.1.4 Exception Handlers](./FORCE-RISCV_User_Manual-v0.8.md#314-exception-handlers)
- [3.2 Back-end characteristics](./FORCE-RISCV_User_Manual-v0.8.md#32-back-end-characteristics)
  - [3.2.1 ISS integration](./FORCE-RISCV_User_Manual-v0.8.md#321-iss-integration)
- [3.3 Register and memory resource controls](./FORCE-RISCV_User_Manual-v0.8.md#33-register-and-memory-resource-controls)
  - [3.3.1 Register initialization and reservation](./FORCE-RISCV_User_Manual-v0.8.md#331-register-initialization-and-reservation)
  - [3.3.2 Unpredictable Register Values](./FORCE-RISCV_User_Manual-v0.8.md#332-unpredictable-register-values)
  - [3.3.3 Memory initialization and reservation](./FORCE-RISCV_User_Manual-v0.8.md#333-memory-initialization-and-reservation)

#### Test Template
- [FORCE-RISCV Test Template](./FORCE-RISCV_User_Manual-v0.8.md#force-riscv-test-template)

#### Front-End APIs Reference
- [5.1 Instruction generation APIs](./FORCE-RISCV_User_Manual-v0.8.md#51-instruction-generation-apis)
  - [5.1.1 genInstruction](./FORCE-RISCV_User_Manual-v0.8.md#511-geninstruction)
  - [5.1.2 queryInstructionRecord](./FORCE-RISCV_User_Manual-v0.8.md#512-queryinstructionrecord)
- [5.2 Sequence Library APIs](./FORCE-RISCV_User_Manual-v0.8.md#52-sequence-library-apis)
  - [5.2.1 chooseOne](./FORCE-RISCV_User_Manual-v0.8.md#521-chooseone)
  - [5.2.2 getPermutated](./FORCE-RISCV_User_Manual-v0.8.md#522-getpermutated)
- [5.3 Address request APIs](./FORCE-RISCV_User_Manual-v0.8.md#53-address-request-apis)
  - [5.3.3 genVAforPA](./FORCE-RISCV_User_Manual-v0.8.md#533-genvaforpa)
  - [5.3.4 verifyVirtualAddress](./FORCE-RISCV_User_Manual-v0.8.md#534-verifyvirtualaddress)
- [5.4 Page request APIs](./FORCE-RISCV_User_Manual-v0.8.md#54-page-request-apis)
  - [5.4.1 genFreePagesRange](./FORCE-RISCV_User_Manual-v0.8.md#541-genfreepagesrange)
  - [5.4.2 getPageInfo](./FORCE-RISCV_User_Manual-v0.8.md#542-getpageinfo)
- [5.5 Register control APIs](./FORCE-RISCV_User_Manual-v0.8.md#55-register-control-apis)
  - [5.5.1 getRandomRegisters](./FORCE-RISCV_User_Manual-v0.8.md#551-getrandomregisters)
  - [5.5.2 getRandomGPR](./FORCE-RISCV_User_Manual-v0.8.md#552-getrandomgpr)
  - [5.5.3 reserveRegister](./FORCE-RISCV_User_Manual-v0.8.md#553-reserveregister)
  - [5.5.4 reserveRegisterByIndex](./FORCE-RISCV_User_Manual-v0.8.md#554-reserveregisterbyindex)
  - [5.5.5 unreserveRegister](./FORCE-RISCV_User_Manual-v0.8.md#555-unreserveregister)
  - [5.5.6 isRegisterReserved](./FORCE-RISCV_User_Manual-v0.8.md#556-isregisterreserved)
  - [5.5.7 readRegister](./FORCE-RISCV_User_Manual-v0.8.md#557-readregister)
  - [5.5.8 writeRegister](./FORCE-RISCV_User_Manual-v0.8.md#558-writeregister)
  - [5.5.9 initializeRegister](./FORCE-RISCV_User_Manual-v0.8.md#559-initializeregister)
  - [5.5.10 initializeRegisterFields](./FORCE-RISCV_User_Manual-v0.8.md#5510-initializeregisterfields)
  - [5.5.11 randomInitializeRegister](./FORCE-RISCV_User_Manual-v0.8.md#5511-randominitializeregister)
  - [5.5.12 randomInitializeRegisterFields](./FORCE-RISCV_User_Manual-v0.8.md#5512-randominitializeregisterfields)
  - [5.5.13 getRegisterIndex](./FORCE-RISCV_User_Manual-v0.8.md#5513-getregisterindex)
  - [5.5.14 getRegisterReloadValue](./FORCE-RISCV_User_Manual-v0.8.md#5514-getregisterreloadvalue)
  - [5.5.15 getRegisterInfo](./FORCE-RISCV_User_Manual-v0.8.md#5515-getregisterinfo)
  - [5.5.16 getRegisterFieldMask](./FORCE-RISCV_User_Manual-v0.8.md#5516-getregisterfieldmask)
  - [5.5.17 getRegisterFieldInfo](./FORCE-RISCV_User_Manual-v0.8.md#5517-getregisterfieldinfo)
  - [5.5.18 SystemRegisterUtils](./FORCE-RISCV_User_Manual-v0.8.md#5518-systemregisterutils)
- [5.6 Exception related APIs](./FORCE-RISCV_User_Manual-v0.8.md#56-exception-related-apis)
  - [5.6.1 queryExceptionVectorBaseAddress](./FORCE-RISCV_User_Manual-v0.8.md#561-queryexceptionvectorbaseaddress)
  - [5.6.2 queryExceptionRecordsCount](./FORCE-RISCV_User_Manual-v0.8.md#562-queryexceptionrecordscount)
  - [5.6.3 queryExceptionRecords](./FORCE-RISCV_User_Manual-v0.8.md#563-queryexceptionrecords)
  - [5.6.4 queryExceptions](./FORCE-RISCV_User_Manual-v0.8.md#564-queryexceptions)
- [5.7 PE states related APIs](./FORCE-RISCV_User_Manual-v0.8.md#57-pe-states-related-apis)
  - [5.7.1 getPEstate](./FORCE-RISCV_User_Manual-v0.8.md#571-getpestate)
  - [5.7.2 setPEstate](./FORCE-RISCV_User_Manual-v0.8.md#572-setpestate)
- [5.8 Memory control APIs](./FORCE-RISCV_User_Manual-v0.8.md#58-memory-control-apis)
  - [5.8.1 initializeMemory](./FORCE-RISCV_User_Manual-v0.8.md#581-initializememory)
- [5.9 ChoicesModifier APIs](./FORCE-RISCV_User_Manual-v0.8.md#59-choicesmodifier-apis)
  - [5.9.1 modifyOperandChoices](./FORCE-RISCV_User_Manual-v0.8.md#591-modifyoperandchoices)
  - [5.9.2 modifyRegisterFieldValueChoices](./FORCE-RISCV_User_Manual-v0.8.md#592-modifyregisterfieldvaluechoices)
  - [5.9.3 modifyPagingChoices](./FORCE-RISCV_User_Manual-v0.8.md#593-modifypagingchoices)
  - [5.9.4 modifyGeneralChoices](./FORCE-RISCV_User_Manual-v0.8.md#594-modifygeneralchoices)
  - [5.9.5 modifyDependenceChoices](./FORCE-RISCV_User_Manual-v0.8.md#595-modifydependencechoices)
  - [5.9.6 commitSet](./FORCE-RISCV_User_Manual-v0.8.md#596-commitset)
  - [5.9.7 registerSet](./FORCE-RISCV_User_Manual-v0.8.md#597-registerset)
  - [5.9.9 register](./FORCE-RISCV_User_Manual-v0.8.md#599-register)
  - [5.9.10 update](./FORCE-RISCV_User_Manual-v0.8.md#5910-update)
  - [5.9.11 revert](./FORCE-RISCV_User_Manual-v0.8.md#5911-revert)
  - [5.9.12 getChoicesTreeInfo](./FORCE-RISCV_User_Manual-v0.8.md#5912-getchoicestreeinfo)
- [5.10 Variable APIs](./FORCE-RISCV_User_Manual-v0.8.md#510-variable-apis)
  - [5.10.1 modifyVariable](./FORCE-RISCV_User_Manual-v0.8.md#5101-modifyvariable)
  - [5.10.2 getVariable](./FORCE-RISCV_User_Manual-v0.8.md#5102-getvariable)
- [5.11 Bnt Sequence APIs](./FORCE-RISCV_User_Manual-v0.8.md#511-bnt-sequence-apis)
  - [5.11.1 setBntHook](./FORCE-RISCV_User_Manual-v0.8.md#5111-setbnthook)
  - [5.11.2 revertBntHook](./FORCE-RISCV_User_Manual-v0.8.md#5112-revertbnthook)
- [5.12 Misc APIs](./FORCE-RISCV_User_Manual-v0.8.md#512-misc-apis)
  - [5.12.1 getOption](./FORCE-RISCV_User_Manual-v0.8.md#5121-getoption)
  - [5.12.2 pickWeighted](./FORCE-RISCV_User_Manual-v0.8.md#5122-pickweighted)
  - [5.12.3 pickWeightedValue](./FORCE-RISCV_User_Manual-v0.8.md#5123-pickweightedvalue)
  - [5.12.4 getPermutated](./FORCE-RISCV_User_Manual-v0.8.md#5124-getpermutated)
  - [5.12.5 sample](./FORCE-RISCV_User_Manual-v0.8.md#5125-sample)
  - [5.12.6 choice](./FORCE-RISCV_User_Manual-v0.8.md#5126-choice)
  - [5.12.7 choicePermutated](./FORCE-RISCV_User_Manual-v0.8.md#5127-choicepermutated)
  - [5.12.8 genInstrOrSequence](./FORCE-RISCV_User_Manual-v0.8.md#5128-geninstrorsequence)
  - [5.12.9 random32](./FORCE-RISCV_User_Manual-v0.8.md#5129-random32)
  - [5.12.10 random64](./FORCE-RISCV_User_Manual-v0.8.md#51210-random64)
  - [5.12.12 notice, warn, debug, info and trace](./FORCE-RISCV_User_Manual-v0.8.md#51212-notice-warn-debug-info-and-trace)
  - [5.12.13 bitstream](./FORCE-RISCV_User_Manual-v0.8.md#51213-bitstream)
  - [5.12.14 genData](./FORCE-RISCV_User_Manual-v0.8.md#51214-gendata)

#### Sequence Examples
- [6.1 Basic Sequences](./FORCE-RISCV_User_Manual-v0.8.md#61-basic-sequences)
- [6.2 Slightly more complicated sequences](./FORCE-RISCV_User_Manual-v0.8.md#62-slightly-more-complicated-sequences)
- [6.3 Sequence library](./FORCE-RISCV_User_Manual-v0.8.md#63-sequence-library)
- [6.4 Creating user defined instruction set or tree](./FORCE-RISCV_User_Manual-v0.8.md#64-creating-user-defined-instruction-set-or-tree)
- [6.5 Controlled way to setup instruction dependency](./FORCE-RISCV_User_Manual-v0.8.md#65-controlled-way-to-setup-instruction-dependency)
- [6.6 Create user defined choices modifier](./FORCE-RISCV_User_Manual-v0.8.md#66-create-user-defined-choices-modifier-and-control-choices-during)
- [6.7 Creating a custom entry point and control flow](./FORCE-RISCV_User_Manual-v0.8.md#67-creating-a-custom-entry-point-and-control-flow-for-a-utility)

#### Choices and Variables
- [7.1 Register dependency controls](./FORCE-RISCV_User_Manual-v0.8.md#71-register-dependency-controls)
- [7.2 Register reloading controls](./FORCE-RISCV_User_Manual-v0.8.md#72-register-reloading-controls)
- [7.3 Address table allocation controls](./FORCE-RISCV_User_Manual-v0.8.md#73-address-table-allocation-controls)
- [7.4 Page table allocation controls](./FORCE-RISCV_User_Manual-v0.8.md#74-page-table-allocation-controls)

#### Appendix
- [Appendix A Architecture version compliance](./FORCE-RISCV_User_Manual-v0.8.md#appendix-a-architecture-version-compliance)

---

## 3. RISC-V Unprivileged ISA Specification

### Chapter 1: Introduction
- [1.1 RISC-V Hardware Platform Terminology](./RISC-V_Unprivileged_ISA.md#1-1)
- [1.2 RISC-V Software Execution Environments and Harts](./RISC-V_Unprivileged_ISA.md#1-2)
- [1.3 RISC-V ISA Overview](./RISC-V_Unprivileged_ISA.md#1-3)
- [1.4 Memory](./RISC-V_Unprivileged_ISA.md#1-4)
- [1.5 Base Instruction-Length Encoding](./RISC-V_Unprivileged_ISA.md#1-5)
- [1.6 Exceptions, Traps, and Interrupts](./RISC-V_Unprivileged_ISA.md#1-6)
- [1.7 UNSPECIFIED Behaviors and Values](./RISC-V_Unprivileged_ISA.md#1-7)

### Chapter 2: RV32I Base Integer Instruction Set
- [2.1 Programmers' Model for Base Integer ISA](./RISC-V_Unprivileged_ISA.md#2-1)
- [2.2 Base Instruction Formats](./RISC-V_Unprivileged_ISA.md#2-2)
- [2.3 Immediate Encoding Variants](./RISC-V_Unprivileged_ISA.md#2-3)
- [2.4 Integer Computational Instructions](./RISC-V_Unprivileged_ISA.md#2-4)
  - [2.4.1 Integer Register-Immediate Instructions](./RISC-V_Unprivileged_ISA.md#2-4-1)
  - [2.4.2 Integer Register-Register Instructions](./RISC-V_Unprivileged_ISA.md#2-4-2)
  - [2.4.3 NOP Instruction](./RISC-V_Unprivileged_ISA.md#2-4-3)
- [2.5 Control Transfer Instructions](./RISC-V_Unprivileged_ISA.md#2-5)
  - [2.5.1 Unconditional Jumps](./RISC-V_Unprivileged_ISA.md#2-5-1)
  - [2.5.2 Conditional Branches](./RISC-V_Unprivileged_ISA.md#2-5-2)
- [2.6 Load and Store Instructions](./RISC-V_Unprivileged_ISA.md#2-6)
- [2.7 Memory Ordering Instructions](./RISC-V_Unprivileged_ISA.md#2-7)
- [2.8 Environment Call and Breakpoints](./RISC-V_Unprivileged_ISA.md#2-8)
- [2.9 HINT Instructions](./RISC-V_Unprivileged_ISA.md#2-9)

### Chapter 3: RV32E Base Integer Instruction Set
- [3.1 RV32E and RV64E Programmers' Model](./RISC-V_Unprivileged_ISA.md#3-1)
- [3.2 RV32E and RV64E Instruction Set Encoding](./RISC-V_Unprivileged_ISA.md#3-2)

### Chapter 4: RV64I Base Integer Instruction Set
- [4.1 Register State](./RISC-V_Unprivileged_ISA.md#4-1)
- [4.2 Integer Computational Instructions](./RISC-V_Unprivileged_ISA.md#4-2)
- [4.3 Load and Store Instructions](./RISC-V_Unprivileged_ISA.md#4-3)
- [4.4 HINT Instructions](./RISC-V_Unprivileged_ISA.md#4-4)

### Chapter 6: Control and Status Registers
- [6.1 CSR Instructions](./RISC-V_Unprivileged_ISA.md#6-1)
  - [6.1.1 CSR Access Ordering](./RISC-V_Unprivileged_ISA.md#6-1-1)

### Chapter 7: Counters and Timers
- [7.1 "Zicntr" Extension for Base Counters and Timers](./RISC-V_Unprivileged_ISA.md#7-1)
- [7.2 "Zihpm" Extension for Hardware Performance Counters](./RISC-V_Unprivileged_ISA.md#7-2)

### Chapter 10: Zcmop Extension
- [10.1 "Zcmop" Compressed May-Be-Operations Extension](./RISC-V_Unprivileged_ISA.md#10-1)

### Chapter 11: Conditional Zero Instructions
- [11.1 Instructions (in alphabetical order)](./RISC-V_Unprivileged_ISA.md#11-1)
  - [11.1.1 czero.eqz](./RISC-V_Unprivileged_ISA.md#11-1-1)
  - [11.1.2 czero.nez](./RISC-V_Unprivileged_ISA.md#11-1-2)
- [11.2 Usage examples](./RISC-V_Unprivileged_ISA.md#11-2)

### Chapter 12: "M" Extension for Integer Multiplication and Division
- [12.1 Multiplication Operations](./RISC-V_Unprivileged_ISA.md#12-1)
- [12.2 Division Operations](./RISC-V_Unprivileged_ISA.md#12-2)
- [12.3 Zmmul Extension](./RISC-V_Unprivileged_ISA.md#12-3)

### Chapter 13: Atomic Instructions
- [13.1 Specifying Ordering of Atomic Instructions](./RISC-V_Unprivileged_ISA.md#13-1)
- [13.2 "Zalrsc" Extension for Load-Reserved/Store-Conditional](./RISC-V_Unprivileged_ISA.md#13-2)
- [13.3 Eventual Success of Store-Conditional Instructions](./RISC-V_Unprivileged_ISA.md#13-3)
- [13.4 "Zaamo" Extension for Atomic Memory Operations](./RISC-V_Unprivileged_ISA.md#13-4)

### Chapter 14-17: Advanced Atomic Operations
- [14.1 Wait-on-Reservation-Set Instructions](./RISC-V_Unprivileged_ISA.md#14-1)
- [15.1 Word/Doubleword/Quadword CAS Instructions](./RISC-V_Unprivileged_ISA.md#15-1)
- [16.1 Byte and Halfword Atomic Memory Operation Instructions](./RISC-V_Unprivileged_ISA.md#16-1)
- [17.1 Load-Acquire and Store-Release Instructions](./RISC-V_Unprivileged_ISA.md#17-1)
- [17.2 Load Acquire](./RISC-V_Unprivileged_ISA.md#17-2)
- [17.3 Store Release](./RISC-V_Unprivileged_ISA.md#17-3)

### Chapter 18: Memory Model
- [18.1 Definition of the RVWMO Memory Model](./RISC-V_Unprivileged_ISA.md#18-1)
  - [18.1.1 Memory Model Primitives](./RISC-V_Unprivileged_ISA.md#18-1-1)
  - [18.1.2 Syntactic Dependencies](./RISC-V_Unprivileged_ISA.md#18-1-2)
  - [18.1.3 Preserved Program Order](./RISC-V_Unprivileged_ISA.md#18-1-3)
  - [18.1.4 Memory Model Axioms](./RISC-V_Unprivileged_ISA.md#18-1-4)
- [18.2 CSR Dependency Tracking Granularity](./RISC-V_Unprivileged_ISA.md#18-2)
- [18.3 Source and Destination Register Listings](./RISC-V_Unprivileged_ISA.md#18-3)

### Chapter 20: Cache Management Operations
- [20.1 Pseudocode for instruction semantics](./RISC-V_Unprivileged_ISA.md#20-1)
- [20.2 Introduction](./RISC-V_Unprivileged_ISA.md#20-2)
- [20.3 Background](./RISC-V_Unprivileged_ISA.md#20-3)
- [20.4 Coherent Agents and Caches](./RISC-V_Unprivileged_ISA.md#20-4)
- [20.5 CSR controls for CMO instructions](./RISC-V_Unprivileged_ISA.md#20-5)
- [20.6 Extensions](./RISC-V_Unprivileged_ISA.md#20-6)
- [20.7 Instructions](./RISC-V_Unprivileged_ISA.md#20-7)

### Chapter 21-24: Floating-Point Extensions
- [21.1 F Register State](./RISC-V_Unprivileged_ISA.md#21-1)
- [21.2 Floating-Point Control and Status Register](./RISC-V_Unprivileged_ISA.md#21-2)
- [21.3 NaN Generation and Propagation](./RISC-V_Unprivileged_ISA.md#21-3)
- [21.4 Subnormal Arithmetic](./RISC-V_Unprivileged_ISA.md#21-4)
- [21.5 Single-Precision Load and Store Instructions](./RISC-V_Unprivileged_ISA.md#21-5)
- [21.6 Single-Precision Floating-Point Computational Instructions](./RISC-V_Unprivileged_ISA.md#21-6)
- [21.7 Single-Precision Floating-Point Conversion and Move Instructions](./RISC-V_Unprivileged_ISA.md#21-7)
- [21.8 Single-Precision Floating-Point Compare Instructions](./RISC-V_Unprivileged_ISA.md#21-8)
- [21.9 Single-Precision Floating-Point Classify Instruction](./RISC-V_Unprivileged_ISA.md#21-9)
- [22.1 D Register State](./RISC-V_Unprivileged_ISA.md#22-1)
- [22.2 NaN Boxing of Narrower Values](./RISC-V_Unprivileged_ISA.md#22-2)
- [22.3 Double-Precision Load and Store Instructions](./RISC-V_Unprivileged_ISA.md#22-3)
- [22.4 Double-Precision Floating-Point Computational Instructions](./RISC-V_Unprivileged_ISA.md#22-4)
- [22.5 Double-Precision Floating-Point Conversion and Move Instructions](./RISC-V_Unprivileged_ISA.md#22-5)
- [22.6 Double-Precision Floating-Point Compare Instructions](./RISC-V_Unprivileged_ISA.md#22-6)
- [22.7 Double-Precision Floating-Point Classify Instruction](./RISC-V_Unprivileged_ISA.md#22-7)
- [23.1 Quad-Precision Load and Store Instructions](./RISC-V_Unprivileged_ISA.md#23-1)
- [23.2 Quad-Precision Computational Instructions](./RISC-V_Unprivileged_ISA.md#23-2)
- [23.3 Quad-Precision Convert and Move Instructions](./RISC-V_Unprivileged_ISA.md#23-3)
- [23.4 Quad-Precision Floating-Point Compare Instructions](./RISC-V_Unprivileged_ISA.md#23-4)
- [23.5 Quad-Precision Floating-Point Classify Instruction](./RISC-V_Unprivileged_ISA.md#23-5)
- [24.1 Half-Precision Load and Store Instructions](./RISC-V_Unprivileged_ISA.md#24-1)
- [24.2 Half-Precision Computational Instructions](./RISC-V_Unprivileged_ISA.md#24-2)
- [24.3 Half-Precision Conversion and Move Instructions](./RISC-V_Unprivileged_ISA.md#24-3)
- [24.4 Half-Precision Floating-Point Compare Instructions](./RISC-V_Unprivileged_ISA.md#24-4)
- [24.5 Half-Precision Floating-Point Classify Instruction](./RISC-V_Unprivileged_ISA.md#24-5)
- [24.6 "Zfhmin" Standard Extension for Minimal Half-Precision Floating-Point](./RISC-V_Unprivileged_ISA.md#24-6)

### Chapter 25: BF16 Extension
- [25.1 Introduction](./RISC-V_Unprivileged_ISA.md#25-1)
- [25.2 Intended Audience](./RISC-V_Unprivileged_ISA.md#25-2)
- [25.3 Number Format](./RISC-V_Unprivileged_ISA.md#25-3)
- [25.4 Extensions](./RISC-V_Unprivileged_ISA.md#25-4)
- [25.5 Instructions](./RISC-V_Unprivileged_ISA.md#25-5)

### Chapter 26-27: Additional Floating-Point
- [26.1 Load-Immediate Instructions](./RISC-V_Unprivileged_ISA.md#26-1)
- [26.2 Minimum and Maximum Instructions](./RISC-V_Unprivileged_ISA.md#26-2)
- [26.3 Round-to-Integer Instructions](./RISC-V_Unprivileged_ISA.md#26-3)
- [26.4 Modular Convert-to-Integer Instruction](./RISC-V_Unprivileged_ISA.md#26-4)
- [26.5 Move Instructions](./RISC-V_Unprivileged_ISA.md#26-5)
- [26.6 Comparison Instructions](./RISC-V_Unprivileged_ISA.md#26-6)
- [27.1 Processing of Narrower Values](./RISC-V_Unprivileged_ISA.md#27-1)
- [27.2 Zdinx](./RISC-V_Unprivileged_ISA.md#27-2)
- [27.3 Processing of Wider Values](./RISC-V_Unprivileged_ISA.md#27-3)
- [27.4 Zhinx](./RISC-V_Unprivileged_ISA.md#27-4)
- [27.5 Zhinxmin](./RISC-V_Unprivileged_ISA.md#27-5)
- [27.6 Privileged Architecture Implications](./RISC-V_Unprivileged_ISA.md#27-6)

### Chapter 28: Compressed Instructions (RVC)
- [28.1 Overview](./RISC-V_Unprivileged_ISA.md#28-1)
- [28.2 Compressed Instruction Formats](./RISC-V_Unprivileged_ISA.md#28-2)
- [28.3 Load and Store Instructions](./RISC-V_Unprivileged_ISA.md#28-3)
- [28.4 Control Transfer Instructions](./RISC-V_Unprivileged_ISA.md#28-4)
- [28.5 Integer Computational Instructions](./RISC-V_Unprivileged_ISA.md#28-5)
- [28.6 Usage of C Instructions in LR/SC Sequences](./RISC-V_Unprivileged_ISA.md#28-6)
- [28.7 HINT Instructions](./RISC-V_Unprivileged_ISA.md#28-7)
- [28.8 RVC Instruction Set Listings](./RISC-V_Unprivileged_ISA.md#28-8)

### Chapter 29: Zc* Extensions
- [29.1 Zc* Overview](./RISC-V_Unprivileged_ISA.md#29-1)
- [29.5 Zca](./RISC-V_Unprivileged_ISA.md#29-5)
- [29.6 Zcf (RV32 only)](./RISC-V_Unprivileged_ISA.md#29-6)
- [29.8 Zcb](./RISC-V_Unprivileged_ISA.md#29-8)
- [29.9 Zcmp](./RISC-V_Unprivileged_ISA.md#29-9)
- [29.10 Zcmt](./RISC-V_Unprivileged_ISA.md#29-10)
- [29.11 Zc instruction formats](./RISC-V_Unprivileged_ISA.md#29-11)
- [29.12 Zcb instructions](./RISC-V_Unprivileged_ISA.md#29-12)
- [29.13 PUSH/POP register instructions](./RISC-V_Unprivileged_ISA.md#29-13)
- [29.14 Table Jump Overview](./RISC-V_Unprivileged_ISA.md#29-14)

### Chapter 30: Bit Manipulation (B Extension)
- [30.1 "B" Extension for Bit Manipulation](./RISC-V_Unprivileged_ISA.md#30-1)
- [30.2 Zba: Extension for Address generation](./RISC-V_Unprivileged_ISA.md#30-2)
- [30.3 Zbb: Extension for Basic bit-manipulation](./RISC-V_Unprivileged_ISA.md#30-3)
- [30.4 Zbc: Extension for Carry-less multiplication](./RISC-V_Unprivileged_ISA.md#30-4)
- [30.5 Zbs: Extension for Single-bit instructions](./RISC-V_Unprivileged_ISA.md#30-5)
- [30.6 Zbkb: Extension for Bit-manipulation for Cryptography](./RISC-V_Unprivileged_ISA.md#30-6)
- [30.7 Zbkc: Extension for Carry-less multiplication for Cryptography](./RISC-V_Unprivileged_ISA.md#30-7)
- [30.8 Zbkx: Extension for Crossbar permutations](./RISC-V_Unprivileged_ISA.md#30-8)
- [30.9 Instructions (in alphabetical order)](./RISC-V_Unprivileged_ISA.md#30-9)

---

## Quick Reference

### FORCE-RISCV API Categories

| Category | Key APIs |
|----------|----------|
| **Instruction Generation** | `genInstruction`, `queryInstructionRecord` |
| **Sequence Library** | `chooseOne`, `getPermutated` |
| **Address/Page** | `genVAforPA`, `verifyVirtualAddress`, `genFreePagesRange`, `getPageInfo` |
| **Register Control** | `getRandomRegisters`, `getRandomGPR`, `reserveRegister`, `readRegister`, `writeRegister`, `initializeRegister` |
| **Exception** | `queryExceptionVectorBaseAddress`, `queryExceptionRecords`, `queryExceptions` |
| **Memory** | `initializeMemory` |
| **Choices Modifier** | `modifyOperandChoices`, `modifyPagingChoices`, `modifyGeneralChoices` |
| **Variable** | `modifyVariable`, `getVariable` |
| **Misc** | `getOption`, `pickWeighted`, `sample`, `choice`, `random32`, `random64` |

### RISC-V ISA Extensions Quick Reference

| Extension | Description |
|-----------|-------------|
| **I** | Base Integer Instruction Set (RV32I/RV64I) |
| **E** | Embedded Base Integer (RV32E/RV64E) |
| **M** | Integer Multiplication and Division |
| **A** | Atomic Instructions (Zaamo, Zalrsc) |
| **F** | Single-Precision Floating-Point |
| **D** | Double-Precision Floating-Point |
| **Q** | Quad-Precision Floating-Point |
| **Zfh/Zfhmin** | Half-Precision Floating-Point |
| **C** | Compressed Instructions |
| **B** | Bit Manipulation (Zba, Zbb, Zbc, Zbs) |
| **Zicntr** | Base Counters and Timers |
| **Zihpm** | Hardware Performance Counters |
| **Zc*** | Additional Compressed Extensions |