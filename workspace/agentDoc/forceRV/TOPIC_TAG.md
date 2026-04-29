# FORCE-RISCV Topic Tag List

## Overview

本文档按 **Topic + Hint + Source Documents** 三层结构重新组织所有标签索引，
用于提高 Agentic Search 的召回精度。

- **Topic**: 可检索的关键词/API 名称
- **Hint**: 一句话描述该主题的用途与适用场景（帮助模型判断何时检索此条目）
- **Source Docs**: 指向原始文档/示例文件

> 与 [TAG_INDEX.md](TAG_INDEX.md) 互为补充：TAG_INDEX 以文件为纲，TOPIC_TAG 以主题为纲。

---

## 1. Memory Operations（内存操作）

### genVA — 生成虚拟地址
- **Hint**: 生成符合对齐/大小要求的有效虚拟地址，支持地址范围、FlatMap、别名控制。所有 load/store 指令生成前必须调用。
- **Source Docs**:
  - [memory_operations_guide.md](memory_operations_guide.md) §1
  - [example/APIs/api_genVA_01_force.py](example/APIs/api_genVA_01_force.py) — 参数扫描（Size, Align, FlatMap）
  - [example/APIs/api_genVA_02_force.py](example/APIs/api_genVA_02_force.py) — 地址范围 + FlatMap 高级用法
  - [example/APIs/api_genVA_reuse_force.py](example/APIs/api_genVA_reuse_force.py) — 地址复用 + ConstraintSet
  - [example/address_solving/address_solving_address_reuse_force.py](example/address_solving/address_solving_address_reuse_force.py) — 地址复用模式
  - [example/privilege_switch/system_call_gen_va_force.py](example/privilege_switch/system_call_gen_va_force.py) — ECALL 场景下 genVA

### genPA — 生成物理地址
- **Hint**: 生成物理地址，支持 MemAttrArch（如 AMOSwap,CoherentL1）和 MemAttrImpl（如 Debug,CLINT,PLIC,GPIO）属性。
- **Source Docs**:
  - [memory_operations_guide.md](memory_operations_guide.md) §2
  - [example/APIs/api_genPA_01_force.py](example/APIs/api_genPA_01_force.py) — 基本物理地址生成 + MemAttr

### genVAforPA — 虚拟地址到物理地址映射
- **Hint**: 为指定物理地址创建虚拟映射，支持 ForceNewAddr 强制创建新映射。用于别名场景（多个 VA 指向同一 PA）。
- **Source Docs**:
  - [memory_operations_guide.md](memory_operations_guide.md) §2
  - [example/APIs/api_genVAforPA_01_force.py](example/APIs/api_genVAforPA_01_force.py) — 基本 PA→VA 映射
  - [example/APIs/api_genVAforPA_alias_force.py](example/APIs/api_genVAforPA_alias_force.py) — 别名映射 + ForceNewAddr
  - [example/paging/paging_va_for_pa_memory_attributes_force.py](example/paging/paging_va_for_pa_memory_attributes_force.py) — PA 映射 + 内存属性

### initializeMemory — 初始化内存内容
- **Hint**: 在生成 load 指令前预填充指定地址的内存数据，确保读取到预期值。支持按字节、半字、字、双字初始化。
- **Source Docs**:
  - [memory_operations_guide.md](memory_operations_guide.md) §3
  - [example/exception_handlers/stack_force.py](example/exception_handlers/stack_force.py) — 栈空间批量初始化
  - [apiDoc/FORCE-RISCV_User_Manual-v0.8.md](apiDoc/FORCE-RISCV_User_Manual-v0.8.md) — 完整参数说明

### LSTarget — Load/Store 目标地址
- **Hint**: 通过 genInstruction 的 LSTarget 参数指定 load/store 目标地址，支持 NoPreamble / UsePreamble / NoSkip 控制。
- **Source Docs**:
  - [memory_operations_guide.md](memory_operations_guide.md) §4
  - [example/APIs/api_genVA_01_force.py](example/APIs/api_genVA_01_force.py)
  - [example/address_solving/address_solving_basic_load_store_force.py](example/address_solving/address_solving_basic_load_store_force.py)
  - [example/address_solving/address_solving_address_reuse_force.py](example/address_solving/address_solving_address_reuse_force.py)

### Address Alias — 地址别名（多 VA 映射同一 PA）
- **Hint**: 用于 Cache Coherence 测试，创建多个虚拟地址指向同一物理地址，通过不同 VA 读写验证一致性。
- **Source Docs**:
  - [memory_operations_guide.md](memory_operations_guide.md) §2 (别名模式)
  - [example/APIs/api_genVAforPA_alias_force.py](example/APIs/api_genVAforPA_alias_force.py) — 基本别名 + ForceNewAddr

### verifyVirtualAddress — 虚拟地址验证
- **Hint**: 验证虚拟地址的有效性（是否在已分配页表范围内）。
- **Source Docs**:
  - [example/APIs/api_verifyVirtualAddress_01_force.py](example/APIs/api_verifyVirtualAddress_01_force.py)

### Misaligned Access — 非对齐访问
- **Hint**: 故意偏移地址产生非对齐访问，测试 RVC 压缩指令的非对齐异常处理。
- **Source Docs**:
  - [example/address_solving/RVC_misaligned_force.py](example/address_solving/RVC_misaligned_force.py)

### Stack Initialization — 栈空间初始化
- **Hint**: 批量初始化栈空间内存，为异常处理函数提供有效栈帧。
- **Source Docs**:
  - [example/exception_handlers/stack_force.py](example/exception_handlers/stack_force.py)

### RV64 Invalid Address — RV64 非法地址空间
- **Hint**: 测试 RV64 下访问非法地址范围的异常行为。
- **Source Docs**:
  - [example/rv64/rv64_invalid_address_force.py](example/rv64/rv64_invalid_address_force.py)

### Compressed Load/Store — 压缩指令访存
- **Hint**: 使用 RVC 压缩指令（C.LW/C.SW/C.LWSP/C.SWSP/C.LD/C.SD/C.LDSP/C.SDSP）进行内存访问。
- **Source Docs**:
  - [example/address_solving/address_solving_compressed_same_operands_force.py](example/address_solving/address_solving_compressed_same_operands_force.py) — 同操作数压缩访存
  - [example/address_solving/address_solving_implied_base_force.py](example/address_solving/address_solving_implied_base_force.py) — SP 相对寻址
  - [example/address_solving/RVC_misaligned_force.py](example/address_solving/RVC_misaligned_force.py) — 非对齐压缩访存

---

## 2. Paging & Virtual Memory（分页与虚拟内存）

### Paging Basics — 基本分页
- **Hint**: 启用 MMU / 分页后随机生成指令，验证虚拟内存基本功能。
- **Source Docs**:
  - [example/paging/paging_force.py](example/paging/paging_force.py) — 基本分页 + 随机指令
  - [example/paging/paging_loadstore_force.py](example/paging/paging_loadstore_force.py) — 分页下 load/store

### genFreePagesRange — 生成空闲页范围
- **Hint**: 查询可用的空闲页地址范围，用于分配页面。
- **Source Docs**:
  - [example/APIs/api_genFreePagesRange_01_force.py](example/APIs/api_genFreePagesRange_01_force.py)

### getPageInfo — 页表信息查询
- **Hint**: 查询指定页面的页表信息（PTE 内容、权限等）。
- **Source Docs**:
  - [example/APIs/api_getPageInfo_01_force.py](example/APIs/api_getPageInfo_01_force.py)

### Page Fault — 缺页异常
- **Hint**: 测试 load/store/instruction-fetch 缺页异常的产生与 trap handler 处理流程。
- **Source Docs**:
  - [example/paging/page_fault_on_load_store_force.py](example/paging/page_fault_on_load_store_force.py)
  - [example/paging/page_fault_on_load_store_03_force.py](example/paging/page_fault_on_load_store_03_force.py)
  - [example/paging/page_fault_on_branch_force.py](example/paging/page_fault_on_branch_force.py)
  - [example/paging/paging_no_access_fault_on_branch_force.py](example/paging/paging_no_access_fault_on_branch_force.py)
  - [example/exception_handlers/trap_vm_force.py](example/exception_handlers/trap_vm_force.py) — VM trap 处理

### Page Table Walk — 页表遍历
- **Hint**: 触发 TLB miss 后的页表遍历流程，验证多级页表访问。
- **Source Docs**:
  - [example/paging/paging_branch_force.py](example/paging/paging_branch_force.py)
  - [example/paging/paging_loadstore_force.py](example/paging/paging_loadstore_force.py)

### PMA / Memory Attributes — 物理内存属性
- **Hint**: 设置和验证物理内存属性（PMA），测试 MemAttr 对访问行为的影响。
- **Source Docs**:
  - [example/paging/paging_memory_attributes_basic_force.py](example/paging/paging_memory_attributes_basic_force.py)
  - [example/paging/paging_va_for_pa_memory_attributes_force.py](example/paging/paging_va_for_pa_memory_attributes_force.py)

---

## 3. Register Management（寄存器管理）

### getRandomGPR / getRandomRegisters — 随机寄存器分配
- **Hint**: 获取随机通用/浮点/向量寄存器索引，支持排除指定寄存器。是生成指令操作数的基础。
- **Source Docs**:
  - [example/APIs/GetRandomRegisterTest_force.py](example/APIs/GetRandomRegisterTest_force.py) — GPR, FPR, VECREG 分配
  - [apiDoc/FORCE-RISCV_User_Manual-v0.8.md](apiDoc/FORCE-RISCV_User_Manual-v0.8.md)

### reserveRegister / unreserveRegister — 寄存器预留
- **Hint**: 预留/释放寄存器以防止其他指令使用，用于异常 handler、特权切换等需要保护特定寄存器的场景。
- **Source Docs**:
  - [example/APIs/ReserveRegisterTest_force.py](example/APIs/ReserveRegisterTest_force.py)
  - [example/APIs/AccessReservedRegisterTest_force.py](example/APIs/AccessReservedRegisterTest_force.py)

### initializeRegister / initializeRegisterFields — 寄存器初始化
- **Hint**: 设置寄存器的初始值，支持整体初始化和按字段初始化。用于向量寄存器、浮点寄存器等的初始值设定。
- **Source Docs**:
  - [example/APIs/InitializeRegisterTest_force.py](example/APIs/InitializeRegisterTest_force.py)
  - [example/APIs/InitializeRandomRandomlyTest_force.py](example/APIs/InitializeRandomRandomlyTest_force.py)
  - [example/vector/vector_simple_add_force.py](example/vector/vector_simple_add_force.py) — initializeVectorRegister

### writeRegister / readRegister — 寄存器读写
- **Hint**: 直接写入/读取寄存器值（含字段级操作），支持 GPR/FPR/VECREG/CSR。
- **Source Docs**:
  - [example/APIs/WriteRegisterTest_force.py](example/APIs/WriteRegisterTest_force.py)
  - [example/APIs/State_force.py](example/APIs/State_force.py) — getPEstate / setPEstate

### Read-Only CSR — 只读系统寄存器
- **Hint**: 使用 AssemblyHelperRISCV 读取 mvendorid/marchid/mimpid/mhartid/vl/vlenb/vtype 等只读 CSR。
- **Source Docs**:
  - [example/register/register_read_only_force.py](example/register/register_read_only_force.py)
  - [example/exception_handlers/assembly_helper_force.py](example/exception_handlers/assembly_helper_force.py)

### misa — ISA 配置寄存器
- **Hint**: 设置 misa CSR 初始值以控制 ISA 扩展使能状态。
- **Source Docs**:
  - [example/APIs/SetMisaInitialValue_force.py](example/APIs/SetMisaInitialValue_force.py)

### Register Dependency — 寄存器依赖
- **Hint**: 通过 modifyDependenceChoices 控制指令间寄存器依赖关系，生成 RAW/WAW/WAR 数据冒险。
- **Source Docs**:
  - [example/APIs/reg_dependence_force.py](example/APIs/reg_dependence_force.py)

---

## 4. State Transition（状态转换）

### StateTransition Basics — 状态转换基础
- **Hint**: 使用 transitionToState() 执行显式状态转换，State 对象包含 Memory/GPR/FPR/VECREG/CSR/PC/PrivilegeLevel 等元素。
- **Source Docs**:
  - [example/state_transition/state_transition_basic_force.py](example/state_transition/state_transition_basic_force.py)
  - [apiDoc/FORCE-RISCV_User_Manual-v0.8.md](apiDoc/FORCE-RISCV_User_Manual-v0.8.md)

### StateTransition Boot — 启动状态转换
- **Hint**: 使用 EStateTransitionType.Boot 执行启动时状态转换，按 EStateElementType 顺序初始化所有架构状态。
- **Source Docs**:
  - [example/state_transition/state_transition_boot_force.py](example/state_transition/state_transition_boot_force.py)
  - [example/state_transition/state_transition_boot_all_gprs_force.py](example/state_transition/state_transition_boot_all_gprs_force.py)

### EStateElementType — 状态元素类型
- **Hint**: 定义状态元素类型枚举：GPR, FloatingPointRegister, VectorRegister, PredicateRegister, Memory, SystemRegister, VmContext, PrivilegeLevel, PC。控制 StateTransition 的作用范围。
- **Source Docs**:
  - [example/state_transition/state_transition_by_state_elem_type_force.py](example/state_transition/state_transition_by_state_elem_type_force.py)
  - [example/state_transition/state_transition_by_all_state_elem_types_force.py](example/state_transition/state_transition_by_all_state_elem_types_force.py)
  - [example/state_transition/state_transition_arbitrary_gprs_force.py](example/state_transition/state_transition_arbitrary_gprs_force.py)

### State Transition Order Mode — 状态转换顺序模式
- **Hint**: AsSpecified / ByStateElementType / ByPriority 三种 order mode 控制状态元素的转换顺序。
- **Source Docs**:
  - [example/state_transition/state_transition_by_priority_force.py](example/state_transition/state_transition_by_priority_force.py)

### State Merge — 状态合并
- **Hint**: 多个 State 对象合并为一个，控制 state elements 的组合策略。
- **Source Docs**:
  - [example/state_transition/state_transition_multi_state_force.py](example/state_transition/state_transition_multi_state_force.py)
  - [example/state_transition/state_transition_merge_state_elements_force.py](example/state_transition/state_transition_merge_state_elements_force.py)

### Partial State — 部分状态转换
- **Hint**: 只转换部分状态元素，不覆盖全部架构状态。用于增量状态修改。
- **Source Docs**:
  - [example/state_transition/state_transition_partial_force.py](example/state_transition/state_transition_partial_force.py)

### Default State by Element — 各类默认状态
- **Hint**: 为 Memory / FPR / CSR / VECREG / VmContext / PrivilegeLevel 设置默认初始状态。
- **Source Docs**:
  - [example/state_transition/state_transition_memory_default_force.py](example/state_transition/state_transition_memory_default_force.py)
  - [example/state_transition/state_transition_fp_registers_default_force.py](example/state_transition/state_transition_fp_registers_default_force.py)
  - [example/state_transition/state_transition_system_registers_default_force.py](example/state_transition/state_transition_system_registers_default_force.py)
  - [example/state_transition/state_transition_vector_registers_default_force.py](example/state_transition/state_transition_vector_registers_default_force.py)
  - [example/state_transition/state_transition_vm_context_default_force.py](example/state_transition/state_transition_vm_context_default_force.py)
  - [example/state_transition/state_transition_privilege_level_default_force.py](example/state_transition/state_transition_privilege_level_default_force.py)

### StateTransition + Random Instructions — 状态转换配合随机指令
- **Hint**: 状态转换前后生成随机指令序列，验证状态一致性。
- **Source Docs**:
  - [example/state_transition/state_transition_broad_random_instructions_force.py](example/state_transition/state_transition_broad_random_instructions_force.py)
  - [example/state_transition/state_transition_branch_instructions_force.py](example/state_transition/state_transition_branch_instructions_force.py)

---

## 5. Branch & Control Flow（分支与控制流）

### Conditional Branch — 条件分支（BEQ/BNE/BLT/BGE/BLTU/BGEU）
- **Hint**: 生成 PC 相对条件分支指令，使用 BRarget 指定目标地址，通过 queryInstructionRecord 获取指令记录验证分支行为。
- **Source Docs**:
  - [example/branch/branch_pc_relative_conditional_force.py](example/branch/branch_pc_relative_conditional_force.py)

### Unconditional Branch — 无条件分支（JAL）
- **Hint**: 生成 PC 相对无条件跳转（JAL），使用 BRarget 指定目标。
- **Source Docs**:
  - [example/branch/branch_pc_relative_unconditional_force.py](example/branch/branch_pc_relative_unconditional_force.py)

### Register-Indirect Branch — 寄存器间接分支（JALR）
- **Hint**: 通过 rs1 寄存器指定跳转目标，用于实现函数返回、虚函数调用等间接跳转。
- **Source Docs**:
  - [example/branch/branch_register_force.py](example/branch/branch_register_force.py)

### BntSequence — 分支未遂序列
- **Hint**: setBntHook + revertBntHook 控制分支预测未遂（Branch-Not-Taken）场景，用于验证 SpeculativeBnt 执行路径。
- **Source Docs**:
  - [example/bnt/speculative_bnt_force.py](example/bnt/speculative_bnt_force.py)

### LoopControl — 循环控制
- **Hint**: 使用 LoopControl(LoopCount=N) 生成 N 次迭代的循环体，支持 register-increment / broad-random / reconverge / unconditional 等模式。
- **Source Docs**:
  - [example/loop/loop_basic_force.py](example/loop/loop_basic_force.py) — 基本循环 + ADDI 递增
  - [example/loop/loop_broad_random_instructions_force.py](example/loop/loop_broad_random_instructions_force.py) — 大范围随机指令循环
  - [example/loop/loop_reconverge_force.py](example/loop/loop_reconverge_force.py) — 条件分支收敛循环
  - [example/loop/loop_unconditional_branches_force.py](example/loop/loop_unconditional_branches_force.py) — 无条件跳转循环
  - [example/APIs/LoopControlTest_force.py](example/APIs/LoopControlTest_force.py) — LoopControl API 基本测试

---

## 6. Exception & Privilege（异常与特权）

### ECALL / EBREAK — 系统调用与断点
- **Hint**: 生成 ECALL（系统调用）和 EBREAK（调试断点）指令，配合 TrapsRedirectModifier 控制 trap 重定向。
- **Source Docs**:
  - [example/exception_handlers/ecall_ebreak_force.py](example/exception_handlers/ecall_ebreak_force.py)

### CSR Access Exception — CSR 访问异常
- **Hint**: 测试非法 CSR 访问引发的异常，验证异常委托机制。
- **Source Docs**:
  - [example/exception_handlers/access_csrs_force.py](example/exception_handlers/access_csrs_force.py)

### Exception Counting — 异常计数
- **Hint**: 使用 queryExceptionRecordsCount 查询异常记录数量，验证异常触发次数。
- **Source Docs**:
  - [example/exception_handlers/exception_counts_force.py](example/exception_handlers/exception_counts_force.py)

### Instruction Misaligned Exception — 指令非对齐异常
- **Hint**: 触发指令地址非对齐异常，验证异常向量与 trap handler。
- **Source Docs**:
  - [example/exception_handlers/instruction_misaligned_exception_force.py](example/exception_handlers/instruction_misaligned_exception_force.py)

### Exception Vector Base Address — 异常向量基地址
- **Hint**: 查询异常向量表基地址。
- **Source Docs**:
  - [example/APIs/api_queryExceptionVectorBaseAddress_force.py](example/APIs/api_queryExceptionVectorBaseAddress_force.py)

### Privilege Switch — 特权级切换
- **Hint**: 使用 MRET/SRET 指令在不同特权级间切换（Machine/Supervisor/User），验证切换流程。
- **Source Docs**:
  - [example/privilege_switch/privilege_switch_force.py](example/privilege_switch/privilege_switch_force.py)
  - [example/privilege_switch/privilege_switch_ret_force.py](example/privilege_switch/privilege_switch_ret_force.py)
  - [example/privilege_switch/privilege_switch_end_of_test_force.py](example/privilege_switch/privilege_switch_end_of_test_force.py)

### System Call Sequence — 系统调用序列
- **Hint**: ECALL 组合特权切换的完整序列测试。
- **Source Docs**:
  - [example/privilege_switch/system_call_sequence_force.py](example/privilege_switch/system_call_sequence_force.py)
  - [example/privilege_switch/system_call_gen_va_force.py](example/privilege_switch/system_call_gen_va_force.py)

---

## 7. Multiprocessing & Threads（多线程与同步）

### Multi-Thread Basics — 多线程基础
- **Hint**: 使用 RV64I_map.pick() 在多线程环境下随机生成指令，验证线程并行执行。
- **Source Docs**:
  - [example/multiprocessing/multiprocessing_basic_force.py](example/multiprocessing/multiprocessing_basic_force.py)
  - [example/multiprocessing/multiprocessing_broad_random_instructions_force.py](example/multiprocessing/multiprocessing_broad_random_instructions_force.py)

### FENCE — 内存屏障
- **Hint**: 生成 FENCE 指令控制内存访问顺序，验证多核内存一致性。
- **Source Docs**:
  - [example/multiprocessing/multiprocessing_fence_options_force.py](example/multiprocessing/multiprocessing_fence_options_force.py)

### Semaphore & Lock — 信号量与锁同步
- **Hint**: 使用 AMO 原子指令实现信号量/锁，测试线程间同步（acquire/release）。
- **Source Docs**:
  - [example/multiprocessing/multiprocessing_semaphore_basic_force.py](example/multiprocessing/multiprocessing_semaphore_basic_force.py)
  - [example/multiprocessing/multiprocessing_thread_locking_force.py](example/multiprocessing/multiprocessing_thread_locking_force.py)

### Thread Context — 线程上下文
- **Hint**: 测试线程上下文切换（no_advance 模式），验证上下文保存/恢复。
- **Source Docs**:
  - [example/multiprocessing/multiprocessing_thread_context_no_advance_force.py](example/multiprocessing/multiprocessing_thread_context_no_advance_force.py)

### Thread Group — 线程组管理
- **Hint**: queryThreadGroup / getThreadGroupId / getFreeThreads 查询线程分区信息，控制线程组分配策略。
- **Source Docs**:
  - [example/thread_group/thread_group_basic_force.py](example/thread_group/thread_group_basic_force.py)
  - [example/thread_group/thread_group_partition_diff_core_force.py](example/thread_group/thread_group_partition_diff_core_force.py)
  - [example/thread_group/thread_group_partition_random_force.py](example/thread_group/thread_group_partition_random_force.py)
  - [example/thread_group/thread_group_partition_same_chip_force.py](example/thread_group/thread_group_partition_same_chip_force.py)

---

## 8. Vector Extension（向量扩展 V）

### Vector Add (VADD.VV) — 向量加法
- **Hint**: 基本向量整数加法，配合 VSEW=0x2(32-bit), VLMUL=0x0(1) 配置。VectorTestSequence 基类提供 setUp/verify 框架。
- **Source Docs**:
  - [example/vector/vector_simple_add_force.py](example/vector/vector_simple_add_force.py)

### VSETVL / VSETVLI / VSETIVLI — 向量长度配置
- **Hint**: 设置 VL（向量长度）的三种方式：寄存器动态、立即数、立即数+SEW 组合。
- **Source Docs**:
  - [example/vector/vector_vsetvl_force.py](example/vector/vector_vsetvl_force.py)
  - [example/vector/vector_vsetvli_force.py](example/vector/vector_vsetvli_force.py)
  - [example/vector/vector_vsetivli_force.py](example/vector/vector_vsetivli_force.py)

### Vector Load/Store — 向量访存
- **Hint**: 多种向量访存模式：unit-stride (VLE/VSE)、strided (VLSE/VSSE)、indexed (VLXEI/VSXEI)、whole-register (VLR/VSR)、segment (VLSEG/VSSEG)。
- **Source Docs**:
  - [example/vector/vector_unit_stride_load_store_force.py](example/vector/vector_unit_stride_load_store_force.py)
  - [example/vector/vector_unit_stride_segment_load_store_force.py](example/vector/vector_unit_stride_segment_load_store_force.py)
  - [example/vector/vector_strided_load_store_force.py](example/vector/vector_strided_load_store_force.py)
  - [example/vector/vector_strided_segment_load_store_force.py](example/vector/vector_strided_segment_load_store_force.py)
  - [example/vector/vector_indexed_load_store_force.py](example/vector/vector_indexed_load_store_force.py)
  - [example/vector/vector_indexed_segment_load_store_force.py](example/vector/vector_indexed_segment_load_store_force.py)
  - [example/vector/vector_whole_register_load_store_force.py](example/vector/vector_whole_register_load_store_force.py)

### Vector Mask — 向量掩码操作
- **Hint**: v0 掩码寄存器初始化、掩码访存（VLEM/VSEM）、掩码操作数冲突控制。
- **Source Docs**:
  - [example/vector/vector_mask_load_store_force.py](example/vector/vector_mask_load_store_force.py)
  - [example/vector/vector_mask_operand_init_force.py](example/vector/vector_mask_operand_init_force.py)
  - [example/vector/vector_mask_operand_conflict_force.py](example/vector/vector_mask_operand_conflict_force.py)

### Vector Operand Conflict — 向量操作数冲突
- **Hint**: always-masked / wide-operand (EW/VLMUL) / instruction-specific 操作数冲突约束测试。
- **Source Docs**:
  - [example/vector/vector_always_masked_operand_conflict_force.py](example/vector/vector_always_masked_operand_conflict_force.py)
  - [example/vector/vector_wide_operand_conflict_force.py](example/vector/vector_wide_operand_conflict_force.py)
  - [example/vector/vector_instruction_specific_operand_conflict_force.py](example/vector/vector_instruction_specific_operand_conflict_force.py)

### Vector Integer Scalar Move — 向量-标量数据移动
- **Hint**: VMV 指令在 VECREG 与 GPR 之间移动数据。
- **Source Docs**:
  - [example/vector/vector_integer_scalar_move_force.py](example/vector/vector_integer_scalar_move_force.py)
  - [example/vector/vector_whole_register_move_force.py](example/vector/vector_whole_register_move_force.py)

### Vector Wide / Floating-Point — 向量浮点与扩展运算
- **Hint**: VFW/VF 系列向量浮点运算、VADC/VSBC 进位/借位运算。
- **Source Docs**:
  - [example/vector/vector_floating_point_wide_operand_force.py](example/vector/vector_floating_point_wide_operand_force.py)
  - [example/vector/vector_add_carry_sub_borrow_force.py](example/vector/vector_add_carry_sub_borrow_force.py)

### Vector AMO — 向量原子操作
- **Hint**: VAMO 系列向量原子内存操作指令。
- **Source Docs**:
  - [example/vector/vector_amo_force.py](example/vector/vector_amo_force.py)

### Vector Extension Coverage — 向量扩展全覆盖
- **Hint**: 一次性覆盖尽可能多的 V 扩展指令，用于回归测试。
- **Source Docs**:
  - [example/vector/vector_extension_instructions_force.py](example/vector/vector_extension_instructions_force.py)

---

## 9. Floating-Point & Arithmetic（浮点与算术）

### FMUL / FDIV / FMADD / FADD — 浮点运算
- **Hint**: 使用 pickWeighted 生成加权浮点指令序列（FMUL.D/FMUL.S/FDIV.D/FDIV.S/FMADD.D/FMADD.S/FADD.D/FADD.S）。
- **Source Docs**:
  - [example/fsuExamples/fsu_basic_force.py](example/fsuExamples/fsu_basic_force.py)

### MUL / DIV / REM — 整数乘除
- **Hint**: M 扩展整数乘除法，含数据约束（genData + ConstraintSet）和 NaN-boxing 边界场景。
- **Source Docs**:
  - [example/fsuExamples/_test_muldiv_force.py](example/fsuExamples/_test_muldiv_force.py)
  - [example/fsuExamples/test_muldiv_data_constr_force.py](example/fsuExamples/test_muldiv_data_constr_force.py)
  - [example/fsuExamples/test_muldiv_nan_boxing_force.py](example/fsuExamples/test_muldiv_nan_boxing_force.py)

---

## 10. Choices & Constraint Control（选项与约束控制）

### ChoicesModifier — 选项修改器
- **Hint**: modifyOperandChoices / modifyRegisterFieldValueChoices / modifyPagingChoices / modifyGeneralChoices 控制指令生成时的随机选择权重。commitSet 提交修改，支持 revert 回滚。
- **Source Docs**:
  - [example/APIs/ChoicesModificationTest_force.py](example/APIs/ChoicesModificationTest_force.py)
  - [example/vector/vector_simple_add_force.py](example/vector/vector_simple_add_force.py) — VSEW/VLMUL 选项控制

### ConstraintSet — 约束集
- **Hint**: addRange / subRange / mergeConstraintSet / chooseValue / isEmpty / size 操作地址约束集，用于限定 LSTarget 地址范围。
- **Source Docs**:
  - [example/APIs/Constraint_force.py](example/APIs/Constraint_force.py)
  - [example/APIs/api_genVA_reuse_force.py](example/APIs/api_genVA_reuse_force.py)
  - [example/address_solving/address_solving_address_reuse_force.py](example/address_solving/address_solving_address_reuse_force.py)

---

## 11. Data Generation（数据生成）

### genData — 数据模式生成
- **Hint**: 生成带约束的数据值：INT32(val)/INT64(range)/FP64(sign/exp/frac)/vector-data 等模式化数据。
- **Source Docs**:
  - [example/APIs/GenData_test_force.py](example/APIs/GenData_test_force.py)

### RandomUtils (random32/random64/pickWeighted) — 随机工具
- **Hint**: random32(min,max) / random64() / pickWeighted(weights) 生成随机值和加权选择。
- **Source Docs**:
  - [example/APIs/PickWeightedValue_test_force.py](example/APIs/PickWeightedValue_test_force.py)
  - [example/APIs/RandomChoiceAPITest_force.py](example/APIs/RandomChoiceAPITest_force.py)
  - [example/APIs/BitstreamTest_force.py](example/APIs/BitstreamTest_force.py) — bitstream 随机数据

---

## 12. Boot & Framework（启动与框架）

### Boot Flow — 启动流程
- **Hint**: 控制 reset_pc → boot → template → end-of-test 流程，支持 skip_boot（无 ISS 模式）。
- **Source Docs**:
  - [apiDoc/FORCE-RISCV_brief_introduction.md](apiDoc/FORCE-RISCV_brief_introduction.md) — 执行流程总览
  - [example/APIs/skip_boot_force.py](example/APIs/skip_boot_force.py) — 跳过启动流程

### Master Run — 主运行框架
- **Hint**: 命令行选项、getOption、多测试序列调度。
- **Source Docs**:
  - [example/masterRun/optionsTest_force.py](example/masterRun/optionsTest_force.py)

### Inquiry APIs — 信息查询
- **Hint**: queryInstructionRecord / getVariable / getPEstate 等查询类 API。
- **Source Docs**:
  - [example/APIs/InquiryAPITest_force.py](example/APIs/InquiryAPITest_force.py)
  - [example/APIs/QueryResourceEntropyTest_force.py](example/APIs/QueryResourceEntropyTest_force.py)

### Custom Entry Point — 自定义入口
- **Hint**: 自定义测试入口点，改变默认执行流。
- **Source Docs**:
  - [example/APIs/CustomEntryPointTest_force.py](example/APIs/CustomEntryPointTest_force.py)

---

## 13. Instruction Generation（指令生成）

### genInstruction — 核心指令生成
- **Hint**: FORCE-RISCV 最核心 API，生成单条指令。支持 LSTarget / NoPreamble / UsePreamble / NoSkip / BRarget 等参数控制。
- **Source Docs**:
  - [apiDoc/FORCE-RISCV_User_Manual-v0.8.md](apiDoc/FORCE-RISCV_User_Manual-v0.8.md) — 完整参数文档
  - [example/APIs/LoadRegisterPreambleTest_force.py](example/APIs/LoadRegisterPreambleTest_force.py) — NoPreamble/UsePreamble 控制
  - [example/APIs/LoadImmediate_force.py](example/APIs/LoadImmediate_force.py) — LI/LUI 立即数

### RV32I Base — RV32I 基础指令
- **Hint**: RV32I 基础整数指令集（ADD/SRLI/ADDI/SLLI/LUI），32-bit 寄存器宽度。
- **Source Docs**:
  - [example/rv32/rv32i_force.py](example/rv32/rv32i_force.py)
  - [apiDoc/RISC-V_Unprivileged_ISA.md](apiDoc/RISC-V_Unprivileged_ISA.md) — RV32I ISA 规范

---

## 14. Full Documents（完整文档参考）

### FORCE-RISCV_brief_introduction.md
- **Hint**: 架构组件总览（Config/Arch/Memory/VirtualMemory/StateTransition/PrivilegeSwitch/Dependency/ReExe/Bnt）和程序执行流程。
- **Topics**: boot-flow, architecture-overview, execution-flow, template-execution
- **Path**: [apiDoc/FORCE-RISCV_brief_introduction.md](apiDoc/FORCE-RISCV_brief_introduction.md)

### FORCE-RISCV_User_Manual-v0.8.md
- **Hint**: 完整用户手册 v0.8，涵盖全部 Front-End API、Choices/Variables 控制、命令行参数、ISS 集成。
- **Topics**: genInstruction, queryInstructionRecord, genVA, genPA, genVAforPA, initializeMemory, getRandomRegisters, reserveRegister, initializeRegister, readRegister, writeRegister, ChoicesModifier, ConstraintSet, StateTransition, LoopControl, setBntHook, modifyVariable, command-line-args
- **Path**: [apiDoc/FORCE-RISCV_User_Manual-v0.8.md](apiDoc/FORCE-RISCV_User_Manual-v0.8.md)

### RISC-V_Unprivileged_ISA.md
- **Hint**: RISC-V 非特权 ISA 规范，涵盖 RV32I/RV64I 基础指令、M/A/F/D/Q/C/B/V 扩展、CSR、内存模型（RVWMO）。
- **Topics**: RV32I, RV64I, M-extension, A-extension, F-extension, D-extension, C-extension, V-extension, B-extension, CSR, instruction-encoding, memory-model, RVWMO
- **Path**: [apiDoc/RISC-V_Unprivileged_ISA.md](apiDoc/RISC-V_Unprivileged_ISA.md)

### README.md
- **Hint**: 快速入门指南，构建步骤、运行示例、master_run 工作流、riscvOVPsim 集成、coverage、handcar-cosim。
- **Topics**: build, setup, quickstart, master-run, ELF-generation, riscvOVPsim, coverage, handcar-cosim
- **Path**: [apiDoc/README.md](apiDoc/README.md)

### memory_operations_guide.md
- **Hint**: 内存操作完整指南，VA/PA 生成 API、内存初始化、LSTarget 用法、常见模式（简单访存/先写后读/预初始化/地址复用/别名）。
- **Topics**: genVA, genPA, genVAforPA, initializeMemory, LSTarget, address-alignment, alias, store-load-sequence, address-reuse, physical-alias
- **Path**: [memory_operations_guide.md](memory_operations_guide.md)

---

## Topic Quick-Search Index（按字母序）

| Topic | Area | Hint 摘要 |
|-------|------|-----------|
| Address Alias | memory | 多 VA→同 PA, Cache Coherence 测试 |
| BntSequence | branch | setBntHook 分支未遂序列 |
| Boot Flow | boot | reset_pc→boot→template→end-of-test |
| ChoicesModifier | choices | 随机选择权重控制 |
| Compressed Load/Store | memory | RVC 压缩指令访存(C.LW/C.SW 等) |
| Conditional Branch | branch | BEQ/BNE/BLT/BGE/BLTU/BGEU |
| ConstraintSet | utility | 地址约束集操作(addRange/subRange 等) |
| CSR Access | exception | CSR 访问与异常委托 |
| Default State | state | Memory/FPR/CSR/VECREG/VmContext/PrivLevel 默认状态 |
| EStateElementType | state | 状态元素类型枚举 |
| ECALL/EBREAK | exception | 系统调用与断点异常 |
| Exception Counting | exception | queryExceptionRecordsCount |
| FENCE | multiprocessing | 内存屏障/多核一致性 |
| FMUL/FDIV/FMADD/FADD | fp | 浮点运算指令序列 |
| genData | data | 数据模式生成(INT32/INT64/FP64) |
| genFreePagesRange | paging | 空闲页范围查询 |
| genInstruction | instruction | 核心指令生成 API |
| genPA | memory | 物理地址生成 + MemAttr |
| genVA | memory | 虚拟地址生成(Size/Align/Range/FlatMap) |
| genVAforPA | memory | PA→VA 映射(ForceNewAddr) |
| getPageInfo | paging | 页表信息查询 |
| getRandomGPR | register | 随机寄存器分配 |
| initializeMemory | memory | 内存内容预填充 |
| initializeRegister | register | 寄存器初始值设定 |
| LoopControl | loop | 循环控制(LoopCount) |
| LSTarget | memory | Load/Store 目标地址 |
| Master Run | framework | 主运行框架/命令行选项 |
| Misaligned Access | memory | 非对齐访存测试 |
| misa | register | ISA 配置寄存器 |
| MUL/DIV/REM | fp | M 扩展整数乘除 |
| Multi-Thread | multiprocessing | 多线程随机指令 |
| Page Fault | paging | 缺页异常(load/store/branch) |
| PMA / MemAttr | paging | 物理内存属性 |
| Privilege Switch | privilege | MRET/SRET 特权级切换 |
| Read-Only CSR | register | mvendorid/marchid/mimpid/mhartid 等 |
| Register Dependency | register | modifyDependenceChoices/RAW/WAW/WAR |
| reserveRegister | register | 寄存器预留/释放 |
| RV32I Base | instruction | RV32I 基础整数指令 |
| Semaphore & Lock | multiprocessing | AMO 原子锁/信号量 |
| Stack Init | memory | 栈空间批量初始化 |
| State Merge | state | 多 State 对象合并 |
| State Order Mode | state | AsSpecified/ByStateElementType/ByPriority |
| StateTransition | state | transitionToState/Explicit/Boot |
| System Call Sequence | privilege | ECALL + 特权切换完整序列 |
| Thread Context | multiprocessing | 线程上下文切换(no_advance) |
| Thread Group | thread-group | queryThreadGroup/线程分区 |
| Vector Add | vector | VADD.VV + VSEW/VLMUL 配置 |
| Vector AMO | vector | VAMO 向量原子操作 |
| Vector Load/Store | vector | unit-stride/strided/indexed/segment/whole-register |
| Vector Mask | vector | v0 掩码初始化/掩码访存/冲突 |
| Vector Op Conflict | vector | 操作数冲突约束(wide/masked/specific) |
| VSETVL/VSETVLI/VSETIVLI | vector | 向量长度配置 |
| writeRegister/readRegister | register | 寄存器读写(含字段级) |
