import fs from "fs"
import path from "path"

const PROJECT_ROOT = path.resolve(import.meta.dir, "../../")
const SRC_DIR = path.join(PROJECT_ROOT, "src")

function deployConfig() {
  const configFiles = [
    { src: "config/opencode.json.tmpl", dest: "opencode.json", process: true },
    { src: "config/server.json.tmpl", dest: ".opencode/server.json", process: true },
    { src: "config/providers.json.tmpl", dest: ".opencode/providers.json", process: false },
    { src: "config/permissions.json.tmpl", dest: ".opencode/permissions.json", process: false },
  ]

  for (const { src, dest, process } of configFiles) {
    const srcPath = path.join(SRC_DIR, src)
    if (!fs.existsSync(srcPath)) continue

    const destPath = path.join(PROJECT_ROOT, dest)
    const destDir = path.dirname(destPath)
    fs.mkdirSync(destDir, { recursive: true })

    let content = fs.readFileSync(srcPath, "utf-8")
    if (process) {
      content = content
        .replace(/\{\{PROJECT_ROOT\}\}/g, PROJECT_ROOT)
        .replace(/\{\{OPENCODE_PORT\}\}/g, process.env.OPENCODE_PORT || "4096")
        .replace(/\{\{OPENCODE_HOSTNAME\}\}/g, process.env.OPENCODE_HOSTNAME || "0.0.0.0")
    }

    fs.writeFileSync(destPath, content)
    console.log(`  Deployed: ${src} -> ${dest}`)
  }
}

deployConfig()