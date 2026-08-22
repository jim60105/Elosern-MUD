#!/usr/bin/env node
// Component-coverage gate: every required component story title registered in
// web/webclient-app/component-manifest.json must be exported by a Storybook
// story file under web/webclient-app, and every registered story title must be
// listed in the manifest (the reverse lint enforces that B-wave families keep
// the manifest in lockstep with the stories they add). A listed component is
// "undocumented" when its story file declares no named story export or no
// story bound to representative prop values (`args:`). B1 seeds the manifest
// with the core families, B2-B4 extend it, B5 freezes it to the complete
// required set; the "showcase is complete before wiring" gate is satisfied at
// B5, so while the manifest is empty (A2 foundation) this gate passes.
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const repoRoot = join(fileURLToPath(new URL("..", import.meta.url)));
const appRoot = join(repoRoot, "web/webclient-app");
// Optional first argument: an alternate manifest path (the test suite probes
// the gate with temporary manifests instead of mutating the tracked file).
const manifestPath =
  process.argv[2] ?? join(appRoot, "component-manifest.json");

const manifest = JSON.parse(readFileSync(manifestPath, "utf-8"));
const required = Array.isArray(manifest.required) ? manifest.required : [];
const requiredTitles = new Set(required);
// B5 freezes the manifest at the complete required set (design D3): the
// `frozen` flag turns the lockstep check into a complete-set check — a new
// story title or manifest entry still fails the gate, and the "showcase is
// complete" state fails closed on an empty set.
const frozen = manifest.frozen === true;
if (frozen && required.length === 0) {
  console.error(
    "component coverage: the frozen required-component manifest is empty " +
      "(the complete set cannot be empty while frozen)",
  );
  process.exit(1);
}

const storyFiles = [];

function collectStoryFiles(dir) {
  for (const entry of readdirSync(dir)) {
    const path = join(dir, entry);
    const stat = statSync(path);
    if (stat.isDirectory()) {
      if (entry === "node_modules" || entry.startsWith(".")) continue;
      collectStoryFiles(path);
      continue;
    }
    if (!entry.endsWith(".stories.js")) continue;
    const source = readFileSync(path, "utf-8");
    const match = source.match(/title:\s*["'`]([^"'`]+)["'`]/);
    if (!match) continue;
    storyFiles.push({ title: match[1], source });
  }
}

collectStoryFiles(appRoot);

const collected = new Set(storyFiles.map(({ title }) => title));
const failures = [];
const missing = required.filter((title) => !collected.has(title));
if (missing.length > 0) {
  const prefix = frozen
    ? `required stories (frozen manifest) missing a story file:`
    : "required stories missing a story file:";
  failures.push(prefix);
  for (const title of missing) failures.push(`  - ${title}`);
}
const unlisted = [...collected].filter((title) => !requiredTitles.has(title));
if (unlisted.length > 0) {
  const prefix = frozen
    ? `registered stories missing from the frozen required-component manifest (unfreezing required to add one):`
    : "registered stories missing from the required-component manifest:";
  failures.push(prefix);
  for (const title of unlisted) failures.push(`  - ${title}`);
}
if (failures.length > 0) {
  console.error("component coverage: " + failures.join("\n"));
  process.exit(1);
}

// A listed story file documents its component only when it declares at least
// one named story export bound to representative prop values (`args:`).
const hasStoryExport = /export\s+const\s+[A-Za-z_$][\w$]*\s*=\s*({|\()/;
const hasBoundStory = /\bargs\s*:/;
const undocumented = [
  ...new Set(
    storyFiles
      .filter(
        ({ title, source }) =>
          requiredTitles.has(title) &&
          (!hasStoryExport.test(source) || !hasBoundStory.test(source)),
      )
      .map(({ title }) => title),
  ),
].sort();
if (undocumented.length > 0) {
  console.error(
    "component coverage: required stories registered but undocumented (no " +
      'named story export or no `args:`-bound story):\n' +
      undocumented.map((title) => `  - ${title}`).join("\n"),
  );
  process.exit(1);
}

console.log(
  `component coverage: all ${required.length} required component(s) have stories ` +
    `and every one of the ${collected.size} registered story title(s) is listed ` +
    `(${collected.size} story title(s) total)` +
    (frozen ? ` — enforcing the frozen manifest (complete required set)` : ""),
);
