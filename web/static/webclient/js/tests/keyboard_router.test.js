/*
 * KeyboardRouter DOM-independent tests (foundation section 5.2).
 *
 * The router is declarative-only: this harness backs each pushed menu with a
 * static resolver source, so the geometry/submission semantics under test are
 * identical while frames carry descriptors, never menus.
 */
const test = require("node:test");
const assert = require("node:assert");

const Router = require("../elosern/keyboard_router.js");

function makeRouter() {
  const events = [];
  const tables = new Map();
  let seq = 0;
  const router = Router.createRouter({
    onEvent: (name, payload) => events.push({ name, payload }),
    resolve: (descriptor) => tables.get(descriptor.source) ?? null,
  });
  // Test-local legacy-menu convenience: back the menu with a static source
  // registered BEFORE the push settles the frame.
  router.pushMenu = (menu, options) => {
    const source = "menu-" + (seq += 1);
    tables.set(source, menu);
    return router.pushFrame({ source, params: {} }, options);
  };
  router.replaceMenu = (menu) => {
    const source = "menu-" + (seq += 1);
    tables.set(source, menu);
    return router.replaceFrame({ source, params: {} });
  };
  router.reset = (menu) => {
    const source = "menu-" + (seq += 1);
    tables.set(source, menu);
    return router.resetFrame({ source, params: {} });
  };
  return { router, events };
}

test("list focus geometry moves with arrows and wraps", () => {
  const { router, events } = makeRouter();
  router.pushMenu({
    items: ["a", "b", "c"].map((label) => Router.menuItem(label, true)),
  });
  events.length = 0;
  router.handle("ArrowDown");
  assert.strictEqual(events[0].name, "focus");
  assert.strictEqual(events[0].payload.row, 1);
  router.handle("ArrowDown");
  router.handle("ArrowDown");
  assert.strictEqual(events[events.length - 1].payload.row, 0);
});

test("grid focus geometry moves in rows and columns", () => {
  const { router, events } = makeRouter();
  const items = [];
  for (let i = 0; i < 6; i += 1) {
    items.push(Router.menuItem("g" + i, true));
  }
  router.pushMenu({ grid: true, gridCols: 3, items });
  events.length = 0;
  router.handle("ArrowRight");
  assert.strictEqual(events[0].payload.row, 0);
  assert.strictEqual(events[0].payload.col, 1);
  router.handle("ArrowDown");
  assert.strictEqual(events[events.length - 1].payload.row, 1);
  assert.strictEqual(events[events.length - 1].payload.col, 1);
});

test("Enter confirms an enabled focused item once", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [Router.menuItem("cast", true)] });
  events.length = 0;
  router.handle("Enter");
  assert.strictEqual(events[0].name, "submit");
  assert.strictEqual(events[0].payload.item.label, "cast");
});

test("submenu return focus restores the prior focused item", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [Router.menuItem("move", true), Router.menuItem("skills", true)] });
  router.handle("ArrowDown");
  router.pushMenu({ items: [Router.menuItem("sub", true)] });
  events.length = 0;
  router.handle("Escape");
  assert.strictEqual(events[0].name, "menu-closed");
  assert.strictEqual(events[0].payload.returnedItemKey, "skills");
  assert.strictEqual(router.depth(), 1);
  assert.strictEqual(router.currentItem().label, "skills");
});

test("Escape pops exactly one menu level", () => {
  const { router } = makeRouter();
  router.pushMenu({ items: [Router.menuItem("root", true)] });
  router.pushMenu({ items: [Router.menuItem("one", true)] });
  router.pushMenu({ items: [Router.menuItem("two", true)] });
  assert.strictEqual(router.depth(), 3);
  router.handle("Escape");
  assert.strictEqual(router.depth(), 2);
  router.handle("Escape");
  assert.strictEqual(router.depth(), 1);
});

test("disabled item explains without sending", () => {
  const { router, events } = makeRouter();
  router.pushMenu({
    items: [Router.menuItem("defend", false, "尚未實作此動作")],
  });
  events.length = 0;
  router.handle("Enter");
  assert.strictEqual(events[0].name, "disabled");
  assert.strictEqual(events[0].payload.item.description, "尚未實作此動作");
  assert.strictEqual(events.some((e) => e.name === "submit"), false);
});

test("slash emits a toggle event each press", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [Router.menuItem("a", true)] });
  events.length = 0;
  router.handle("/");
  assert.strictEqual(events[0].name, "toggle-drawer");
  // The router never decides open vs close; every press re-emits the toggle
  // and the browser gate resolves the drawer's current state.
  router.handle("/");
  assert.strictEqual(events[1].name, "toggle-drawer");
  assert.strictEqual(events.filter((e) => e.name === "toggle-drawer").length, 2);
});

test("space is reserved for multi-select and emits a space event", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [Router.menuItem("a", true)] });
  events.length = 0;
  router.handle(" ");
  assert.strictEqual(events[0].name, "space");
});

test("repeated Enter is suppressed after a submit", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [Router.menuItem("cast", true)] });
  events.length = 0;
  router.handle("Enter");
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 1);
  router.handle("Enter", true);
  router.handle("Enter", true);
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 1);
});

test("mutation in flight suppresses further submits", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [Router.menuItem("cast", true)] });
  router.setMutationInFlight(true);
  events.length = 0;
  router.handle("Enter");
  assert.strictEqual(events[0].name, "locked");
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 0);
  router.setMutationInFlight(false);
  router.handle("Enter");
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 1);
});

test("action locking awaits declared presentation revision", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [Router.menuItem("cast", true)] });
  router.setAwaitingRevision(12);
  events.length = 0;
  router.handle("Enter");
  assert.strictEqual(events[0].name, "locked");
  router.setAwaitingRevision(null);
  router.handle("Enter");
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 1);
});

test("focusItemByKey moves focus and emits focus for a hit", () => {
  const { router, events } = makeRouter();
  router.pushMenu({
    items: [
      { key: "move", label: "移動", enabled: true },
      { key: "look", label: "查看", enabled: true },
      { key: "interact", label: "互動", enabled: true },
    ],
  });
  events.length = 0;
  const moved = router.focusItemByKey("interact");
  assert.strictEqual(moved, true);
  assert.strictEqual(events[0].name, "focus");
  assert.strictEqual(events[0].payload.itemKey, "interact");
  assert.strictEqual(router.currentItem().key, "interact");
});

test("focusItemByKey returns false without side effects on a miss", () => {
  const { router, events } = makeRouter();
  router.pushMenu({
    items: [
      { key: "move", label: "移動", enabled: true },
      { key: "look", label: "查看", enabled: true },
    ],
  });
  events.length = 0;
  const moved = router.focusItemByKey("nonexistent");
  assert.strictEqual(moved, false);
  assert.strictEqual(events.length, 0);
  assert.strictEqual(router.currentItem().key, "move");
});

test("focusItemByKey resolves grid items by row and column", () => {
  const { router, events } = makeRouter();
  const items = [];
  for (let i = 0; i < 6; i += 1) {
    items.push({ key: "g" + i, label: "g" + i, enabled: true });
  }
  router.pushMenu({ grid: true, gridCols: 3, items });
  events.length = 0;
  router.focusItemByKey("g4");
  assert.strictEqual(events[0].payload.row, 1);
  assert.strictEqual(events[0].payload.col, 1);
  assert.strictEqual(router.currentItem().key, "g4");
});

test("pointer confirm on an enabled item emits exactly one submit", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [{ key: "cast", label: "cast", enabled: true }] });
  events.length = 0;
  router.confirm({ source: "pointer" });
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 1);
});

test("pointer confirm on a disabled item emits disabled and no submit", () => {
  const { router, events } = makeRouter();
  router.pushMenu({
    items: [{ key: "defend", label: "defend", enabled: false, description: "no" }],
  });
  events.length = 0;
  router.confirm({ source: "pointer" });
  assert.strictEqual(events[0].name, "disabled");
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 0);
});

test("pointer confirm while locked emits locked", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [{ key: "cast", label: "cast", enabled: true }] });
  router.setMutationInFlight(true);
  events.length = 0;
  router.confirm({ source: "pointer" });
  assert.strictEqual(events[0].name, "locked");
  router.setMutationInFlight(false);
  router.setAwaitingRevision(3);
  events.length = 0;
  router.confirm({ source: "pointer" });
  assert.strictEqual(events[0].name, "locked");
});

test("two consecutive pointer confirms both submit (no repeat guard)", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [{ key: "cast", label: "cast", enabled: true }] });
  events.length = 0;
  router.confirm({ source: "pointer" });
  router.confirm({ source: "pointer" });
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 2);
});

test("odd-count 2-column grid: final cell sits bottom-left and empty cells do not move", () => {
  const { router, events } = makeRouter();
  const items = [];
  for (let i = 0; i < 7; i += 1) {
    items.push({ key: "g" + i, label: "g" + i, enabled: true });
  }
  router.pushMenu({ grid: true, gridCols: 2, items });
  events.length = 0;

  // ArrowUp from the first cell wraps to the bottom-left final cell.
  router.handle("ArrowUp");
  assert.strictEqual(events[events.length - 1].payload.row, 3);
  assert.strictEqual(events[events.length - 1].payload.col, 0);
  assert.strictEqual(router.currentItem().key, "g6");

  // ArrowDown wraps back to the first cell.
  router.handle("ArrowDown");
  assert.strictEqual(router.currentItem().key, "g0");

  // The missing bottom-right cell (row 3, col 1) never receives focus:
  // ArrowRight from the final cell returns false without moving.
  router.handle("ArrowUp"); // back to g6 (3,0)
  events.length = 0;
  const moved = router.handle("ArrowRight");
  assert.strictEqual(moved, false);
  assert.strictEqual(router.currentItem().key, "g6");
  assert.strictEqual(events.length, 0, "an empty cell must not move or emit");

  // ArrowLeft from the final cell also hits the empty right column and
  // stays put; ArrowUp reaches g4 in the previous row, then ArrowRight to g5.
  router.handle("ArrowLeft");
  assert.strictEqual(router.currentItem().key, "g6");
  router.handle("ArrowUp");
  assert.strictEqual(router.currentItem().key, "g4");
  router.handle("ArrowRight");
  assert.strictEqual(router.currentItem().key, "g5");

  // Down from the final cell wraps to the first row.
  router.focusItemByKey("g6");
  router.handle("ArrowDown");
  assert.strictEqual(router.currentItem().key, "g0");
});

test("focusItemByKey resolves odd-count grid cells by row and column", () => {
  const { router, events } = makeRouter();
  const items = [];
  for (let i = 0; i < 7; i += 1) {
    items.push({ key: "g" + i, label: "g" + i, enabled: true });
  }
  router.pushMenu({ grid: true, gridCols: 2, items });
  events.length = 0;
  const moved = router.focusItemByKey("g6");
  assert.strictEqual(moved, true);
  assert.strictEqual(events[0].payload.row, 3);
  assert.strictEqual(events[0].payload.col, 0);
  assert.strictEqual(router.currentItem().key, "g6");
  assert.strictEqual(router.focusItemByKey("g7"), false);
});

test("repeated Space is suppressed while a single Space emits once", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [{ key: "area-x", label: "x", enabled: true }] });
  events.length = 0;
  router.handle(" ");
  assert.strictEqual(events.filter((e) => e.name === "space").length, 1);
  router.handle(" ", true);
  router.handle(" ", true);
  assert.strictEqual(
    events.filter((e) => e.name === "repeat-suppressed").length,
    2,
    "held Space must not repeatedly toggle AREA candidates"
  );
  assert.strictEqual(events.filter((e) => e.name === "space").length, 1);
  // A fresh deliberate press still emits.
  router.handle(" ");
  assert.strictEqual(events.filter((e) => e.name === "space").length, 2);
});

test("repeated Enter suppression is unchanged for keyboard confirms", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [{ key: "cast", label: "cast", enabled: true }] });
  events.length = 0;
  router.handle("Enter");
  router.handle("Enter", true);
  router.handle("Enter", true);
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 1);
  assert.strictEqual(events.filter((e) => e.name === "repeat-suppressed").length, 2);
});

test("confirm defaults to the keyboard source", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [{ key: "cast", label: "cast", enabled: true }] });
  events.length = 0;
  router.confirm();
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 1);
  // The default keyboard confirm sets the repeat guard.
  router.confirm();
  assert.strictEqual(events.filter((e) => e.name === "submit").length, 1);
  assert.strictEqual(events.filter((e) => e.name === "repeat-suppressed").length, 1);
});

// webclient-scene-overview-component (task 2.4): the `sections` geometry.
function sectionedMenu(counts) {
  const items = [];
  const sections = counts.map((count, s) => {
    for (let i = 0; i < count; i += 1) {
      items.push({ key: `s${s}-${i}`, label: `s${s}-${i}`, enabled: true });
    }
    return { key: `sec${s}`, label: s === counts.length - 1 ? null : `sec${s}`, count };
  });
  return { items, sections, geometry: "sections", title: "場景" };
}

function focusedKey(router) {
  return router.currentItem().key;
}

test("sections: Left/Right step through the reading order and wrap across sections", () => {
  const { router } = makeRouter();
  router.pushMenu(sectionedMenu([2, 3, 1]));
  assert.strictEqual(focusedKey(router), "s0-0");
  router.handle("ArrowRight");
  router.handle("ArrowRight");
  assert.strictEqual(focusedKey(router), "s1-0");
  router.handle("ArrowLeft");
  assert.strictEqual(focusedKey(router), "s0-1");
  router.handle("ArrowLeft");
  router.handle("ArrowLeft");
  assert.strictEqual(focusedKey(router), "s2-0", "Left from the first chip wraps to the last");
  router.handle("ArrowRight");
  assert.strictEqual(focusedKey(router), "s0-0", "Right from the last chip wraps to the first");
});

test("sections: Up/Down keep the ordinal, clamp to a shorter section, and wrap", () => {
  const { router, events } = makeRouter();
  router.pushMenu(sectionedMenu([2, 3, 1]));
  assert.ok(router.focusItemByKey("s1-2"));
  router.handle("ArrowDown");
  assert.strictEqual(focusedKey(router), "s2-0", "ordinal 2 clamps to the one-chip section");
  router.handle("ArrowDown");
  assert.strictEqual(focusedKey(router), "s0-0", "Down from the last section wraps to the first");
  assert.ok(router.focusItemByKey("s0-1"));
  router.handle("ArrowDown");
  assert.strictEqual(focusedKey(router), "s1-1");
  router.handle("ArrowUp");
  assert.strictEqual(focusedKey(router), "s0-1");
  router.handle("ArrowUp");
  assert.strictEqual(focusedKey(router), "s2-0", "Up from the first section wraps to the last");
  const last = events[events.length - 1];
  assert.strictEqual(last.name, "focus");
  assert.strictEqual(last.payload.row, 5);
  assert.strictEqual(last.payload.itemKey, "s2-0");
});

test("sections: Up/Down are no-ops with a single section", () => {
  const { router, events } = makeRouter();
  router.pushMenu(sectionedMenu([3]));
  events.length = 0;
  assert.strictEqual(router.handle("ArrowDown"), false);
  assert.strictEqual(router.handle("ArrowUp"), false);
  assert.strictEqual(events.length, 0);
  router.handle("ArrowRight");
  assert.strictEqual(focusedKey(router), "s0-1");
});

test("sections: counts that disagree with the items fall back to list behaviour", () => {
  const { router } = makeRouter();
  const menu = sectionedMenu([2, 2]);
  menu.sections[1].count = 5;
  router.pushMenu(menu);
  router.handle("ArrowDown");
  assert.strictEqual(focusedKey(router), "s0-1", "Down steps to the next row as a list");
  assert.strictEqual(router.handle("ArrowRight"), false, "Left/Right are list no-ops");
});

test("sections: focusItemByKey and re-resolution keep the focused key", () => {
  const { router } = makeRouter();
  const menu = sectionedMenu([2, 2]);
  router.pushMenu(menu);
  assert.ok(router.focusItemByKey("s1-1"));
  // The same source re-resolves to a menu with one more chip in front.
  menu.items.unshift({ key: "s0-x", label: "s0-x", enabled: true });
  menu.sections[0].count = 3;
  assert.strictEqual(focusedKey(router), "s1-1");
  router.handle("ArrowUp");
  assert.strictEqual(focusedKey(router), "s0-0", "ordinal 1 in the section above");
});
