# OpenCode-RVDV 项目规则

## 项目概述

基于OpenCode原生的RISC-V CPU覆盖率验证框架。

## 核心命令

- `/verify <file> <lines>` - 启动完整验证流程
- `/collect <file> <lines>` - 仅收集/查询覆盖率
- `/generate <plan>` - 生成ISG脚本、编译并完成gem5预筛选
- `/status` - 查看任务状态

## 启动流程

1. 准备运行环境
   - 安装 `bun` 与 `opencode` 命令行工具
   - 参考 `.env.example` 配置 `.env`，至少补充 `PROJECT_ROOT`
   - 如需自定义服务地址，可额外设置 `OPENCODE_PORT`、`OPENCODE_HOSTNAME`

2. 初始化项目
   - 推荐执行：`./scripts/init-project.sh`
   - 或直接执行：`bun run src/init/init.ts`
   - 该步骤会生成运行时配置 `opencode.json`，并同步 `.opencode/` 下的 commands、prompts、skills

3. 启动依赖服务（可选但推荐）
   - 若需要覆盖率查询能力，请先启动 UCAPI 服务，并确保 `http://localhost:5000/health` 可访问
   - 若未启动 UCAPI，`./scripts/start-server.sh` 会给出告警，但 OpenCode server 仍可继续启动

4. 启动 OpenCode server
   - 推荐执行：`./scripts/start-server.sh`
   - 或通过脚本入口执行：`npm start`
   - 默认监听地址为 `0.0.0.0:4096`，可通过 `.env` 中的 `OPENCODE_PORT` / `OPENCODE_HOSTNAME` 覆盖

5. 验证启动结果
   - 启动成功后可通过浏览器访问 `http://localhost:4096`
   - 若命令行提示 `Project not initialized`，请先重新执行初始化步骤

## 工作流程

1. Coordinator接收任务
2. Coverage Collector收集并查询BASELINE覆盖率
3. Coordinator分析RTL与微架构上下文并制定测试计划
4. Generator生成ISG脚本、通过Columbus FORCE-RISCV编译，并委托gem5预筛选
5. 执行RTL/VCS仿真并获取覆盖率
6. 迭代优化直至目标达成

## 目录结构

- `workspace/agentDoc/` - Agent参考文档
  - 设计/ISA参考文档（如项目提供）- RISC-V或设计专用ISA说明
  - `condition_coverage.md` - 条件覆盖率规则
  - `ISG_Script/` - ISG脚本示例
  - `forceRV/` - ForceRISCV指令定义和文档
- `.opencode/skills/coverage/coverageDB/` - 覆盖率数据存储（随 coverage skill 迁移）
  - `template/BASELINE.vdb/` - 基准覆盖率数据库
  - `template/sim/` - 仿真模板（makefileFRV）
  - `tasks/<task_name>/` - 任务运行目录
- `src/skills/` - OpenCode技能包（按工具族组织，包含SKILL.md；覆盖率等能力可包含Python CLI脚本）
- `src/prompts/` - Agent系统提示词

## 注意事项

- 每个任务独立目录: .opencode/skills/coverage/coverageDB/tasks/<task_name>/
- ISG脚本存放: workspace/isgScripts/<task_name>/
- 专注BASELINE未覆盖的VP
- 默认仅考虑标准RISC-V，通常为RV64GC；设计专用扩展指令须由任务显式启用
- ISG方法论：间接驱动与概率碰撞，用数量弥补精度
- 本项目不再注入 TypeScript custom tools；覆盖率、编译、gem5预筛选与wavekit追踪能力通过 `.opencode/skills/*/SKILL.md` 暴露使用规约，必要时由受限 `bash` 调用对应本地CLI
