/*
 * The shared v4 gallery story fixtures stay protocol-valid (change
 * gallery-v4-validators): every panel exported by
 * web/webclient-app/stories/gallery-fixtures-v4.js passes the version-4
 * client validator, so stories and component tests never render a shape the
 * wire would reject.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");
const path = require("node:path");
const { pathToFileURL } = require("node:url");

const Protocol = require("../elosern/protocol.js");

const FIXTURES = pathToFileURL(
  path.join(__dirname, "../../../../webclient-app/stories/gallery-fixtures-v4.js"),
).href;

test("every exported v4 gallery fixture passes validateGalleryPanel", async () => {
  const module = await import(FIXTURES);
  const panels = Object.entries(module).filter(
    ([, value]) => value !== null && typeof value === "object" && value.kind === "gallery",
  );
  // Guard against a vacuous pass: the fixture module exports several panels.
  assert.ok(panels.length >= 5, `expected at least five panels, found ${panels.length}`);
  for (const [name, panel] of panels) {
    assert.equal(panel.schema_version, Protocol.GALLERY_SCHEMA_VERSION, name);
    assert.doesNotThrow(() => Protocol.validateGalleryPanel(panel), name);
  }
});

// The scene panels (change gallery-landscape-page) are rendered by the
// landscape page before gallery-scene-category admits `scene:<archetype>`
// subject keys, so they live in a container rather than among the validated
// panels. This pin fails once the validator admits scene keys; the panels then
// move into the validated set and this test is removed.
test("the scene panels are refused for their scene subject key until scenes are admitted", async () => {
  const module = await import(FIXTURES);
  const panels = Object.entries(module.GALLERY_V4_SCENE_PANELS);
  assert.ok(panels.length >= 2, `expected the scene panels, found ${panels.length}`);
  for (const [name, panel] of panels) {
    assert.equal(panel.kind, "gallery", name);
    assert.equal(panel.schema_version, Protocol.GALLERY_SCHEMA_VERSION, name);
    assert.ok(panel.groups.every((group) => group.subjects.every((row) => row.subject_key.startsWith("scene:"))), name);
    assert.throws(() => Protocol.validateGalleryPanel(panel), /^Error: invalid gallery subject$/, name);
  }
});
