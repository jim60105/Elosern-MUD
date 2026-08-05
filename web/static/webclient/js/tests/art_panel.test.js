/*
 * DOM-independent tests for the art panel model (task 6.1).
 *
 * Runs with Node 24's built-in test runner and node:assert. Covers payload
 * validation acceptance/rejection (through the protocol validator), scene
 * placeholder and pending-with-prior states, catalog reduction, focus
 * adoption/survival rules, no-focus no-card, full-view open/close, and the
 * client-local focus bus.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const ArtPanel = require("../elosern/art_panel.js");
const ArtFocus = require("../elosern/art_focus.js");

function validScene(overrides) {
  return Object.assign(
    {
      archetype: "tavern_interior",
      label: "酒館內部",
      subject_key: "scene:tavern_interior",
      status: "done",
      url: "/art/scene/tavern_interior.png",
      aspect_ratio: "16:9",
      alt: "酒館內部場景",
      placeholder: null,
    },
    overrides
  );
}

function validEntry(overrides) {
  return Object.assign(
    {
      subject_key: "portrait:monster:low",
      status: "done",
      url: "/art/portrait/monster/low.png",
      aspect_ratio: "3:4",
      alt: "低階魔物",
      placeholder: null,
      context: { name: "哥布林", role: "敵方" },
    },
    overrides
  );
}

function validPanel(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      kind: "scene",
      scene: validScene(),
      portrait_catalog: {
        "1": validEntry({ context: { name: "英雄", role: "隊友" } }),
        "2": validEntry({ context: { name: "哥布林", role: "敵方" } }),
      },
    },
    overrides
  );
}

test("the validated art payload is accepted by the protocol reducer", () => {
  const panel = Protocol.validateArtPanel(validPanel());
  assert.equal(panel.available, true);
  assert.equal(panel.kind, "scene");
});

test("malformed art payloads are rejected by the protocol validator", () => {
  assert.throws(() => Protocol.validateArtPanel(validPanel({ kind: "combat" })));
  assert.throws(() =>
    Protocol.validateArtPanel(validPanel({ scene: validScene({ url: "https://x.test/a.png" }) }))
  );
  assert.throws(() =>
    Protocol.validateArtPanel(validPanel({ portrait_catalog: { x: validEntry() } }))
  );
  assert.throws(() =>
    Protocol.validateArtPanel(
      validPanel({ scene: validScene({ status: "pending", url: null, placeholder: null }) })
    )
  );
});

test("a done scene reduces to the asset state", () => {
  const model = ArtPanel.reducePanel(validPanel(), "exploration", {});
  assert.equal(model.available, true);
  assert.equal(model.scene.state, "asset");
  assert.equal(model.scene.url, "/art/scene/tavern_interior.png");
  assert.equal(model.scene.label, "酒館內部");
  assert.equal(model.scene.alt, "酒館內部場景");
});

test("a missing or failed scene reduces to the placeholder state", () => {
  const panel = validPanel({
    scene: validScene({
      status: "failed",
      url: null,
      placeholder: { kind: "missing", label: "未生成" },
    }),
  });
  const model = ArtPanel.reducePanel(panel, "exploration", {});
  assert.equal(model.scene.state, "placeholder");
  assert.equal(model.scene.placeholderKind, "missing");
  assert.equal(model.scene.url, null);
});

test("a pending scene with no prior image reduces to the placeholder state", () => {
  const panel = validPanel({
    scene: validScene({
      status: "pending",
      url: null,
      placeholder: { kind: "missing", label: "未生成" },
    }),
  });
  const model = ArtPanel.reducePanel(panel, "exploration", {});
  assert.equal(model.scene.state, "placeholder");
  assert.equal(model.scene.status, "pending");
  assert.equal(model.scene.url, null);
});

test("a pending scene with a prior image retains it dimmed", () => {
  const prior = ArtPanel.reducePanel(validPanel(), "exploration", {});
  assert.equal(prior.scene.state, "asset");
  const pending = validPanel({
    scene: validScene({
      status: "pending",
      url: null,
      placeholder: { kind: "missing", label: "未生成" },
    }),
  });
  const model = ArtPanel.reducePanel(pending, "exploration", prior);
  assert.equal(model.scene.state, "pending");
  assert.equal(model.scene.url, "/art/scene/tavern_interior.png");
});

test("catalog reduction keys entries by opaque catalog IDs", () => {
  const model = ArtPanel.reducePanel(validPanel(), "exploration", {});
  assert.deepEqual(Object.keys(model.catalog).sort(), ["1", "2"]);
  assert.equal(model.catalog["2"].name, "哥布林");
  assert.equal(model.catalog["2"].role, "敵方");
  assert.equal(model.catalog["2"].url, "/art/portrait/monster/low.png");
});

test("focus survives when its catalog ID survives", () => {
  const initial = ArtPanel.reducePanel(validPanel(), "exploration", { focusKey: "2" });
  assert.equal(initial.focusKey, "2");
  const next = ArtPanel.reducePanel(validPanel(), "exploration", initial);
  assert.equal(next.focusKey, "2");
});

test("a vanished focus adopts the mode rule", () => {
  // Exploration: a vanished focus means no focus.
  const model = ArtPanel.reducePanel(
    validPanel({ portrait_catalog: { "3": validEntry() } }),
    "exploration",
    { focusKey: "2" }
  );
  assert.equal(model.focusKey, null);
  assert.equal(ArtPanel.focusedEntry(model), null);

  // Combat: a vanished focus selects the first valid participant.
  const combat = ArtPanel.reducePanel(
    validPanel({ portrait_catalog: { "3": validEntry() } }),
    "combat",
    { focusKey: "2" }
  );
  assert.equal(combat.focusKey, "3");
});

test("no focus means no portrait card", () => {
  const model = ArtPanel.reducePanel(validPanel(), "exploration", { focusKey: null });
  assert.equal(model.focusKey, null);
  assert.equal(ArtPanel.focusedEntry(model), null);
});

test("combat with no prior focus selects the first participant", () => {
  const model = ArtPanel.reducePanel(validPanel(), "combat", {});
  assert.equal(model.focusKey, "1");
  assert.equal(ArtPanel.focusedEntry(model).name, "英雄");
});

test("moveFocus wraps within deterministic catalog order", () => {
  const model = ArtPanel.reducePanel(validPanel(), "combat", {});
  assert.equal(ArtPanel.moveFocus(model, 1), "2");
  assert.equal(ArtPanel.moveFocus(model, -1), "2");
});

test("scene and portrait full-view state is preserved across reduction", () => {
  const previous = {
    focusKey: "2",
    sceneFullView: true,
    portraitFullView: false,
  };
  const model = ArtPanel.reducePanel(validPanel(), "exploration", previous);
  assert.equal(model.sceneFullView, true);
  assert.equal(model.portraitFullView, false);
});

test("a placeholder catalog entry has no URL", () => {
  const panel = validPanel({
    portrait_catalog: {
      "2": validEntry({
        subject_key: null,
        status: null,
        url: null,
        aspect_ratio: null,
        placeholder: { kind: "unavailable", label: "無法提供" },
      }),
    },
  });
  const model = ArtPanel.reducePanel(panel, "combat", {});
  assert.equal(model.catalog["2"].url, null);
  assert.equal(model.catalog["2"].placeholderKind, "unavailable");
});

test("the client-local focus bus publishes and delivers without a packet", () => {
  const bus = ArtFocus.createBus();
  const seen = [];
  const unsubscribe = bus.subscribe((key) => seen.push(key));
  bus.publish("42");
  bus.publish(null);
  unsubscribe();
  bus.publish("99");
  assert.deepEqual(seen, ["42", null]);
});

test("a broken focus subscriber cannot break the bus", () => {
  const bus = ArtFocus.createBus();
  bus.subscribe(() => {
    throw new Error("boom");
  });
  const seen = [];
  bus.subscribe((key) => seen.push(key));
  assert.doesNotThrow(() => bus.publish("7"));
  assert.deepEqual(seen, ["7"]);
});
