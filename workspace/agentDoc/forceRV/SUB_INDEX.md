# FORCE-RISCV SUB_INDEX — 低频/专用 Topic

> 二级索引：低频 + 深度专题。一级入口见 [INDEX.md](INDEX.md)，完整内容见 [TOPIC_TAG.md](TOPIC_TAG.md)。

---

## Memory（内存操作 — 进阶）

### Address Alias — 地址别名
- **ref**: [TOPIC_TAG.md:57](TOPIC_TAG.md#address-alias--地址别名多-va-映射同一-pa)
- **hint**: 多 VA→同 PA，Cache Coherence 测试。ForceNewAddr=1 + CanAlias=1。
- **docs**: [memory_operations_guide.md](memory_operations_guide.md) §2; [api_genVAforPA_alias_force.py](example/APIs/api_genVAforPA_alias_force.py)

### verifyVirtualAddress — VA 验证
- **ref**: [TOPIC_TAG.md:63](TOPIC_TAG.md#verifyvirtualaddress--虚拟地址验证)
- **hint**: 验证虚拟地址是否在已分配页表范围内。
- **docs**: [api_verifyVirtualAddress_01_force.py](example/APIs/api_verifyVirtualAddress_01_force.py)

### Misaligned Access — 非对齐访问
- **ref**: [TOPIC_TAG.md:68](TOPIC_TAG.md#misaligned-access--非对齐访问)
- **hint**: 故意偏移地址产生非对齐访问，测试 RVC 压缩指令的非对齐异常。
- **docs**: [RVC_misaligned_force.py](example/address_solving/RVC_misaligned_force.py)

### Stack Initialization — 栈初始化
- **ref**: [TOPIC_TAG.md:73](TOPIC_TAG.md#stack-initialization--栈空间初始化)
- **hint**: 批量初始化栈空间（initializeMemory + RandomUtils.random64），为异常 handler 提供栈帧。
- **docs**: [stack_force.py](example/exception_handlers/stack_force.py)

### RV64 Invalid Address — RV64 非法地址
- **ref**: [TOPIC_TAG.md:78](TOPIC_TAG.md#rv64-invalid-address--rv64-非法地址空间)
- **hint**: RV64 下访问非法地址范围的异常行为。
- **docs**: [rv64_invalid_address_force.py](example/rv64/rv64_invalid_address_force.py)

### Compressed Load/Store — RVC 压缩访存
- **ref**: [TOPIC_TAG.md:83](TOPIC_TAG.md#compressed-loadstore--压缩指令访存)
- **hint**: C.LW/C.SW/C.LWSP/C.SWSP/C.LD/C.SD/C.LDSP/C.SDSP 压缩访存，含 SP 相对寻址。
- **docs**: [address_solving_compressed_same_operands_force.py](example/address_solving/address_solving_compressed_same_operands_force.py); [address_solving_implied_base_force.py](example/address_solving/address_solving_implied_base_force.py)

---

## Paging（分页 — 进阶）

### Paging Basics — 基本分页
- **ref**: [TOPIC_TAG.md:94](TOPIC_TAG.md#paging-basics--基本分页)
- **hint**: 启用 MMU 分页后随机生成指令，验证虚拟内存。
- **docs**: [paging_force.py](example/paging/paging_force.py); [paging_loadstore_force.py](example/paging/paging_loadstore_force.py)

### genFreePagesRange — 空闲页范围
- **ref**: [TOPIC_TAG.md:100](TOPIC_TAG.md#genfreepagesrange--生成空闲页范围)
- **hint**: 查询可用的空闲页地址范围。
- **docs**: [api_genFreePagesRange_01_force.py](example/APIs/api_genFreePagesRange_01_force.py)

### getPageInfo — 页表信息查询
- **ref**: [TOPIC_TAG.md:105](TOPIC_TAG.md#getpageinfo--页表信息查询)
- **hint**: 查询指定页面 PTE 内容、权限等页表信息。
- **docs**: [api_getPageInfo_01_force.py](example/APIs/api_getPageInfo_01_force.py)

### Page Table Walk — 页表遍历
- **ref**: [TOPIC_TAG.md:119](TOPIC_TAG.md#page-table-walk--页表遍历)
- **hint**: TLB miss 后多级页表遍历流程。
- **docs**: [paging_branch_force.py](example/paging/paging_branch_force.py)

### PMA / Memory Attributes — 物理内存属性
- **ref**: [TOPIC_TAG.md:125](TOPIC_TAG.md#pma--memory-attributes--物理内存属性)
- **hint**: 设置和验证 PMA，测试 MemAttr 对访问行为的影响。
- **docs**: [paging_memory_attributes_basic_force.py](example/paging/paging_memory_attributes_basic_force.py); [paging_va_for_pa_memory_attributes_force.py](example/paging/paging_va_for_pa_memory_attributes_force.py)

---

## Register（寄存器 — 进阶）

### Read-Only CSR — 只读系统寄存器
- **ref**: [TOPIC_TAG.md:160](TOPIC_TAG.md#read-only-csr--只读系统寄存器)
- **hint**: AssemblyHelperRISCV 读取 mvendorid/marchid/mimpid/mhartid/vl/vlenb/vtype。
- **docs**: [register_read_only_force.py](example/register/register_read_only_force.py); [assembly_helper_force.py](example/exception_handlers/assembly_helper_force.py)

### misa — ISA 配置寄存器
- **ref**: [TOPIC_TAG.md:166](TOPIC_TAG.md#misa--isa-配置寄存器)
- **hint**: 设置 misa CSR 初始值控制 ISA 扩展使能。
- **docs**: [SetMisaInitialValue_force.py](example/APIs/SetMisaInitialValue_force.py)

### Register Dependency — 寄存器依赖
- **ref**: [TOPIC_TAG.md:171](TOPIC_TAG.md#register-dependency--寄存器依赖)
- **hint**: modifyDependenceChoices 控制 RAW/WAW/WAR 数据冒险。
- **docs**: [reg_dependence_force.py](example/APIs/reg_dependence_force.py)

---

## State Transition（状态转换 — 进阶）

### StateTransition Boot — 启动状态转换
- **ref**: [TOPIC_TAG.md:186](TOPIC_TAG.md#statetransition-boot--启动状态转换)
- **hint**: EStateTransitionType.Boot，按 EStateElementType 顺序初始化所有架构状态。
- **docs**: [state_transition_boot_force.py](example/state_transition/state_transition_boot_force.py); [state_transition_boot_all_gprs_force.py](example/state_transition/state_transition_boot_all_gprs_force.py)

### EStateElementType — 状态元素类型枚举
- **ref**: [TOPIC_TAG.md:192](TOPIC_TAG.md#estateelementtype--状态元素类型)
- **hint**: GPR / FloatingPointRegister / VectorRegister / PredicateRegister / Memory / SystemRegister / VmContext / PrivilegeLevel / PC。
- **docs**: [state_transition_by_state_elem_type_force.py](example/state_transition/state_transition_by_state_elem_type_force.py); [state_transition_by_all_state_elem_types_force.py](example/state_transition/state_transition_by_all_state_elem_types_force.py); [state_transition_arbitrary_gprs_force.py](example/state_transition/state_transition_arbitrary_gprs_force.py)

### State Order Mode — 状态转换顺序
- **ref**: [TOPIC_TAG.md:199](TOPIC_TAG.md#state-transition-order-mode--状态转换顺序模式)
- **hint**: AsSpecified / ByStateElementType / ByPriority 三种 order mode。
- **docs**: [state_transition_by_priority_force.py](example/state_transition/state_transition_by_priority_force.py)

### State Merge — 状态合并
- **ref**: [TOPIC_TAG.md:204](TOPIC_TAG.md#state-merge--状态合并)
- **hint**: 多个 State 对象合并为一个。
- **docs**: [state_transition_multi_state_force.py](example/state_transition/state_transition_multi_state_force.py); [state_transition_merge_state_elements_force.py](example/state_transition/state_transition_merge_state_elements_force.py)

### Partial State — 部分状态转换
- **ref**: [TOPIC_TAG.md:210](TOPIC_TAG.md#partial-state--部分状态转换)
- **hint**: 只转换部分状态元素，不覆盖全部架构状态。用于增量修改。
- **docs**: [state_transition_partial_force.py](example/state_transition/state_transition_partial_force.py)

### Default State by Element — 各类默认状态
- **ref**: [TOPIC_TAG.md:215](TOPIC_TAG.md#default-state-by-element--各类默认状态)
- **hint**: Memory / FPR / CSR / VECREG / VmContext / PrivilegeLevel 的默认初始状态设置。
- **docs**: 6 个 `state_transition_*_default_force.py` 文件（memory / fp_registers / system_registers / vector_registers / vm_context / privilege_level）

### StateTransition + Random Instructions
- **ref**: [TOPIC_TAG.md:225](TOPIC_TAG.md#statetransition--random-instructions--状态转换配合随机指令)
- **hint**: 状态转换前后生成随机/分支指令序列，验证状态一致性。
- **docs**: [state_transition_broad_random_instructions_force.py](example/state_transition/state_transition_broad_random_instructions_force.py); [state_transition_branch_instructions_force.py](example/state_transition/state_transition_branch_instructions_force.py)

---

## Branch & Loop（分支与循环 — 进阶）

### Unconditional Branch — JAL 无条件分支
- **ref**: [TOPIC_TAG.md:240](TOPIC_TAG.md#unconditional-branch--无条件分支jal)
- **hint**: PC 相对 JAL 跳转，BRarget 指定目标。
- **docs**: [branch_pc_relative_unconditional_force.py](example/branch/branch_pc_relative_unconditional_force.py)

### Register-Indirect Branch — JALR 间接分支
- **ref**: [TOPIC_TAG.md:245](TOPIC_TAG.md#register-indirect-branch--寄存器间接分支jalr)
- **hint**: 通过 rs1 指定跳转目标，用于函数返回、虚函数调用。
- **docs**: [branch_register_force.py](example/branch/branch_register_force.py)

### BntSequence — 分支未遂
- **ref**: [TOPIC_TAG.md:250](TOPIC_TAG.md#bntsequence--分支未遂序列)
- **hint**: setBntHook + revertBntHook，控制 SpeculativeBnt 执行路径。
- **docs**: [speculative_bnt_force.py](example/bnt/speculative_bnt_force.py)

### Loop Reconverge — 循环收敛
- **ref**: [TOPIC_TAG.md:255](TOPIC_TAG.md#loopcontrol--循环控制) (loop_reconverge_force.py)
- **hint**: 条件分支收敛循环模式。
- **docs**: [loop_reconverge_force.py](example/loop/loop_reconverge_force.py)

### Loop Unconditional — 无条件循环
- **ref**: [TOPIC_TAG.md:255](TOPIC_TAG.md#loopcontrol--循环控制) (loop_unconditional_branches_force.py)
- **hint**: 无条件跳转（JAL）循环模式。
- **docs**: [loop_unconditional_branches_force.py](example/loop/loop_unconditional_branches_force.py)

---

## Exception（异常 — 进阶）

### CSR Access Exception — CSR 访问异常
- **ref**: [TOPIC_TAG.md:273](TOPIC_TAG.md#csr-access-exception--csr-访问异常)
- **hint**: 非法 CSR 访问引发异常，验证异常委托机制。
- **docs**: [access_csrs_force.py](example/exception_handlers/access_csrs_force.py)

### Exception Counting — 异常计数
- **ref**: [TOPIC_TAG.md:278](TOPIC_TAG.md#exception-counting--异常计数)
- **hint**: queryExceptionRecordsCount 查询异常数量。
- **docs**: [exception_counts_force.py](example/exception_handlers/exception_counts_force.py)

### Instruction Misaligned Exception — 指令非对齐异常
- **ref**: [TOPIC_TAG.md:283](TOPIC_TAG.md#instruction-misaligned-exception--指令非对齐异常)
- **hint**: 指令地址非对齐触发异常，验证异常向量与 trap handler。
- **docs**: [instruction_misaligned_exception_force.py](example/exception_handlers/instruction_misaligned_exception_force.py)

### Exception Vector Base Address — 异常向量基地址
- **ref**: [TOPIC_TAG.md:288](TOPIC_TAG.md#exception-vector-base-address--异常向量基地址)
- **hint**: 查询异常向量表基地址。
- **docs**: [api_queryExceptionVectorBaseAddress_force.py](example/APIs/api_queryExceptionVectorBaseAddress_force.py)

---

## Privilege（特权 — 进阶）

### System Call Sequence — 系统调用序列
- **ref**: [TOPIC_TAG.md:300](TOPIC_TAG.md#system-call-sequence--系统调用序列)
- **hint**: ECALL + 特权切换完整序列测试。
- **docs**: [system_call_sequence_force.py](example/privilege_switch/system_call_sequence_force.py); [system_call_gen_va_force.py](example/privilege_switch/system_call_gen_va_force.py)

---

## Multiprocessing（多线程 — 进阶）

### Semaphore & Lock — 信号量与锁
- **ref**: [TOPIC_TAG.md:321](TOPIC_TAG.md#semaphore--lock--信号量与锁同步)
- **hint**: AMO 原子指令实现信号量/锁（acquire/release）。
- **docs**: [multiprocessing_semaphore_basic_force.py](example/multiprocessing/multiprocessing_semaphore_basic_force.py); [multiprocessing_thread_locking_force.py](example/multiprocessing/multiprocessing_thread_locking_force.py)

### Thread Context — 线程上下文
- **ref**: [TOPIC_TAG.md:327](TOPIC_TAG.md#thread-context--线程上下文)
- **hint**: 线程上下文切换（no_advance 模式），验证上下文保存/恢复。
- **docs**: [multiprocessing_thread_context_no_advance_force.py](example/multiprocessing/multiprocessing_thread_context_no_advance_force.py)

### Thread Group — 线程组管理
- **ref**: [TOPIC_TAG.md:332](TOPIC_TAG.md#thread-group--线程组管理)
- **hint**: queryThreadGroup / getThreadGroupId / getFreeThreads，线程分区策略（same_chip / diff_core / random）。
- **docs**: 4 个 `thread_group_partition_*_force.py` + [thread_group_basic_force.py](example/thread_group/thread_group_basic_force.py)

---

## Vector（向量 — 进阶）

### Vector Load/Store — 向量访存（全部模式）
- **ref**: [TOPIC_TAG.md:356](TOPIC_TAG.md#vector-loadstore--向量访存)
- **hint**: unit-stride (VLE/VSE) / strided (VLSE/VSSE) / indexed (VLXEI/VSXEI) / whole-register (VLR/VSR) / segment (VLSEG/VSSEG) × 3 种（unit/strided/indexed）。
- **docs**: 7 个 `vector_*_load_store_force.py` 文件

### Vector Mask — 向量掩码
- **ref**: [TOPIC_TAG.md:367](TOPIC_TAG.md#vector-mask--向量掩码操作)
- **hint**: v0 掩码寄存器初始化 / 掩码访存 (VLEM/VSEM) / 掩码操作数冲突。
- **docs**: 3 个 `vector_mask_*_force.py` 文件

### Vector Operand Conflict — 向量操作数冲突
- **ref**: [TOPIC_TAG.md:374](TOPIC_TAG.md#vector-operand-conflict--向量操作数冲突)
- **hint**: always-masked / wide-operand (EW/VLMUL) / instruction-specific 冲突约束。
- **docs**: 3 个 `vector_*_operand_conflict_force.py` 文件

### Vector Integer Scalar Move — 向量-标量移动
- **ref**: [TOPIC_TAG.md:381](TOPIC_TAG.md#vector-integer-scalar-move--向量-标量数据移动)
- **hint**: VMV 在 VECREG ↔ GPR 间移动数据。
- **docs**: [vector_integer_scalar_move_force.py](example/vector/vector_integer_scalar_move_force.py); [vector_whole_register_move_force.py](example/vector/vector_whole_register_move_force.py)

### Vector Wide / Floating-Point — 向量浮点
- **ref**: [TOPIC_TAG.md:387](TOPIC_TAG.md#vector-wide--floating-point--向量浮点与扩展运算)
- **hint**: VFW/VF 浮点运算 + VADC/VSBC 进位借位。
- **docs**: [vector_floating_point_wide_operand_force.py](example/vector/vector_floating_point_wide_operand_force.py); [vector_add_carry_sub_borrow_force.py](example/vector/vector_add_carry_sub_borrow_force.py)

### Vector AMO — 向量原子操作
- **ref**: [TOPIC_TAG.md:393](TOPIC_TAG.md#vector-amo--向量原子操作)
- **hint**: VAMO 系列向量原子内存操作。
- **docs**: [vector_amo_force.py](example/vector/vector_amo_force.py)

### Vector Extension Coverage — 向量全覆盖
- **ref**: [TOPIC_TAG.md:398](TOPIC_TAG.md#vector-extension-coverage--向量扩展全覆盖)
- **hint**: 全覆盖 V 扩展指令，用于回归测试。
- **docs**: [vector_extension_instructions_force.py](example/vector/vector_extension_instructions_force.py)

---

## Floating-Point / Arithmetic（浮点/算术 — 进阶）

### MUL / DIV / REM — 整数乘除
- **ref**: [TOPIC_TAG.md:412](TOPIC_TAG.md#mul--div--rem--整数乘除)
- **hint**: M 扩展整数乘除法，含数据约束 + NaN-boxing 边界。
- **docs**: [_test_muldiv_force.py](example/fsuExamples/_test_muldiv_force.py); [test_muldiv_data_constr_force.py](example/fsuExamples/test_muldiv_data_constr_force.py); [test_muldiv_nan_boxing_force.py](example/fsuExamples/test_muldiv_nan_boxing_force.py)

---

## Data Generation（数据生成 — 进阶）

### RandomUtils — 随机工具
- **ref**: [TOPIC_TAG.md:445](TOPIC_TAG.md#randomutils-random32random64pickweighted--随机工具)
- **hint**: random32(min,max) / random64() / pickWeighted(weights) / bitstream。
- **docs**: [PickWeightedValue_test_force.py](example/APIs/PickWeightedValue_test_force.py); [RandomChoiceAPITest_force.py](example/APIs/RandomChoiceAPITest_force.py); [BitstreamTest_force.py](example/APIs/BitstreamTest_force.py)

---

## Framework（框架 — 进阶）

### Master Run — 主运行框架
- **ref**: [TOPIC_TAG.md:462](TOPIC_TAG.md#master-run--主运行框架)
- **hint**: 命令行选项、getOption、多测试序列调度。
- **docs**: [optionsTest_force.py](example/masterRun/optionsTest_force.py)

### Inquiry APIs — 信息查询
- **ref**: [TOPIC_TAG.md:467](TOPIC_TAG.md#inquiry-apis--信息查询)
- **hint**: queryInstructionRecord / getVariable / getPEstate 等查询 API。
- **docs**: [InquiryAPITest_force.py](example/APIs/InquiryAPITest_force.py); [QueryResourceEntropyTest_force.py](example/APIs/QueryResourceEntropyTest_force.py)

### Custom Entry Point — 自定义入口
- **ref**: [TOPIC_TAG.md:473](TOPIC_TAG.md#custom-entry-point--自定义入口)
- **hint**: 自定义测试入口点，改变默认执行流。
- **docs**: [CustomEntryPointTest_force.py](example/APIs/CustomEntryPointTest_force.py)

---

## ISA（指令集 — 进阶）

### RV32I Base — RV32I 基础指令
- **ref**: [TOPIC_TAG.md:489](TOPIC_TAG.md#rv32i-base--rv32i-基础指令)
- **hint**: RV32I 基础整数指令（ADD/SRLI/ADDI/SLLI/LUI），32-bit 寄存器。
- **docs**: [rv32i_force.py](example/rv32/rv32i_force.py); [RISC-V_Unprivileged_ISA.md](apiDoc/RISC-V_Unprivileged_ISA.md)
