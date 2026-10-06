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
// The GM portal (gm-portal-s1-foundation) keeps its own frozen manifest of
// `GM/<Component>` story titles under web/admin-app; it is checked after the
// game gate passes, with the same lockstep and documentation rules plus a
// file-level check that every components/Gm*.vue is listed.
const gmAppRoot = join(repoRoot, "web/admin-app");
// Optional first argument: an alternate manifest path (the test suite probes
// the gate with temporary manifests instead of mutating the tracked file).
// `--gm-manifest <path>` likewise swaps the GM manifest for a probe.
const cliArgs = process.argv.slice(2);
const gmFlag = cliArgs.indexOf("--gm-manifest");
const gmManifestPath =
  gmFlag === -1 ? join(gmAppRoot, "component-manifest.json") : cliArgs[gmFlag + 1];
const positional = cliArgs.filter(
  (arg, index) => arg !== "--gm-manifest" && (gmFlag === -1 || index !== gmFlag + 1),
);
const manifestPath = positional[0] ?? join(appRoot, "component-manifest.json");

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

// Concurrent showcase-evidence gates create transient story trees under the
// app root (mkdtemp tmp directories) and delete them when done. A scan that
// walks the tree concurrently can therefore observe an entry vanish between
// enumeration and stat/read; an ENOENT on a transient path means the file is
// gone (not a required story), never a scan failure. Anything else rethrows.
function readdirSafe(dir) {
  try {
    return readdirSync(dir);
  } catch (error) {
    if (error.code === "ENOENT") return [];
    throw error;
  }
}

function statSafe(path) {
  try {
    return statSync(path);
  } catch (error) {
    if (error.code === "ENOENT") return null;
    throw error;
  }
}

function collectStoryFiles(dir, out = storyFiles) {
  for (const entry of readdirSafe(dir)) {
    const path = join(dir, entry);
    const stat = statSafe(path);
    if (stat === null) continue;
    if (stat.isDirectory()) {
      if (entry === "node_modules" || entry.startsWith(".")) continue;
      collectStoryFiles(path, out);
      continue;
    }
    if (!entry.endsWith(".stories.js")) continue;
    let source;
    try {
      source = readFileSync(path, "utf-8");
    } catch (error) {
      if (error.code === "ENOENT") continue;
      throw error;
    }
    const match = source.match(/title:\s*["'`]([^"'`]+)["'`]/);
    if (!match) continue;
    out.push({ title: match[1], source });
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

// GM portal gate: the same rules over web/admin-app's own manifest.
const gmManifest = JSON.parse(readFileSync(gmManifestPath, "utf-8"));
const gmRequired = Array.isArray(gmManifest.required) ? gmManifest.required : [];
const gmStories = [];
collectStoryFiles(gmAppRoot, gmStories);
const gmCollected = new Set(gmStories.map(({ title }) => title));
const gmFailures = [];
if (gmManifest.frozen === true && gmRequired.length === 0) {
  gmFailures.push("the frozen GM manifest is empty");
}
for (const title of gmRequired) {
  if (!title.startsWith("GM/")) gmFailures.push(`GM title outside the GM/ namespace: ${title}`);
  if (!gmCollected.has(title)) gmFailures.push(`required GM story missing a story file: ${title}`);
}
for (const title of gmCollected) {
  if (!gmRequired.includes(title)) {
    gmFailures.push(`registered GM story missing from the GM manifest: ${title}`);
  }
}
for (const entry of readdirSafe(join(gmAppRoot, "components"))) {
  const match = entry.match(/^(Gm\w+)\.vue$/);
  if (match && !gmRequired.includes(`GM/${match[1]}`)) {
    gmFailures.push(`GM component without a manifest entry: components/${entry}`);
  }
}
for (const { title, source } of gmStories) {
  if (gmRequired.includes(title) && (!hasStoryExport.test(source) || !hasBoundStory.test(source))) {
    gmFailures.push(`required GM story registered but undocumented: ${title}`);
  }
}
if (gmFailures.length > 0) {
  console.error("GM component coverage:\n" + gmFailures.map((line) => `  - ${line}`).join("\n"));
  process.exit(1);
}

console.log(
  `component coverage: all ${required.length} required component(s) have stories ` +
    `and every one of the ${collected.size} registered story title(s) is listed ` +
    `(${collected.size} story title(s) total)` +
    (frozen ? ` — enforcing the frozen manifest (complete required set)` : ""),
);
console.log(
  `GM component coverage: all ${gmRequired.length} required GM component(s) have ` +
    `documented stories and every GM story title is listed`,
);
