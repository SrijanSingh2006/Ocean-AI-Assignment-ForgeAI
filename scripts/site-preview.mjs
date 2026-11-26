import { spawn } from "node:child_process";
import { parseArgs } from "node:util";

const { values } = parseArgs({
  options: {
    host: { type: "string", default: "127.0.0.1" },
    port: { type: "string", default: process.env.PORT || "8000" },
    strictPort: { type: "boolean" },
  },
});
const child = spawn("python", ["-m", "forgeai", "serve", "--host", values.host, "--port", values.port], { stdio: "inherit" });
for (const signal of ["SIGINT", "SIGTERM"]) {
  process.on(signal, () => child.kill(signal));
}
child.on("exit", (status) => process.exit(status ?? 1));
child.on("error", (error) => { console.error(error.message); process.exit(1); });
