import { tool } from "@opencode-ai/plugin"
import path from "path"

export default tool({
  description: "List all available test names from coverage database (.vdb)",

  args: {
    task_name: tool.schema.string()
      .describe("Task name to locate VDB"),
    vdb_path: tool.schema.string()
      .optional()
      .describe("VDB path, auto-detect if not provided"),
  },

  async execute(args, context) {
    const scriptPath = path.join(context.worktree, "src/scripts/ucapi_client.py")

    const cmdArgs = ["list-tests", "--task-name", args.task_name]
    if (args.vdb_path) {
      cmdArgs.push("--vdb-path", args.vdb_path)
    }

    const result = await Bun.$`python3 ${scriptPath} ${cmdArgs}`.text()
    return result.trim()
  },
})
