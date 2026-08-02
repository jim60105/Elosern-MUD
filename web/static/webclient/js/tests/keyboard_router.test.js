/*
 * KeyboardRouter DOM-independent tests (foundation section 5.2).
 */
const test = require("node:test");
const assert = require("node:assert");

const Router = require("../elosern/keyboard_router.js");

function makeRouter() {
  const events = [];
  const router = Router.createRouter({ onEvent: (name, payload) => events.push({ name, payload }) });
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

test("slash opens the command drawer", () => {
  const { router, events } = makeRouter();
  router.pushMenu({ items: [Router.menuItem("a", true)] });
  events.length = 0;
  router.handle("/");
  assert.strictEqual(events[0].name, "open-drawer");
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
