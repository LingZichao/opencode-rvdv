import { tool } from "@opencode-ai/plugin"
import path from "path"

export const file_system_tools = {
  read_agent_doc: tool({
    description: "Read a file from workspace/agentDoc directory.",
    args: {
      file_path: tool.schema.string().describe("Relative path within agentDoc"),
    },
    async execute(args, context) {
      const fullPath = path.join(context.worktree, "workspace/agentDoc", args.file_path)
      try {
        const content = await Bun.file(fullPath).text()
        return `=== ${args.file_path} ===\n${content}`
      } catch {
        return `File not found: ${args.file_path}`
      }
    },
  }),
}