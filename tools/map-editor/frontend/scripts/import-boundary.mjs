#!/usr/bin/env node
// Standalone map editor dependency boundary (frontend design D1): the editor
// frontend may import from the game tree ONLY web/webclient-app/styles/
// tokens.css, styles/fonts*.css and the pure lib/ui_scale.js. It reuses the
// GM portal's scanner (scripts/gm-import-boundary.mjs) with the editor's own
// exact allowlist and aliases, so both apps resolve references identically.
// The build output (dist/), dependency trees and the node tests (fixture strings,
// never bundled) are not scanned.
import { join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import { formatViolations, listScannedSources, scanBoundary } from "../../../../scripts/gm-import-boundary.mjs";
import { EDITOR_ALIASES, EDITOR_ALLOWED_GAME_FILES } from "../editor-aliases.mjs";

export const EDITOR_IGNORE_DIRS = Object.freeze(["node_modules", "dist", "tests"]);

export function scanEditorBoundary({ appRoot, repoRoot }) {
  return scanBoundary({
    appRoot,
    repoRoot,
    aliases: EDITOR_ALIASES,
    allowedGameFiles: EDITOR_ALLOWED_GAME_FILES,
    ignoreDirs: EDITOR_IGNORE_DIRS,
  });
}

const isMain = process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url;
if (isMain) {
  const appRoot = fileURLToPath(new URL("..", import.meta.url));
  const repoRoot = join(appRoot, "../../..");
  const violations = scanEditorBoundary({ appRoot, repoRoot });
  const scanned = listScannedSources(appRoot, EDITOR_IGNORE_DIRS).length;
  if (process.argv.includes("--json")) {
    console.log(JSON.stringify({ scanned, violations }));
  } else if (violations.length) {
    console.error(`Map editor import boundary: ${violations.length} violation(s)\n${formatViolations(violations)}`);
  } else {
    console.log(`Map editor import boundary: ${scanned} sources import only the allowlisted game tokens, fonts and ui-scale`);
  }
  process.exit(violations.length ? 1 : 0);
}
