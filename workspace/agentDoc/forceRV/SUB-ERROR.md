# SUB-ERROR — ISG 脚本开发常见错误与排查经验

> 文档记录 FORCE-RISCV ISG 开发过程中踩过的坑、报错信息排查方法及解决方案。按错误类型分类。

---

## 1. API 使用错误

### 1.1 `initializeMemory` 参数不匹配

**错误信息**：
```
TypeError: initializeMemory() missing 2 required positional arguments: 'is_instr' and 'is_virtual'
```

**原因**：`initializeMemory` 的函数签名是：
```python
initializeMemory(addr, bank, size, data, is_instr, is_virtual)
```

其中：
- `addr`、`bank`、`size`、`data` 为 **位置参数**（不支持 kwargs）
- `bank` 必须为 **int**（如 `0`），不可传字符串 `"Default"`
- `is_instr` / `is_virtual` 为 bool

**正确用法**：
```python
self.initializeMemory(base_addr + 0, 0, 8, 0xA5A5A5A5A5A5A5A5, False, True)
```

**参考**：`example/exception_handlers/stack_force.py:42`

---

## 2. ISS 模拟错误

### 2.1 `M5EXIT` 在 ISS 中触发非法指令异常导致内存写入 crash

**错误信息**：
```
[fail]Failed to write memory 0xfffffffffffffff8. No matched memory bytes object, please initialize first
```

**根因**：
1. `M5EXIT`（编码 `0x4200007b`）不是标准 RISC-V 指令，FORCE-RISCV 内置 ISS（HANDCAR）视其为非法指令
2. ISS 触发 Illegal Instruction 异常（`Excpt ID 0x2`），跳转到 `mtvec`（通常为 `0x20000`）
3. M-mode 异常处理程序位于 `mtvec` 地址处，使用 **`x28`（t2）作为临时栈帧指针**（非 `x2/sp`）
4. `x28` 初始值为 `0`，handler 执行 `addi x28, x28, -8` → x28 = `0xfffffffffffffff8`（回绕）
5. 随后 `sd x1, 0(x28)` 试图写入该地址，但因未分配内存而 crash

**排查方法**：逐行阅读 `sim.log` 跟踪 ISS 执行轨迹，发现：
```
Cpu 0 PC(VA) 0x0000000000020200 op: 0x00000000ff8e0e13 : addi    x28, x28, -8
Cpu 0 Reg R x28 val 0x0000000000000000 mask 0xffffffffffffffff
Cpu 0 Reg W x28 val 0xfffffffffffffff8 mask 0xffffffffffffffff
Cpu 0 868 ----
Cpu 0 PC(VA) 0x0000000000020204 op: 0x00000000001e3023 : sd      x1, 0(x28)
```

可见 handler 用 x28 而非 x2/sp 作为 scratch 指针。

**解决方案**（三步）：
1. 用 `genVA` 分配一块 scratch 内存区域
2. 用 `initializeMemory` 预填充该区域
3. 用 `writeRegister("x28", scratch_top)` 直接设置 x28 初始值

```python
scratch_size = 0x200
scratch_base = self.genVA(Size=scratch_size, Align=8, Type="D")
for offs in range(0, scratch_size, 8):
    self.initializeMemory(scratch_base + offs, 0, 8, 0xDEADBEEFDEADBEEF, False, True)
self.writeRegister("x28", scratch_base + scratch_size)
```

**注意**：此问题仅在 FORCE-RISCV ISS 模拟时出现。实际 gem5 执行时 `M5EXIT` 被正确识别，不会触发非法指令异常。编译生成的 ELF 在 `isg_compiler` 返回 `failed` 前已完整写入，gem5 预筛选可正常运行。

---

### 2.2 嵌套异常（exception-in-exception）

**错误信息**：
```
[fail]{GenExceptionAgent::HandleException} unsupported exception-in-exception case.
[StoreAmoAddrMisaligned exception] taken to M from U, address 0x0=>[?]0x?,
preferred return address 0x0
```

**原因**：FORCE-RISCV ISS 不支持嵌套异常。当一个异常正在处理过程中（例如 LoadAddrMisaligned），CPU 又触发了另一个异常（例如 StoreAmoAddrMisaligned），ISS 无法处理这种场景。

**触发场景**：脚本中连续的非对齐访存指令过多，导致 ISS 在一个异常 handler 返回前遭遇第二次异常。

**缓解方法**：
- 减少非对齐访存的密度，在每对非对齐访存之间插入对齐访存或 ALU 指令作为缓冲
- 或将非对齐访存量控制在刚好满足最低要求（≥8），避免极端密集触发

**注意**：此问题仅限 FORCE-RISCV ISS 模拟阶段，不影响 ELF 生成和 gem5 执行。

---

## 3. 编译状态与 ELF 分离

### 3.1 `isg_compiler` 返回 `failed` 但 ELF 已生成

**错误信息**：无特定错误 — `isg_compiler` JSON 中 `"status": "failed"` 但 `"elf_path"` 不为 null。

**原因**：FORCE-RISCV 前端执行分两步：
1. **指令生成 + ELF 写入**（此步成功）
2. **ISS 模拟**（此步可能失败）

步骤 2 的 ISS 错误（如 2.1 或 2.2）会导致整体退出码非零，但 ELF 已在步骤 1 完成时写入磁盘。

**验证方法**：
- 确认 `.ELF` 和 `.S` 文件存在且非空
- 用 gem5 预筛选直接加载该 ELF，验证能否正常执行到 M5EXIT

```bash
python3 .opencode/skills/gem5-prescreen/scripts/gem5_prescreener.py run \
  --script-path <path>.Default.ELF \
  --artifact-path <output_dir>/m5out
```

**注意事项**：若 ISS 在步骤 1 完成前崩溃（如语法错误、Python 异常），则 ELF 可能不完整。此情况通常伴随明显的 Python traceback。

---

## 5. 分支与控制流

### 5.1 `CondTaken` + `BRTarget` 约束冲突

**错误信息**：
```
[fail]{FullsizeConditionalBranchOperandConstraint::SetConditionalBranchTaken}
not resolved condition taken constraint:1
[FAIL]{unresolved-condition-taken-constraint} in file './src/OperandConstraintRISCV.cc'
```

**原因**：`CondTaken="1"`（强制分支跳转）与 `BRTarget=addr`（指定目标地址）同时使用时，FORCE 约束求解器无法找到同时满足两个约束的偏移量——因为分支偏移编码同时决定了是否跳转和跳到哪里，两者不可独立指定。

**正确做法**：二者只能选其一：
- 用 `CondTaken` 控制跳转方向，接受框架随机生成的目标地址
- 或用 `BRTarget` 指定目标地址，不使用 `CondTaken`（分支方向由寄存器值决定）

```python
# 方式 A：CondTaken 控制方向，目标由框架决定
self.genInstruction("BEQ##RISCV", {"rs1": 1, "rs2": 2, "CondTaken": "1", "NoPreamble": 1})

# 方式 B：BRTarget 固定目标，方向由寄存器值决定
self.genInstruction("BEQ##RISCV", {"rs1": 1, "rs2": 2, "BRTarget": target_addr, "NoPreamble": 1})
```

**注意**：`BRTarget`（大写 T）接受具体地址值；`BRarget`（小写 g）接受地址范围字符串如 `"0x1000-0x2000"`。两者用法不同，但都与 `CondTaken` 冲突。

**验证**：在 case_002 中尝试 `CondTaken="1"` + `BRTarget=pc+16` 时触发此错误，放弃 `BRTarget` 后编译通过。

---

### 5.2 `CondTaken="0"` 在某些分支类型上无法解析

**错误信息**：
```
[fail]{FullsizeConditionalBranchOperandConstraint::SetConditionalBranchTaken}
not resolved condition taken constraint:0
```

**原因**：与 5.1 类似。在某些分支类型（BLTU、BGEU 等）上，FORCE 后端在生成分支偏移量时可能预设了跳转方向，`CondTaken="0"` 与之冲突。框架内部的偏移量生成策略可能与 `CondTaken` 约束独立进行，导致时序冲突。

**触发场景**：对 BLTU、BGEU 等 unsigned 分支使用 `CondTaken="0"` 时较易触发，对 BEQ/BNE 使用 `CondTaken` 则较少出现。

**解决方案**：彻底放弃 `CondTaken` 参数，完全依靠寄存器值驱动分支方向：

| 分支类型 | Taken 条件 | Not-Taken 条件 |
|---------|-----------|---------------|
| BEQ | rs1 == rs2 | rs1 != rs2 |
| BNE | rs1 != rs2 | rs1 == rs2 |
| BLT | rs1 < rs2 (signed) | rs1 >= rs2 |
| BGE | rs1 >= rs2 | rs1 < rs2 |
| BLTU | rs1 < rs2 (unsigned) | rs1 >= rs2 |
| BGEU | rs1 >= rs2 | rs1 < rs2 |

```python
# 正确：通过寄存器值驱动，不用 CondTaken
self.genInstruction("ADDI##RISCV", {"rd": 1, "rs1": 0, "simm12": 10})
self.genInstruction("ADDI##RISCV", {"rd": 2, "rs1": 0, "simm12": 10})
self.genInstruction("BEQ##RISCV", {"rs1": 1, "rs2": 2})  # TAKEN (10==10)
```

---

### 5.3 Taken 条件分支的目标偏移不可控导致 gem5 无限循环

**现象**：仿真在 gem5 中跑满 `--maxinsts`（如 1000 万条）仍未到达 M5EXIT，输出：
```
Exiting @ tick ... because a thread reached the max instruction count
```

**根因**：taken 条件分支（因寄存器值满足条件而跳转）的目标地址由 FORCE 框架随机生成。若生成的偏移将 PC 指向 boot/preamble 代码区（包含 JALR/JAL 的循环），则执行陷入无限循环。

**特征**：stats.txt 中 `DirectUncond` 的值接近 `simInsts` 总量（如 1000 万中有 999 万是 DirectUncond），说明执行流进入了一个以无条件跳转为主的循环。

**缓解方法**：
1. **最小化 taken 分支数量**：仅保留刚好满足需求（≥2）的 taken 分支，其余全部设为 not-taken
2. **NoPreamble=1 + PC 算术**：对所有指令使用 `NoPreamble=1`，用 `getPEstate("PC")` + 固定偏移量计算目标地址，将 EXIT 代码放在生成代码的最末尾
3. **Accept 不可控性**：如果循环出现，重新编译（FORCE 会生成不同的随机偏移），或调整指令布局改变取指地址分布

**典型布局（已验证可通过）**：
```
预热区 → 条件分支 → JAL/JALR → EXIT(末尾)
```
EXIT 在生成代码最末尾，taken 分支跳转到 boot 区时即使循环，也不会跳过 EXIT。

**验证**：case_002 中 v4/v5 因 2 条 JAL（随机偏移）形成循环跑满 1000 万条；v9 去掉循环 JAL、改用 `BRTarget` 固定目标后，仅 311 条指令就到达 M5EXIT。

---

## 6. 指令名称错误

### 6.1 RV64I 指令需要 `form` 后缀

**错误信息**：
```
[fail]Instruction with ID "SLLI##RISCV" not found.
[FAIL]{instruction-look-up-by-id-fail} in file '../base/src/InstructionSet.cc' line 602
```

**原因**：RV64I 的部分指令（SLLI、SRLI、SRAI 等）在 XML 定义中有独立的 `form="RV64I"`，必须使用带 form 后缀的全名。而 RV32I 同名指令使用 `##RISCV` 后缀。

**正确名称对照**：

| 指令 | RV32 (通用) | RV64 |
|------|-----------|------|
| SLLI | `SLLI##RISCV` | `SLLI#RV64I#RISCV` |
| SRLI | `SRLI##RISCV` | `SRLI#RV64I#RISCV` |
| SRAI | `SRAI##RISCV` | `SRAI#RV64I#RISCV` |
| ADDI | `ADDI##RISCV` | `ADDI##RISCV`（通用） |
| ADD  | `ADD##RISCV`  | `ADD##RISCV`（通用） |

**检查方法**：查看对应 XML 文件中的 `form` 属性：
```xml
<!-- g_instructions_rv64.xml -->
<I name="SLLI" form="RV64I" isa="RISCV" ... />  <!-- → SLLI#RV64I#RISCV -->
```
```xml
<!-- g_instructions.xml -->
<I name="SLLI" form="RV32I" isa="RISCV" ... />   <!-- → SLLI##RISCV (RV32) -->
```

**注意事项**：
- 配置 `riscv_rv64_c910.config` 同时加载 `g_instructions.xml`（RV32I）和 `g_instructions_rv64.xml`（RV64I）
- 通用指令（ADDI、ADD、XOR、BEQ 等）在 RV32I 定义，使用 `##RISCV` 后缀
- RV64 特有指令（ADDW、ADDIW、SLLIW 等）和带 form 的指令使用 `#RV64I#RISCV` 后缀

---

## 7. gem5 模型特定行为

### 7.1 C910 BP 将 JALR(rd=x0) 统计为 Return 而非 IndirectUncond

**现象**：stats.txt 中 JALR 指令的统计位置与预期不符：
```
# 期望：IndirectUncond 为 2（两条 JALR rd=x0）
# 实际：IndirectUncond=0，Return=2
system.cpu.branchPred.committed_0::Return            2
system.cpu.branchPred.committed_0::IndirectUncond    0
```

**原因**：C910 gem5 模型（`fs_c910.py`）的分支预测器对 JALR 的分类规则与标准 gem5 不同。当 `rd=x0`（不保存返回地址）时，该模型将 JALR 归类为 `Return` 而非 `IndirectUncond`。

**影响**：
- 不意味着 JALR 未执行——`Return=2` 证实两条都已提交
- 解读证据时不应只看 `IndirectUncond`，应综合 `Return` + `IndirectUncond`
- JALR 的总提交数 = `committed_0::Return` + `committed_0::IndirectUncond`

**验证方法**：通过 `m5out/stats.txt` 中的 `committed_0::total` 确认总分支数，再结合 `DirectCond`（条件分支）、`DirectUncond`（JAL）、`Return`（JALR）的和来核对。

**适用模型**：仅 `fs_c910.py`（C910 full-system 模型）有此行为。标准 gem5 O3/TimingSimpleCPU 模型可能分类不同。

---

## 8. 文档缺失

### 8.1 `genMetaInstruction` 完全无文档

**现象**：在示例 `speculative_bnt_force.py` 中使用了 `genMetaInstruction`，但：
- INDEX.md 的 Core API 速查表中无此 API
- TOPIC_TAG.md 中无对应条目
- User Manual 全文检索无此函数

**已知信息**：
- 函数签名：`genMetaInstruction(instr_name, kwargs)`，参数与 `genInstruction` 相同
- 用途（推测）：在分支指令后生成 meta-block 指令，位于分支目标路径
- 仅出现在 BNT（分支未遂）场景的示例中

**注意**：在非 BNT 场景中尝试使用 `genMetaInstruction` 可能导致不可预期的行为，建议避免。如需在分支目标路径放置指令，建议使用条件分支的 fallthrough 路径（not-taken 时执行的下一条指令）。

---

## 9. 通用排查建议

1. **优先读 `sim.log`**：ISS 执行的全部轨迹（PC、指令编码、寄存器读写）记录在此，可精确定位 crash 点
2. **区分 ISS 错误与 gem5 错误**：ISS 错误只影响编译阶段，gem5 错误影响实际验证。以 gem5 结果为准
3. **最小复现法**：遇到 ISS 异常时，先构造一个仅包含目标指令 + M5EXIT 的最小脚本，确认基础路径通后再逐步增加复杂度
4. **关注寄存器使用**：FORCE-RISCV ISS 内部 handler 使用约定可能与 RISC-V ABI 不同（如 x28 代替 x2/sp），不可假设
