# FORCE-RISCV Document Tag Index

## Overview

本文档为 FORCE-RISCV 的 `agentDoc/forceRV/apiDoc` 和 `agentDoc/forceRV/example` 中的所有文件
建立了层次化标签索引，用于提升 Agentic Search 的检索精度（hier mem index optimize）。

### Tag 体系说明

每个文件附带一组分层标签，遵循以下约定：

| 层级 | 前缀 | 含义 | 示例 |
|------|------|------|------|
| `area:` | 功能域 | API reference / ISA spec / 代码示例所属大类 | `area:memory` |
| `feat:` | 功能点 | 具体的功能或 API | `feat:genVA` |
| `ext:`  | ISA 扩展 | RISC-V ISA 扩展名 | `ext:RV64I` |
| `type:` | 文档类型 | doc / example / guide | `type:example` |
| `pat:`  | 测试模式 | 示例采用的测试策略 | `pat:basic` |

### Tag 使用说明

- **apiDoc 文件**：大型文档（User Manual、ISA Spec）标注其覆盖的全部章节/主题
- **example 文件**：每个 `*_force.py` 示例标注 3-5 个最相关的标签
- **控制文件**（`*_fctrl.py`）：标注为 `type:config`

---

## 1. apiDoc — 文档标签

### FORCE-RISCV_brief_introduction.md
| 标签 | 值 |
|------|-----|
| `area:` | architecture |
| `feat:` | component-overview, execution-flow, boot-sequence, template-execution, end-of-test |
| `type:` | doc |
| `desc:` | FORCE-RISCV 架构组件总览（Config/Arch/Memory/VirtualMemory/StateTransition/PrivilegeSwitch/Dependency/ReExe/Bnt）和程序执行流程 |

### FORCE-RISCV_User_Manual-v0.8.md
| 标签 | 值 |
|------|-----|
| `area:` | api-reference |
| `feat:` | genInstruction, queryInstructionRecord, chooseOne, getPermutated, genVAforPA, verifyVirtualAddress, genFreePagesRange, getPageInfo, getRandomRegisters, getRandomGPR, reserveRegister, unreserveRegister, readRegister, writeRegister, initializeRegister, queryExceptionRecords, queryExceptions, getPEstate, setPEstate, initializeMemory, modifyOperandChoices, modifyPagingChoices, modifyGeneralChoices, modifyVariable, getVariable, setBntHook, revertBntHook, pickWeighted, sample, random32, random64, genData, bitstream, ConstraintSet, ChoicesModifier, sequence-library, test-template, command-line-args, backend-options, frontend-options, ISS-integration, register-dependency, register-reloading, page-table-allocation, address-table-allocation |
| `type:` | doc |
| `desc:` | FORCE-RISCV 完整用户手册 v0.8，涵盖全部 Front-End API、测试模板、命令行参数、Choices/Variables 控制 |

### RISC-V_Unprivileged_ISA.md
| 标签 | 值 |
|------|-----|
| `area:` | isa-spec |
| `ext:` | RV32I, RV64I, RV32E, Zicsr, Zicntr, Zihpm, Zcmop, Zicond, M, Zaamo, Zalrsc, F, D, Q, Zfh, Zfhmin, Zfbf, Zfa, Zfinx, C, Zca, Zcf, Zcb, Zcmp, Zcmt, B, Zba, Zbb, Zbc, Zbs, Zbkb, Zbkc, Zbkx |
| `feat:` | instruction-encoding, instruction-semantics, CSR, memory-model, RVWMO, cache-management, floating-point, compressed-instructions, bit-manipulation |
| `type:` | doc |
| `desc:` | RISC-V 非特权 ISA 规范，涵盖 RV32I/RV64I 基础指令、M/A/F/D/Q/C/B/V 扩展、CSR、内存模型 |

### README.md
| 标签 | 值 |
|------|-----|
| `area:` | quickstart |
| `feat:` | build-instructions, setup, run-examples, master-run, ELF-generation, riscvOVPsim, coverage, handcar-cosim |
| `type:` | doc |
| `desc:` | FORCE-RISCV 快速入门指南，包含构建步骤、运行示例、master_run 工作流、输出文件说明 |

### INDEX.md
| 标签 | 值 |
|------|-----|
| `area:` | navigation |
| `feat:` | table-of-contents, api-categories, isa-extensions, progressive-loading |
| `type:` | doc |
| `desc:` | API 文档索引导航，提供按章节定位的渐进加载指南和 API 分类速查表 |

### AGENTS.md (apiDoc/)
| 标签 | 值 |
|------|-----|
| `area:` | navigation |
| `feat:` | progressive-loading, document-index, api-categories, isa-chapters |
| `type:` | doc |
| `desc:` | apiDoc 目录的 AI Agent 导航文件，提供三级渐进加载指南 |

---

## 2. Standalone Guides — 独立指南

### memory_operations_guide.md
| 标签 | 值 |
|------|-----|
| `area:` | memory |
| `feat:` | genVA, genPA, genVAforPA, initializeMemory, LSTarget, address-alignment, alias-pattern, store-load-sequence, memory-init-pattern, address-reuse, physical-alias, constraint-set |
| `type:` | guide |
| `desc:` | 内存操作完整指南，涵盖所有 VA/PA 生成 API、内存初始化、LSTarget 用法和常见模式 |

### AGENTS.md (forceRV/)
| 标签 | 值 |
|------|-----|
| `area:` | navigation |
| `feat:` | directory-structure, quick-reference, common-tasks, advanced-features, key-apis |
| `type:` | doc |
| `desc:` | forceRV 文档库根导航文件，提供目录结构和常用任务速查 |

### AGENTS.md (example/)
| 标签 | 值 |
|------|-----|
| `area:` | navigation |
| `feat:` | example-index, control-file-convention, category-overview, learning-path |
| `type:` | doc |
| `desc:` | example 目录的 AI Agent 导航文件，提供示例分类和推荐学习路径 |

---

## 3. Example — 示例标签

### 3.1 APIs/ (32 `*_force.py` files)

#### api_genFreePagesRange_01_force.py
| `area:` | paging | `feat:` | genFreePagesRange | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### api_genPA_01_force.py
| `area:` | memory | `feat:` | genPA, MemAttr | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### api_genVA_01_force.py
| `area:` | memory | `feat:` | genVA, LSTarget, alignment | `ext:` | RV64G | `type:` | example | `pat:` | parametric-sweep |

#### api_genVA_02_force.py
| `area:` | memory | `feat:` | genVA, FlatMap, address-range | `ext:` | RV64G | `type:` | example | `pat:` | advanced |

#### api_genVAforPA_01_force.py
| `area:` | memory | `feat:` | genVAforPA, PA-VA-mapping | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### api_genVAforPA_alias_force.py
| `area:` | memory | `feat:` | genVAforPA, alias-mapping, ForceNewAddr | `ext:` | RV64G | `type:` | example | `pat:` | alias |

#### api_genVA_reuse_force.py
| `area:` | memory | `feat:` | genVA, address-reuse, ConstraintSet | `ext:` | RV64G | `type:` | example | `pat:` | reuse |

#### api_getPageInfo_01_force.py
| `area:` | paging | `feat:` | getPageInfo, page-table-query | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### api_queryExceptionVectorBaseAddress_force.py
| `area:` | exception | `feat:` | queryExceptionVectorBaseAddress, exception-vector | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### api_verifyVirtualAddress_01_force.py
| `area:` | memory | `feat:` | verifyVirtualAddress, VA-validation | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### AccessReservedRegisterTest_force.py
| `area:` | register | `feat:` | reserveRegister, register-access-control | `ext:` | RV64G | `type:` | example | `pat:` | access-control |

#### BitstreamTest_force.py
| `area:` | misc | `feat:` | bitstream, random-data | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### ChoicesModificationTest_force.py
| `area:` | choices | `feat:` | modifyOperandChoices, modifyRegisterFieldValueChoices, modifyPagingChoices, modifyGeneralChoices, commitSet, revert | `ext:` | RV64G | `type:` | example | `pat:` | comprehensive |

#### Constraint_force.py
| `area:` | utility | `feat:` | ConstraintSet, addRange, subRange, mergeConstraintSet, chooseValue | `ext:` | - | `type:` | example | `pat:` | unit-test |

#### CustomEntryPointTest_force.py
| `area:` | flow-control | `feat:` | custom-entry-point, control-flow | `ext:` | RV64G | `type:` | example | `pat:` | advanced |

#### GenData_test_force.py
| `area:` | data | `feat:` | genData, INT32, INT64, FP64, vector-data, data-pattern | `ext:` | RV64G | `type:` | example | `pat:` | unit-test |

#### GetRandomRegisterTest_force.py
| `area:` | register | `feat:` | getRandomGPR, getRandomRegisters, FPR, VECREG | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### InitializeRandomRandomlyTest_force.py
| `area:` | register | `feat:` | randomInitializeRegister, random-initialization | `ext:` | RV64G | `type:` | example | `pat:` | random |

#### InitializeRegisterTest_force.py
| `area:` | register | `feat:` | initializeRegister, initializeRegisterFields, register-reload | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### InquiryAPITest_force.py
| `area:` | misc | `feat:` | queryInstructionRecord, getVariable, getPEstate, inquiry-APIs | `ext:` | RV64G | `type:` | example | `pat:` | comprehensive |

#### LoadImmediate_force.py
| `area:` | instruction | `feat:` | load-immediate, LI, LUI | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### LoadRegisterPreambleTest_force.py
| `area:` | instruction | `feat:` | load-register, NoPreamble, UsePreamble, preamble-control | `ext:` | RV64G | `type:` | example | `pat:` | preamble |

#### LoopControlTest_force.py
| `area:` | loop | `feat:` | LoopControl, loop-iteration, register-verify | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### PickWeightedValue_test_force.py
| `area:` | utility | `feat:` | pickWeightedValue, weighted-selection | `ext:` | - | `type:` | example | `pat:` | basic |

#### QueryResourceEntropyTest_force.py
| `area:` | misc | `feat:` | resource-entropy, query-resources | `ext:` | RV64G | `type:` | example | `pat:` | diagnostic |

#### RandomChoiceAPITest_force.py
| `area:` | utility | `feat:` | choice, random-selection, choicePermutated | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### reg_dependence_force.py
| `area:` | dependency | `feat:` | register-dependence, modifyDependenceChoices, operand-dependency | `ext:` | RV64G | `type:` | example | `pat:` | dependence |

#### ReserveRegisterTest_force.py
| `area:` | register | `feat:` | reserveRegister, unreserveRegister, isRegisterReserved | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### SetMisaInitialValue_force.py
| `area:` | register | `feat:` | misa, system-register, ISA-configuration | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### skip_boot_force.py
| `area:` | boot | `feat:` | skip-boot, GenMode, no-ISS | `ext:` | RV64G | `type:` | example | `pat:` | boot-flow |

#### State_force.py
| `area:` | state | `feat:` | getPEstate, setPEstate, state-management | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### WriteRegisterTest_force.py
| `area:` | register | `feat:` | writeRegister, readRegister, register-field | `ext:` | RV64G | `type:` | example | `pat:` | basic |

---

### 3.2 address_solving/ (5 `*_force.py` files)

#### address_solving_address_reuse_force.py
| `area:` | memory | `feat:` | address-reuse, ConstraintSet, LSTarget, genVA | `ext:` | RV64G | `type:` | example | `pat:` | reuse |

#### address_solving_basic_load_store_force.py
| `area:` | memory | `feat:` | load-store, NoPreamble, address-solving, queryExceptionRecordsCount | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### address_solving_compressed_same_operands_force.py
| `area:` | memory | `feat:` | compressed-load-store, same-operand, C.LW, C.SW | `ext:` | RVC | `type:` | example | `pat:` | edge-case |

#### address_solving_implied_base_force.py
| `area:` | memory | `feat:` | implied-base, SP-relative, C.LWSP, C.SWSP | `ext:` | RVC | `type:` | example | `pat:` | edge-case |

#### RVC_misaligned_force.py
| `area:` | memory | `feat:` | misaligned-access, compressed-instruction, RVC-misalignment | `ext:` | RVC | `type:` | example | `pat:` | edge-case |

---

### 3.3 bnt/ (1 `*_force.py` file)

#### speculative_bnt_force.py
| `area:` | branch | `feat:` | BntSequence, setBntHook, revertBntHook, SpeculativeBnt, JALR, branch-not-taken | `ext:` | RV64G | `type:` | example | `pat:` | speculative |

---

### 3.4 branch/ (3 `*_force.py` files)

#### branch_pc_relative_conditional_force.py
| `area:` | branch | `feat:` | conditional-branch, PC-relative, BRarget, queryInstructionRecord, BEQ, BNE, BLT, BGE | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### branch_pc_relative_unconditional_force.py
| `area:` | branch | `feat:` | unconditional-branch, PC-relative, JAL, BRarget | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### branch_register_force.py
| `area:` | branch | `feat:` | register-indirect-branch, JALR, rs1 | `ext:` | RV64G | `type:` | example | `pat:` | basic |

---

### 3.5 exception_handlers/ (7 `*_force.py` files)

#### access_csrs_force.py
| `area:` | exception | `feat:` | CSR-access, trap-handling, exception-delegation, privilege | `ext:` | RV64G | `type:` | example | `pat:` | exception |

#### assembly_helper_force.py
| `area:` | utility | `feat:` | AssemblyHelperRISCV, genReadSystemRegister, wrapper | `ext:` | RV64G | `type:` | example | `pat:` | utility |

#### ecall_ebreak_force.py
| `area:` | exception | `feat:` | ECALL, EBREAK, systemCall, TrapsRedirectModifier, privilege-switch, BntSequence | `ext:` | RV64G | `type:` | example | `pat:` | exception |

#### exception_counts_force.py
| `area:` | exception | `feat:` | queryExceptionRecordsCount, exception-counting, trap-statistics | `ext:` | RV64G | `type:` | example | `pat:` | diagnostic |

#### instruction_misaligned_exception_force.py
| `area:` | exception | `feat:` | instruction-misaligned, exception-vector, trap-handler | `ext:` | RV64G | `type:` | example | `pat:` | exception |

#### stack_force.py
| `area:` | memory | `feat:` | stack-initialization, initializeMemory, stack-pointer, RandomUtils.random64 | `ext:` | RV64G | `type:` | example | `pat:` | setup |

#### trap_vm_force.py
| `area:` | exception | `feat:` | virtual-memory-trap, page-fault, trap-handler, MMU | `ext:` | RV64G | `type:` | example | `pat:` | exception |

---

### 3.6 fsuExamples/ (4 `*_force.py` files)

#### fsu_basic_force.py
| `area:` | floating-point | `feat:` | pickWeighted, FMUL, FDIV, FMADD, FADD | `ext:` | F, D | `type:` | example | `pat:` | basic |

#### test_muldiv_data_constr_force.py
| `area:` | floating-point | `feat:` | MUL, DIV, data-constraint, genData | `ext:` | M, RV64G | `type:` | example | `pat:` | constrained |

#### test_muldiv_nan_boxing_force.py
| `area:` | floating-point | `feat:` | NaN-boxing, MUL, DIV, narrow-value | `ext:` | M, F, D | `type:` | example | `pat:` | edge-case |

#### _test_muldiv_force.py
| `area:` | floating-point | `feat:` | MUL, DIV, REM, integer-arithmetic | `ext:` | M, RV64G | `type:` | example | `pat:` | basic |

---

### 3.7 loop/ (4 `*_force.py` files)

#### loop_basic_force.py
| `area:` | loop | `feat:` | LoopControl, loop-iteration, register-increment, ADDI | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### loop_broad_random_instructions_force.py
| `area:` | loop | `feat:` | LoopControl, broad-random, instruction-variety | `ext:` | RV64G | `type:` | example | `pat:` | random |

#### loop_reconverge_force.py
| `area:` | loop | `feat:` | loop-reconvergence, conditional-branch, control-flow | `ext:` | RV64G | `type:` | example | `pat:` | reconverge |

#### loop_unconditional_branches_force.py
| `area:` | loop | `feat:` | loop-control, unconditional-branch, JAL | `ext:` | RV64G | `type:` | example | `pat:` | edge-case |

---

### 3.8 masterRun/ (1 `*_force.py` file)

#### optionsTest_force.py
| `area:` | framework | `feat:` | master-run, command-line-options, getOption | `ext:` | - | `type:` | example | `pat:` | harness |

---

### 3.9 multiprocessing/ (6 `*_force.py` files)

#### multiprocessing_basic_force.py
| `area:` | multiprocessing | `feat:` | multi-thread, random-instruction, thread-parallel | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### multiprocessing_broad_random_instructions_force.py
| `area:` | multiprocessing | `feat:` | multi-thread, broad-random, instruction-variety | `ext:` | RV64G | `type:` | example | `pat:` | random |

#### multiprocessing_fence_options_force.py
| `area:` | multiprocessing | `feat:` | FENCE, memory-ordering, synchronization | `ext:` | RV64G | `type:` | example | `pat:` | fence |

#### multiprocessing_semaphore_basic_force.py
| `area:` | multiprocessing | `feat:` | semaphore, thread-synchronization, lock, atomic | `ext:` | Zaamo, Zalrsc | `type:` | example | `pat:` | synchronization |

#### multiprocessing_thread_context_no_advance_force.py
| `area:` | multiprocessing | `feat:` | thread-context, no-advance, context-switch | `ext:` | RV64G | `type:` | example | `pat:` | edge-case |

#### multiprocessing_thread_locking_force.py
| `area:` | multiprocessing | `feat:` | thread-locking, synchronization, lock-acquire | `ext:` | Zaamo, Zalrsc | `type:` | example | `pat:` | synchronization |

---

### 3.10 paging/ (9 `*_force.py` files)

#### paging_force.py
| `area:` | paging | `feat:` | basic-paging, MMU, random-instruction | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### paging_loadstore_force.py
| `area:` | paging | `feat:` | page-walk, load-store, virtual-memory | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### paging_branch_force.py
| `area:` | paging | `feat:` | branch-paging, instruction-fetch, page-walk-on-branch | `ext:` | RV64G | `type:` | example | `pat:` | edge-case |

#### page_fault_on_load_store_force.py
| `area:` | paging | `feat:` | page-fault, load-store, trap-handler | `ext:` | RV64G | `type:` | example | `pat:` | exception |

#### page_fault_on_load_store_03_force.py
| `area:` | paging | `feat:` | page-fault, load-store, extended-scenario | `ext:` | RV64G | `type:` | example | `pat:` | exception |

#### page_fault_on_branch_force.py
| `area:` | paging | `feat:` | page-fault-on-branch, instruction-fetch-fault | `ext:` | RV64G | `type:` | example | `pat:` | exception |

#### paging_no_access_fault_on_branch_force.py
| `area:` | paging | `feat:` | no-access-fault, branch-execution, permission | `ext:` | RV64G | `type:` | example | `pat:` | edge-case |

#### paging_memory_attributes_basic_force.py
| `area:` | paging | `feat:` | memory-attributes, PMA, MemAttr | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### paging_va_for_pa_memory_attributes_force.py
| `area:` | paging | `feat:` | genVAforPA, memory-attributes, VA-PA-mapping, PMA | `ext:` | RV64G | `type:` | example | `pat:` | advanced |

---

### 3.11 privilege_switch/ (5 `*_force.py` files)

#### privilege_switch_force.py
| `area:` | privilege | `feat:` | privilege-switch, MRET, supervisor, machine-mode | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### privilege_switch_ret_force.py
| `area:` | privilege | `feat:` | xRET, MRET, SRET, privilege-return | `ext:` | RV64G | `type:` | example | `pat:` | basic |

#### privilege_switch_end_of_test_force.py
| `area:` | privilege | `feat:` | end-of-test, privilege-switch, branch-to-self | `ext:` | RV64G | `type:` | example | `pat:` | shutdown |

#### system_call_gen_va_force.py
| `area:` | privilege | `feat:` | system-call, ECALL, genVA, privilege-switch | `ext:` | RV64G | `type:` | example | `pat:` | combined |

#### system_call_sequence_force.py
| `area:` | privilege | `feat:` | system-call, ECALL, sequence, privilege-change | `ext:` | RV64G | `type:` | example | `pat:` | sequence |

---

### 3.12 register/ (1 `*_force.py` file)

#### register_read_only_force.py
| `area:` | register | `feat:` | read-only-register, CSR, AssemblyHelperRISCV, mvendorid, marchid, mimpid, mhartid, vl, vlenb, vtype | `ext:` | RV64G | `type:` | example | `pat:` | basic |

---

### 3.13 rv32/ (1 `*_force.py` file)

#### rv32i_force.py
| `area:` | instruction | `feat:` | RV32I-base, ADD, SRLI, ADDI, SLLI, LUI, register-width | `ext:` | RV32I | `type:` | example | `pat:` | coverage |

---

### 3.14 rv64/ (1 `*_force.py` file)

#### rv64_invalid_address_force.py
| `area:` | memory | `feat:` | invalid-address, RV64-address-space, exception-count | `ext:` | RV64I | `type:` | example | `pat:` | edge-case |

---

### 3.15 state_transition/ (18 `*_force.py` files)

#### state_transition_basic_force.py
| `area:` | state | `feat:` | StateTransition, State, EStateElementType, transitionToState, Explicit | `ext:` | - | `type:` | example | `pat:` | basic |

#### state_transition_boot_force.py
| `area:` | state | `feat:` | StateTransition, Boot, EStateTransitionType, boot-state | `ext:` | - | `type:` | example | `pat:` | boot |

#### state_transition_boot_all_gprs_force.py
| `area:` | state | `feat:` | StateTransition, Boot, GPR, all-registers | `ext:` | - | `type:` | example | `pat:` | boot |

#### state_transition_arbitrary_gprs_force.py
| `area:` | state | `feat:` | StateTransition, GPR, arbitrary-registers, Explicit | `ext:` | - | `type:` | example | `pat:` | arbitrary |

#### state_transition_by_state_elem_type_force.py
| `area:` | state | `feat:` | StateTransition, EStateElementType, ByStateElementType, order-mode | `ext:` | - | `type:` | example | `pat:` | advanced |

#### state_transition_by_all_state_elem_types_force.py
| `area:` | state | `feat:` | StateTransition, all-state-element-types, comprehensive | `ext:` | - | `type:` | example | `pat:` | comprehensive |

#### state_transition_by_priority_force.py
| `area:` | state | `feat:` | StateTransition, priority-order, ByPriority | `ext:` | - | `type:` | example | `pat:` | advanced |

#### state_transition_multi_state_force.py
| `area:` | state | `feat:` | StateTransition, multi-state, merge, multiple-states | `ext:` | - | `type:` | example | `pat:` | advanced |

#### state_transition_merge_state_elements_force.py
| `area:` | state | `feat:` | StateTransition, merge, state-elements, combine | `ext:` | - | `type:` | example | `pat:` | merge |

#### state_transition_partial_force.py
| `area:` | state | `feat:` | StateTransition, partial-state, selective-elements | `ext:` | - | `type:` | example | `pat:` | partial |

#### state_transition_broad_random_instructions_force.py
| `area:` | state | `feat:` | StateTransition, broad-random, instruction-variety | `ext:` | RV64G | `type:` | example | `pat:` | random |

#### state_transition_branch_instructions_force.py
| `area:` | state | `feat:` | StateTransition, branch, conditional-branch, control-flow | `ext:` | RV64G | `type:` | example | `pat:` | branch |

#### state_transition_memory_default_force.py
| `area:` | state | `feat:` | StateTransition, Memory, default-state, EStateElementType.Memory | `ext:` | - | `type:` | example | `pat:` | basic |

#### state_transition_fp_registers_default_force.py
| `area:` | state | `feat:` | StateTransition, FloatingPointRegister, default-FPR | `ext:` | F | `type:` | example | `pat:` | basic |

#### state_transition_system_registers_default_force.py
| `area:` | state | `feat:` | StateTransition, SystemRegister, CSR, default-state | `ext:` | - | `type:` | example | `pat:` | basic |

#### state_transition_vector_registers_default_force.py
| `area:` | state | `feat:` | StateTransition, VectorRegister, default-VECREG | `ext:` | V | `type:` | example | `pat:` | basic |

#### state_transition_vm_context_default_force.py
| `area:` | state | `feat:` | StateTransition, VmContext, virtual-memory-context | `ext:` | - | `type:` | example | `pat:` | basic |

#### state_transition_privilege_level_default_force.py
| `area:` | state | `feat:` | StateTransition, PrivilegeLevel, execution-mode | `ext:` | - | `type:` | example | `pat:` | basic |

---

### 3.16 thread_group/ (4 `*_force.py` files)

#### thread_group_basic_force.py
| `area:` | thread-group | `feat:` | queryThreadGroup, getThreadGroupId, getFreeThreads, thread-partition | `ext:` | - | `type:` | example | `pat:` | basic |

#### thread_group_partition_diff_core_force.py
| `area:` | thread-group | `feat:` | thread-partition, different-core, thread-spread | `ext:` | - | `type:` | example | `pat:` | partition |

#### thread_group_partition_random_force.py
| `area:` | thread-group | `feat:` | thread-partition, random-assignment, partition-strategy | `ext:` | - | `type:` | example | `pat:` | random |

#### thread_group_partition_same_chip_force.py
| `area:` | thread-group | `feat:` | thread-partition, same-chip, thread-grouping | `ext:` | - | `type:` | example | `pat:` | partition |

---

### 3.17 vector/ (23 `*_force.py` files)

#### vector_simple_add_force.py
| `area:` | vector | `feat:` | VADD.VV, VectorTestSequence, VSEW, VLMUL, initializeVectorRegister, readRegister | `ext:` | V | `type:` | example | `pat:` | basic |

#### vector_extension_instructions_force.py
| `area:` | vector | `feat:` | vector-extensions, broad-coverage, instruction-variety | `ext:` | V | `type:` | example | `pat:` | coverage |

#### vector_integer_scalar_move_force.py
| `area:` | vector | `feat:` | VMV, integer-scalar-move, VECREG-to-GPR | `ext:` | V | `type:` | example | `pat:` | basic |

#### vector_whole_register_move_force.py
| `area:` | vector | `feat:` | VMV, whole-register-move, VECREG | `ext:` | V | `type:` | example | `pat:` | basic |

#### vector_vsetvl_force.py
| `area:` | vector | `feat:` | VSETVL, VL, vector-length-config | `ext:` | V | `type:` | example | `pat:` | configuration |

#### vector_vsetvli_force.py
| `area:` | vector | `feat:` | VSETVLI, VL, vector-length-immediate | `ext:` | V | `type:` | example | `pat:` | configuration |

#### vector_vsetivli_force.py
| `area:` | vector | `feat:` | VSETIVLI, VL, vector-length-immediate | `ext:` | V | `type:` | example | `pat:` | configuration |

#### vector_unit_stride_load_store_force.py
| `area:` | vector | `feat:` | unit-stride, VLE, VSE, load-store | `ext:` | V | `type:` | example | `pat:` | load-store |

#### vector_unit_stride_segment_load_store_force.py
| `area:` | vector | `feat:` | unit-stride, segment, VLSEG, VSSEG, load-store | `ext:` | V | `type:` | example | `pat:` | load-store |

#### vector_strided_load_store_force.py
| `area:` | vector | `feat:` | strided, VLSE, VSSE, load-store | `ext:` | V | `type:` | example | `pat:` | load-store |

#### vector_strided_segment_load_store_force.py
| `area:` | vector | `feat:` | strided, segment, VLSSEG, VSSSEG, load-store | `ext:` | V | `type:` | example | `pat:` | load-store |

#### vector_indexed_load_store_force.py
| `area:` | vector | `feat:` | indexed, VLXEI, VSXEI, load-store | `ext:` | V | `type:` | example | `pat:` | load-store |

#### vector_indexed_segment_load_store_force.py
| `area:` | vector | `feat:` | indexed, segment, VLXSEG, VSXSEG, load-store | `ext:` | V | `type:` | example | `pat:` | load-store |

#### vector_whole_register_load_store_force.py
| `area:` | vector | `feat:` | whole-register, VLR, VSR, load-store | `ext:` | V | `type:` | example | `pat:` | load-store |

#### vector_mask_load_store_force.py
| `area:` | vector | `feat:` | mask, VLEM, VSEM, mask-load-store | `ext:` | V | `type:` | example | `pat:` | mask |

#### vector_mask_operand_init_force.py
| `area:` | vector | `feat:` | mask-operand, v0, mask-initialization | `ext:` | V | `type:` | example | `pat:` | mask |

#### vector_mask_operand_conflict_force.py
| `area:` | vector | `feat:` | mask-operand, conflict, operand-constraint | `ext:` | V | `type:` | example | `pat:` | conflict |

#### vector_always_masked_operand_conflict_force.py
| `area:` | vector | `feat:` | always-masked, operand-conflict, constraint | `ext:` | V | `type:` | example | `pat:` | conflict |

#### vector_wide_operand_conflict_force.py
| `area:` | vector | `feat:` | wide-operand, EW, conflict, VLMUL | `ext:` | V | `type:` | example | `pat:` | conflict |

#### vector_instruction_specific_operand_conflict_force.py
| `area:` | vector | `feat:` | instruction-specific, operand-conflict, constraint | `ext:` | V | `type:` | example | `pat:` | conflict |

#### vector_floating_point_wide_operand_force.py
| `area:` | vector | `feat:` | floating-point, wide-operand, VFW, VF | `ext:` | V, F | `type:` | example | `pat:` | floating-point |

#### vector_add_carry_sub_borrow_force.py
| `area:` | vector | `feat:` | VADC, VSBC, carry, borrow | `ext:` | V | `type:` | example | `pat:` | arithmetic |

#### vector_amo_force.py
| `area:` | vector | `feat:` | atomic-memory-operation, VAMO, atomics | `ext:` | V, A | `type:` | example | `pat:` | atomic |

---

## 4. 标签统计摘要

| 标签类别 | 数量 |
|----------|------|
| `area:memory` | 19 |
| `area:paging` | 12 |
| `area:register` | 9 |
| `area:state` | 18 |
| `area:vector` | 23 |
| `area:exception` | 6 |
| `area:branch` | 5 |
| `area:loop` | 5 |
| `area:multiprocessing` | 6 |
| `area:privilege` | 5 |
| `area:floating-point` | 4 |
| `area:thread-group` | 4 |
| `area:instruction` | 3 |
| `area:data` | 1 |
| `area:dependency` | 1 |
| `area:choices` | 1 |
| `area:utility` | 4 |
| `area:misc` | 3 |
| `area:api-reference` | 1 (doc) |
| `area:isa-spec` | 1 (doc) |
| `area:architecture` | 1 (doc) |
| `area:quickstart` | 1 (doc) |
| `area:navigation` | 4 (docs) |
| `type:doc` | 7 |
| `type:guide` | 1 |
| `type:example` | 125 |

### ISA 扩展覆盖

| 扩展 | 标签文件数 |
|------|-----------|
| RV64G | ~90 (默认架构) |
| RVC | 5 |
| V | 23 |
| F | 3 |
| D | 3 |
| M | 4 |
| A / Zaamo / Zalrsc | 3 |
| RV32I | 2 |
| RV64I | 2 |

### 测试模式覆盖

| 模式 | 文件数 |
|------|--------|
| basic | 48 |
| advanced | 8 |
| edge-case | 9 |
| exception | 7 |
| conflict | 4 |
| random | 5 |
| load-store | 8 |
| boot | 4 |
| configuration | 4 |
| synchronization | 2 |
| partition | 2 |
| mask | 2 |
| other | ~22 |
