import { copyFileSync, cpSync, mkdirSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";

const distDir = join(process.cwd(), "dist");
const clientDir = join(distDir, "client");
const hostingSource = join(process.cwd(), ".openai", "hosting.json");
const hostingTarget = join(distDir, ".openai", "hosting.json");
const workerTarget = join(distDir, "server", "index.js");

mkdirSync(clientDir, { recursive: true });
mkdirSync(dirname(hostingTarget), { recursive: true });
mkdirSync(dirname(workerTarget), { recursive: true });

for (const entry of readdirSync(distDir, { withFileTypes: true })) {
  if ([".openai", "client", "server"].includes(entry.name)) {
    continue;
  }

  cpSync(join(distDir, entry.name), join(clientDir, entry.name), { recursive: true });
}

copyFileSync(hostingSource, hostingTarget);

writeFileSync(
  workerTarget,
  `export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const acceptsHtml = request.headers.get("accept")?.includes("text/html");

    if (url.pathname === "/") {
      url.pathname = "/index.html";
    }

    let response = await env.ASSETS.fetch(new Request(url, request));

    if (response.status === 404 && acceptsHtml) {
      url.pathname = "/index.html";
      response = await env.ASSETS.fetch(new Request(url, request));
    }

    return response;
  }
};
`,
  "utf8"
);
