# Manual Generator Benchmark

这个脚本用于线性跑完 `manual_trace_seed/cases` 下的手工 case，评测小模型在 generator 角色下生成 FORCE-RISCV ISG 脚本、编译修复、gem5 预筛选的能力。

## 运行

默认模型使用当前 `opencode.jsonc` 中的本地 Qwen 配置：

```bash
scripts/run-manual-generator-benchmark.sh
```

常用调试方式：

```bash
# 只跑前三个 case
scripts/run-manual-generator-benchmark.sh --max 3

# 只跑某个 case
scripts/run-manual-generator-benchmark.sh case_004_floating_data_constraint

# 接到已启动的 opencode serve，减少每个 case 的冷启动
opencode serve --port 4096 --hostname 127.0.0.1
scripts/run-manual-generator-benchmark.sh --attach http://localhost:4096

# 切换模型
scripts/run-manual-generator-benchmark.sh --model localmodel/qwopus3.5-9b@q8_0
```

## 输出

每次运行会创建：

```text
workspace/manual_generator_runs/<run_id>/
  run_config.env
  summary.csv
  case_*/
    test_plan.md
    manifest.yaml
    prompt.md
    opencode.json.log
    status.json
    generated_files.txt
    workspace_new_files.txt
```

生成脚本会要求模型写入：

```text
workspace/isgScripts/manual_benchmark/<run_id>/<case_name>/
```

`summary.csv` 是批跑总览；每个 case 的 `status.json` 记录退出码、耗时、产物数量、日志路径和输出目录。如果 OpenCode 退出码为 0 但指定输出目录没有任何文件，runner 会标记为 `no_artifact`；如果有脚本但没有 `.ELF` 编译产物或 gem5 `output.log`/`manifest.json`/`m5out/stats.txt` 证据，会标记为 `incomplete_validation`，避免把“只写了脚本但未完成验证”的情况算作成功。`manifest.yaml` 只复制到结果目录用于人工评测，脚本提示词明确禁止 generator 读取或引用 manifest/unit_catalog 标注元数据。

## 可调环境变量

- `OPENCODE_GENERATOR_MODEL`: 默认 `localmodel/qwen3.5-9b@q8_0`
- `OPENCODE_GENERATOR_AGENT`: 默认 `generator`
- `OPENCODE_ATTACH`: 等同 `--attach`
- `OPENCODE_CONFIG`: 默认使用项目根目录 `opencode.jsonc`
- `MANUAL_RUN_ID`: 指定输出 run id
- `MANUAL_CASE_TIMEOUT`: 单 case 超时，例如 `45m`
- `MANUAL_LIVE_LOG=1`: 实时 tee OpenCode 输出
- `MANUAL_SKIP_PERMISSIONS=0`: 关闭 `--dangerously-skip-permissions`

## OpenCode 用法依据

脚本使用 OpenCode 官方文档中的非交互 CLI 入口 `opencode run`，并使用 `--agent`、`--model provider/model`、`--file`、`--format json`、`--attach` 等参数。模型 ID 对应配置中的自定义 provider/model 形式，例如 `localmodel/qwen3.5-9b@q8_0`。
