---
description: 采样FSDB并收集指令运行数据
agent: instracer
subtask: true
---

# 指令运行轨迹采样

请根据以下需求编写 APV YAML 采样脚本，运行 FSDB 采样，并汇报 `trace_lifecycle.txt` 中的指令运行证据。

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

1. 加载 `fsdb-sampling` skill
2. 阅读必要的 RTL/微架构上下文
3. 在 `workspace/apvTraces/<task_name>/trace.yaml` 编写 APV YAML
4. 对非平凡依赖图先执行 `--deps-only`
5. 运行 APV 并读取 `trace_lifecycle.txt`
6. 汇报匹配路径、时间点、捕获信号和缺失/重复匹配
