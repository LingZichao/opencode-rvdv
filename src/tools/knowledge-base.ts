import { tool } from "@opencode-ai/plugin"
import path from "path"

export const query_knowledge_base = tool({
  description: `Query the LightRAG knowledge base for CPU microarchitecture documentation.

Use this tool to query:
- openc910: OpenC910 microarchitecture design, pipeline stages, instruction flows
- forcerv: ForceRISCV ISG framework documentation, API usage, examples`,
  
  args: {
    query: tool.schema.string()
      .describe("Question about the knowledge base (e.g. 'What is the pipeline structure?')"),
    knowledge_base: tool.schema.string()
      .default("openc910")
      .describe("KB to query: 'openc910' (default) or 'forcerv'")
  },
  
  async execute(args) {
    const kbConfig = {
      openc910: { port: 9621, name: "OpenC910" },
      forcerv: { port: 9622, name: "ForceRV" },
    }
    
    const config = kbConfig[args.knowledge_base as keyof typeof kbConfig]
    if (!config) {
      return `Unknown knowledge base: ${args.knowledge_base}. Options: openc910, forcerv`
    }
    
    try {
      const resp = await fetch(`http://localhost:${config.port}/query`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: args.query,
          mode: "mix",
          include_references: true,
          response_type: "Multiple Paragraphs",
          top_k: 10,
          max_total_tokens: 8000,
        }),
      })
      
      if (!resp.ok) {
        return `Query failed: HTTP ${resp.status} - ${await resp.text()}`
      }
      
      const result = await resp.json() as any
      let output = result.response || ""
      
      if (result.references?.length) {
        output += "\n\nReferences:\n"
        for (const ref of result.references) {
          output += `[${ref.reference_id}] ${ref.file_path}\n`
        }
      }
      
      return output
    } catch (e: any) {
      if (e.message?.includes("fetch") || e.message?.includes("connect")) {
        return `Cannot connect to ${config.name} LightRAG service (port ${config.port}). Ensure service is running.`
      }
      return `Query error: ${e.message}`
    }
  }
})

export const list_agent_docs = tool({
  description: "List all documentation files in the workspace/agentDoc directory.",
  
  args: {},
  
  async execute(_args, context) {
    const agentDocDir = path.join(context.worktree, "workspace/agentDoc")
    
    try {
      const result = await Bun.$`find ${agentDocDir} -type f -not -path '*/.*' | sort`.text()
      const files = result.trim().split("\n").filter(Boolean)
      
      if (files.length === 0) {
        return "No files found in workspace/agentDoc."
      }
      
      let output = "Available documents in workspace/agentDoc:\n\n"
      for (const file of files) {
        const relative = file.replace(agentDocDir + "/", "")
        output += `  ${relative}\n`
      }
      return output
    } catch {
      return `AgentDoc directory not found: ${agentDocDir}`
    }
  }
})

export const read_agent_doc = tool({
  description: `Read a specific file from the workspace/agentDoc directory.

Use this tool to read agent documentation, ISG script guides, and ISA specifications.
Call list_agent_docs first to see available files.`,
  
  args: {
    file_path: tool.schema.string()
      .describe("Relative path within agentDoc (e.g. 'C910ISA_Agent_Friendly.md')")
  },
  
  async execute(args, context) {
    const agentDocDir = path.join(context.worktree, "workspace/agentDoc")
    const fullPath = path.join(agentDocDir, args.file_path)
    
    try {
      const content = await Bun.file(fullPath).text()
      return `=== ${args.file_path} ===\n${content}`
    } catch {
      return `File not found: ${args.file_path}\nCall list_agent_docs to see available files.`
    }
  }
})

export const knowledge_base_tools = {
  query_knowledge_base,
  list_agent_docs,
  read_agent_doc,
}