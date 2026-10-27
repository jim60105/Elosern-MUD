// Glyph shapes and the theme hook. A glyph's footprint comes from an explicit
// host descriptor, never from a payload node; a theme is completed and
// published under the package's own custom-property namespace.

import assert from "node:assert/strict";
import { test } from "node:test";

import { GATE_FOOTPRINT, GATE_HALF, HALO_R, HERE_GLOW_R, NODE_DOT_R, gatePath, glyphFootprint } from "../src/glyph.js";
import { DEFAULT_THEME, THEME_PREFIX, THEME_ROLES, resolveTheme, themeVars } from "../src/theme.js";

const close = (actual, expected, digits = 9) => assert.ok(Math.abs(actual - expected) < 10 ** -digits, `${actual} ≉ ${expected}`);

test("returns the painted footprint of each explicit glyph input", () => {
  // The travel halo's outer edge, stroke included, is the widest plain mark.
  assert.equal(glyphFootprint({ haloTarget: true }), HALO_R + 1);
  assert.equal(glyphFootprint({ state: "current" }), HERE_GLOW_R);
  assert.equal(glyphFootprint({ state: "current", haloTarget: true }), HALO_R + 1);
  // The gate's farthest painted point is a mitred base corner of the arch.
  assert.equal(glyphFootprint({ gateway: true }), GATE_FOOTPRINT);
  close(GATE_FOOTPRINT, Math.hypot(GATE_HALF + 1, GATE_HALF + 1));
  assert.equal(glyphFootprint({}), NODE_DOT_R + 1);
  // A haloed plain node keeps the halo, not the dot.
  assert.equal(glyphFootprint({ gateway: true, haloTarget: true }), HALO_R + 1);
});

test("scales the whole glyph footprint by the surface scale", () => {
  assert.equal(glyphFootprint({ haloTarget: true }, 0.75), (HALO_R + 1) * 0.75);
  close(glyphFootprint({ gateway: true }, 0.875), GATE_FOOTPRINT * 0.875);
  assert.equal(glyphFootprint({ state: "current" }, 2), HERE_GLOW_R * 2);
  assert.throws(() => glyphFootprint({}, 0), RangeError);
});

test("draws the gate arch only from the shared path", () => {
  assert.equal(gatePath(), "M-8 8 V-2 A8 8 0 0 1 8 -2 V8 Z");
  // The path is derived from the shared half-width, never duplicated.
  assert.ok(gatePath().includes(`M-${GATE_HALF} ${GATE_HALF}`));
});

test("fills omitted theme roles with neutral defaults", () => {
  const theme = resolveTheme({ accent: "var(--host-accent)" });
  assert.equal(theme.accent, "var(--host-accent)");
  for (const role of THEME_ROLES) {
    assert.equal(typeof theme[role], "string");
    assert.ok(theme[role].length > 0);
  }
  assert.equal(theme.node, DEFAULT_THEME.node);
  assert.ok(Object.isFrozen(theme));
  assert.deepEqual(resolveTheme(), DEFAULT_THEME);
});

test("rejects an unknown role and an empty value", () => {
  assert.throws(() => resolveTheme({ glowing: "#fff" }), TypeError);
  assert.throws(() => resolveTheme({ accent: "" }), TypeError);
  assert.throws(() => resolveTheme({ accent: 12 }), TypeError);
  assert.throws(() => resolveTheme([]), TypeError);
  assert.throws(() => resolveTheme(null), TypeError);
});

test("publishes a complete theme under the package namespace", () => {
  const theme = resolveTheme({ accentMuted: "#101010", halo: "var(--host-halo)" });
  const vars = themeVars(theme);
  assert.deepEqual(Object.keys(vars).sort(), THEME_ROLES.map((role) => `${THEME_PREFIX}-${role.replace(/[A-Z]/g, (l) => `-${l.toLowerCase()}`)}`).sort());
  assert.equal(vars["--map-view-accent-muted"], "#101010");
  assert.equal(vars["--map-view-halo"], "var(--host-halo)");
  assert.equal(vars["--map-view-node"], DEFAULT_THEME.node);
  assert.ok(Object.isFrozen(vars));
  // A host may publish the namespace under its own prefix.
  assert.equal(themeVars(theme, "--editor-map")["--editor-map-accent-muted"], "#101010");
  // A half-filled theme is refused, so a surface never publishes a gap.
  assert.throws(() => themeVars({ accent: "#fff" }), TypeError);
});
