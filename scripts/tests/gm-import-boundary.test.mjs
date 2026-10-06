// Dependency-free Node test for the GM import boundary
// (gm-portal-s1-foundation). Fixture trees are generated in a temporary
// directory, outside web/admin-app, so the real scan never sees them.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { formatViolations, scanBoundary } from "../gm-import-boundary.mjs";
import { GM_ALIASES } from "../../web/admin-app/gm-aliases.mjs";

const REPO_ROOT = fileURLToPath(new URL("../..", import.meta.url));

function fixtureRepo(files) {
  const root = mkdtempSync(join(tmpdir(), "gm-boundary-"));
  const base = {
    "web/webclient-app/styles/tokens.css": ":root{}",
    "web/webclient-app/styles/fonts.css": "",
    "web/webclient-app/styles/fonts-mono.css": "",
    "web/webclient-app/styles/app-shell.css": "",
    "web/webclient-app/styles/tokens.css.evil": "",
    "web/webclient-app/components/TopBar.vue": "<template><i/></template>",
    "web/webclient-app/stores/game.js": "export {}",
    "web/webclient-app/transport.js": "export {}",
    "web/static/webclient/js/elosern/protocol.js": "module.exports = {}",
    "web/admin-app/lib/local.js": "export const x = 1;",
  };
  for (const [path, content] of Object.entries({ ...base, ...files })) {
    mkdirSync(dirname(join(root, path)), { recursive: true });
    writeFileSync(join(root, path), content);
  }
  return root;
}

function scan(files) {
  const repoRoot = fixtureRepo(files);
  try {
    return scanBoundary({ appRoot: join(repoRoot, "web/admin-app"), repoRoot, aliases: GM_ALIASES });
  } finally {
    rmSync(repoRoot, { recursive: true, force: true });
  }
}

test("the real GM tree imports only allowlisted tokens and fonts", () => {
  const violations = scanBoundary({
    appRoot: join(REPO_ROOT, "web/admin-app"),
    repoRoot: REPO_ROOT,
    aliases: GM_ALIASES,
  });
  assert.deepEqual(violations, [], formatViolations(violations));
});

test("allowed token and font imports pass in every spelling", () => {
  const violations = scan({
    "web/admin-app/main.js": [
      'import "../webclient-app/styles/tokens.css";',
      'import "@elosern/styles/fonts.css";',
      'import "@elosern/styles/fonts-mono.css?inline";',
      'import { x } from "./lib/local.js";',
      'import { x as y } from "@gm/lib/local.js";',
      'import { createApp } from "vue";',
      'export { x } from "./lib/local.js";',
      'const lazy = () => import("./lib/local.js");',
      '// import "../webclient-app/styles/app-shell.css";',
    ].join("\n"),
    "web/admin-app/styles/gm.css": '@import "../../webclient-app/styles/tokens.css";\n.a{background:url(data:image/png;base64,AAA)}',
    "web/admin-app/components/GmX.vue":
      '<template><i/></template>\n<script setup>\nimport "/web/webclient-app/styles/fonts.css";\n</script>\n<style scoped>\n@import url("@elosern/styles/tokens.css");\n.a { color: red; }\n</style>',
  });
  assert.deepEqual(violations, [], formatViolations(violations));
});

const FORBIDDEN = {
  "game component (JS import)": ["web/admin-app/a.js", 'import TopBar from "../webclient-app/components/TopBar.vue";'],
  "app-shell stylesheet": ["web/admin-app/a.js", 'import "../webclient-app/styles/app-shell.css";'],
  "alternate relative path": ["web/admin-app/lib/a.js", 'import "../../admin-app/../webclient-app/styles/./app-shell.css";'],
  "alias to a non-token file": ["web/admin-app/a.js", 'import "@elosern/styles/app-shell.css";'],
  "alias escaping the styles dir": ["web/admin-app/a.js", 'import "@elosern/styles/../stores/game.js";'],
  "suffix-extended token name": ["web/admin-app/a.js", 'import "@elosern/styles/tokens.css.evil";'],
  "root-absolute game path": ["web/admin-app/a.js", 'import "/web/webclient-app/transport.js";'],
  "game protocol under web/static": ["web/admin-app/a.js", 'import P from "../static/webclient/js/elosern/protocol.js";'],
  "re-export": ["web/admin-app/a.js", 'export * from "../webclient-app/stores/game.js";'],
  "named re-export": ["web/admin-app/a.js", 'export { useGame } from "../webclient-app/stores/game.js";'],
  "literal dynamic import": ["web/admin-app/a.js", 'const m = () => import("../webclient-app/stores/game.js");'],
  "non-literal dynamic import": ["web/admin-app/a.js", "const m = (p) => import(p);"],
  "import.meta.glob": ["web/admin-app/a.js", 'const all = import.meta.glob("../webclient-app/components/*.vue");'],
  "new URL asset": ["web/admin-app/a.js", 'const u = new URL("../webclient-app/transport.js", import.meta.url);'],
  "require": ["web/admin-app/a.cjs", 'const t = require("../webclient-app/transport.js");'],
  "CSS @import": ["web/admin-app/s.css", '@import "../webclient-app/styles/app-shell.css";'],
  "CSS url()": ["web/admin-app/s.css", '.a { background: url("../webclient-app/styles/app-shell.css"); }'],
  "Vue script import": ["web/admin-app/C.vue", '<script setup>\nimport TopBar from "../webclient-app/components/TopBar.vue";\n</script>'],
  "Vue style @import": ["web/admin-app/C.vue", '<style>\n@import "../webclient-app/styles/app-shell.css";\n</style>'],
  "Vue style src": ["web/admin-app/C.vue", '<style src="../webclient-app/styles/app-shell.css"></style>'],
};

for (const [label, [file, content]] of Object.entries(FORBIDDEN)) {
  test(`forbidden: ${label} fails with source and dependency`, () => {
    const violations = scan({ [file]: content });
    assert.equal(violations.length, 1, formatViolations(violations));
    assert.equal(violations[0].source, file);
    assert.ok(violations[0].specifier, "the diagnostic names the dependency");
    assert.match(formatViolations(violations), new RegExp(file.replace(/[.]/g, "\\.")));
  });
}

test("forbidden: a symlink into the game tree is resolved before the allowlist", () => {
  const repoRoot = fixtureRepo({ "web/admin-app/a.js": 'import "./linked/app-shell.css";' });
  try {
    symlinkSync(join(repoRoot, "web/webclient-app/styles"), join(repoRoot, "web/admin-app/linked"));
    const violations = scanBoundary({ appRoot: join(repoRoot, "web/admin-app"), repoRoot, aliases: GM_ALIASES });
    // The symlinked directory is itself walked (its CSS files are not GM
    // sources but plain files), so assert on the importer's violation.
    const fromImporter = violations.filter((v) => v.source === "web/admin-app/a.js");
    assert.equal(fromImporter.length, 1, formatViolations(violations));
    assert.equal(fromImporter[0].resolved, "web/webclient-app/styles/app-shell.css");
  } finally {
    rmSync(repoRoot, { recursive: true, force: true });
  }
});
