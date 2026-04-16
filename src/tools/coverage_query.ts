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