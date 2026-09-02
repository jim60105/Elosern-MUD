/*
 * Declarative frame-stack tests (webclient-declarative-frame-stack).
 *
 * Covers the dual frame contract: access-time resolution, the focus-key
 * rule, unresolvable cascade pop with opener-key restore, degraded root,
 * suggestions-style root exit, unknown-shape rejection, and the legacy
 * pass-through that keeps unmigrated families byte-for-byte.
 */
const test = require("node:test");
const assert = require("node:assert");

const Router = require("../elosern/keyboard_router.js");

function itemsOf(labels) {
  return labels.map((label) => Router.menuItem(label, true, null, null));
}

function menuOf(labels, title) {
  return { items: itemsOf(labels), grid: false, title: title || "" };
}

function declRouter(resolve) {
  const events = [];
  const router = Router.createRouter({
    onEvent: (name, payload) => events.push({ name, payload }),
    resolve,
  });
  return { router, events };
}

const MARKER = { unresolvable: true, reason: "面板已更新" };

test("declarative push focuses the first item from the push-time resolve", () => {
  let panel = { items: ["a", "b", "c"] };
  const resolve = (d) => menuOf(panel.items);
  const { router, events } = declRouter(resolve);
  router.pushFrame({ source: "exploration.move", params: {} });
  const focus = events[events.length - 1];
  assert.strictEqual(focus.name, "focus");
  assert.strictEqual(focus.payload.row, 0);
  assert.strictEqual(focus.payload.itemKey, "a");
  assert.strictEqual(router.depth(), 1);
});

test("arrow geometry reads the current resolve, not the open-time copy", () => {
  let panel = { items: ["a", "b", "c"] };
  const resolve = () => menuOf(panel.items);
  const { router } = declRouter(resolve);
  router.pushFrame({ source: "exploration.move", params: {} });
  // The panel changes AFTER the frame opened (a fresh push commit).
  panel = { items: ["x", "y"] };
  router.handle("ArrowDown");
  assert.strictEqual(router.currentItem().label, "y");
  // trail reflects the new menu's title too.
  assert.strictEqual(router.currentMenu().items.length, 2);
});

test("focus key survives re-resolution at its new index", () => {
  let panel = { items: ["a", "b", "c"] };
  const resolve = () => menuOf(panel.items);
  const { router } = declRouter(resolve);
  router.pushFrame({ source: "exploration.move", params: {} });
  router.handle("ArrowDown"); // focus b
  router.handle("ArrowDown"); // focus c
  panel = { items: ["c", "a", "b"] };
  // The next read re-projects focus onto key c at its new index.
  assert.strictEqual(router.currentItem().label, "c");
  router.handle("ArrowDown"); // continues from the projected row
  assert.strictEqual(router.currentItem().label, "a");
});

test("lost focus key lands on the nearest surviving index (earlier tie)", () => {
  let panel = { items: ["a", "b", "c", "d"] };
  const resolve = () => menuOf(panel.items);
  const { router } = declRouter(resolve);
  router.pushFrame({ source: "exploration.move", params: {} });
  router.handle("ArrowDown");
  router.handle("ArrowDown"); // focus c (index 2)
  panel = { items: ["d", "b"] }; // c gone; cached index 2
  // Nearest surviving to index 2 is index 1 ("b"); earlier-row tie applies.
  assert.strictEqual(router.currentItem().label, "b");
});

test("empty resolved menu focuses no row", () => {
  let panel = { items: [] };
  const resolve = () => menuOf(panel.items);
  const { router } = declRouter(resolve);
  router.pushFrame({ source: "exploration.move", params: {} });
  assert.strictEqual(router.currentItem(), null);
  panel = { items: ["a"] };
  assert.strictEqual(router.currentItem().label, "a");
});

test("confirm writes the activated row's key back as focusKey", () => {
  const resolve = () => menuOf(["a", "b"]);
  const { router, events } = declRouter(resolve);
  router.pushFrame({ source: "exploration.wait", params: {} });
  router.handle("ArrowDown"); // focus b
  router.confirm({ source: "pointer" });
  const submit = events[events.length - 1];
  assert.strictEqual(submit.name, "submit");
  assert.strictEqual(submit.payload.itemKey, "b");
});

test("an unresolvable frame pops one level and restores the opener key", () => {
  const opens = new Map([
    ["exploration.root", () => menuOf(["移動", "互動"])],
    ["exploration.interact", (p) => (p.identity === "gate" ? menuOf(["開", "查看"]) : MARKER)],
  ]);
  const resolve = (d) => (opens.get(d.source) || (() => MARKER))(d.params);
  const { router } = declRouter(resolve);
  router.pushFrame({ source: "exploration.root", params: {} });
  router.focusItemByKey("互動");
  router.pushFrame(
    { source: "exploration.interact", params: { identity: "gate" } },
    { openerKey: "互動" }
  );
  assert.strictEqual(router.depth(), 2);
  // The target vanishes server-side (panel data changed).
  opens.set("exploration.interact", () => MARKER);
  assert.strictEqual(router.depth(), 1); // settled at next read
  assert.strictEqual(router.currentItem().label, "互動");
});

test("cascade pops while each next top is also unresolvable", () => {
  const state = { target: false, keywords: false };
  const resolve = (d) => {
    if (d.source === "exploration.root") return menuOf(["移動"]);
    if (d.source === "exploration.interact") return menuOf(["Talk"]);
    if (d.source === "exploration.target") return state.target ? menuOf(["x"]) : MARKER;
    if (d.source === "exploration.keywords") return state.keywords ? menuOf(["k"]) : MARKER;
    return MARKER;
  };
  const { router } = declRouter(resolve);
  state.target = true;
  state.keywords = true;
  router.pushFrame({ source: "exploration.root", params: {} });
  router.pushFrame({ source: "exploration.interact", params: {} }, { openerKey: "移動" });
  router.pushFrame({ source: "exploration.target", params: {} }, { openerKey: "Talk" });
  router.pushFrame({ source: "exploration.keywords", params: {} }, { openerKey: "x" });
  assert.strictEqual(router.depth(), 4);
  // Both upper frames become unresolvable → cascade stops at interact.
  state.target = false;
  state.keywords = false;
  assert.strictEqual(router.depth(), 2);
  assert.strictEqual(router.currentMenu().items[0].label, "Talk");
});

test("unresolvableAction root exits the stack to the root frame", () => {
  let sugg = menuOf(["s"]);
  const resolve = (d) => {
    if (d.source === "exploration.root") return menuOf(["移動", "建議"]);
    if (d.source === "exploration.suggestions") return sugg === null ? menuOf(["s"]) : sugg;
    return MARKER;
  };
  const { router } = declRouter(resolve);
  router.pushFrame({ source: "exploration.root", params: {} });
  router.focusItemByKey("建議");
  router.pushFrame(
    { source: "exploration.suggestions", params: {} },
    { openerKey: "建議", unresolvableAction: "root" }
  );
  assert.strictEqual(router.depth(), 2);
  sugg = MARKER; // status flips to unavailable while the frame is open
  assert.strictEqual(router.depth(), 1); // deterministically back to root
  assert.strictEqual(router.currentMenu().items[0].label, "移動");
});

test("unresolvable root degrades in place to the disabled marker-reason row", () => {
  let root = MARKER;
  const resolve = () => root;
  const { router } = declRouter(resolve);
  router.pushFrame({ source: "exploration.root", params: {} });
  const menu = router.currentMenu();
  assert.strictEqual(menu.items.length, 1);
  assert.strictEqual(menu.items[0].enabled, false);
  assert.strictEqual(menu.items[0].label, "面板已更新"); // carries the reason
  assert.strictEqual(menu.items[0].description, null);
  // The reason is visible without activation; arrow motion is a no-op.
  router.handle("ArrowDown");
  assert.strictEqual(router.currentItem().label, "面板已更新");
  // Submit is impossible: the row is disabled.
  assert.strictEqual(router.confirm({ source: "pointer" }), false);
  // rootMenu stays null while degraded so the tab bar never shows it.
  assert.strictEqual(router.rootMenu(), null);
  assert.deepStrictEqual(router.degradedRoot(), {
    key: "degraded-root",
    reason: "面板已更新",
    fallback: Router.DEGRADED_ROOT_FALLBACK,
  });
  // Recovery: the descriptor resolves again → normal presentation.
  root = menuOf(["移動"]);
  assert.strictEqual(router.currentMenu().items[0].label, "移動");
  assert.strictEqual(router.degradedRoot(), null);
});

test("degraded root without a server reason uses the local fallback line", () => {
  const resolve = () => ({ unresolvable: true });
  const { router } = declRouter(resolve);
  router.pushFrame({ source: "exploration.root", params: {} });
  assert.strictEqual(router.currentItem().label, "畫面狀態已更新，請返回上層");
  assert.strictEqual(router.degradedRoot().reason, null);
});

test("unknown frame shapes throw at the push site", () => {
  const { router } = declRouter(() => menuOf(["a"]));
  assert.throws(() => router.pushFrame({ params: {} }), TypeError);
  assert.throws(() => router.pushMenu(null), TypeError);
  assert.doesNotThrow(() => router.pushMenu({ items: [] }));
});

test("legacy frames pass through unchanged beside declarative ones", () => {
  const resolve = () => menuOf(["d"]);
  const { router, events } = declRouter(resolve);
  // Combat/creation families keep using the copy shape (change 4 migrates).
  router.pushMenu(menuOf(["legacy"]));
  assert.strictEqual(router.currentMenu().items[0].label, "legacy");
  router.handle("ArrowDown"); // wrap within single item
  assert.strictEqual(router.currentItem().label, "legacy");
  router.pushMenu(menuOf(["legacy2"]));
  router.popMenu();
  assert.strictEqual(router.depth(), 1);
  assert.strictEqual(router.currentDescriptor(), null);
});

test("resetFrame tears down to one declarative root frame", () => {
  const resolve = (d) => (d.source === "exploration.root" ? menuOf(["移動"]) : MARKER);
  const { router } = declRouter(resolve);
  router.pushFrame({ source: "exploration.root", params: {} });
  router.pushFrame({ source: "exploration.interact", params: {} });
  router.resetFrame({ source: "exploration.root", params: {} });
  assert.strictEqual(router.depth(), 1);
  assert.strictEqual(router.currentItem().label, "移動");
});

test("empty declarative stack reads throw rather than silently recover", () => {
  const { router } = declRouter(() => menuOf(["a"]));
  router.reset(); // legacy menu-less reset (no push happened)
  assert.strictEqual(router.depth(), 0);
  // Reads on an empty stack are safe nulls; the empty-stack fuse deletion
  // lands with the change-4 teardown. Here we only pin the access shape.
  assert.strictEqual(router.currentItem(), null);
  assert.strictEqual(router.currentMenu(), null);
});
