import fs from "fs"
import path from "path"

const PROJECT_ROOT = path.resolve(import.meta.dir, "../../")
const SRC_DIR = path.join(PROJECT_ROOT, "src")
const RUNTIME_DIR = path.join(PROJECT_ROOT, ".opencode")

function init() {
  console.log("Initializing OpenCode-RVDV project...")

  fs.rmSync(RUNTIME_DIR, { recursive: true, force: true })

  const modules = ["tools", "commands", "prompts"]
  for (const mod of modules) {
    const srcMod = path.join(SRC_DIR, mod)
    const destMod = path.join(RUNTIME_DIR, mod)
    if (fs.existsSync(srcMod)) {
      fs.mkdirSync(destMod, { recursive: true })
      fs.cpSync(srcMod, destMod, { recursive: true })
    }
  }

  generateConfig()
  validateEnvironment()
  createDirectories()

  console.log("Initialization complete!")
  console.log("   Run: ./scripts/start-server.sh")
}

function generateConfig() {
  const templatePath = path.join(SRC_DIR, "config", "opencode.json.tmpl")
  if (!fs.existsSync(templatePath)) {
    console.warn("Config template not found: " + templatePath)
    return
  }

  const template = fs.readFileSync(templatePath, "utf-8")

  const config = template
    .replace(/\{\{PROJECT_ROOT\}\}/g, PROJECT_ROOT)
    .replace(/\{\{OPENCODE_PORT\}\}/g, process.env.OPENCODE_PORT || "4096")
    .replace(/\{\{OPENCODE_HOSTNAME\}\}/g, process.env.OPENCODE_HOSTNAME || "0.0.0.0")

  fs.writeFileSync(path.join(PROJECT_ROOT, "opencode.json"), config)
}

function validateEnvironment() {
  const required = ["QWEN_API_KEY"]
  const missing = required.filter(k => !process.env[k])
  if (missing.length > 0) {
    console.warn(`Missing environment variables: ${missing.join(", ")}`)
    console.warn("   Copy .env.example to .env and fill in values")
  }
}

function createDirectories() {
  const dirs = [
    "workspace/agentDoc",
    "workspace/ISG_Script",
    "workspace/isgScripts",
    "workspace/rtl",
    "coverageDB/template",
    "coverageDB/tasks",
    "coverageDB/regression",
    "logs",
  ]

  for (const dir of dirs) {
    const fullPath = path.join(PROJECT_ROOT, dir)
    if (!fs.existsSync(fullPath)) {
      fs.mkdirSync(fullPath, { recursive: true })
    }
  }
}

init()
