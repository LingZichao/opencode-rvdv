import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
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
      .default("http://localhost:5000/api/v1/query"),
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
  },
})
