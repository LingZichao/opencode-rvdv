# OpenCode-RVDV 项目规则

## 项目概述

基于OpenCode原生的RISC-V CPU覆盖率验证框架。

## 核心命令

- `/verify <file> <lines>` - 启动完整验证流程
- `/analyze <file> <lines>` - 仅分析覆盖率
- `/generate <plan>` - 仅生成ISG脚本
- `/status` - 查看任务状态

## 工作流程

1. Coordinator接收任务
2. Analyzer分析BASELINE覆盖率
3. Recognizer识别微架构场景
4. Generator生成ISG脚本
5. 执行仿真并获取覆盖率
6. 迭代优化直至目标达成

## 目录结构

- `workspace/agentDoc/` - Agent参考文档
  - `C910ISA_Agent_Friendly.md` - C910 ISA参考文档
  - `condition_coverage.md` - 条件覆盖率规则
  - `ISG_Script/` - ISG脚本示例
  - `forceRV/` - ForceRISCV指令定义和文档
- `coverageDB/` - 覆盖率数据存储
  - `template/BASELINE.vdb/` - 基准覆盖率数据库
  - `template/sim/` - 仿真模板（makefileFRV）
  - `tasks/<task_name>/` - 任务运行目录
- `src/scripts/` - Python工具实现
- `src/tools/` - TypeScript工具包装
- `src/prompts/` - Agent系统提示词

## 注意事项

- 每个任务独立目录: coverageDB/tasks/<task_name>/
- ISG脚本存放: workspace/isgScripts/<task_name>/
- 专注BASELINE未覆盖的VP
- C910扩展指令集不可用，仅考虑RV64GC
- ISG方法论：间接驱动与概率碰撞，用数量弥补精度