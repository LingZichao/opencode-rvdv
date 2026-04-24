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

  console.log("Environment validation passed")
  return true
}

validateEnv()