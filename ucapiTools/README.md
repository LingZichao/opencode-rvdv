# ucapiTools

`ucapiTools` 目录保存基于 Synopsys UCAPI 的 VP 提取器，用于从 `.vdb` 直接生成 AgenticISG 可读取的 VP JSON。

当前提供：

- `covdb_extract_line_vp_design.exe`
- `covdb_extract_condition_vp_design.exe`
- `covdb_extract_branch_vp_design.exe`
- `covdb_extract_fsm_vp_design.exe`
- `covdb_extract_tgl_vp_design.exe`

说明：

- `line`、`cond`、`branch`、`fsm` 已接入 `scheduler_v2`
- `tgl` 目前只做实验性提取，暂未接入调度器

## 1. libucapi 环境配置

这些工具运行前需要让系统能找到 `libucapi.so`。

常见配置方式：

```bash
export UCAPI_HOME=/home/yian/Synopsys/vcs/V-2023.12-SP2
export UCAPI_INC=$UCAPI_HOME/include
export UCAPI_LIB=$UCAPI_HOME/linux64/lib
export LD_LIBRARY_PATH=$UCAPI_LIB:$LD_LIBRARY_PATH
```

如果你本地已经有统一环境脚本，也可以直接 `source` 那个脚本，只要最终满足：

- 头文件路径可用：`$UCAPI_INC/covdb_user.h`
- 动态库路径可用：`$UCAPI_LIB/libucapi.so`
- `LD_LIBRARY_PATH` 包含 `$UCAPI_LIB`

快速检查：

```bash
ls $UCAPI_INC/covdb_user.h
ls $UCAPI_LIB/libucapi.so
```

## 2. 重新编译提取器

如果你修改了 `.c` 文件，可以在 `AgenticISG/ucapiTools` 下重新编译。

示例：

```bash
gcc -I"$UCAPI_INC" covdb_extract_line_vp_design.c \
  -L"$UCAPI_LIB" -Wl,-rpath,"$UCAPI_LIB" \
  -o covdb_extract_line_vp_design.exe -lucapi
```

其他几个工具同理：

```bash
gcc -I"$UCAPI_INC" covdb_extract_condition_vp_design.c \
  -L"$UCAPI_LIB" -Wl,-rpath,"$UCAPI_LIB" \
  -o covdb_extract_condition_vp_design.exe -lucapi

gcc -I"$UCAPI_INC" covdb_extract_branch_vp_design.c \
  -L"$UCAPI_LIB" -Wl,-rpath,"$UCAPI_LIB" \
  -o covdb_extract_branch_vp_design.exe -lucapi

gcc -I"$UCAPI_INC" covdb_extract_fsm_vp_design.c \
  -L"$UCAPI_LIB" -Wl,-rpath,"$UCAPI_LIB" \
  -o covdb_extract_fsm_vp_design.exe -lucapi

gcc -I"$UCAPI_INC" covdb_extract_tgl_vp_design.c \
  -L"$UCAPI_LIB" -Wl,-rpath,"$UCAPI_LIB" \
  -o covdb_extract_tgl_vp_design.exe -lucapi
```

## 3. 运行参数

所有提取器接口一致：

```bash
./<tool>.exe <vdb> <test> <first|all> [module-filter]
```

参数说明：

- `<vdb>`: 设计 coverage database，例如 `coverageDB/template/BASELINE.vdb`
- `<test>`: 对应 test 路径，例如 `coverageDB/template/BASELINE.vdb/test`
- `<first|all>`:
  - `first`: 每个 definition 只展开一个 instance
  - `all`: 展开全部 instance
- `[module-filter]`: 可选，只导出某一个 definition

一般建议先用 `first`，这样生成的 VP 列表规模更可控，也更适合 AgenticISG 调度。

## 4. 生成各类 VP JSON

在 `AgenticISG` 根目录下，常用命令如下。

### line

```bash
./ucapiTools/covdb_extract_line_vp_design.exe \
  ./coverageDB/template/BASELINE.vdb \
  ./coverageDB/template/BASELINE.vdb/test \
  first > ./line_vp_list.json
```

### condition

```bash
./ucapiTools/covdb_extract_condition_vp_design.exe \
  ./coverageDB/template/BASELINE.vdb \
  ./coverageDB/template/BASELINE.vdb/test \
  first > ./condition_vp_list.json
```

### branch

```bash
./ucapiTools/covdb_extract_branch_vp_design.exe \
  ./coverageDB/template/BASELINE.vdb \
  ./coverageDB/template/BASELINE.vdb/test \
  first > ./branch_vp_list.json
```

### fsm

```bash
./ucapiTools/covdb_extract_fsm_vp_design.exe \
  ./coverageDB/template/BASELINE.vdb \
  ./coverageDB/template/BASELINE.vdb/test \
  first > ./fsm_vp_list.json
```

### tgl

```bash
./ucapiTools/covdb_extract_tgl_vp_design.exe \
  ./coverageDB/template/BASELINE.vdb \
  ./coverageDB/template/BASELINE.vdb/test \
  first > ./tgl_vp_list.json
```

## 5. 单模块实验

先抽单模块验证结构时，可以加 `module-filter`：

```bash
./ucapiTools/covdb_extract_branch_vp_design.exe \
  ./coverageDB/template/BASELINE.vdb \
  ./coverageDB/template/BASELINE.vdb/test \
  first ct_ifu_l1_refill
```

```bash
./ucapiTools/covdb_extract_fsm_vp_design.exe \
  ./coverageDB/template/BASELINE.vdb \
  ./coverageDB/template/BASELINE.vdb/test \
  first ct_ifu_l1_refill
```

## 6. 与 scheduler_v2 的关系

`scheduler_v2` 会从 `src/utils/project_paths.py` 里的 `get_ucapi_snapshot_tool_path()` 自动查找这些工具。

默认查找目录：

```text
AgenticISG/ucapiTools/
```

可选覆盖方式：

- 整个目录：

```bash
export AGENTICISG_UCAPI_TOOLS_ROOT=/abs/path/to/ucapiTools
```

- 单个工具：

```bash
export AGENTICISG_LINE_VP_TOOL=/abs/path/to/covdb_extract_line_vp_design.exe
export AGENTICISG_COND_VP_TOOL=/abs/path/to/covdb_extract_condition_vp_design.exe
export AGENTICISG_BRANCH_VP_TOOL=/abs/path/to/covdb_extract_branch_vp_design.exe
export AGENTICISG_FSM_VP_TOOL=/abs/path/to/covdb_extract_fsm_vp_design.exe
```

## 7. 常见问题

### `error while loading shared libraries: libucapi.so`

说明 `LD_LIBRARY_PATH` 没配对。重新执行：

```bash
export UCAPI_LIB=/home/yian/Synopsys/vcs/V-2023.12-SP2/linux64/lib
export LD_LIBRARY_PATH=$UCAPI_LIB:$LD_LIBRARY_PATH
```

### `failed to load design`

通常说明：

- `<vdb>` 路径不对
- `.vdb` 不完整
- 当前终端环境缺少 UCAPI 运行依赖

先检查：

```bash
ls ./coverageDB/template/BASELINE.vdb
```

### `failed to load test`

通常说明 `<test>` 路径不对。  
对于 baseline，通常是：

```bash
./coverageDB/template/BASELINE.vdb/test
```

如果是 merge 后的 VDB，可能要看：

```bash
<merged_vdb>/snps/coverage/db/testdata/
```

## 8. 推荐生成顺序

当前推荐先生成并使用：

1. `line_vp_list.json`
2. `condition_vp_list.json`
3. `branch_vp_list.json`
4. `fsm_vp_list.json`

`tgl_vp_list.json` 目前更多是实验用途，不建议直接接入调度器。
