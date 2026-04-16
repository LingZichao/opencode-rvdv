import fs from "fs"
import path from "path"

const PROJECT_ROOT = path.resolve(import.meta.dir, "../../")

function validateEnv() {
  const envPath = path.join(PROJECT_ROOT, ".env")
  const examplePath = path.join(PROJECT_ROOT, ".env.example")

  if (!fs.existsSync(envPath)) {
    if (fs.existsSync(examplePath)) {
      console.warn(".env file not found. Copy .env.example to .env and fill in values:")
      console.warn("  cp .env.example .env")
    }
    return false
  }

  const envContent = fs.readFileSync(envPath, "utf-8")
  const requiredVars = ["QWEN_API_KEY"]
  const missing = requiredVars.filter(v => {
    const pattern = new RegExp(`^${v}=`, "m")
    const match = envContent.match(pattern)
    if (!match) return true
    const value = envContent.slice(match.index! + v.length + 1)
    const lineEnd = value.indexOf("\n")
    const val = lineEnd >= 0 ? value.slice(0, lineEnd).trim() : value.trim()
    return val === "" || val === `your_${v.toLowerCase()}_here`
  })

  if (missing.length > 0) {
    console.warn(`Required env vars not set: ${missing.join(", ")}`)
    return false
  }

  console.log("Environment validation passed")
  return true
}

validateEnv()