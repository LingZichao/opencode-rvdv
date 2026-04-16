# C910 验证 TB 指令加载方式分析

## 问题概述

当前 C910 验证 TB 采用 **静态指令流加载** 方式：
- 指令文件：[inst.pat](file:///home/c910/wangyahao/openc910/smart_run/tb1/inst.pat)（最多 64KB 指令流）
- 加载位置：SRAM 内存 (`tb.x_soc.x_axi_slave128.x_f_spsram_large`)
- 地址范围：`0x00000000 - 0x00003FFF`（16KB 指令空间）

```verilog
// tb.v 中的加载逻辑
for (j = 0; i < 32'h4000; i = j / 4)  // 最多 16K 字 = 64KB
begin
  `RTL_MEM.ram0.mem[i][7:0] = mem_inst_temp[j][31:24];
  // ... 加载到 SRAM
end
```

---

## 难以覆盖的模块分析

### 1. ICache Refill 模块 ❌

| 问题 | 原因 | 影响模块 |
|------|------|----------|
| **ICache Miss 难以触发** | 64KB 指令可能完全装入 ICache | `ct_ifu_l1_refill` |
| **Refill 状态机覆盖不全** | 无连续 miss，状态机停留在 IDLE | `ct_ifu_l1_refill` 状态机 |
| **Refill 与 Invalidation 并发** | 无动态代码修改，无法触发 CTC_INV 状态 | `ct_ifu_l1_refill.CTC_INV` |

**难以覆盖的状态**：
```
IDLE → REQ → WFD1 → WFD2 → ... → IDLE  ✓ (可能覆盖)
IDLE → REQ → CTC_INV → INV_WFDx → IDLE  ❌ (几乎无法覆盖)
```

**改进建议**：
- 使用大地址范围跳转指令触发 ICache miss
- 通过 CSR 指令动态 invalidation ICache
- 参考文档：`target/smc_icache_refill_test_doc.md`

---

### 2. TLB/MMU 模块 ❌

| 问题 | 原因 | 影响模块 |
|------|------|----------|
| **TLB Miss 无法触发** | 16KB 地址空间太小，无需页表遍历 | [ct_mmu_*](file:///home/c910/wangyahao/openc910/C910_RTL_FACTORY/gen_rtl/mmu/rtl/ct_mmu_arb.v) |
| **页故障异常无法测试** | 所有地址都在有效范围内 | `ct_exception_*` |
| **虚拟地址转换逻辑** | 物理地址直接访问，无地址转换 | `ct_tlb_*` |

**当前地址空间**：
```
0x00000000 - 0x00003FFF  ✓ (直接映射，无 TLB 查询)
0x80000000+              ❌ (需要 TLB 转换，但未使用)
```

**改进建议**：
- 使用大地址范围（如 0x80000000+）触发 TLB miss
- 配置页表并触发页故障异常
- 测试虚拟地址到物理地址的转换

---

### 3. 分支预测模块 ⚠️

| 问题 | 原因 | 影响模块 |
|------|------|----------|
| **BHT (Branch History Table)** | 小范围代码分支模式单一 | `ct_bpu_bht` |
| **BTB (Branch Target Buffer)** | 跳转目标固定，BTB 命中率过高 | `ct_bpu_btb` |
| **RAS (Return Address Stack)** | 函数调用深度不足 | `ct_bpu_ras` |
| **预测错误恢复** |  predictable 分支多，预测错误少 | `ct_bpu_*` |

**改进建议**：
- 增加随机跳转指令（JAL/JALR）
- 使用间接跳转增加 BTB 压力
- 增加函数调用深度测试 RAS

---

### 4. 指令预取单元 ⚠️

| 问题 | 原因 | 影响模块 |
|------|------|----------|
| **预取失败场景** | 顺序执行，预取总是成功 | `ct_ifu_fetch` |
| **预取取消逻辑** | 无分支预测错误，预取无需取消 | `ct_ifu_fetch` |
| **预取深度测试** | 小代码量，预取队列不满 | `ct_ifu_fifo` |

**改进建议**：
- 增加频繁分支跳转触发预取取消
- 使用长延迟指令测试预取队列深度

---

### 5. LSU (Load/Store Unit) ⚠️

| 问题 | 原因 | 影响模块 |
|------|------|----------|
| **Store Buffer 满** | 数据访问少，Store Buffer 不溢出 | `ct_lsu_sbuf` |
| **Load Queue 冲突** | Load 指令数量有限 | `ct_lsu_lqueue` |
| **Cache 一致性** | 单核测试，无核间一致性场景 | `ct_lsu_coherency` |
| **非对齐访问** | 测试程序可能未覆盖 | `ct_lsu_misalign` |

**改进建议**：
- 增加大量 Load/Store 指令
- 测试非对齐内存访问
- 多核场景测试 Cache 一致性

---

### 6. 异常/中断控制器 ❌

| 问题 | 原因 | 影响模块 |
|------|------|----------|
| **外部中断** | 无外部中断信号触发 | `ct_int_ctrl` |
| **定时器中断** | 未配置或测试定时器 | `ct_timer_*` |
| **异常处理** | 无非法指令/地址错误触发 | `ct_exception_*` |
| **NMI (不可屏蔽中断)** | 无法触发 | `ct_nmi_ctrl` |

**改进建议**：
- 配置中断控制器并触发中断
- 故意触发异常（非法指令、地址错误）
- 测试中断嵌套和优先级

---

### 7. 流水线冒险处理 ⚠️

| 问题 | 原因 | 影响模块 |
|------|------|----------|
| **RAW 冒险** | 指令依赖性可能不足 | [ct_iu_*](file:///home/c910/wangyahao/openc910/C910_RTL_FACTORY/gen_rtl/iu/rtl/ct_iu_alu.v) |
| **WAW/WAR 冒险** | 寄存器重用模式单一 | `ct_iu_renamer` |
| **结构冒险** | 资源冲突场景少 | `ct_iu_scheduler` |

**改进建议**：
- 增加指令间依赖性（RAW）
- 使用相同目标寄存器制造 WAW/WAR
- 同时发射多条指令测试结构冒险

---

### 8. 多核一致性模块 ❌

| 问题 | 原因 | 影响模块 |
|------|------|----------|
| **Cache 一致性协议** | 单核测试，无核间通信 | `ct_ccn_*` |
| **内存屏障** | 无需同步，屏障指令未测试 | `ct_lsu_fence` |
| **原子操作** | 无多核竞争场景 | `ct_lsu_atomic` |

**改进建议**：
- 使用多核配置运行测试
- 测试原子指令（LR/SC、AMOSWAP 等）
- 验证内存屏障指令效果

---

## 覆盖率影响总结

| 模块类别 | 影响程度 | 主要原因 |
|----------|----------|----------|
| **ICache Refill** | 🔴 严重 | 64KB 指令无法触发 miss |
| **TLB/MMU** | 🔴 严重 | 地址空间太小 |
| **异常/中断** | 🔴 严重 | 无异常触发机制 |
| **多核一致性** | 🔴 严重 | 单核测试 |
| **分支预测** | 🟡 中等 | 分支模式单一 |
| **LSU** | 🟡 中等 | 数据访问有限 |
| **流水线冒险** | 🟡 中等 | 指令多样性不足 |
| **指令预取** | 🟢 轻微 | 基本功能可覆盖 |

---

## 改进方案建议

### 方案 1: 动态指令生成 (推荐)
```python
# 使用 FORCE-RISCV 动态生成指令流
# 参考：target/smc_icache_refill_test.py

class MainSequence(Sequence):
    def main(self):
        # 大地址范围跳转触发 ICache miss
        for _ in range(500):
            self.genInstruction("JAL##RISCV", {'rd': 1, 'imm': random_offset})
        
        # CSR 指令触发 ICache invalidation
        self.genInstruction("CSRRW#register#RISCV", {'csr': 0x7C2})
```

### 方案 2: 扩大地址空间
```python
# 使用 0x80000000+ 地址触发 TLB miss
base_addr = 0x80000000
self.genInstruction("LW##RISCV", {'rs1': reg, 'imm': large_offset})
```

### 方案 3: 增加异常触发
```python
# 故意触发异常
self.genInstruction("illegal_instruction")  # 非法指令
self.genInstruction("LW##RISCV", {'rs1': reg, 'imm': invalid_addr})  # 地址错误
```

### 方案 4: 多核测试配置
```bash
# 修改仿真配置启用多核
make -f makefileFRV run CORE_NUM=2
```

---

## 参考文档

| 文档 | 用途 |
|------|------|
| [agentDoc/C910ISA_Agent_Friendly.md](file:///home/c910/wangyahao/AgenticISG/agentDoc/C910ISA_Agent_Friendly.md) | 指令集参考 |
| [agentDoc/condition_coverage.md](file:///home/c910/wangyahao/AgenticISG/agentDoc/condition_coverage.md) | 覆盖率规则 |
| [agentDoc/ISG_Script/*.py](file:///home/c910/wangyahao/AgenticISG/agentDoc/ISG_Script/viq_dlb_test.py) | ISG 脚本模板 |

---

## 给 Agent 的建议

当分析覆盖率不足问题时，请考虑：

1. **检查模块类型**：是否为上述难以覆盖的模块？
2. **分析触发条件**：是否需要特殊指令序列或地址范围？


---

*文档生成时间：2026-03-21*  
*适用框架：AgenticISG + FORCE-RISCV*