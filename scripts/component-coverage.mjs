#!/usr/bin/env node
// Component-coverage gate: every required component story title registered in
// web/webclient-app/component-manifest.json must be exported by a Storybook
// story file under web/webclient-app. B1 seeds the manifest with the core
// families, B2-B4 extend it, B5 freezes it to the complete required set; the
// "showcase is complete before wiring" gate is satisfied at B5, so while the
// manifest is empty (A2 foundation) this gate passes.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(fileURLToPath(new URL("..", import.meta.url)));
const appRoot = join(repoRoot, "web/webclient-app");
const manifestPath = join(appRoot, "component-manifest.json");

const manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
const required = Array.isArray(manifest.required) ? manifest.required : [];

const collected = new Set();

function collectStoryTitles(dir) {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) {
      if (entry === "node_modules" || entry.startsWith(".")) continue;
      collectStoryTitles(path);
      continue;
    }
    if (!entry.endsWith(".stories.js")) continue;
    const source = readFileSync(path, "utf-8");
    const match = source.match(/title:\s*["'`]([^"'`]+)["'`]/);
    if (match) collected.add(match[1]);
  }
}

collectStoryTitles(appRoot);

const missing = required.filter((title) => !collected.has(title));
if (missing.length > 0) {
  console.error("component coverage: required stories missing a story file:");
  for (const title of missing) console.error(`  - ${title}`);
  process.exit(1);
}

console.log(
  `component coverage: all ${required.length} required component(s) have stories ` +
    `(${collected.size} story title(s) registered)`,
);
