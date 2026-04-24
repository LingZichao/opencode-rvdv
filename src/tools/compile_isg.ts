import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: `Compile ISG script using FORCE-RISCV.

This tool compiles the ISG test script from workspace/isgScripts/<task_id>/.
Returns compilation output including success/failure information.`,

  args: {
    script_name: tool.schema.string()
      .describe("ISG script filename (e.g. test_branch_1.py)"),
    task_name: tool.schema.string()
      .describe("Task name"),
  },

  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "src/scripts/isg_compiler.py")

    const result = await Bun.$`python3 ${scriptPath} \
      --script-name ${args.script_name} \
      --task-name ${args.task_name}`.text()

    return result.trim()
  },
})
