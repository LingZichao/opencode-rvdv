import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
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
      .describe("UCAPI server URL"),
  },

  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "src/scripts/ucapi_client.py")

    const result = await Bun.$`python3 ${scriptPath} query-baseline \
      --rtl-file ${args.rtl_file} \
      --start-line ${args.start_line} \
      --end-line ${args.end_line} \
      --kind ${args.kind} \
      --api-url ${args.http_api_url}`.text()

    return result.trim()
  },
})
