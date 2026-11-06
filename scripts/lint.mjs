// A dependency-free lint: every script must parse, and the page must declare its doctype and language.
import { spawnSync } from "node:child_process";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const root = new URL("..", import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, "$1");
const problems = [];

function* files(dir) {
  for (const name of readdirSync(dir)) {
    if (name === "node_modules" || name.startsWith(".")) continue;
    const path = join(dir, name);
    if (statSync(path).isDirectory()) yield* files(path);
    else yield path;
  }
}

for (const file of files(root)) {
  if (!/\.(m?js)$/.test(file)) continue;
  const result = spawnSync(process.execPath, ["--check", file], { encoding: "utf8" });
  if (result.status !== 0) problems.push(`${file}: ${result.stderr.trim().split("\n")[0]}`);
  if (/\bconsole\.log\(/.test(readFileSync(file, "utf8")) && !file.includes("scripts")) {
    problems.push(`${file}: leftover console.log`);
  }
}

const html = readFileSync(join(root, "index.html"), "utf8");
if (!/^<!doctype html>/i.test(html)) problems.push("index.html: missing <!doctype html>");
if (!/<html[^>]*\slang=/.test(html)) problems.push("index.html: <html> has no lang attribute");

if (problems.length) {
  console.error(problems.join("\n"));
  process.exit(1);
}
console.log("lint ok");
