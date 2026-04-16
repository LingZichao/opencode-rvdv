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