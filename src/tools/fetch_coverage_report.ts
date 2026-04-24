import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
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
      .describe("Task name"),
  },

  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "src/scripts/simulation_runner.py")

    const result = await Bun.$`python3 ${scriptPath} \
      --script-name ${args.script_name} \
      --iter-count ${args.iter_count} \
      --task-name ${args.task_name}`.text()

    return result.trim()
  },
})
