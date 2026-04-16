# gem5 m5out 仿真结果解读指南

本文档帮助你正确理解 gem5 仿真输出 (m5out)，从中提取有效证据来验证 ISG 脚本的质量。

## 1. 仿真环境概述

当前 gem5 配置：
- **CPU 模型**: `BaseO3CPU` (乱序超标量流水线, C910 profile 近似)
- **运行模式**: bare-metal full-system (`--bare-metal`)
- **ISA**: RV64GC (RVV enabled, VLEN=256, ELEN=64, 但 C910 不使用 Vector)
- **Cache 层次**: L1 ICache + L1 DCache → L2 → DRAM
- **Cache Line**: 64 bytes
- **内存起始**: `--mem-start 0x0`
- **默认 maxinsts**: 10,000,000 (服务端固定)

> **注意**: C910 profile 是功能近似，不精确建模 L0 BTB、22-bit GHR、分离发射队列、JTLB=1024 等。

## 2. Artifact 目录结构

每次仿真在 `gem5_artifacts/<run_id>/` 下生成：

```
<run_id>/
├── output.log          # gem5 控制台 SSE 输出 (启动信息 + 退出原因)
├── manifest.json       # 本次仿真的元数据 (task_id, status, exit_code, 文件列表)
├── m5out.tar.gz        # m5out 原始归档
└── m5out/              # 解压后的仿真输出
    ├── stats.txt       # ★ 核心统计文件 (1500+ 行)
    ├── config.ini      # 仿真配置 (CPU/Cache/Memory 参数)
    ├── config.json     # 同上, JSON 格式
    ├── config.dot      # 系统拓扑图 (DOT 格式)
    ├── config.dot.svg  # 系统拓扑图 (SVG)
    └── citations.bib   # gem5 引用信息 (无分析价值)
```

## 3. output.log 解读

output.log 是 gem5 进程的标准输出，关键信息：

### 正常退出模式
| 退出原因 | output.log 中的标志行 | 含义 |
|----------|----------------------|------|
| M5EXIT 指令 | `Exiting @ tick N because m5_exit instruction encountered` | ISG 脚本主动调用了 M5EXIT##RISCV 终止仿真，且传给 gem5 的 delay 足够小（通常应为 0） |
| maxinsts 达到 | `Exiting @ tick N because a thread reached the max instruction count` | 指令数达到上限, 仿真被截断 |
| 仿真完成 | `=== Simulation completed ===` | 仿真进程正常结束 |

### 如何判断 ISG 脚本是否被完整执行

- **M5EXIT 退出**: 脚本完整执行了, 包括你写的 `self.genInstruction("M5EXIT##RISCV")`，并且 `a0/x10` 中的 delay 没有把退出事件推迟到 maxinsts 之后
- **maxinsts 截断**: 脚本 **可能没执行完**, FORCE-RISCV 约添加 ~800 条基础指令, 加上你的指令, 如果 ISG 生成的指令总数 > maxinsts, 后面部分不会被执行
- 可以从 `stats.txt` 的 `simInsts` 确认实际执行了多少条指令

### M5EXIT 使用注意事项

- gem5 的 `m5_exit` 会把 `a0/x10` 解释为 delay 参数；如果该寄存器里残留随机大值，即使执行到了 `M5EXIT`，真正退出事件也可能被安排到很远未来，最终仍被 `maxinsts` 抢先终止
- 因此在生成退出序列时，必须先显式清零 `a0/x10`，再发出 `M5EXIT##RISCV`
- 推荐模式：

```python
self.genInstruction("ADDI##RISCV", {"rd": 10, "rs1": 0, "simm12": 0})
self.genInstruction("M5EXIT##RISCV")
```

### 异常/错误信号
```
warn: ...     # 警告, 通常不影响结果
info: ...     # 信息, 可以忽略
panic: ...    # 严重错误, 仿真中断
fatal: ...    # 致命错误, 仿真中断
```

## 4. stats.txt 核心指标速查表

stats.txt 是验证 ISG 目标的主要证据来源。以下按验证场景分组：

### 4.1 全局概览指标

| 指标 | 前缀 | 含义 | 怎么用 |
|------|------|------|--------|
| `simInsts` | (顶层) | 实际执行的指令数 | 验证指令流长度, 判断是否被 maxinsts 截断 |
| `simTicks` | (顶层) | 仿真消耗的时钟 tick | 计算执行时间 |
| `hostSeconds` | (顶层) | 宿主机实际运行秒数 | 仿真性能参考 |
| `system.cpu.cpi` | system.cpu | 每条指令消耗周期数 | 流水线效率总览 |
| `system.cpu.ipc` | system.cpu | 每周期执行指令数 | 流水线效率总览 |

### 4.2 指令类型分布 — 验证"是否生成了目标指令"

**关键前缀**: `system.cpu.commit.committedInstType_0::<OpClass>`

这些指标记录了 **实际提交(committed)** 的指令按功能单元分类的数量：

| OpClass 名称 | 对应 ISG 指令类型 | 示例 |
|-------------|-------------------|------|
| `IntAlu` | 整数算术/逻辑 (ADD, SUB, AND, OR, XOR, SLL, SRL, SRA, SLT 等) | 最常见, 通常占 99%+ |
| `IntMult` | 整数乘法 (MUL, MULH, MULW 等) | |
| `IntDiv` | 整数除法 (DIV, DIVU, REM, REMU 等) | |
| `FloatAdd` | 浮点加减 (FADD, FSUB) | |
| `FloatMult` | 浮点乘法 (FMUL) | |
| `FloatDiv` | 浮点除法 (FDIV) | |
| `FloatSqrt` | 浮点开方 (FSQRT) | |
| `FloatCmp` | 浮点比较 (FEQ, FLT, FLE) | |
| `FloatCvt` | 浮点转换 (FCVT) | |
| `MemRead` | Load 指令 (LB, LH, LW, LD 等) | |
| `MemWrite` | Store 指令 (SB, SH, SW, SD 等) | |
| `FloatMemRead` | 浮点 Load (FLW, FLD) | |
| `FloatMemWrite` | 浮点 Store (FSW, FSD) | |

**验证方法**: 搜索 `committedInstType_0::<目标类型>`, 确认 count > 0。

> **重要**: FORCE-RISCV 自动添加的 ~800 条基础指令也会被计入。如果你的 ISG 脚本只生成了少量目标指令, 其 count 可能被基础指令的数量淹没。关注非零值即可。

**另一组等价指标** (按线程汇总):
- `system.cpu.commitStats0.numIntInsts` — 整数指令总数
- `system.cpu.commitStats0.numFpInsts` — 浮点指令总数
- `system.cpu.commitStats0.numLoadInsts` — Load 总数
- `system.cpu.commitStats0.numStoreInsts` — Store 总数
- `system.cpu.commitStats0.numVecInsts` — 向量指令总数
- `system.cpu.commitStats0.numMemRefs` — 内存访问总数 (Load + Store)

### 4.3 分支预测 — 验证"分支行为"

**关键前缀**: `system.cpu.branchPred`

| 指标 | 含义 | ISG 验证用途 |
|------|------|-------------|
| `committed_0::DirectCond` | 提交的条件分支数 (BEQ, BNE, BLT 等) | 验证条件分支是否被执行 |
| `committed_0::DirectUncond` | 提交的无条件跳转数 (JAL) | 验证无条件跳转 |
| `committed_0::IndirectUncond` | 提交的间接跳转数 (JALR) | 验证间接跳转 |
| `committed_0::Return` | 提交的函数返回数 | 验证 RET/JALR 返回 |
| `committed_0::CallDirect` | 提交的直接调用数 | 验证 JAL 函数调用 |
| `mispredicted_0::total` | 分支预测错误总数 | 分支预测压力测试 |
| `BTBHits` | BTB 命中数 | BTB 覆盖率 |
| `BTBMispredicted` | BTB 预测错误数 | BTB 压力测试 |
| `ras.pushes` / `ras.pops` | RAS 入栈/出栈次数 | 函数调用深度测试 |
| `condPredicted` | 条件分支预测次数 | |
| `condIncorrect` | 条件分支预测错误 | |

**分支类型子键**:
- `NoBranch`, `Return`, `CallDirect`, `CallIndirect`, `DirectCond`, `DirectUncond`, `IndirectCond`, `IndirectUncond`

### 4.4 Cache 行为 — 验证"内存访问模式"

#### ICache (指令缓存)
**前缀**: `system.cpu.icache`

| 指标 | 含义 |
|------|------|
| `demandHits::total` | ICache 命中次数 |
| `demandMisses::total` | ICache 未命中次数 |
| `demandMissRate::total` | ICache 未命中率 |
| `replacements` | ICache 行替换次数 |

**验证用途**: 如果 ISG 目标是测试 ICache refill, 需要看到较高的 `demandMisses` 和 `replacements`。

#### DCache (数据缓存)
**前缀**: `system.cpu.dcache`

| 指标 | 含义 |
|------|------|
| `demandHits::total` | DCache 命中次数 |
| `demandMisses::total` | DCache 未命中次数 |
| `demandMissRate::total` | DCache 未命中率 |
| `replacements` | DCache 行替换次数 |
| `blockedCauses::no_mshrs` | MSHR 满导致阻塞次数 |
| `ReadReq.hits/misses/accesses` | 读请求细分 |
| `WriteReq.hits/misses/accesses` | 写请求细分 (如果有 Store) |

#### L2 Cache
**前缀**: `system.l2`

| 指标 | 含义 |
|------|------|
| `overallHits::total` | L2 命中次数 |
| `overallMisses::total` | L2 未命中次数 |
| `overallMissRate::total` | L2 未命中率 |

### 4.5 流水线微架构 — 验证"流水线压力"

| 指标 | 前缀 | 含义 |
|------|------|------|
| `numSquashedInsts` | system.cpu | Squash 的指令数 (冒险/预测错误导致) |
| `squashedInstsExamined` | system.cpu | Squash 过程中检查的指令数 |
| `timesIdled` | system.cpu | CPU 空闲次数 |
| `idleCycles` | system.cpu | CPU 空闲周期数 |
| `fuBusy` | system.cpu | 功能单元繁忙拒绝次数 |
| `statFuBusy::<FU>` | system.cpu | 各功能单元繁忙次数细分 |
| `numIssuedDist::N` | system.cpu | 每周期发射 N 条指令的周期数 |
| `commit.branchMispredicts` | system.cpu | 提交阶段发现的分支预测错误数 |
| `commit.commitSquashedInsts` | system.cpu | 提交阶段 squash 的指令数 |
| `decode.branchMispred` | system.cpu | 译码阶段发现的分支预测错误 |

**功能单元繁忙分布** (`statFuBusy`): 如果目标是制造功能单元竞争, 检查 `IntMult`, `IntDiv`, `FloatDiv` 等的繁忙计数。

### 4.6 内存系统 — 验证"DRAM 访问"

**前缀**: `system.mem_ctrls` / `system.mem_ctrls.dram`

| 指标 | 含义 |
|------|------|
| `numReads::total` | DRAM 读请求数 |
| `readRowHitRate` | DRAM 行缓冲命中率 |
| `busUtil` | DRAM 总线利用率 |
| `avgMemAccLat` | 平均内存访问延迟 |

### 4.7 控制指令 — 验证"控制流特征"

**前缀**: `system.cpu.commitStats0.committedControl`

| 指标 | 含义 |
|------|------|
| `IsControl` | 控制指令总数 |
| `IsDirectControl` | 直接跳转控制总数 |
| `IsIndirectControl` | 间接跳转控制总数 |
| `IsCondControl` | 条件控制总数 |
| `IsUncondControl` | 无条件控制总数 |
| `IsReturn` | 返回指令总数 |

### 4.8 寄存器访问

**前缀**: `system.cpu.executeStats0`

| 指标 | 含义 |
|------|------|
| `numIntRegReads` / `numIntRegWrites` | 整数寄存器读写次数 |
| `numFpRegReads` / `numFpRegWrites` | 浮点寄存器读写次数 |
| `numMiscRegReads` / `numMiscRegWrites` | 特殊寄存器 (CSR) 读写次数 |

## 5. 验证策略与 grep 模式

根据不同 ISG 测试目标, 建议使用以下 `grep_gem5_results` 搜索模式：

### 验证指令类型覆盖
```python
# 确认浮点指令被执行
grep_gem5_results(task_name, r"committedInstType_0::Float\w+\s+[1-9]")

# 确认 Load/Store 被执行
grep_gem5_results(task_name, r"committedInstType_0::Mem\w+\s+[1-9]")

# 确认整数乘除被执行
grep_gem5_results(task_name, r"committedInstType_0::Int(Mult|Div)\s+[1-9]")
```

### 验证分支行为
```python
# 确认条件分支被执行
grep_gem5_results(task_name, r"committed_0::DirectCond\s+[1-9]")

# 确认有分支预测错误 (压力测试)
grep_gem5_results(task_name, r"mispredicted_0::total\s+[1-9]")

# 确认间接跳转
grep_gem5_results(task_name, r"committed_0::Indirect\w+\s+[1-9]")
```

### 验证 Cache 行为
```python
# DCache miss 是否发生
grep_gem5_results(task_name, r"dcache\.demandMisses::total\s+[1-9]")

# ICache miss 是否发生
grep_gem5_results(task_name, r"icache\.demandMisses::total\s+[1-9]")

# Cache 替换
grep_gem5_results(task_name, r"(icache|dcache)\.replacements\s+[1-9]")
```

### 验证退出方式
```python
# 确认是 M5EXIT 退出还是 maxinsts 截断
grep_gem5_results(task_name, r"Exiting @ tick")
```

### 通用: 查看指令总数和 CPI
```python
grep_gem5_results(task_name, r"^(simInsts|system\.cpu\.cpi|system\.cpu\.ipc)\s")
```

## 6. 常见误判与陷阱

### 误判 1: "仿真完成 = 测试通过"
**错误**: 只看到 `Status: completed, Exit Code: 0` 就判断目标达成。
**正确**: 必须在 stats.txt 中找到支持目标的具体指标。

### 误判 2: "指令数很多 = 目标指令被执行"
**错误**: `simInsts = 10000000` 并不意味着你的目标指令被执行了。
**正确**: FORCE-RISCV 自动添加约 800 条基础指令, 大量 JAL 跳转用于指令间连接。检查 `committedInstType` 中具体 OpClass 的数量。

### 误判 3: "IntAlu 占比 99% 说明只有算术指令"
**错误**: 认为 IntAlu 高占比意味着没有其他指令。
**正确**: FORCE-RISCV 用大量 JAL (归类为 IntAlu) 连接指令, 所以 IntAlu 天然很高。关注目标类型的绝对数量而非占比。

### 误判 4: "maxinsts 截断 = 脚本有问题"
**错误**: 因为仿真被 maxinsts 截断就认为 ISG 有 bug。
**正确**: maxinsts 截断只意味着没执行完, ISG 生成的指令可能很多。如果测试目标的证据已经在截断前产生, 结果仍然有效。

### 误判 4.1: "执行到了 M5EXIT 但没退出 = gem5 的 m5_exit 坏了"
**错误**: 认为只要汇编里有 `M5EXIT`，gem5 就一定会立刻退出。
**正确**: 还要检查 `a0/x10` 是否被显式清零。若它带着非零大 delay，`pseudo_inst::m5exit(...)` 仍会被调用，但退出事件会被延后，最后可能仍表现为 `maxinsts` 截断。

### 误判 5: "DCache miss rate 很高 = 有问题"
**错误**: 认为高 miss rate 代表错误。
**正确**: 取决于测试目标。如果目的是测试 cache miss 场景, 高 miss rate 反而是好事。

## 7. config.ini / config.json 用途

这些文件记录仿真配置参数, 通常不需要分析, 但在以下场景有用：
- 确认 CPU 类型: `[system.cpu] type=BaseO3CPU`
- 确认 Cache 大小: `[system.cpu.dcache] size=...`
- 确认 maxinsts 设置
- 确认内存映射范围

## 8. 与 C910 RTL 验证的关联

gem5 C910 profile 仿真与 RTL TB 验证的映射关系：

| gem5 stats 指标 | 对应 C910 RTL 模块 | ISG 验证关注点 |
|----------------|-------------------|---------------|
| `branchPred.*` | ct_bpu_bht, ct_bpu_btb, ct_bpu_ras | 分支预测压力 |
| `icache.*` | ct_ifu_l1_refill | ICache refill 状态机 |
| `dcache.*` | ct_lsu_* | Load/Store 单元 |
| `commit.branchMispredicts` | ct_iu_* (流水线冲刷) | 流水线冒险 |
| `statFuBusy::IntDiv` | ct_iu_div | 除法器竞争 |
| `numSquashedInsts` | ct_iu_renamer, ct_iu_scheduler | 指令取消/重发 |
| `dtb_walker_cache.*` | ct_mmu_* | TLB/MMU (当前 bare-metal 不活跃) |
| `commit.amos` | ct_lsu_atomic | 原子操作 |
| `commit.membars` | ct_lsu_fence | 内存屏障 |

> **注意**: 由于运行在 bare-metal 模式, TLB/MMU 相关指标通常为 0。如需测试这些模块, 需要配置页表或使用 OS 模式。
