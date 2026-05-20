---
description: 生成ISG脚本并完成gem5预筛选（不执行RTL/VCS仿真）
agent: generator
subtask: true
---

# ISG脚本生成与预筛选

请根据以下测试计划生成ISG脚本，完成 Columbus FORCE-RISCV 编译，并通过 screener 子代理执行 gem5 预筛选。

测试计划: $ARGUMENTS

## 执行步骤

1. 理解测试计划要求
2. 生成唯一的ISG脚本
3. 使用 `isg-compile` skill 编译并确认ELF
4. 委托 `screener` 运行gem5预筛选并检查artifact证据
5. 报告脚本路径、ELF路径、gem5 artifact路径和关键证据
