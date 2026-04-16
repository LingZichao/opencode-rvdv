# FORCE-RISCV Memory Operations Guide

本文档汇总 FORCE-RISCV 中内存操作相关的 API 用法、参数说明和常见模式。

## 核心 API 速查

| API | 用途 | 返回值 |
|-----|------|--------|
| `genVA()` | 生成有效虚拟地址 | 虚拟地址 (int) |
| `genPA()` | 生成有效物理地址 | 物理地址 (int) |
| `genVAforPA()` | 为物理地址创建虚拟映射 | 虚拟地址 (int) |
| `initializeMemory()` | 初始化内存内容 | None |
| LSTarget 参数 | 指定 load/store 目标地址 | (genInstruction 参数) |

---

## 1. genVA - 生成虚拟地址

```python
addr = self.genVA(Size=8, Align=8, Type="D")
```

**参数：**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `Size` | int | 1 | 内存块大小（字节） |
| `Align` | int | 1 | 对齐要求，必须为 2 的幂 |
| `Type` | str | - | `"D"` (数据) 或 `"I"` (指令) |
| `Bank` | str/int | `"Default"` | 内存 bank |
| `Range` | str | - | 地址范围，如 `"0x1000-0x2000"` 或 `"0x1000-0x1FFF,0x8000-0x9FFF"` |
| `FlatMap` | int | 0 | 1 = VA 直接映射 PA |
| `ForceAlias` | int | 0 | 1 = 强制创建别名映射 |
| `CanAlias` | int | 1 | 0 = 禁止后续页别名 |
| `Shared` | int | 0 | 1 = 跨线程共享 |

**常见用法：**

```python
# 基本用法 - 8字节对齐的数据地址
addr = self.genVA(Size=8, Align=8, Type="D")

# 指定地址范围
addr = self.genVA(Size=8, Align=8, Type="D", Range="0x1F00-0x1FFF")

# 多段地址范围
addr = self.genVA(Size=8, Align=8, Type="D", Range="0x1000-0x1FFF,0x88000-0x89800")

# 大块地址空间（用于后续 ConstraintSet 复用）
init_size = 256
addr = self.genVA(Size=init_size, Align=init_size, Type="D")
```

> 参考示例: `example/APIs/api_genVA_01_force.py`, `example/APIs/api_genVA_02_force.py`

---

## 2. genPA / genVAforPA - 物理地址与映射

当需要精确控制物理地址或创建多个虚拟地址指向同一物理地址（别名）时使用。

```python
# 生成物理地址
pa = self.genPA(Size=8, Align=8, Type="D")

# 为物理地址创建虚拟映射
va = self.genVAforPA(PA=pa, Size=8, Type="D")
```

**genPA 额外参数：**

| 参数 | 说明 |
|------|------|
| `MemAttrArch` | 架构级内存属性，如 `"AMOSwap,CoherentL1,ReadIdempotent"` |
| `MemAttrImpl` | 实现级内存属性，如 `"Debug"`, `"CLINT"`, `"PLIC"`, `"GPIO"` |

**genVAforPA 额外参数：**

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `PA` | (必填) | 目标物理地址 |
| `ForceNewAddr` | 0 | 1 = 创建新映射而非复用已有映射 |

**别名模式 - 多个 VA 映射同一 PA：**

```python
pa = self.genPA(Size=8, Align=8, Type="D", CanAlias=1)
va_1 = self.genVAforPA(PA=pa, Size=8, Type="D")
va_2 = self.genVAforPA(PA=pa, Size=8, Type="D", ForceNewAddr=1)

self.genInstruction("SD##RISCV", {"LSTarget": va_1})  # store 通过 va_1
self.genInstruction("LD##RISCV", {"LSTarget": va_2})  # load 通过 va_2（同一物理位置）
```

> 参考示例: `example/APIs/api_genPA_01_force.py`, `example/APIs/api_genVAforPA_alias_force.py`

---

## 3. initializeMemory - 初始化内存

在生成 load 指令前预填充内存内容，确保读取到预期值。

```python
self.initializeMemory(
    addr=va,         # 地址
    bank=0,          # 内存 bank
    size=8,          # 字节数（最大 8）
    data=0x12345678, # 初始值
    is_instr=False,  # False = 数据, True = 指令
    is_virtual=True, # True = addr 是虚拟地址
)
```

**批量初始化模式（如栈空间）：**

```python
from RandomUtils import RandomUtils

stack_size = 0x800
stack_addr = self.genVA(Size=stack_size, Align=8, Type="D")

for offset in range(0, stack_size, 8):
    self.initializeMemory(
        addr=(stack_addr + offset),
        bank=0,
        size=8,
        data=RandomUtils.random64(),
        is_instr=False,
        is_virtual=True,
    )
```

> 参考示例: `example/exception_handlers/stack_force.py`

---

## 4. LSTarget - Load/Store 目标地址

通过 `genInstruction` 的 `LSTarget` 参数指定 load/store 的目标地址。

```python
# 直接指定地址
self.genInstruction("LD##RISCV", {"LSTarget": addr})

# 配合 NoPreamble（不生成地址计算前导指令，要求 base 寄存器已就绪）
self.genInstruction("LD##RISCV", {"LSTarget": addr, "NoPreamble": 1})

# 配合 UsePreamble（显式生成前导指令设置 base 寄存器）
self.genInstruction("SD##RISCV", {"LSTarget": addr, "UsePreamble": 1})

# 配合 NoSkip（地址无法求解时报错而非跳过）
self.genInstruction("LD##RISCV", {"LSTarget": addr, "NoSkip": 1})
```

**使用 ConstraintSet 指定地址范围：**

```python
from Constraint import ConstraintSet

init_size = 256
init_addr = self.genVA(Size=init_size, Align=init_size, Type="D")
addr_constr = ConstraintSet(init_addr, init_addr + init_size - 1)

# LSTarget 接受 ConstraintSet 的字符串形式
self.genInstruction("LD##RISCV", {"LSTarget": str(addr_constr), "NoSkip": 1})
```

> 参考示例: `example/address_solving/address_solving_address_reuse_force.py`

---

## 5. Load/Store 指令列表

### 标准指令

| 指令 | 宽度 | 说明 |
|------|------|------|
| `LB##RISCV` / `SB##RISCV` | 8-bit | 字节 |
| `LH##RISCV` / `SH##RISCV` | 16-bit | 半字 |
| `LW##RISCV` / `SW##RISCV` | 32-bit | 字 |
| `LD##RISCV` / `SD##RISCV` | 64-bit | 双字 (RV64) |
| `LBU##RISCV` | 8-bit | 字节无符号扩展 |
| `LHU##RISCV` | 16-bit | 半字无符号扩展 |
| `LWU##RISCV` | 32-bit | 字无符号扩展 (RV64) |

### 压缩指令 (RVC)

| 指令 | 说明 |
|------|------|
| `C.LW##RISCV` / `C.SW##RISCV` | 压缩字 load/store |
| `C.LD##RISCV` / `C.SD##RISCV` | 压缩双字 load/store |
| `C.LWSP##RISCV` / `C.SWSP##RISCV` | SP 为基址的字 load/store |
| `C.LDSP##RISCV` / `C.SDSP##RISCV` | SP 为基址的双字 load/store |
| `C.FLD##RISCV` / `C.FSD##RISCV` | 浮点双字 load/store |
| `C.FLDSP##RISCV` / `C.FSDSP##RISCV` | SP 为基址的浮点 load/store |

---

## 6. 常见模式速查

### 模式 1：简单 load/store

```python
addr = self.genVA(Size=8, Align=8, Type="D")
self.genInstruction("LD##RISCV", {"LSTarget": addr})
```

### 模式 2：先写后读（store-load 序列）

```python
addr = self.genVA(Size=8, Align=8, Type="D")
self.genInstruction("SD##RISCV", {"LSTarget": addr})
self.genInstruction("LD##RISCV", {"LSTarget": addr})
```

### 模式 3：预初始化内存后读取

```python
addr = self.genVA(Size=8, Align=8, Type="D")
self.initializeMemory(addr=addr, bank=0, size=8, data=0xDEADBEEF, is_instr=False, is_virtual=True)
self.genInstruction("LD##RISCV", {"LSTarget": addr})
```

### 模式 4：地址复用（同一区域多次访问）

```python
from Constraint import ConstraintSet

region_size = 256
region_addr = self.genVA(Size=region_size, Align=region_size, Type="D")
region = ConstraintSet(region_addr, region_addr + region_size - 1)

for _ in range(100):
    instr = self.choice(("LD##RISCV", "SD##RISCV"))
    self.genInstruction(instr, {"LSTarget": str(region), "NoSkip": 1})
```

### 模式 5：物理地址别名（cache coherence 测试）

```python
pa = self.genPA(Size=8, Align=8, Type="D", CanAlias=1)
va_a = self.genVAforPA(PA=pa, Size=8, Type="D")
va_b = self.genVAforPA(PA=pa, Size=8, Type="D", ForceNewAddr=1)

self.genInstruction("SD##RISCV", {"LSTarget": va_a})
self.genInstruction("LD##RISCV", {"LSTarget": va_b})
```

---

## 对齐要求

Load/store 指令的地址对齐必须匹配访问宽度：

| 访问宽度 | 最小 Align |
|----------|-----------|
| 1 字节 (LB/SB) | 1 |
| 2 字节 (LH/SH) | 2 |
| 4 字节 (LW/SW) | 4 |
| 8 字节 (LD/SD) | 8 |

如需测试非对齐访问，可手动偏移地址：

```python
target_addr = self.genVA(Align=0x1000) | 0xFFE  # 故意非对齐
self.genInstruction("C.LD##RISCV", {"LSTarget": target_addr})
```

> 参考示例: `example/address_solving/RVC_misaligned_force.py`
