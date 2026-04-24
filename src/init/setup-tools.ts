import { execSync } from "child_process"
import path from "path"

const PROJECT_ROOT = path.resolve(import.meta.dir, "../../")

function setupTools() {
  console.log("Checking tool dependencies...")

  try {
    execSync("python3 --version", { stdio: "pipe" })
    console.log("  python3: OK")
  } catch {
    console.warn("  python3: NOT FOUND - required for coverage and simulation tools")
  }

  try {
    execSync("bun --version", { stdio: "pipe" })
    console.log("  bun: OK")
  } catch {
    console.warn("  bun: NOT FOUND - required for TypeScript tool execution")
  }

  try {
    const resp = execSync("curl -s http://localhost:5000/health", { stdio: "pipe" })
    console.log("  UCAPI server: OK")
  } catch {
    console.warn("  UCAPI server: NOT RUNNING - start it manually: python src/scripts/ucapi_server.py")
  }

}

setupTools()
