# FORCE-RISCV Documentation Index

> 总入口。二级细节见 [SUB_INDEX.md](SUB_INDEX.md)，完整 Topic→Doc 映射见 [TOPIC_TAG.md](TOPIC_TAG.md)。

---

## 1. Directory Structure

| Directory | Description | When to Read |
|-----------|-------------|--------------|
| [apiDoc/](apiDoc/) | API 参考手册、RISC-V ISA 规范、架构介绍 | 需要 API 用法、函数签名、ISA 细节 |
| [config/](config/) | XML 指令定义与架构配置 | 需要指令编码、操作数细节、架构配置 |
| [example/](example/) | Python 测试模板示例（按功能组织） | 需要特定功能的代码示例 |
| [memory_operations_guide.md](memory_operations_guide.md) | 内存操作独立指南 | load/store、地址生成、内存初始化 |

---

## 2. Progressive Loading Guide

### Level 1 — 入门
阅读 [FORCE-RISCV_brief_introduction.md](apiDoc/FORCE-RISCV_brief_introduction.md)：
- 架构组件：Config / Arch / Memory / Virtual Memory / State Transition / Privilege Switch / Dependency / ReExe / Bnt
- 程序执行流程：reset_pc → boot → template → end-of-test

### Level 2 — API 参考（按需查阅）
使用 [apiDoc/INDEX.md](apiDoc/INDEX.md) 在 User Manual 中定位章节：

| 需求 | User Manual 章节 |
|------|-----------------|
| 指令生成 | §5.1 `genInstruction`, `queryInstructionRecord` |
| 序列模式 | §5.2, §6.1-6.7 |
| 地址/页面 API | §5.3 (address), §5.4 (page) |
| 寄存器控制 | §5.5 (all register APIs) |
| 异常处理 | §5.6 (exception APIs) |
| PE 状态控制 | §5.7 `getPEstate`, `setPEstate` |
| 内存控制 | §5.8 `initializeMemory` |
| Choices 修改 | §5.9 (operand/paging/general choices) |
| Variables/Knobs | §5.10 `modifyVariable`, `getVariable` |
| BNT 分支未遂 | §5.11 `setBntHook`, `revertBntHook` |
| 工具函数 | §5.12 (`pickWeighted`, `sample`, `random32/64`, `genData` 等) |

### Level 3 — RISC-V ISA 规范（按需查阅）
[apiDoc/RISC-V_Unprivileged_ISA.md](apiDoc/RISC-V_Unprivileged_ISA.md) 各扩展对应章节：

| Extension | Chapters | 内容 |
|-----------|----------|------|
| RV32I/RV64I | Ch.2, Ch.4 | 基础整数指令集 |
| M | Ch.12 | 乘除法 |
| A | Ch.13-17 | 原子操作 |
| F/D/Q | Ch.21-23 | 浮点 |
| Zfh | Ch.24 | 半精度浮点 |
| C | Ch.28 | 压缩指令 |
| B | Ch.30 | 位操作 |
| V | Ch.31 | 向量扩展 |
| Memory Model | Ch.18 | RVWMO 内存模型 |
| CSR | Ch.6 | 控制状态寄存器 |

---

## 3. Quick Reference

### 写一个基本 ISG 脚本
1. 读本页 §4 Core API Index → `genInstruction`
2. 浏览 `example/APIs/` 了解基础 API 用法
3. 参考下方 §5 的示例学习路径

### 针对特定指令集
1. 查 `config/` 确认 XML 配置
2. 查 `example/instructions/` 找对应指令示例

### 常用 API 速查

| API | 用途 | 详见 |
|-----|------|------|
| `genInstruction(name, kwargs)` | 生成单条指令 | [TOPIC_TAG.md:482](TOPIC_TAG.md#geninstruction--核心指令生成) |
| `genVA(Size, Align, Type, Range)` | 生成虚拟地址 | [TOPIC_TAG.md:18](TOPIC_TAG.md#genva--生成虚拟地址) |
| `genPA(Size, Align, Type)` | 生成物理地址 | [TOPIC_TAG.md:28](TOPIC_TAG.md#genpa--生成物理地址) |
| `genVAforPA(PA, Size, Type)` | PA→VA 映射 | [TOPIC_TAG.md:34](TOPIC_TAG.md#genvaforpa--虚拟地址到物理地址映射) |
| `initializeMemory(addr, bank, size, data)` | 预填充内存 | [TOPIC_TAG.md:42](TOPIC_TAG.md#initializememory--初始化内存内容) |
| `getRandomGPR()` / `getRandomRegisters()` | 随机寄存器分配 | [TOPIC_TAG.md:135](TOPIC_TAG.md#getrandomgpr--getrandomregisters--随机寄存器分配) |
| `reserveRegister()` / `unreserveRegister()` | 寄存器预留/释放 | [TOPIC_TAG.md:141](TOPIC_TAG.md#reserveregister--unreserveregister--寄存器预留) |
| `initializeRegister()` / `initializeRegisterFields()` | 寄存器初始化 | [TOPIC_TAG.md:147](TOPIC_TAG.md#initializeregister--initializeregisterfields--寄存器初始化) |
| `readRegister()` / `writeRegister()` | 寄存器读写 | [TOPIC_TAG.md:154](TOPIC_TAG.md#writeregister--readregister--寄存器读写) |
| `modifyOperandChoices()` | 约束操作数选择 | [TOPIC_TAG.md:423](TOPIC_TAG.md#choicesmodifier--选项修改器) |
| `modifyVariable()` | 修改生成控制变量 | [apiDoc/INDEX.md](apiDoc/INDEX.md) §5.10 |
| `genData(pattern)` | 生成模式化数据 | [TOPIC_TAG.md:440](TOPIC_TAG.md#gendata--数据模式生成) |
| `LSTarget` (genInstruction 参数) | 指定 load/store 地址 | [TOPIC_TAG.md:49](TOPIC_TAG.md#lstarget--loadstore-目标地址) |
| `setBntHook()` / `revertBntHook()` | 分支未遂控制 | [SUB_INDEX.md](SUB_INDEX.md) > Branch |

---

## 4. Core API Index（高频 Topic）

### 4.1 Memory Operations

#### genVA — 虚拟地址生成
- **ref**: [TOPIC_TAG.md:18](TOPIC_TAG.md#genva--生成虚拟地址)
- 生成符合对齐/大小的有效 VA，支持 Range / FlatMap / ForceAlias。所有 load/store 前必须调用。
- 别名 → `Address Alias` @SUB_INDEX; 地址复用 → `ConstraintSet`; 压缩访存 → `Compressed Load/Store` @SUB_INDEX

#### genInstruction — 核心指令生成
- **ref**: [TOPIC_TAG.md:482](TOPIC_TAG.md#geninstruction--核心指令生成)
- FORCE-RISCV 最核心 API。参数：LSTarget / NoPreamble / UsePreamble / NoSkip / BRarget。
- 立即数 → [LoadImmediate_force.py](example/APIs/LoadImmediate_force.py); Preamble 控制 → [LoadRegisterPreambleTest_force.py](example/APIs/LoadRegisterPreambleTest_force.py)

#### LSTarget — Load/Store 目标地址
- **ref**: [TOPIC_TAG.md:49](TOPIC_TAG.md#lstarget--loadstore-目标地址)
- 通过 genInstruction 的 LSTarget 参数指定 load/store 地址，配合 NoPreamble/UsePreamble/NoSkip 控制。
- 地址求解 → `Address Solving` @SUB_INDEX; 非对齐 → `Misaligned Access` @SUB_INDEX

#### initializeMemory — 内存初始化
- **ref**: [TOPIC_TAG.md:42](TOPIC_TAG.md#initializememory--初始化内存内容)
- load 前预填充内存数据（最大 8 字节）。参数：addr / bank / size / data / is_instr / is_virtual。
- 栈初始化 → `Stack Init` @SUB_INDEX

#### genPA — 物理地址生成
- **ref**: [TOPIC_TAG.md:28](TOPIC_TAG.md#genpa--生成物理地址)
- 支持 MemAttrArch（AMOSwap,CoherentL1）和 MemAttrImpl（Debug,CLINT,PLIC,GPIO）。
- PA→VA → `genVAforPA`; 内存属性 → `PMA / MemAttr` @SUB_INDEX

#### genVAforPA — VA→PA 映射
- **ref**: [TOPIC_TAG.md:34](TOPIC_TAG.md#genvaforpa--虚拟地址到物理地址映射)
- ForceNewAddr=1 强制新建映射。配合 `Address Alias` @SUB_INDEX 实现多 VA→同 PA。

### 4.2 Register Management

#### getRandomGPR / getRandomRegisters
- **ref**: [TOPIC_TAG.md:135](TOPIC_TAG.md#getrandomgpr--getrandomregisters--随机寄存器分配)
- 随机 GPR/FPR/VECREG 索引，支持 exclude。指令操作数生成的基础。
- 依赖控制 → `Register Dependency` @SUB_INDEX; CSR 读取 → `Read-Only CSR` @SUB_INDEX

#### initializeRegister / initializeRegisterFields
- **ref**: [TOPIC_TAG.md:147](TOPIC_TAG.md#initializeregister--initializeregisterfields--寄存器初始化)
- 整体/按字段初始化寄存器值。常用于向量和浮点寄存器。
- 向量初始化 → `Vector Add`; 随机初始化 → `RandomUtils` @SUB_INDEX

#### reserveRegister / unreserveRegister
- **ref**: [TOPIC_TAG.md:141](TOPIC_TAG.md#reserveregister--unreserveregister--寄存器预留)
- 预留/释放寄存器，用于异常 handler、特权切换等场景。

#### writeRegister / readRegister
- **ref**: [TOPIC_TAG.md:154](TOPIC_TAG.md#writeregister--readregister--寄存器读写)
- 寄存器读写（含字段级），支持 GPR / FPR / VECREG / CSR。
- PE 状态 → `Inquiry APIs` @SUB_INDEX; 只读 CSR → `Read-Only CSR` @SUB_INDEX

### 4.3 State & Control Flow

#### StateTransition — 状态转换
- **ref**: [TOPIC_TAG.md:180](TOPIC_TAG.md#statetransition-basics--状态转换基础)
- transitionToState() 执行状态转换。State 包含 Memory/GPR/FPR/VECREG/CSR/PC/PrivilegeLevel。支持 Explicit / Boot。
- Boot → `StateTransition Boot` @SUB_INDEX; 合并 → `State Merge` @SUB_INDEX; 顺序 → `State Order Mode` @SUB_INDEX; 默认状态 ×6 → `Default State` @SUB_INDEX

#### ChoicesModifier — 选项修改器
- **ref**: [TOPIC_TAG.md:423](TOPIC_TAG.md#choicesmodifier--选项修改器)
- modifyOperandChoices / modifyRegisterFieldValueChoices / modifyPagingChoices / modifyGeneralChoices。commitSet 提交，支持 revert。

#### ConstraintSet — 约束集
- **ref**: [TOPIC_TAG.md:429](TOPIC_TAG.md#constraintset--约束集)
- addRange / subRange / mergeConstraintSet / chooseValue / isEmpty / size。配合 LSTarget 限定地址范围。

#### LoopControl — 循环控制
- **ref**: [TOPIC_TAG.md:255](TOPIC_TAG.md#loopcontrol--循环控制)
- LoopControl(LoopCount=N)，支持 register-increment / broad-random / reconverge / unconditional 四种模式。
- 收敛 → `Loop Reconverge` @SUB_INDEX; 无条件 → `Loop Unconditional` @SUB_INDEX

#### Conditional Branch — 条件分支
- **ref**: [TOPIC_TAG.md:235](TOPIC_TAG.md#conditional-branch--条件分支beq-bne-blt-bge-bltu-bgeu)
- BEQ/BNE/BLT/BGE/BLTU/BGEU，PC 相对寻址，BRarget 指定目标。
- JAL → `Unconditional Branch` @SUB_INDEX; JALR → `Register-Indirect Branch` @SUB_INDEX; Bnt → `BntSequence` @SUB_INDEX

### 4.4 Exception & Privilege

#### ECALL / EBREAK
- **ref**: [TOPIC_TAG.md:268](TOPIC_TAG.md#ecall--ebreak--系统调用与断点)
- 系统调用与断点，配合 TrapsRedirectModifier。
- CSR 异常 → `CSR Access Exception` @SUB_INDEX; 异常计数 → `Exception Counting` @SUB_INDEX; 指令非对齐 → `Instruction Misaligned` @SUB_INDEX

#### Privilege Switch — 特权级切换
- **ref**: [TOPIC_TAG.md:293](TOPIC_TAG.md#privilege-switch--特权级切换)
- MRET/SRET 在 Machine/Supervisor/User 间切换。
- 系统调用序列 → `System Call Sequence` @SUB_INDEX

#### Page Fault — 缺页异常
- **ref**: [TOPIC_TAG.md:110](TOPIC_TAG.md#page-fault--缺页异常)
- load/store/instruction-fetch 缺页异常 + trap handler，含 no-access-fault 场景。
- 分页基础 → `Paging Basics` @SUB_INDEX; 页表遍历 → `Page Table Walk` @SUB_INDEX

### 4.5 Multiprocessing

#### Multi-Thread Basics
- **ref**: [TOPIC_TAG.md:310](TOPIC_TAG.md#multi-thread-basics--多线程基础)
- 多线程环境随机指令生成，RV64I_map.pick() 调度。
- 锁同步 → `Semaphore & Lock` @SUB_INDEX; 上下文切换 → `Thread Context` @SUB_INDEX; 线程组 → `Thread Group` @SUB_INDEX

#### FENCE — 内存屏障
- **ref**: [TOPIC_TAG.md:316](TOPIC_TAG.md#fence--内存屏障)
- FENCE 指令控制内存访问顺序，验证多核一致性。

### 4.6 Vector Extension

#### Vector Add (VADD.VV)
- **ref**: [TOPIC_TAG.md:344](TOPIC_TAG.md#vector-add-vaddvv--向量加法)
- VSEW=0x2(32-bit) + VLMUL=0x0(1)。VectorTestSequence 基类提供 setUp/verify。
- 全部 vector 子主题 → `Vector Load/Store`, `Vector Mask`, `Vector Op Conflict`, `Vector AMO` 等详见 @SUB_INDEX

#### VSETVL / VSETVLI / VSETIVLI — VL 配置
- **ref**: [TOPIC_TAG.md:349](TOPIC_TAG.md#vsetvl--vsetvli--vsetivli--向量长度配置)
- VL 配置三种方式：VSETVL(rs2 动态) / VSETVLI(立即数) / VSETIVLI(立即数+SEW)。

### 4.7 Floating-Point & Data

#### FMUL / FDIV / FMADD / FADD
- **ref**: [TOPIC_TAG.md:407](TOPIC_TAG.md#fmul--fdiv--fmadd--fadd--浮点运算)
- 使用 pickWeighted 加权生成浮点指令（.D/.S 变体）。
- 整数乘除 → `MUL/DIV/REM` @SUB_INDEX

#### genData — 数据模式生成
- **ref**: [TOPIC_TAG.md:440](TOPIC_TAG.md#gendata--数据模式生成)
- 生成带约束数据：INT32(val) / INT64(range) / FP64(sign,exp,frac) / vector-data。
- 随机工具 → `RandomUtils` @SUB_INDEX

### 4.8 Boot & Framework

#### Boot Flow — 启动流程
- **ref**: [TOPIC_TAG.md:456](TOPIC_TAG.md#boot-flow--启动流程)
- reset_pc → boot → template → end-of-test，支持 skip_boot。
- 主运行框架 → `Master Run` @SUB_INDEX; 自定义入口 → `Custom Entry Point` @SUB_INDEX; 查询 → `Inquiry APIs` @SUB_INDEX

---

## 5. Implementing Advanced Features

| Feature | Doc Location | Example Location |
|---------|-------------|-----------------|
| **Memory operations** | [memory_operations_guide.md](memory_operations_guide.md) | `example/APIs/api_genVA_*.py`, `example/address_solving/` |
| Address solving | User Manual §5.3 | `example/address_solving/` |
| Paging / Virtual Memory | User Manual §5.4 | `example/paging/` |
| Exception handling | User Manual §5.6 | `example/exception_handlers/` |
| Register control | User Manual §5.5 | `example/APIs/` register tests, `example/register/` |
| Branch / BNT | User Manual §5.11 | `example/branch/`, `example/bnt/` |
| State transition | User Manual §5.7 | `example/state_transition/` |
| Privilege switching | Brief Intro §1.1 | `example/privilege_switch/` |
| Multiprocessing | User Manual §3.1 | `example/multiprocessing/` |
| Loop control | User Manual §5.12 | `example/loop/` |
| Vector instructions | ISA Spec Ch.31 | `example/vector/` |
| Floating-point | ISA Spec Ch.21-24 | `example/fsuExamples/` |
| Compressed instructions | ISA Spec Ch.28 | `example/address_solving/` RVC files, `example/instructions/` |

---

## 6. Example Learning Path

推荐按以下顺序阅读示例（由浅入深）：

1. [GenData_test_force.py](example/APIs/GenData_test_force.py) — `genData()` 数据生成
2. [InitializeRegisterTest_force.py](example/APIs/InitializeRegisterTest_force.py) — 寄存器初始化
3. [ReserveRegisterTest_force.py](example/APIs/ReserveRegisterTest_force.py) — 寄存器预留
4. [Constraint_force.py](example/APIs/Constraint_force.py) — 约束集应用
5. [api_genVA_01_force.py](example/APIs/api_genVA_01_force.py) — 虚拟地址生成
6. [branch_pc_relative_conditional_force.py](example/branch/branch_pc_relative_conditional_force.py) — 分支指令
7. [paging_force.py](example/paging/paging_force.py) — 基本分页
8. [vector_simple_add_force.py](example/vector/vector_simple_add_force.py) — 向量指令

### Control File Convention
- `_def_fctrl.py` — 默认配置（含测试文件列表 + 生成器选项如 `--cfg riscv_rv64.config`）
- `_noiss_fctrl.py` — 无 ISS 模式
- `_rv32_fctrl.py` — RV32 专用配置
- `_perf_fctrl.py` — 性能测试配置

---

## 7. Full Documents

| Document | ref | 覆盖范围 |
|----------|-----|---------|
| FORCE-RISCV_brief_introduction.md | [TOPIC_TAG.md:499](TOPIC_TAG.md#force-riscv_brief_introductionmd) | 架构总览 + 执行流程 |
| FORCE-RISCV_User_Manual-v0.8.md | [TOPIC_TAG.md:504](TOPIC_TAG.md#force-riscv_user_manual-v08md) | 全部 Front-End API + 命令行参数 |
| RISC-V_Unprivileged_ISA.md | [TOPIC_TAG.md:509](TOPIC_TAG.md#risc-v_unprivileged_isamd) | RV32I/RV64I + M/A/F/D/Q/C/B/V 扩展 |
| README.md | [TOPIC_TAG.md:514](TOPIC_TAG.md#readmemd) | 快速入门 / 构建 / 运行 |
| memory_operations_guide.md | [TOPIC_TAG.md:519](TOPIC_TAG.md#memory_operations_guidemd) | 内存操作完整指南 |

---

## 8. SUB_INDEX 内容速览

以下低频/专用主题详见 [SUB_INDEX.md](SUB_INDEX.md)：

| 域 | 覆盖 |
|----|------|
| Memory | Address Alias, verifyVirtualAddress, Misaligned Access, Stack Init, RV64 Invalid Address, Compressed Load/Store |
| Paging | Paging Basics, genFreePagesRange, getPageInfo, Page Table Walk, PMA/MemAttr |
| Register | Read-Only CSR, misa, Register Dependency |
| State | StateTransition Boot, EStateElementType, State Order Mode, State Merge, Partial State, Default State ×6 |
| Branch/Loop | Unconditional Branch, Register-Indirect Branch, BntSequence, Loop Reconverge, Loop Unconditional |
| Exception/Privilege | CSR Access Exception, Exception Counting, Instruction Misaligned, Exception Vector Base Address, System Call Sequence |
| Multiprocessing | Semaphore & Lock, Thread Context, Thread Group ×4 |
| Vector | Vector Load/Store ×7, Vector Mask ×3, Vector Op Conflict ×3, Vector Scalar Move ×2, Vector Wide/FP, Vector AMO, Vector Coverage |
| FP/Data/Framework | MUL/DIV/REM ×3, RandomUtils, Master Run, Inquiry APIs, Custom Entry Point, RV32I Base |
