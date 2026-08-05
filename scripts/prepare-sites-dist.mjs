import { copyFileSync, mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

const distDir = join(process.cwd(), "dist");
const hostingSource = join(process.cwd(), ".openai", "hosting.json");
const hostingTarget = join(distDir, ".openai", "hosting.json");
const workerTarget = join(distDir, "server", "index.js");

mkdirSync(dirname(hostingTarget), { recursive: true });
mkdirSync(dirname(workerTarget), { recursive: true });

copyFileSync(hostingSource, hostingTarget);

writeFileSync(
  workerTarget,
  `export default {
  async fetch(request, env) {
    return env.ASSETS.fetch(request);
  }
};
`,
  "utf8"
);
