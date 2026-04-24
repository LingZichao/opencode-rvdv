# AgenticISG → OpenCode-RVDV 迁移方案

> 基于LangGraph的AgenticISG项目迁移至OpenCode原生架构

---

## 一、项目概述

### 源项目：AgenticISG

基于LangGraph的多Agent协作RISC-V CPU覆盖率导向验证框架，包含：

- **主协调Agent (Coordinator)**: 规划验证迭代流程
- **覆盖率分析Agent (Analyzer)**: 分析覆盖率报告
- **ISG生成Agent (Generator)**: 生成FORCE-RISCV脚本
- **场景识别Agent (Recognizer)**: 识别微架构行为

### 目标项目：OpenCode-RVDV

完全基于OpenCode原生架构的独立项目，以Server模式运行，支持：

- 多会话并发
- Web/TUI/CLI/SDK多客户端接入
- 自定义Agent、工具、命令
- 完整的workspace和coverageDB独立维护

---

## 二、架构映射

### 概念对照表

| LangGraph概念 | OpenCode对应 | 说明 |
|--------------|-------------|------|
| StateGraph | Agent配置 | 通过opencode.json定义 |
| AgentState (TypedDict) | Session状态 | OpenCode自动管理会话状态 |
| 子图 (Subgraph) | 子代理 (subagent) | mode: "subagent" |
| ToolNode + 工具函数 | 自定义工具 | .opencode/tools/*.ts |
| 条件路由 (add_conditional_edges) | Task工具调用 | 主代理通过Task工具调用子代理 |
| langgraph.json | opencode.json | 主配置文件 |
| messages字段 | Session消息历史 | OpenCode自动管理 |
| 流式输出 (stream模式) | SDK实时事件 | event.subscribe() |

---

## 三、目录结构

```
opencode-rvdv/
│
├── src/                           # ===== 源码维护区 =====
│   ├── agents/                    # Agent定义源码
│   │   ├── coordinator.md         # 主协调代理
│   │   ├── analyzer.md            # 覆盖率分析子代理
│   │   ├── generator.md           # ISG脚本生成子代理
│   │   ├── recognizer.md          # 微架构场景识别子代理
│   │   └── compaction.md          # 压缩代理（可选）
│   │   └── title.md               # 标题生成代理（可选）
│   │
│   ├── tools/                     # TypeScript工具包装
│   │   ├── coverage.ts            # 覆盖率工具入口
│   │   ├── coverage_query.ts      # query_baseline_coverage, query_coverage
│   │   ├── coverage_fetch.ts      # fetch_coverage_report, list_coverage_tests
│   │   ├── isg.ts                 # ISG工具入口
│   │   ├── isg_compile.ts         # compile_isg_script
│   │   ├── isg_run.ts             # run_simulation
│   │   ├── knowledge-base.ts      # 知识库查询工具
│   │   └── file-system.ts         # 文件操作工具
│   │
│   ├── commands/                  # 命令定义
│   │   ├── verify.md              # /verify 启动验证任务
│   │   ├── analyze.md             # /analyze 仅分析覆盖率
│   │   ├── generate.md            # /generate 仅生成ISG
│   │   └── status.md              # /status 查看任务状态
│   │
│   ├── prompts/                   # 详细系统prompt（迁移原System Prompt）
│   │   ├── coordinator.md         # COORDINATOR_SYSTEM_PROMPT
│   │   ├── analyzer.md            # COV_ANALYZER_PROMPT
│   │   ├── generator.md           # ISG_GENERATOR_PROMPT
│   │   └── recognizer.md          # RECOGNIZER_SYSTEM_PROMPT
│   │
│   ├── scripts/                   # Python实现脚本
│   │   ├── ucapi_client.py        # UCAPI HTTP客户端
│   │   ├── coverage_query.py      # 覆盖率查询逻辑
│   │   ├── simulation_runner.py   # VCS仿真执行
│   │   ├── isg_compiler.py        # FORCE-RISCV编译
│   │   └── coverage_parser.py     # 覆盖率数据解析
│   │
│   ├── config/                    # 配置模板
│   │   ├── opencode.json.tmpl     # OpenCode配置模板
│   │   ├── server.json.tmpl       # Server配置模板
│   │   ├── providers.json.tmpl    # Provider配置模板
│   │   └── permissions.json.tmpl  # 权限配置模板
│   │
│   └── init/                      # 初始化脚本
│       ├── init.ts                # 主初始化脚本
│       ├── deploy-config.ts       # 部署配置
│       ├── setup-tools.ts         # 安装工具依赖
│       └── validate-env.ts        # 环境校验
│
├── workspace/                     # ===== Agent静态资源 =====
│   ├── agentDoc/                  # Agent文档
│   │   ├── C910ISA_Agent_Friendly.md
│   │   ├── condition_coverage.md
│   │   ├── branch_coverage.md
│   │   ├── ISG_Script/            # ISG脚本示例
│   │   │   ├── example_basic.py
│   │   │   ├── example_branch.py
│   │   │   └── example_cond.py
│   │   └── force_rv/              # ForceRISCV指令定义XML
│   │
│   └── rtl/                       # RTL代码镜像
│   │   └── openc910/
│   │       └── C910_RTL_FACTORY/gen_rtl/*.v
│
├── coverageDB/                    # ===== 覆盖率运行数据 =====
│   ├── template/                  # 共享模板
│   │   ├── BASELINE.vdb/          # 基准覆盖率数据库
│   │   └── sim/                   # 仿真模板
│   │       ├── makefileFRV
│   │       ├── AgenticTargetTest.py
│   │       └── ...
│   │
│   ├── tasks/                     # 任务运行目录
│   │   └ {task_name}/
│   │       ├── isg_scripts/
│   │       ├── reports/
│   │       ├── logs/
│   │       └── sim/
│   │           └ work_force/
│   │               └ simv.vdb/
│   │               └ cov_report/
│   │
│   └── regression/                # 回归历史
│       └ long_agent_scoreboard/
│           ├── scoreboard.csv
│           ├── scoreboard_state.json
│           └ scoreboard_events.jsonl
│
├── scripts/                       # ===== CLI/运维脚本 =====
│   ├── start-server.sh            # 启动OpenCode server
│   ├── init-project.sh            # 项目初始化
│   ├── run-task.sh                # 运行单个任务
│   ├── batch-run.sh               # 批量运行任务
│   └ scoreboard-webui.sh         # Scoreboard WebUI
│
├── .opencode/                     # ===== 【运行时生成】=====
│   ├── agents/                    # 从src/agents/部署
│   ├── tools/                     # 从src/tools/部署
│   ├── commands/                  # 从src/commands/部署
│   ├── prompts/                   # 从src/prompts/部署
│   └ plugins/                     # 插件（可选）
│
├── opencode.json                  # 【运行时生成】主配置
│
├── webui/                         # ===== WebUI（可选）=====
│   ├── scoreboard/                # Scoreboard监控页面
│   └ dashboard/                   # 任务Dashboard
│
├── tests/                         # ===== 测试 =====
│   ├── tools/                     # 工具测试
│   ├── agents/                    # Agent测试
│   └ integration/                 # 集成测试
│
├── package.json                   # Node.js依赖
├── tsconfig.json                  # TypeScript配置
├── bunfig.toml                    # Bun配置
├── AGENTS.md                      # 项目规则
├── README.md                      # 项目文档
└ .env.example                    # 环境变量示例
└ .gitignore
``---

## 四、迁移步骤

### Phase 1: 基础框架搭建

1. 创建目录结构
2. 初始化package.json、tsconfig.json
3. 创建.env.example
4. 编写初始化脚本 src/init/init.ts

### Phase 2: 工具实现

1. 创建Python脚本（从AgenticISG迁移）
   - ucapi_client.py（封装UCAPI HTTP调用）
   - coverage_query.py
   - simulation_runner.py
   - isg_compiler.py

2. 创建TypeScript工具包装
   - coverage_query.ts
   - coverage_fetch.ts
   - isg_compile.ts
   - isg_run.ts
   - knowledge-base.ts

### Phase 3: Agent定义

1. 创建src/agents/*.md
2. 创建src/prompts/*.md（迁移System Prompt）
3. 配置权限和工具访问

### Phase 4: 命令与配置

1. 创建src/commands/*.md
2. 创建src/config/*.tmpl
3. 编写AGENTS.md

### Phase 5: Server与运维

1. 编写scripts/start-server.sh
2. 编写scripts/run-task.sh
3. 配置coverageDB/workspace
4. 编写README.md

---

## 五、关键文件示例

### 5.1 初始化脚本 (src/init/init.ts)

```typescript
import fs from "fs"
import path from "path"

const PROJECT_ROOT = path.resolve(__dirname, "../../")
const SRC_DIR = path.join(PROJECT_ROOT, "src")
const RUNTIME_DIR = path.join(PROJECT_ROOT, ".opencode")

function init() {
  console.log("🚀 Initializing OpenCode-RVDV project...")
  
  // Step 1: 创建运行时目录
  fs.rmSync(RUNTIME_DIR, { recursive: true, force: true })
  
  const modules = ["agents", "tools", "commands", "prompts"]
  for (const mod of modules) {
    const srcMod = path.join(SRC_DIR, mod)
    const destMod = path.join(RUNTIME_DIR, mod)
    if (fs.existsSync(srcMod)) {
      fs.mkdirSync(destMod, { recursive: true })
      fs.cpSync(srcMod, destMod, { recursive: true })
    }
  }
  
  // Step 2: 生成配置文件
  generateConfig()
  
  // Step 3: 验证环境
  validateEnvironment()
  
  // Step 4: 创建必要目录
  createDirectories()
  
  console.log("✅ Initialization complete!")
  console.log("   Run: ./scripts/start-server.sh")
}

function generateConfig() {
  const template = fs.readFileSync(
    path.join(SRC_DIR, "config", "opencode.json.tmpl"),
    "utf-8"
  )
  
  const config = template
    .replace(/\{\{PROJECT_ROOT\}\}/g, PROJECT_ROOT)
    .replace(/\{\{RTL_ROOT\}\}/g, "${PROJECT_ROOT}/workspace/openc910")
    .replace(/\{\{COVERAGE_DB\}\}/g, "${PROJECT_ROOT}/coverageDB")
  
  fs.writeFileSync(
    path.join(PROJECT_ROOT, "opencode.json"),
    config
  )
}

function validateEnvironment() {
  const required = ["QWEN_API_KEY"]
  const missing = required.filter(k => !process.env[k])
  if (missing.length > 0) {
    console.warn(`⚠️  Missing environment variables: ${missing.join(", ")}`)
    console.warn("   Copy .env.example to .env and fill in values")
  }
}

function createDirectories() {
  const dirs = [
    "workspace/agentDoc",
    "workspace/rtl",
    "coverageDB/template",
    "coverageDB/tasks",
    "coverageDB/regression",
    "logs"
  ]
  
  for (const dir of dirs) {
    const fullPath = path.join(PROJECT_ROOT, dir)
    if (!fs.existsSync(fullPath)) {
      fs.mkdirSync(fullPath, { recursive: true })
    }
  }
}

init()
```

### 5.2 配置模板 (src/config/opencode.json.tmpl)

```jsonc
{
  "$schema": "https://opencode.ai/config.json",
  
  "model": "qwen/glm-5",
  
  "server": {
    "port": 4096,
    "hostname": "0.0.0.0",
    "mdns": true,
    "mdnsDomain": "rvdv.local"
  },
  
  "provider": {
    "qwen": {
      "options": {
        "baseURL": "https://coding.dashscope.aliyuncs.com/v1",
        "apiKey": "{env:QWEN_API_KEY}",
        "timeout": 300000
      }
    }
  },
  
  "agent": {
    "coordinator": {
      "description": "主协调Agent - 规划RISC-V验证迭代流程",
      "mode": "primary",
      "model": "qwen/glm-5",
      "prompt": "{file:.opencode/prompts/coordinator.md}",
      "color": "primary",
      "permission": {
        "task": {
          "analyzer": "allow",
          "generator": "allow",
          "recognizer": "allow"
        }
      }
    },
    
    "analyzer": {
      "description": "覆盖率分析子代理 - 分析覆盖率报告和版本管理",
      "mode": "subagent",
      "model": "qwen/glm-5",
      "prompt": "{file:.opencode/prompts/analyzer.md}",
      "tools": {
        "coverage_query": true,
        "coverage_fetch": true,
        "coverage_list": true,
        "read": true,
        "grep": true,
        "glob": true
      }
    },
    
    "generator": {
      "description": "ISG脚本生成子代理 - 生成FORCE-RISCV测试脚本",
      "mode": "subagent",
      "model": "qwen/glm-5",
      "prompt": "{file:.opencode/prompts/generator.md}",
      "tools": {
        "write": true,
        "edit": true,
        "isg_compile": true,
        "isg_run": true,
        "knowledge-base": true,
        "read": true
      }
    },
    
    "recognizer": {
      "description": "微架构场景识别子代理 - 识别RTL模块行为",
      "mode": "subagent",
      "model": "qwen/glm-5",
      "prompt": "{file:.opencode/prompts/recognizer.md}",
      "tools": {
        "read": true,
        "grep": true,
        "glob": true,
        "browse": true,
        "knowledge-base": true
      }
    }
  },
  
  "command": {
    "verify": {
      "description": "启动RTL覆盖率验证任务",
      "template": "分析RTL文件 $1 行号范围 $2 的覆盖率不足问题并制定ISG脚本方案",
      "agent": "coordinator"
    },
    "analyze": {
      "description": "仅分析覆盖率（不生成脚本）",
      "template": "分析RTL文件 $1 行号范围 $2 的覆盖率情况",
      "agent": "analyzer",
      "subtask": true
    },
    "generate": {
      "description": "仅生成ISG脚本（不执行仿真）",
      "template": "根据以下测试计划生成ISG脚本: $ARGUMENTS",
      "agent": "generator",
      "subtask": true
    },
    "status": {
      "description": "查看任务状态和覆盖率进度",
      "template": "查看当前任务的进度和覆盖率状态",
      "agent": "coordinator"
    }
  },
  
  "instructions": [
    "AGENTS.md",
    "workspace/agentDoc/C910ISA_Agent_Friendly.md",
    "workspace/agentDoc/condition_coverage.md"
  ],
  
  "permission": {
    "edit": "allow",
    "bash": "allow"
  },
  
  "compaction": {
    "auto": true,
    "prune": true,
    "reserved": 10000
  },
  
  "experimental": {
    "lsp": true
  }
}
```

### 5.3 覆盖率工具 (src/tools/coverage_query.ts)

```typescript
import { tool } from "@opencode-ai/plugin"
import path from "path"

export const query_baseline_coverage = tool({
  description: `Query coverage from BASELINE database using UCAPI.

Coverage Types:
- line: Statement/line execution coverage (contains branch+FSM)
- cond/condition: Boolean expression condition coverage
- branch: If/else, case branch coverage
- tgl: Signal transition coverage
- fsm: FSM state/transition coverage
- vp: Verification Point summary

Use "line+cond+vp" for multiple types.`,
  
  args: {
    rtl_file: tool.schema.string()
      .describe("RTL file name, e.g. ct_idu_ir_ctrl.v"),
    start_line: tool.schema.number()
      .default(0)
      .describe("Starting line number"),
    end_line: tool.schema.number()
      .default(50000)
      .describe("Ending line number"),
    kind: tool.schema.string()
      .default("line")
      .describe("Coverage type: line, cond, branch, tgl, fsm, vp. Use '+' for multiple."),
    http_api_url: tool.schema.string()
      .default("http://localhost:5000/api/v1/query")
      .describe("UCAPI server URL")
  },
  
  async execute(args, context) {
    const scriptPath = path.join(
      context.worktree, 
      "src/scripts/ucapi_client.py"
    )
    
    const result = await Bun.$`python3 ${scriptPath} query-baseline \
      --rtl-file ${args.rtl_file} \
      --start-line ${args.start_line} \
      --end-line ${args.end_line} \
      --kind ${args.kind} \
      --api-url ${args.http_api_url}`.text()
    
    return result.trim()
  }
})

export const query_coverage = tool({
  description: `Query coverage from task VDB using UCAPI.

IMPORTANT: testname is REQUIRED. Use list_coverage_tests first to get available tests.`,
  
  args: {
    rtl_file: tool.schema.string()
      .describe("RTL file name"),
    testname: tool.schema.string()
      .describe("Test name - REQUIRED. Use list_coverage_tests first."),
    start_line: tool.schema.number().default(0),
    end_line: tool.schema.number().default(50000),
    task_name: tool.schema.string()
      .describe("Task name to locate VDB"),
    kind: tool.schema.string().default("line"),
    http_api_url: tool.schema.string()
      .default("http://localhost:5000/api/v1/query")
  },
  
  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "src/scripts/ucapi_client.py")
    
    const result = await Bun.$`python3 ${scriptPath} query \
      --rtl-file ${args.rtl_file} \
      --testname ${args.testname} \
      --start-line ${args.start_line} \
      --end-line ${args.end_line} \
      --task-name ${args.task_name} \
      --kind ${args.kind} \
      --api-url ${args.http_api_url}`.text()
    
    return result.trim()
  }
})

export const list_coverage_tests = tool({
  description: "List all available test names from coverage database (.vdb)",
  
  args: {
    task_name: tool.schema.string()
      .describe("Task name to locate VDB"),
    vdb_path: tool.schema.string()
      .optional()
      .describe("VDB path, auto-detect if not provided")
  },
  
  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "src/scripts/ucapi_client.py")
    
    let cmdArgs = ["list-tests", "--task-name", args.task_name]
    if (args.vdb_path) {
      cmdArgs.push("--vdb-path", args.vdb_path)
    }
    
    const result = await Bun.$`python3 ${scriptPath} ${cmdArgs}`.text()
    return result.trim()
  }
})
```

### 5.4 ISG工具 (src/tools/isg.ts)

```typescript
import { tool } from "@opencode-ai/plugin"
import path from "path"

export const compile_isg = tool({
  description: `Compile ISG script using FORCE-RISCV.

This tool compiles the ISG test script from workspace/isgScripts/<task_id>/.
Returns compilation output including success/failure information.`,
  
  args: {
    script_name: tool.schema.string()
      .describe("ISG script filename (e.g. test_branch_1.py)"),
    task_name: tool.schema.string()
      .describe("Task name")
  },
  
  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "src/scripts/isg_compiler.py")
    
    const result = await Bun.$`python3 ${scriptPath} \
      --script-name ${args.script_name} \
      --task-name ${args.task_name}`.text()
    
    return result.trim()
  }
})

export const run_simulation = tool({
  description: `Execute simulation and fetch coverage report.

Steps:
1. Copy script to simulation directory
2. Run FORCE-RISCV to generate instructions
3. Execute VCS simulation
4. Return VDB path for coverage query`,
  
  args: {
    script_name: tool.schema.string()
      .describe("ISG script name"),
    iter_count: tool.schema.number()
      .default(1)
      .describe("Iteration count for version naming"),
    task_name: tool.schema.string()
      .describe("Task name")
  },
  
  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "src/scripts/simulation_runner.py")
    
    const result = await Bun.$`python3 ${scriptPath} \
      --script-name ${args.script_name} \
      --iter-count ${args.iter_count} \
      --task-name ${args.task_name}`.text()
    
    return result.trim()
  }
})
```

### 5.5 主代理Prompt (src/prompts/coordinator.md)

```markdown
## 项目背景：
你正在验证一个复杂的RISC-V Out-of-Order CPU核，项目代号OpenC910.
整个验证的框架流程如下：
1. 复杂生成：基于随机指令流生成器（ISG）框架FORCE-RISCV，接受一个类Python脚本，生成RISC-V机器码。
2. 仿真执行：使用Synopsys RTL仿真器 VCS RTL进行硬件软件仿真，执行生成的RISC-V机器码。
3. 覆盖率收集：通过Verdi工具收集RTL覆盖率报告，涵盖代码覆盖率、功能覆盖率等多个维度。

## 你的职责：
你需要**自主规划**多轮迭代的分析-生成工作流程，协调并调用以下子代理工具完成工作：
1. **覆盖率分析子代理 (@analyzer)**：获取、分析覆盖率报告，管理覆盖率版本。
2. **场景识别子代理 (@recognizer)**：识别目标模块的微架构行为，试图在硬件信号和抽象行为间建立关系。
3. **ISG撰写子代理 (@generator)**：生成可以编译的指令序列ISG脚本。

在任何阶段，如果你有不确定之处，应询问Subagent或直接阅读项目源码获取更多信息。
当一个轮次结束时，通常是ISG撰写子代理完成，你需要告知用户等待用户评估。

## ISG方案设计要点：
1. 避免冗余设计、过度设计。

2. **操作守则：明确的生成边界**：
任何模糊的生成请求都是无效的。在生成指令流时，你须定义并执行以下三个维度的具体参数：
Scope (类型)：指定具体的ISA子集（例如：RV64I Base Integer）或某几种指令。
Volume (量级)：明确给出指令生成的规模。例如，"生成50到100条连续的某种指令"以确保触发微架构的长周期行为。
Data Rules (数据规则)：对操作数施加物理约束。例如：
- 寄存器：指定使用的索引范围（如 x0-x15）。
- 依赖性：控制RAW/WAW依赖的密度。
- 特殊值：根据验证点的功能确定是否需要Corner Case数值。

注意：ISG撰写Subagent只能确保生成满足你的测试计划且符合语法的FORCE-RISCV脚本，无法校验有效性。
因此，你的测试计划必须足够明确和具体，避免模糊或不完整的描述，同时严格遵守原子化原则——
因为，验证环境编译ISG脚本后生成RISCV机器码文件，然后由VCS/Verdi仿真RTL得到覆盖率报告，
我们只能看到最终的覆盖率数据，无法追踪每条指令或每个阶段的具体执行效果。

3. **ISG方法论：间接驱动与概率碰撞**：
你必须理解，作为ISG（指令流生成器），你对微架构模块（Micro-architecture）没有直接控制权（无直接信号接口）。
你不能像定向RTL测试那样精准地"写入"状态，只能通过编排外部的指令序列（Instruction Stream），
利用硬件对指令的响应逻辑，间接诱导内部状态发生变化，你永远做不到精确控制。
这就是为什么建议你深度结合微架构知识进行推导分析，同时思考一条指令是如何在RTL层级流动的。

因此，你的方法论基础是**"随机碰撞（Stochastic Hitting）"**：
依靠生成大量但是定向设计的随机指令流，利用概率统计原理去"碰撞"出那些难以触达的目标覆盖点，
而非进行手术刀式的精确驱动控制（例如试图通过个位数条指令精准驱动，这不总是有效）。
**注意**：每种指令存在/重复数百数千条(100~9999)以上的量级规模才能称为"大量""大规模"
         每种指令存在/重复数百万条(1000000以上)以上的量级规模才能称为"超大量""超大规模"，这在验证中是常态。
         FORCE-RISCV会添加必要的指令集指令，约800条，因此最终生成的指令数量多于你编写的部分是正常现象
         但在校验测试计划时，指令数量要扣除这部分自动添加的指令。

**时刻牢记**：在ISG方法论下，任何指令的预期效果都只能是"可能会"而非"必然会"，
你需要通过大量的随机尝试和指令数量来提升触发目标覆盖点的概率。用数量弥补精度，承认ISG的间接性和随机性。

4. **生成准则：原子化验证 (Atomic Verification)**
为了确保验证结果的可观测性与高效迭代，撰写脚本时必须遵循**"单次任务、单一场景"**原则：
- 单一目标 (Single Target)：每脚本严禁同时针对多个验证目标。
- 单一场景 (Single Scenario)：每脚本只能聚焦于单一测试场景，严格按照测试计划执行。
- 明确的阶段目的 (Clear Phase Objectives)：你的测试计划必须清晰定义并记录每个阶段的具体的设计目标和预期效果，避免模糊不清的描述。
        这样在没有达到预期覆盖率时，你可以反思并尝试定位问题所在并进行调整。

5. 目前是基于RTL文本的静态分析验证，只能通过RTL文本分析进行验证
6. 所验证的CPU为C910，程序通过testbench直接加载到L1 Cache中执行，L1 Cache地址空间为0x00000-0x40000，也就是约64K指令(假设每指令4字节)存储空间，可以认为ISG脚本生成的随机指令只在这个范围执行。
7. 玄铁C910扩展指令默认不可用，请勿在测试中验证，涉及到扩展指令集的模块和结构可以放弃验证

## 关键提示：
- 当覆盖率没有提升时，尝试发现并提出问题，重新审视信号定义、功能和微架构行为，重新考虑SystemPrompt中的提示。
- CPU中大量组件由流水线组成，指令在多个阶段被处理。
  因此需要理解指令在流水线中的流动，对于不确定的模块不能假定是原子的，否则会对时序产生误判。
  例如一条长周期指令可能会在下一个周期立刻进入下一个阶段，而不是停留在当前阶段数个周期，因为下游阶段流水线可以容纳多条指令
  所以，一条指令可能要重复多次才能真正触发目标模块的功能。

- **关联模块**：
尽管你的主要关注点是目标代码段，但也要留意其他模块的覆盖率情况，寻找潜在的耦合影响因素，尤其是：
上游模块：哪些模块的输出是本模块的输入？（谁驱动了我？条件是什么？）
下游模块：本模块的输出是哪些模块的输入？（我驱动了谁？条件是什么？)
兄弟模块：与本模块处于同一层级的模块或者重复声明的示例有哪些？它们之间有何交互？
这些模块的覆盖率情况可能会间接影响目标代码段的覆盖率表现，你也可以调用覆盖率分析子代理
和微架构分析子代理获取这些信息。

保持清晰的协调思路，灵活使用工具，充分利用SubAgent的专业能力。

## 参考文档目录：
阅读AGENTS.md获取目录功能预览。
Agent 文档位于 workspace/agentDoc/ 目录，可使用文件系统工具（read、glob、browse）直接访问：
- C910ISA_Agent_Friendly.md: C910 ISA 参考文档（指令集、延迟、流水线信息）
- ISG_Script/: ISG 脚本示例
- force_rv/: ForceRISCV 指令定义 XML 文件
- condition_coverage.md: 条件覆盖率规则文档
```

### 5.6 Analyzer Prompt (src/prompts/analyzer.md)

```markdown
你是一位专业的覆盖率报告分析和版本管理工程师，专注于RTL验证覆盖率的分析报告，
同时完成多版本覆盖率报告的获取与查询。

## 核心分析职责：
1. 寻找到匹配迭代轮次的最新覆盖率报告
2. 根据源代码位置定位对应覆盖率报告段落
3. 解析目标覆盖率数据（包括分支、翻转、行覆盖率等）
4. 初步分析RTL层级未覆盖的原因及其触发条件
5. 关注并汇报关联模块实例的覆盖率情况

## 报告版本管理：
- 系统支持基于多轮迭代下的多版本覆盖率报告
- 任务一开始没有生成ISG脚本进行得到覆盖率报告，请查询BASELINE覆盖数据
- BASELINE数据所缺失的覆盖漏洞才是本次任务的重点
- 本次任务的ISG脚本是针对BASELINE的覆盖漏洞生成，很可能/必然会导致BASELINE已有的覆盖点缺失，不必过分关注
- 重点关注BASELINE数据所缺失的覆盖漏洞，去覆盖这些这才是本次任务的重点
- 如果没有当前版本的最新报告，请调用FETCH工具生成；如果有，则直接查询，避免重复生成
- 查询工具默认（初始）使用 BASELINE 版本，可通过 version 参数指定其他版本
- 建议对比分析时，先查询版本列表，然后对比 BASELINE 或上一轮迭代版本的差异

## 重要：关注 BASELINE 未覆盖的 VP
系统已在初始化时查询了 BASELINE 覆盖率，并提取了未覆盖的 VP（Verification Point）列表。
**你需要重点关注这些未覆盖的 VP**，无需过分关注已覆盖的部分下降的情况。

未覆盖 VP 的信息会在任务提示中提供，包含：
- kind: 覆盖率类型 (line/cond/branch)
- range: 行号范围
- pct: 当前覆盖率百分比
- covered/coverable: 已覆盖/可覆盖数量

## 关于覆盖率下降的说明
新生成的 ISG 脚本是针对 BASELINE 未覆盖的 VP 设计的，可能会导致：
- BASELINE 已覆盖的点在新脚本中未被覆盖（这是正常的，无需关注）
- 整体覆盖率可能暂时下降（这是正常的优化过程）

**你的目标**：专注于提升 BASELINE 未覆盖 VP 的覆盖率，而非维持已有覆盖率。

## 可能的分析方向：
1. **总体概览**：汇报模块总体覆盖率、目标段落覆盖率的变化趋势
2. **未覆盖项列表**：总结列出未覆盖的分支、条件或代码行的覆盖率情况
3. **触发条件**：阅读RTL初步说明触发覆盖所需的输入/状态条件
4. **轮次比较**：对比当前迭代轮次和上一轮迭代轮次的覆盖率差异，突出变化和改进

**注意事项**：
0. 仅完成指定分析任务，无需额外扩展，无需给出改进建议
1. 对覆盖率报告的操作应使用提供的工具函数，禁止直接通过文件系统读取
2. 重点关注 BASELINE 未覆盖的 VP，忽略覆盖率下降的情况

保持分析的准确性和深度，给出可操作的结论。完成分析后直接输出报告。
```

### 5.7 Generator Prompt (src/prompts/generator.md)

```markdown
你是一位专业的ISG（Instruction Stream Generation）脚本撰写助手，
专注于调用工具为RISC-V CPU核生成符合Force-RISCV框架要求的随机指令序列脚本。

## 你的核心职责：
1. **严格**按照测试计划生成可编译通过的ISG Python脚本，确保指令种类、数量及数据规则符合要求
2. 根据编译错误调试并修复脚本，直至编译成功
3. 可调用forcerv知识库查询相关API与示例代码
4. 最终交付：一份可编译的ISG脚本文件（汇报最新的脚本名称，脚本名称包含迭代轮次） + 一份说明文档

## 编译后ISG脚本的运行流程：
这部分为补充的背景知识，帮助你更好的撰写ISG脚本。

### 运行逻辑
生成的 ISG 脚本经FORCE-RISCV编译器处理后，将在 RTL 仿真器（如 VCS/Verdi）上加载运行。
每一段脚本应被视为一个独立的实验样本。仿真结束后，Main Agent会分析覆盖率报告根据此制定下一轮测试计划。

### 生成准则：原子化验证 (Atomic Verification)
为了确保验证结果的可观测性与高效迭代，撰写脚本时必须遵循**"单次任务、单一场景"**原则：
- 单一目标 (Single Target)：每脚本严禁同时针对多个验证目标。
- 单一场景 (Single Scenario)：每脚本只能聚焦于单一测试场景，严格按照测试计划执行。
- 最小阶段 (Minimal Phases)：指令序列应精简为三个标准阶段：
* 预设阶段 (Setup)：初始化必要的寄存器或内存状态。
* 激发阶段 (Trigger)：执行核心指令流碰撞目标覆盖点。
* 结束阶段 (Finish)：这里你不需要关心。

## 重要提示：
0. 仅完成指定测试计划拟定的任务，无需额外补充或扩展。当编译成功时需要报告最新的脚本名称。
1. 从基础开始：首先生成能编译通过的基本指令序列，避免过度设计，但要确保满足测试计划要求
2. 保持脚本代码简洁清晰，避免冗余内容输出，
   禁止使用Python print()，如有需要前端输出的需求(例如日志或调试信息)请查阅专用API
3. 脚本文件名应具有描述性，你最终仅输出一个脚本文件。因此请在一个文件中完成所有修改。
   创建新文件时使用 write；修改已有文件时使用 edit。
   edit 可传入一组非重叠的 edits，且 start_line/end_line 使用从 1 开始、包含边界的行号；同一文件的离散修改优先合并到一次调用里。
   write 不能覆盖已有文件。
4. 脚本编译通过后，直接输出报告，等待下一个修改计划
5. 脚本需符合标准Python语法，可合理运用Python特性提升简洁性、可读性与可维护性
6. FORCE-RISCV会添加必要的指令集指令，约800条，因此最终生成的指令数量多于你编写的部分是正常现象
   但在校验测试计划时，指令数量要扣除这部分自动添加的指令
7. 如果你对测试计划有任何不明确之处，请返回给协调者进行咨询，切勿自行猜测或假设
8. C910自定义扩展指令集暂时不需要考虑生成和验证，而且Force-Riscv不支持直接生成C910的扩展指令，考虑RV64GC指令集即可
9. 编写ISG脚本时注意命名需要加上迭代轮次，如isg_name_iter_1.py, isg_name_iter_2.py etc.

## 基本示例:
这里给出一个基本的最简易直接的、无Python技巧的ISG脚本结构
```python
from riscv.EnvRISCV import EnvRISCV
from riscv.GenThreadRISCV import GenThreadRISCV
from base.Sequence import Sequence

class MainSequence(Sequence):
    def generate(self, **kargs):
        self.genInstruction("ADD##RISCV")
        self.genInstruction("SUB##RISCV")
        self.genInstruction("AND##RISCV")
        self.genInstruction("OR##RISCV")
        self.genInstruction("SLL##RISCV")
        self.genInstruction("SRL##RISCV")
        self.genInstruction("JAL##RISCV")
        self.genInstruction("BEQ##RISCV")

MainSequenceClass = MainSequence
GenThreadClass = GenThreadRISCV
EnvClass = EnvRISCV
```
```

### 5.8 Recognizer Prompt (src/prompts/recognizer.md)

```markdown
你的任务是正确识别待验证模块在RISC-V CPU体系结构中的行为描述。
你可以使用工具查询存放openc910微架构的本地 RAG 知识库。
你可以使用工具查阅具体的RTL硬件设计以理解实际硬件细节。

## 参考文档目录：
Agent 文档位于 workspace/agentDoc/ 目录，可使用文件系统工具（read、glob、browse）直接访问：
- C910ISA_Agent_Friendly.md: C910 ISA 参考文档（指令集、延迟、流水线信息）
- ISG_Script/: ISG 脚本示例
- force_rv/: ForceRISCV 指令定义 XML 文件
- condition_coverage.md: 条件覆盖率规则文档

## 核心职责：
你将从自顶向下和自底向上的两个角度，识别给定RTL代码块的以下内容，最终二者结合给出一个合理准确的分析结论。

### 自顶向下分析
1. 模块在CPU微架构中的角色（数据通路组件、控制单元、缓存控制器等）
2. 模块在流水线中的处理阶段（取指、译码、发射、调度、执行、退休等等，需要结合具体的微架构设计）

### 自底向上分析
1. 查阅RTL源代码，明确硬件实现的细节

## 潜在的识别方向
在包含两个方向分析的基础上，请至少针对以下4个方向，并在对应标签内输出结果：
1. **流水线处理阶段与触发位置**：明确一条指令在该CPU微架构流水线中经过的处理阶段，以及最终触发该模块功能的具体流水线位置（如在乱序流水线中的某一/某几个节点）。
2. **触发指令类型**：列出RV64GC指令集中能够触发该模块功能的所有指令类型（需明确指令名称或指令大类，如算术指令、加载存储指令等）。
3. **模块角色与核心作用**：阐述该模块在处理器微架构中的具体角色（如数据通路组件、控制单元、缓存控制器等）及核心作用（如完成数据运算、生成控制信号、管理存储访问等）。
4. **关联硬件模块**：在RTL中，请明确分析目标模块的关联关系：
上游模块：哪些模块的输出是本模块的输入？（谁驱动了我？条件是什么？）
下游模块：本模块的输出是哪些模块的输入？（我驱动了谁？条件是什么？)
兄弟模块：与本模块处于同一层级的模块或者重复声明的示例有哪些？它们之间有何交互？

**注意**：仅完成场景识别任务，不需要给出完整的测试方案。
给出使用架构级指令触发待验证场景的初步思路
```

### 5.9 Agent定义 (src/agents/coordinator.md)

```markdown
---
description: 主协调Agent - 规划RISC-V验证迭代流程
mode: primary
model: qwen/glm-5
color: primary
permission:
  task:
    analyzer: allow
    generator: allow
    recognizer: allow
---

# Coordinator Agent

你是RISC-V CPU覆盖率验证的主协调者。

## 调用子代理

使用 Task 工具调用以下子代理：

- **@analyzer**: 分析覆盖率报告
- **@generator**: 生成ISG测试脚本  
- **@recognizer**: 识别微架构场景

## 工作流程

1. 接收用户指定的RTL文件和行号范围
2. 调用 @analyzer 获取BASELINE覆盖率
3. 调用 @recognizer 识别场景
4. 制定测试计划，调用 @generator
5. 调用 run_simulation 执行仿真
6. 调用 @analyzer 分析新覆盖率
7. 决定继续迭代或完成任务

## 注意事项

- 每次迭代只生成一个ISG脚本
- 每轮迭代后需要用户评估反馈
- 专注BASELINE未覆盖的VP，忽略覆盖率下降
```

### 5.10 命令定义 (src/commands/verify.md)

```markdown
---
description: 启动RTL覆盖率验证任务
agent: coordinator
subtask: false
---

# 验证任务

请分析以下RTL模块的覆盖率不足问题并制定ISG脚本方案。

目标信息：
- RTL文件: **$1**
- 行号范围: **$2**
- 任务描述: $ARGUMENTS

## 执行步骤

1. 查询BASELINE覆盖率，确定未覆盖点
2. 识别模块的微架构行为
3. 设计原子化测试方案
4. 生成ISG脚本并编译
5. 执行仿真获取覆盖率
6. 分析结果并决定是否继续迭代
```

### 5.11 启动脚本 (scripts/start-server.sh)

```bash
#!/bin/bash
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

# 检查初始化
if [ ! -f "$PROJECT_ROOT/opencode.json" ]; then
    echo "⚠️  Project not initialized. Run: bun run src/init/init.ts"
    exit 1
fi

# 加载环境变量
if [ -f "$PROJECT_ROOT/.env" ]; then
    export $(cat "$PROJECT_ROOT/.env" | grep -v '^#' | xargs)
fi

# 检查UCAPI服务
if ! curl -s http://localhost:5000/health > /dev/null 2>&1; then
    echo "⚠️  UCAPI coverage server not running at localhost:5000"
    echo "   Please start it manually: python src/scripts/ucapi_server.py"
fi

# 启动OpenCode server
echo "🚀 Starting OpenCode server..."
cd "$PROJECT_ROOT"

opencode serve \
    --port 4096 \
    --hostname 0.0.0.0

# 或者使用Bun运行
# bun x opencode serve --port 4096 --hostname 0.0.0.0
```

### 5.12 package.json

```json
{
  "name": "opencode-rvdv",
  "version": "1.0.0",
  "description": "RISC-V Coverage Verification with OpenCode",
  "type": "module",
  "scripts": {
    "init": "bun run src/init/init.ts",
    "start": "./scripts/start-server.sh",
    "test": "bun test",
    "lint": "eslint src/"
  },
  "dependencies": {
    "@opencode-ai/sdk": "latest",
    "@opencode-ai/plugin": "latest"
  },
  "devDependencies": {
    "@types/bun": "latest",
    "typescript": "^5.0.0"
  }
}
```

### 5.13 AGENTS.md

```markdown
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
- `coverageDB/` - 覆盖率数据存储
- `src/scripts/` - Python工具实现

## 注意事项

- 每个任务独立目录: coverageDB/tasks/<task_name>/
- ISG脚本存放: workspace/isgScripts/<task_name>/
- 专注BASELINE未覆盖的VP
```

---

## 六、运行流程

### 初始化

```bash
cd opencode-rvdv

# 1. 初始化项目
bun run init

# 2. 配置环境
cp .env.example .env
# 编辑 .env 填入:
# QWEN_API_KEY=your_key
```

### 启动Server

```bash
# 方式1: Shell脚本
./scripts/start-server.sh

# 方式2: Bun命令
bun run start

# 方式3: 直接运行
opencode serve --port 4096 --hostname 0.0.0.0
```

### 使用方式

```bash
# CLI方式
opencode run "/verify ct_idu_ir_ctrl.v 1326-1338"

# TUI方式
opencode
# 然后输入: /verify ct_idu_ir_ctrl.v 1326-1338

# SDK方式
bun run scripts/run-task.ts --file ct_idu_ir_ctrl.v --lines 1326-1338

# Web方式
访问 http://localhost:4096
```

---

## 七、迁移清单

### 需迁移的文件

| 源文件 (AgenticISG) | 目标文件 (opencode-rvdv) |
|-------------------|------------------------|
| src/nodes/coordinator.py COORDINATOR_SYSTEM_PROMPT | src/prompts/coordinator.md |
| src/nodes/subgraphs/analyzer.py COV_ANALYZER_PROMPT | src/prompts/analyzer.md |
| src/nodes/subgraphs/generator.py ISG_GENERATOR_PROMPT | src/prompts/generator.md |
| src/nodes/subgraphs/recognizer.py RECOGNIZER_SYSTEM_PROMPT | src/prompts/recognizer.md |
| src/utils/toolset/coverage_tools.py | src/scripts/ucapi_client.py, coverage_query.py |
| src/utils/toolset/file_system_tools.py | src/tools/file-system.ts |
| src/utils/toolset/knowledge_base_tools.py | src/tools/knowledge-base.ts |
| workspace/agentDoc/* | workspace/agentDoc/* (复制) |
| coverageDB/template/* | coverageDB/template/* (复制) |

### 需新建的文件

| 文件 | 说明 |
|-----|------|
| src/init/init.ts | 初始化脚本 |
| src/config/opencode.json.tmpl | 配置模板 |
| src/tools/coverage_query.ts | 覆盖率工具TS包装 |
| src/tools/isg.ts | ISG工具TS包装 |
| src/agents/*.md | Agent定义 |
| src/commands/*.md | 命令定义 |
| package.json | Node.js配置 |
| AGENTS.md | 项目规则 |
| scripts/start-server.sh | 启动脚本 |

---

## 八、待确认事项

1. **UCAPI服务**: 是否需要集成到项目启动流程，还是保持独立运行？
2. **RTL代码镜像**: workspace/rtl/ 是否需要完整复制还是软链接？
3. **Scoreboard WebUI**: 是否需要迁移？
4. **多任务并行**: OpenCode多会话如何映射到任务隔离？
5. **模型选择**: glm-5是否为最终选择，还是需要支持多模型切换？

---

## 九、参考资源

- OpenCode文档: https://opencode.ai/docs
- OpenCode配置Schema: https://opencode.ai/config.json
- OpenCode SDK: https://opencode.ai/docs/sdk
- Agent配置: https://opencode.ai/docs/agents
- 自定义工具: https://opencode.ai/docs/custom-tools
- LangGraph文档: https://langchain-ai.github.io/langgraph/

---

*文档版本: 1.0*
*创建日期: 2026-04-16*
