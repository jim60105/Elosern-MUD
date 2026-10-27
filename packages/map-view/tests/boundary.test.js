// The package boundary, checked on the real sources: only relative sibling
// imports, no DOM/network/timer access, no host stylesheet or design token,
// and a public entry that carries map primitives only.

import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import * as api from "../src/index.js";

const ROOT = join(dirname(fileURLToPath(import.meta.url)), "..");
const SRC = join(ROOT, "src");
const SOURCES = readdirSync(SRC).filter((name) => name.endsWith(".js")).sort();

function sourceOf(name) {
  return readFileSync(join(SRC, name), "utf8");
}

// Comments may quote an example value; the rule is about code.
function codeOf(name) {
  return sourceOf(name)
    .replace(/\/\*[\s\S]*?\*\//g, "")
    .replace(/^\s*\/\/.*$/gm, "");
}

test("imports only relative sibling modules", () => {
  assert.ok(SOURCES.length > 0);
  for (const name of SOURCES) {
    const source = sourceOf(name);
    const specifiers = [
      ...source.matchAll(/^import\s.*?from\s+"([^"]+)";$/gm),
      ...source.matchAll(/^export\s.*?from\s+"([^"]+)";$/gm),
    ].map((match) => match[1]);
    for (const specifier of specifiers) {
      assert.match(specifier, /^\.\/[a-z_]+\.js$/, `${name} imports ${specifier}`);
    }
    // No dynamic import, no require: the module graph stays static.
    assert.doesNotMatch(source, /\bimport\s*\(/, `${name} uses a dynamic import`);
    assert.doesNotMatch(source, /\brequire\s*\(/, `${name} uses require`);
  }
});

test("never touches the DOM, a timer, a network or host state", () => {
  const banned = /\b(document|window|globalThis|localStorage|sessionStorage|fetch|WebSocket|XMLHttpRequest|setTimeout|setInterval|requestAnimationFrame|process|navigator)\b/;
  for (const name of SOURCES) {
    assert.doesNotMatch(sourceOf(name), banned, `${name} reaches a host global`);
  }
});

test("ships no stylesheet and names no host design token", () => {
  for (const name of SOURCES) {
    const source = codeOf(name);
    assert.doesNotMatch(source, /\.css\b|@import\b|@font-face|url\(/, `${name} pulls in a stylesheet`);
    // Host-owned tokens stay with their host; only the package's own
    // `--map-view-*` namespace is allowed.
    assert.doesNotMatch(source, /--gold-|--paper-|--seal-|--map-label-|--motion-|--f-|--text-|--ui-scale/, `${name} names a host token`);
  }
});

test("declares no dependency and keeps the source list explicit", () => {
  const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
  assert.equal(pkg.name, "@elosern/map-view");
  assert.equal(pkg.type, "module");
  assert.deepEqual(pkg.exports, { ".": "./src/index.js" });
  assert.equal(pkg.dependencies, undefined);
  assert.equal(pkg.peerDependencies, undefined);
  for (const required of ["values.js", "projection.js", "navigation.js", "glyph.js", "theme.js", "index.js"]) {
    assert.ok(SOURCES.includes(required), `missing src/${required}`);
  }
});

test("exposes the documented public surface only", () => {
  assert.deepEqual(Object.keys(api).sort(), [
    "DEFAULT_MARGIN_PX",
    "DEFAULT_THEME",
    "DRAG_THRESHOLD_PX",
    "GATE_FOOTPRINT",
    "GATE_HALF",
    "GATE_STROKE",
    "HALO_R",
    "HERE_DOT_R",
    "HERE_GLOW_R",
    "HERE_RING_R",
    "MARKER_LANDMARK_R",
    "NODE_DOT_R",
    "STOP_STEP_TOLERANCE",
    "THEME_PREFIX",
    "THEME_ROLES",
    "UNITS",
    "WHEEL_ZOOM_BASE",
    "ZOOM_IN_SLACK",
    "ZOOM_OUT_SLACK",
    "boundsCentredOn",
    "boundsOfPoints",
    "cellCentre",
    "cellOf",
    "cellRect",
    "cellUnit",
    "centreOn",
    "clampToRect",
    "createStop",
    "createView",
    "dotField",
    "estimateTextWidth",
    "fitBounds",
    "formatDistance",
    "gatePath",
    "glyphFootprint",
    "insetRect",
    "isMetricLayer",
    "metricBounds",
    "metricPoints",
    "nearestStop",
    "nextStop",
    "niceStepAtLeast",
    "orderedStops",
    "panByPixels",
    "placeLabels",
    "previousStop",
    "project",
    "rectCentre",
    "rectsOverlap",
    "resolveTheme",
    "scaleBar",
    "scaleOf",
    "spanLimits",
    "themeVars",
    "toMetres",
    "unproject",
    "wheelFactor",
    "zoomAt",
    "zoomBy",
  ]);
});
