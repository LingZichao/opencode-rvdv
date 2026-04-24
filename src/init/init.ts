import fs from "fs"
import path from "path"

const PROJECT_ROOT = path.resolve(import.meta.dir, "../../")
const SRC_DIR = path.join(PROJECT_ROOT, "src")
const RUNTIME_DIR = path.join(PROJECT_ROOT, ".opencode")

function init() {
  console.log("Initializing OpenCode-RVDV project...")

  fs.rmSync(RUNTIME_DIR, { recursive: true, force: true })

  const modules = ["commands", "prompts", "skills"]
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
  if (!process.env.PROJECT_ROOT) {
    console.warn("PROJECT_ROOT is not set. Using the project directory detected at runtime.")
  }
}

function createDirectories() {
  const dirs = [
    "workspace/agentDoc",
    "workspace/ISG_Script",
    "workspace/isgScripts",
    "workspace/rtl",
    ".opencode/skills/coverage/coverageDB/tasks",
    ".opencode/skills/coverage/coverageDB/regression",
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
