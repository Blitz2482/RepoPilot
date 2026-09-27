import fs from "node:fs";
import path from "node:path";

const root = path.resolve(process.cwd());
const pkg = JSON.parse(fs.readFileSync(path.join(root, "frontend/package.json"), "utf8"));
const vercel = JSON.parse(fs.readFileSync(path.join(root, "frontend/vercel.json"), "utf8"));
if (pkg.engines?.node !== ">=20 <25") throw new Error("Unexpected frontend Node engine range");
if (vercel.framework !== "nextjs") throw new Error("Vercel framework must be Next.js");
if (!fs.existsSync(path.join(root, ".nvmrc"))) throw new Error("Missing .nvmrc");
const nextConfig = fs.readFileSync(path.join(root, "frontend", "next.config.mjs"), "utf8");
if (!nextConfig.includes("poweredByHeader: false")) throw new Error("Next.js powered-by header must be disabled");
if (!nextConfig.includes("Strict-Transport-Security")) throw new Error("Missing frontend HSTS security header");
console.log("Frontend deployment configuration PASS");
