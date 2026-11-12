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

test("every exported v4 gallery fixture passes validateGalleryPanelV4", async () => {
  const module = await import(FIXTURES);
  const panels = Object.entries(module).filter(
    ([, value]) => value !== null && typeof value === "object" && value.kind === "gallery",
  );
  // Guard against a vacuous pass: the fixture module exports several panels.
  assert.ok(panels.length >= 5, `expected at least five panels, found ${panels.length}`);
  for (const [name, panel] of panels) {
    assert.equal(panel.schema_version, Protocol.GALLERY_V4_SCHEMA_VERSION, name);
    assert.doesNotThrow(() => Protocol.validateGalleryPanelV4(panel), name);
  }
});
