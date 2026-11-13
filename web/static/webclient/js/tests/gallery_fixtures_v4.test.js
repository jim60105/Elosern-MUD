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

// The scene panels (change gallery-scene-category) are validated members of
// the exported set: scene subject keys, landscape card originals and the
// bundled-scene terminal are protocol-valid on the client mirror.
test("the scene panels are validated exports", async () => {
  const module = await import(FIXTURES);
  for (const name of ["GALLERY_V4_SCENE", "GALLERY_V4_SCENE_BUNDLED", "GALLERY_V4_SCENE_EMPTY"]) {
    const panel = module[name];
    assert.equal(panel.category, "scene", name);
    assert.ok(panel.groups.every((group) => group.subjects.every((row) => row.subject_key.startsWith("scene:"))), name);
    assert.doesNotThrow(() => Protocol.validateGalleryPanel(panel), name);
  }
  assert.equal(module.GALLERY_V4_SCENE_PANELS, undefined);
});
