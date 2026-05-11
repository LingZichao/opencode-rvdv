---
description: 采样FSDB并收集指令运行数据
agent: instracer
subtask: true
---

# 指令运行轨迹采样

请根据以下需求编写 wavekit trace 脚本，运行 FSDB 采样，并汇报指令运行证据。

采样需求: $ARGUMENTS

## 输入要求

请在需求中提供或明确要求自动发现以下信息：

1. FSDB路径
2. globalClock
3. scope
4. 目标事件/指令
5. identity anchors
6. 可选输出路径

## 执行步骤

1. 加载 `wavekit` 和 `inst-sampling` skills
2. 阅读必要的 RTL/微架构上下文
3. 在 `workspace/instTraces/<task_name>/trace.py` 编写 trace 脚本
4. 运行 trace 脚本
5. 汇报匹配路径、时间点、捕获信号和缺失/重复匹配
