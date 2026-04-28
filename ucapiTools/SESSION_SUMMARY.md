# UCAPI Session Summary

这份文档总结了本轮对话中与 UCAPI 相关的实验结论、工具实现和调度接入情况，便于后续对话快速恢复上下文。

## 1. 总体结论

本轮工作的核心结论是：

- UCAPI 能稳定枚举完整模块集合，不是 `blocked_unresolved_rtl` 的根因
- 旧问题主要来自 `urg` 文本报告抽取不精确
- 更合适的路线是：直接从 UCAPI 提取 VP，再用本地 snapshot 批量刷新覆盖率

## 2. 模块与 instance 枚举

我们先验证了 UCAPI 是否能拿到整个设计的模块和实例。

结论：

- UCAPI 可以枚举完整 `definition`
- 也可以继续展开 `instance`
- `covdb_load` 后需要等待设计完全加载，否则 iterator 很容易段错误
- 在实验中，`sleep(1)` 能明显提升稳定性

相关实验工具：

- `covdb_list_modules.c`
- `covdb_list_instances.c`

使用策略：

- `first` 模式：每个 definition 只取一个 instance，适合给 AgenticISG 降负载
- `all` 模式：展开所有 instance，适合全量分析

## 3. handle / iterator 生命周期

这是本轮实验里很重要的一条经验：

- 从 iterator 中 `covdb_scan()` 得到的 `covdbHandle`，生命周期通常和 iterator 强相关
- 如果太早 `covdb_release_handle(iterator)`，后续继续使用 scan 出来的 handle 很容易失效甚至段错误

建议：

- 不必过早释放 iterator
- 尽量在同一作用域内完成 scan 后的处理
- 对 string property 不要假定可长期持有，必要时立即复制

## 4. metric 与 container 层级关系

我们对多个 metric 做了 probe，明确了 VP 应绑定的层级。

### 4.1 Line

结构：

- `qualified instance -> container(ALWAYS) -> block`

结论：

- VP 最适合绑定 `ALWAYS container`
- 对特别大的 `always` 再做切分

### 4.2 Condition

结构：

- `qualified instance -> root container -> expr container -> cross`

结论：

- VP 最适合绑定“表达式 container”
- 不要直接绑 `covdbCross`

### 4.3 Branch

结构：

- `qualified instance -> branch container -> cross`

结论：

- VP 最适合绑定顶层 `branch container`
- `cross` 只作为细节统计

### 4.4 Tgl

结构：

- `qualified instance -> port/signal container -> deeper container/sequence/value`

结论：

- 结构比 `line/cond/branch` 更碎
- 当前只做提取实验，暂不接调度器

### 4.5 Fsm

结构：

- `qualified instance -> FSM container -> states/transitions container`

结论：

- VP 最适合绑定顶层 FSM container

## 5. 各类 VP 的最终策略

本轮最终落了五个 UCAPI 提取器，统一输出 AgenticISG 可读 JSON：

- `covdb_extract_line_vp_design`
- `covdb_extract_condition_vp_design`
- `covdb_extract_branch_vp_design`
- `covdb_extract_fsm_vp_design`
- `covdb_extract_tgl_vp_design`

当前接入状态：

- 已接调度器：`line` / `cond` / `branch` / `fsm`
- 未接调度器：`tgl`

## 6. line VP 策略

`line` 路径的经验最完整。

策略：

- 以 `ALWAYS container` 为 VP
- 关键标识依赖 `line_range`
- string property 不稳定，不能依赖 `Name/FullName`
- 对超大 `always` 自动切分

切分规则：

- 单个子 VP 最多 20 个 block
- 相邻 block 行号 gap 大于 8 时断开

## 7. condition VP 策略

初版是每个 expr 一个 VP，后来发现某些模块同一行会展开很多位条件，太碎。

最终策略：

- 按 `line` 聚合
- 底层仍保留 expr 明细

输出保留：

- `expr`
- `expr_count`
- `exprs`
- `crosses`
- `covered/coverable/pct`

## 8. branch VP 策略

策略：

- 直接使用顶层 `branch container`

输出字段：

- `expr`
- `line`
- `crosses`
- `covered/coverable/pct`

结果：

- 没有明显重复问题
- 规模可接受
- 已接 `scheduler_v2`

## 9. fsm VP 策略

策略：

- 直接使用顶层 FSM container

输出字段：

- `name`
- `line`
- `children`
- `covered/coverable/pct`

结果：

- 数量不大
- 结构稳定
- 已接 `scheduler_v2`

## 10. tgl VP 策略

`tgl` 提取器已完成，但当前判断暂不接调度器。

原因：

- 全设计数量过大
- 大向量信号很多
- 某些 `width` 和 `coverable` 非常大

当前定位：

- 主要用于实验
- 是否纳入调度，后续再评估

## 11. scheduler_v2 的设计结论

旧 `scoreboard_scheduler` 的主要问题：

- VP 来源基于 `urg` 文本
- 覆盖率刷新偏向逐 VP HTTP 查询
- 对 `line` 尤其低效，还长期占用 UCAPI 服务

新的方向是：

- 保留 scheduler 外壳思想
- 新建 `scheduler_v2`
- 去掉过时的 VP 来源和覆盖率刷新方式
- 使用本地 UCAPI snapshot 批量刷新

### 当前 scheduler_v2 支持

命令：

- `init`
- `select`
- `manual-select`
- `launch`
- `complete`
- `fail`
- `recover`

支持的 VP kind：

- `line`
- `cond`
- `branch`
- `fsm`

不支持：

- `tgl`

刷新方式：

- `line/cond/branch/fsm` 都是本地 snapshot 批量更新
- 不再逐 VP HTTP 调 UCAPI

### 多 VP 列表支持

`init` 已支持重复 `--vp-list`，可以同时加载：

- `line_vp_list.json`
- `condition_vp_list.json`
- `branch_vp_list.json`
- `fsm_vp_list.json`

## 12. UCAPI 工具路径与仓库集成

后来我们把 UCAPI 提取器迁到了：

- `AgenticISG/ucapiTools/`

并把路径逻辑统一收口到：

- `src/utils/project_paths.py`

新增函数：

- `get_ucapi_tools_root()`
- `get_ucapi_snapshot_tool_path(kind)`

默认工具目录：

- `AgenticISG/ucapiTools`

支持环境变量覆盖：

- `AGENTICISG_UCAPI_TOOLS_ROOT`
- `AGENTICISG_LINE_VP_TOOL`
- `AGENTICISG_COND_VP_TOOL`
- `AGENTICISG_BRANCH_VP_TOOL`
- `AGENTICISG_FSM_VP_TOOL`

## 13. 本地 UCAPI 服务

现在有两条 UCAPI 使用路线。

### 13.1 本地 snapshot 路线

给 `scheduler_v2` 使用，是当前主路径。

方式：

- 直接调用 `ucapiTools/*.exe`

### 13.2 HTTP 服务路线

给旧流程和部分在线查询工具使用。

方式：

- 通过 `IntericSim/coverage_server.py`
- 提供 `http://localhost:5000/api/v1/query`

为此新增：

- `scripts/start_local_ucapi_service.py`

用于从 AgenticISG 侧启动本地 UCAPI HTTP 服务。

## 14. 当前推荐使用方式

当前推荐主流程：

1. 用 `ucapiTools` 生成：
   - `line_vp_list.json`
   - `condition_vp_list.json`
   - `branch_vp_list.json`
   - `fsm_vp_list.json`
2. 用 `scheduler_v2` 初始化：

```bash
python -m src.utils.scheduler_v2 \
  --output-dir coverageDB/regression/long_agent_scoreboard \
  init \
  --vp-list line_vp_list.json \
  --vp-list condition_vp_list.json \
  --vp-list branch_vp_list.json \
  --vp-list fsm_vp_list.json \
  --baseline-vdb coverageDB/template/BASELINE.vdb
```

3. 后续使用：
   - `manual-select`
   - `launch`
   - `complete`

## 15. 必须记住的关键经验

最关键的几条：

- UCAPI 本身能拿到模块、实例、VP，不是能力瓶颈
- 早释放 iterator 很危险
- `line` 适合 `ALWAYS container`
- `condition` 适合 expr container，后来按 line 聚合
- `branch` 适合顶层 branch container
- `fsm` 适合顶层 FSM container
- `tgl` 目前太碎，先不进调度器
- `scheduler_v2` 已经是新的主路径
- 旧 `scoreboard_scheduler` 仅做兼容保留
