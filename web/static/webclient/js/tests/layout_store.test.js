/*
 * DOM-independent tests for versioned layout persistence.
 *
 * Runs with Node 24's built-in test runner. Covers known migration, unknown /
 * malformed / oversized reset, required-component restoration, bounded wrapper
 * validation, and rejection of canonical state, identity, request, command,
 * epoch, revision, and panel fields from browser storage.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const LayoutStore = require("../elosern/layout_store.js");

function mockStorage(initial) {
  const data = Object.assign({}, initial);
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(data, key) ? data[key] : null;
    },
    setItem(key, value) {
      data[key] = String(value);
    },
    removeItem(key) {
      delete data[key];
    },
    keys() {
      return Object.keys(data);
    },
  };
}

function defaultStore(initial) {
  // Accept either raw seed data or an already-built mock storage.
  if (initial && typeof initial.getItem === "function") {
    return LayoutStore.createStore({ storage: initial });
  }
  return LayoutStore.createStore({ storage: mockStorage(initial) });
}

function wrapper(overrides) {
  return Object.assign(
    {
      layout_version: 1,
      dimensions: { narrative: 62 },
      tabs: {},
      preferences: { text2html: true },
    },
    overrides
  );
}

function allRequiredPresent(config) {
  const present = [];
  (function walk(item) {
    if (item && Array.isArray(item.content)) {
      item.content.forEach(walk);
    }
    if (item && item.type === "component") {
      present.push(item.componentName);
    }
  })(config);
  return LayoutStore.REQUIRED_COMPONENTS.every((name) => present.indexOf(name) !== -1);
}

function componentByName(config, name) {
  let found = null;
  (function walk(item) {
    if (item && item.type === "component" && item.componentName === name) {
      found = item;
    }
    if (item && Array.isArray(item.content)) {
      item.content.forEach(walk);
    }
  })(config);
  return found;
}

test("default wrapper is versioned and bounded", () => {
  const def = LayoutStore.defaultWrapper();
  assert.equal(def.layout_version, 1);
  assert.ok(JSON.stringify(def).length <= LayoutStore.MAX_STORAGE_BYTES);
});

test("missing storage loads the version-1 default", () => {
  const store = defaultStore();
  const result = store.load();
  assert.deepEqual(result.state, LayoutStore.defaultWrapper());
  assert.ok(allRequiredPresent(result.config));
});

test("a known layout version migrates to the current version", () => {
  const migrations = {
    1: (raw) => Object.assign({}, raw, { layout_version: 2 }),
    2: (raw) => raw,
  };
  const storage = mockStorage({
    "elosern.layout": JSON.stringify(
      wrapper({ layout_version: 1, dimensions: { narrative: 55 } })
    ),
  });
  const store = LayoutStore.createStore({ storage, currentVersion: 2, migrations });
  const result = store.load();
  assert.equal(result.state.layout_version, 2);
  assert.equal(result.state.dimensions.narrative, 55);
  assert.equal(result.state.preferences.text2html, true);
  // The migrated version is written back for future loads.
  assert.equal(JSON.parse(storage.getItem("elosern.layout")).layout_version, 2);
});

test("unknown layout version resets to the approved default", () => {
  const storage = mockStorage({
    "elosern.layout": JSON.stringify(wrapper({ layout_version: 99 })),
  });
  const store = defaultStore(storage);
  const result = store.load();
  assert.deepEqual(result.state, LayoutStore.defaultWrapper());
  assert.deepEqual(JSON.parse(storage.getItem("elosern.layout")), LayoutStore.defaultWrapper());
});

test("malformed stored JSON resets to the approved default", () => {
  const storage = mockStorage({ "elosern.layout": "{not json" });
  const store = defaultStore(storage);
  const result = store.load();
  assert.deepEqual(result.state, LayoutStore.defaultWrapper());
});

test("missing layout_version resets to the approved default", () => {
  const storage = mockStorage({
    "elosern.layout": JSON.stringify(wrapper({ layout_version: undefined })),
  });
  const store = defaultStore(storage);
  assert.deepEqual(store.load().state, LayoutStore.defaultWrapper());
});

test("oversized stored wrappers reset to the approved default", () => {
  const storage = mockStorage({
    "elosern.layout": JSON.stringify(
      wrapper({ layout_version: 1, junk: "x".repeat(5000) })
    ),
  });
  const store = defaultStore(storage);
  const result = store.load();
  assert.deepEqual(result.state, LayoutStore.defaultWrapper());
});

test("canonical state, identity, request, command, epoch, revision, and panel fields are rejected", () => {
  const forbiddenTopLevel = [
    "presentation_epoch",
    "revision",
    "panels",
    "actor",
    "actor_id",
    "request_id",
    "command",
    "command_text",
    "server_time",
    "generation",
    "retired_epochs",
    "result",
  ];
  forbiddenTopLevel.forEach((field) => {
    const storage = mockStorage({
      "elosern.layout": JSON.stringify(wrapper({ layout_version: 1, [field]: "anything" })),
    });
    const store = defaultStore(storage);
    const result = store.load();
    assert.deepEqual(
      result.state,
      LayoutStore.defaultWrapper(),
      `field ${field} must be rejected`
    );
    assert.equal(
      LayoutStore.validateWrapper(wrapper({ layout_version: 1, [field]: "anything" })),
      null,
      `validateWrapper must reject field ${field}`
    );
  });
});

test("stock Evennia GoldenLayout keys are never imported", () => {
  const storage = mockStorage({
    evenniaGoldenLayoutSavedState: JSON.stringify({ content: [{ type: "component" }] }),
    evenniaGoldenLayoutSavedStateName: "default",
  });
  const store = defaultStore(storage);
  const result = store.load();
  assert.deepEqual(result.state, LayoutStore.defaultWrapper());
  assert.ok(allRequiredPresent(result.config), "default layout has every required component");
});

test("save persists only bounded dimensions and harmless preferences", () => {
  const store = defaultStore();
  const saved = store.save({
    layout_version: 1,
    dimensions: { narrative: 62, epoch: 999, "action-dock": 11 },
    tabs: { status: true, evil: true },
    preferences: { text2html: false, fontScale: 1.1, evil: 1 },
  });
  assert.equal(saved, true);
  const stored = JSON.parse(store.storage.getItem(LayoutStore.STORAGE_KEY));
  assert.deepEqual(stored.dimensions, { narrative: 62, "action-dock": 11 });
  assert.deepEqual(stored.tabs, { status: true });
  assert.deepEqual(stored.preferences, { text2html: false, fontScale: 1.1 });
});

test("save rejects wrappers carrying canonical state", () => {
  const storage = mockStorage({});
  const store = defaultStore(storage);
  assert.equal(
    store.save({ layout_version: 1, panels: { status: { available: true } } }),
    false
  );
  assert.equal(
    store.save({ layout_version: 1, revision: 3 }),
    false
  );
  assert.equal(storage.getItem(LayoutStore.STORAGE_KEY), null, "nothing persisted");
});

test("save rejects unknown versions and malformed wrappers", () => {
  const store = defaultStore();
  assert.equal(store.save({ layout_version: 7 }), false);
  assert.equal(store.save("nonsense"), false);
  assert.equal(store.save(null), false);
});

test("fontScale preference is bounded", () => {
  const store = defaultStore();
  const saved = store.save(
    wrapper({ preferences: { text2html: true, fontScale: 99 } })
  );
  assert.equal(saved, true);
  const stored = JSON.parse(store.storage.getItem(LayoutStore.STORAGE_KEY));
  assert.deepEqual(stored.preferences, { text2html: true }, "out-of-range fontScale dropped");
});

// H5 (webclient-hud-05-overlays-and-command-line, task 9.2): the two added
// PREFERENCE_TYPES keys (reducedMotion, colorblind) — a version-1 wrapper
// lacking the keys still normalizes and no version bump occurs.
test("a version-1 wrapper lacking the H5 preference keys still normalizes without a version bump", () => {
  const validated = LayoutStore.validateWrapper(
    wrapper({ preferences: { text2html: true, fontScale: 1.12 } })
  );
  assert.ok(validated, "the old wrapper is valid");
  assert.equal(validated.layout_version, 1, "no version bump");
  assert.deepEqual(
    validated.preferences,
    { text2html: true, fontScale: 1.12 },
    "unknown preference keys are dropped, known keys kept"
  );
});

test("the H5 preference keys (reducedMotion, colorblind) validate as booleans", () => {
  const store = defaultStore();
  const saved = store.save(
    wrapper({
      preferences: {
        text2html: true,
        fontScale: 0.92,
        reducedMotion: false,
        colorblind: true,
        evil: "x",
      }
    })
  );
  assert.equal(saved, true);
  const stored = JSON.parse(store.storage.getItem(LayoutStore.STORAGE_KEY));
  assert.deepEqual(
    stored.preferences,
    { text2html: true, fontScale: 0.92, reducedMotion: false, colorblind: true }
  );
});

test("required components are preserved and never closable", () => {
  const config = LayoutStore.buildConfig(LayoutStore.defaultWrapper());
  assert.ok(allRequiredPresent(config));
  LayoutStore.REQUIRED_COMPONENTS.forEach((name) => {
    const item = componentByName(config, name);
    assert.ok(item, `${name} present`);
    assert.equal(item.isClosable, false, `${name} is not permanently closable`);
  });
  assert.ok(componentByName(config, "command-drawer").id === "inputComponent");
});

test("restoreRequiredComponents re-adds missing required components", () => {
  const config = JSON.parse(JSON.stringify(LayoutStore.DEFAULT_LAYOUT_CONFIG));
  const column = config.content[0].content[0];
  column.content = column.content.filter((item) => item.componentName !== "action-dock");
  assert.equal(componentByName(config, "action-dock"), null);
  LayoutStore.restoreRequiredComponents(config);
  const restored = componentByName(config, "action-dock");
  assert.ok(restored, "action-dock restored");
  assert.equal(restored.isClosable, false);
  assert.ok(allRequiredPresent(config));
});

test("extractDimensions returns only required component percentages", () => {
  const dimensions = LayoutStore.extractDimensions(LayoutStore.DEFAULT_LAYOUT_CONFIG);
  assert.equal(dimensions.narrative, 62);
  assert.equal(dimensions.header, 7);
  assert.equal(dimensions["action-dock"], 9);
  Object.keys(dimensions).forEach((key) => {
    assert.ok(LayoutStore.REQUIRED_COMPONENTS.indexOf(key) !== -1, `${key} is required`);
  });
});

test("applyDimensions round-trips and drops unknown keys", () => {
  const config = LayoutStore.applyDimensions(
    LayoutStore.DEFAULT_LAYOUT_CONFIG,
    { narrative: 70, art: 40, evil: 999 }
  );
  assert.equal(componentByName(config, "narrative").width, 70);
  assert.equal(componentByName(config, "art").height, 40);
  assert.ok(allRequiredPresent(config));
});
