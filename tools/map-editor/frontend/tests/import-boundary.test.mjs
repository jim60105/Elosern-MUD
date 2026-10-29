// The editor's game-tree allowlist: tokens, font faces and ui-scale only.
// Fixture trees are generated in a temporary directory so the real scan never
// sees them.
import { test } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { scanEditorBoundary } from "../scripts/import-boundary.mjs";

const FRONTEND = fileURLToPath(new URL("..", import.meta.url));
const REPO_ROOT = join(FRONTEND, "../../..");
const APP = "tools/map-editor/frontend";

function scan(files) {
  const root = mkdtempSync(join(tmpdir(), "editor-boundary-"));
  const base = {
    "web/webclient-app/styles/tokens.css": ":root{}",
    "web/webclient-app/styles/fonts.css": "",
    "web/webclient-app/styles/fonts-mono.css": "",
    "web/webclient-app/styles/app-shell.css": "",
    "web/webclient-app/lib/ui_scale.js": "export {}",
    "web/webclient-app/lib/map_glyphs.js": "export {}",
    "web/webclient-app/components/TopBar.vue": "<template><i/></template>",
    "web/webclient-app/stores/game.js": "export {}",
    "web/webclient-app/transport.js": "export {}",
    "web/static/webclient/js/elosern/protocol.js": "module.exports = {}",
    "packages/map-view/src/index.js": "export {}",
    [`${APP}/src/local.js`]: "export const x = 1;",
  };
  try {
    for (const [path, content] of Object.entries({ ...base, ...files })) {
      mkdirSync(dirname(join(root, path)), { recursive: true });
      writeFileSync(join(root, path), content);
    }
    return scanEditorBoundary({ appRoot: join(root, APP), repoRoot: root });
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

test("the real editor tree imports only the allowlisted game files", () => {
  assert.deepEqual(scanEditorBoundary({ appRoot: FRONTEND, repoRoot: REPO_ROOT }), []);
});

test("tokens, fonts, ui-scale, map-view and bare packages are allowed", () => {
  const violations = scan({
    [`${APP}/src/main.js`]: [
      'import "@game/tokens.css";',
      'import "@game/fonts.css";',
      'import "@game/fonts-mono.css";',
      'import { installUiScale } from "@game/ui_scale.js";',
      'import { project } from "../../../../packages/map-view/src/index.js";',
      'import { createApp } from "vue";',
    ].join("\n"),
  });
  assert.deepEqual(violations, []);
});

for (const [label, specifier] of [
  ["the game shell stylesheet", "../../../../web/webclient-app/styles/app-shell.css"],
  ["a game store", "../../../../web/webclient-app/stores/game.js"],
  ["a game component", "../../../../web/webclient-app/components/TopBar.vue"],
  ["the game transport", "../../../../web/webclient-app/transport.js"],
  ["another game lib module", "../../../../web/webclient-app/lib/map_glyphs.js"],
  ["the preserved protocol", "/web/static/webclient/js/elosern/protocol.js"],
]) {
  test(`importing ${label} is a violation`, () => {
    const violations = scan({ [`${APP}/src/bad.js`]: `import x from "${specifier}";` });
    assert.equal(violations.length, 1);
    assert.match(violations[0].reason, /forbidden game-tree dependency/);
  });
}

test("a CSS import of the game shell and a non-literal dynamic import fail closed", () => {
  const css = scan({ [`${APP}/src/x.css`]: '@import "../../../../web/webclient-app/styles/app-shell.css";' });
  assert.equal(css.length, 1);
  const dynamic = scan({ [`${APP}/src/y.js`]: "const m = await import(name);" });
  assert.equal(dynamic[0].reason, "unresolvable reference");
});

test("build output and dependencies are not scanned as authored source", () => {
  const violations = scan({
    [`${APP}/dist/assets/index.js`]: "const m = await import(name);",
    [`${APP}/capture-dist/assets/index.js`]: "const m = await import(name);",
    [`${APP}/node_modules/x/index.js`]: 'import "../../../../../web/webclient-app/stores/game.js";',
  });
  assert.deepEqual(violations, []);
});
