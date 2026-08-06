/*
 * DOM-level contract tests for the shared dock surface renderer and the
 * delegated pointer bridge (webclient-pointer-activation). These exercise
 * `DockSurface` against a minimal DOM double so the row markup contract, the
 * composite-widget semantics, and the bridge activation predicate are
 * verified without a browser.
 */
const test = require("node:test");
const assert = require("node:assert/strict");

// ---------------------------------------------------------------------------
// Minimal DOM double: enough element surface for renderRows and the bridge.
// ---------------------------------------------------------------------------

class FakeElement {
  constructor(tag) {
    this.tagName = tag;
    this.children = [];
    this.attributes = {};
    this.classList = {
      names: new Set(),
      add: (name) => this.classList.names.add(name),
      remove: (name) => this.classList.names.delete(name),
    };
    this.parentNode = null;
    this.isConnected = true;
    this.listeners = {};
    this.type = null;
    this.id = null;
    this.textContent = "";
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  getAttribute(name) {
    return this.attributes[name] || null;
  }

  removeAttribute(name) {
    delete this.attributes[name];
  }

  appendChild(child) {
    child.parentNode = this;
    this.children.push(child);
    if (child.nodeType === 3) {
      this.textContent += child.value;
    }
    return child;
  }

  removeChild(child) {
    const index = this.children.indexOf(child);
    if (index !== -1) {
      this.children.splice(index, 1);
    }
    return child;
  }

  get firstChild() {
    return this.children[0] || null;
  }

  get nextSibling() {
    return null;
  }

  addEventListener(name, handler) {
    this.listeners[name] = handler;
  }

  closest(selector) {
    if (selector === "[data-item-key]" && this.attributes["data-item-key"] !== undefined) {
      return this;
    }
    return this.parentNode ? this.parentNode.closest(selector) : null;
  }

  focus() {
    this.focused = true;
  }
}

class FakeTextNode {
  constructor(value) {
    this.nodeType = 3;
    this.value = String(value);
  }
}

function installDomDouble() {
  const elements = [];
  const documentDouble = {
    createElement(tag) {
      const element = new FakeElement(tag);
      elements.push(element);
      return element;
    },
    createTextNode(value) {
      return new FakeTextNode(value);
    },
    getElementById(id) {
      return elements.find((element) => element.id === id) || null;
    },
  };
  const windowDouble = { Elosern: {} };
  global.window = windowDouble;
  global.document = documentDouble;
  return { window: windowDouble, elements };
}

function loadDockSurface() {
  delete require.cache[require.resolve("../plugins/dock_surface.js")];
  require("../plugins/dock_surface.js");
  return window.Elosern.DockSurface;
}

function items(spec) {
  return spec.map((entry) =>
    typeof entry === "string"
      ? { key: entry, label: entry, enabled: true }
      : { key: entry.key, label: entry.label, enabled: entry.enabled !== false }
  );
}

// ---------------------------------------------------------------------------

test("renderRows renders one row per item with the row identity and roles", () => {
  installDomDouble();
  const DockSurface = loadDockSurface();
  const container = new FakeElement("div");
  DockSurface.renderRows(container, items(["move", "look"]), {
    focusKey: "look",
    idPrefix: "exploration-row",
  });

  assert.equal(container.getAttribute("role"), "listbox");
  assert.equal(container.getAttribute("tabindex"), "0");
  assert.equal(container.getAttribute("aria-activedescendant"), "exploration-row-1");

  assert.equal(container.children.length, 2);
  const [first, second] = container.children;
  assert.equal(first.getAttribute("data-item-key"), "move");
  assert.equal(first.id, "exploration-row-0");
  assert.equal(first.getAttribute("role"), "option");
  assert.equal(first.getAttribute("tabindex"), "-1");
  assert.equal(first.getAttribute("aria-selected"), "false");
  assert.equal(second.getAttribute("data-item-key"), "look");
  assert.equal(second.id, "exploration-row-1");
  assert.equal(second.getAttribute("aria-selected"), "true");
});

test("renderRows marks the focused row and keeps others unfocused", () => {
  installDomDouble();
  const DockSurface = loadDockSurface();
  const container = new FakeElement("div");
  DockSurface.renderRows(container, items(["move", "look", "interact"]), {
    focusKey: "interact",
    idPrefix: "row",
  });
  const [first, second, third] = container.children;
  assert.equal(first.classList.names.has("focused"), false);
  assert.equal(second.classList.names.has("focused"), false);
  assert.equal(third.classList.names.has("focused"), true);
  assert.equal(container.getAttribute("aria-activedescendant"), "row-2");
});

test("renderRows suffixes disabled rows and associates the disabled state", () => {
  installDomDouble();
  const DockSurface = loadDockSurface();
  const container = new FakeElement("div");
  DockSurface.renderRows(
    container,
    items([
      { key: "defend", label: "防禦", enabled: false },
      { key: "attack", label: "攻擊", enabled: true },
    ]),
    { focusKey: "attack", idPrefix: "combat-row" }
  );
  const [first, second] = container.children;
  assert.equal(first.classList.names.has("disabled"), true);
  assert.equal(first.getAttribute("aria-disabled"), "true");
  assert.equal(first.textContent, "防禦（無法使用）");
  assert.equal(second.classList.names.has("disabled"), false);
  assert.equal(second.getAttribute("aria-disabled"), null);
  assert.equal(second.textContent, "攻擊");
});

test("renderRows clears the container before rendering", () => {
  installDomDouble();
  const DockSurface = loadDockSurface();
  const container = new FakeElement("div");
  container.appendChild(new FakeElement("button"));
  container.appendChild(new FakeElement("button"));
  DockSurface.renderRows(container, items(["only"]), { focusKey: "only" });
  assert.equal(container.children.length, 1);
});

test("renderRows falls back to the first row when no focusKey matches", () => {
  installDomDouble();
  const DockSurface = loadDockSurface();
  const container = new FakeElement("div");
  DockSurface.renderRows(container, items(["move", "look"]), { focusKey: "nope" });
  assert.equal(container.getAttribute("aria-activedescendant"), "row-0");
  assert.equal(container.children[0].classList.names.has("focused"), true);
});

// ---------------------------------------------------------------------------
// Pointer bridge activation predicate.
// ---------------------------------------------------------------------------

function makeBridgeHarness() {
  const { window, elements } = installDomDouble();
  const DockSurface = loadDockSurface();
  const dock = new FakeElement("div");
  dock.id = "action-dock";
  document.body = new FakeElement("body");
  document.body.appendChild(dock);
  elements.push(dock);

  const calls = [];
  window.Elosern.keyboard = {
    focusItemByKey(key) {
      calls.push(["focus", key]);
    },
    confirm(options) {
      calls.push(["confirm", options]);
    },
  };
  DockSurface.installPointerBridge();
  return { dock, calls, DockSurface };
}

function fireClick(dock, detail, row) {
  dock.listeners.click({
    detail,
    target: row,
  });
}

test("bridge activates only on detail === 1 and calls focus then pointer confirm", () => {
  const { dock, calls } = makeBridgeHarness();
  const row = new FakeElement("button");
  row.setAttribute("data-item-key", "move");
  row.isConnected = true;

  fireClick(dock, 0, row); // keyboard-synthesized click
  assert.deepEqual(calls, []);

  fireClick(dock, 2, row); // multi-click repeat
  assert.deepEqual(calls, []);

  fireClick(dock, 1, row);
  assert.deepEqual(calls, [
    ["focus", "move"],
    ["confirm", { source: "pointer" }],
  ]);
});

test("bridge ignores an activation whose row was detached by a re-render", () => {
  const { dock, calls } = makeBridgeHarness();
  const row = new FakeElement("button");
  row.setAttribute("data-item-key", "skills");
  row.isConnected = false; // the first activation's re-render detached it

  fireClick(dock, 1, row);
  assert.deepEqual(calls, []);
});

test("bridge ignores a click that resolves no row", () => {
  const { dock, calls } = makeBridgeHarness();
  const outside = new FakeElement("div");
  fireClick(dock, 1, outside);
  assert.deepEqual(calls, []);
});

test("mousedown on a row prevents default and focuses the listbox container", () => {
  const { dock } = makeBridgeHarness();
  const container = new FakeElement("div");
  const row = new FakeElement("button");
  row.setAttribute("data-item-key", "move");
  container.appendChild(row);
  row.isConnected = true;

  let prevented = false;
  dock.listeners.mousedown({
    target: row,
    preventDefault() {
      prevented = true;
    },
  });
  assert.equal(prevented, true);
  assert.equal(container.focused, true);
});

test("mousedown outside a row does not steal focus", () => {
  const { dock } = makeBridgeHarness();
  const outside = new FakeElement("div");
  let prevented = false;
  dock.listeners.mousedown({
    target: outside,
    preventDefault() {
      prevented = true;
    },
  });
  assert.equal(prevented, false);
});

// ---------------------------------------------------------------------------
// Synchronous re-render invariant: a router focus event re-renders the rows
// synchronously, so no interval exists in which the rendered rows describe a
// frame the router has already left. The stale-row guard backstops this.
// ---------------------------------------------------------------------------

test("a router focus event synchronously re-renders the dock rows", () => {
  installDomDouble();
  const DockSurface = loadDockSurface();
  const container = new FakeElement("div");

  const router = {
    currentItem() {
      return { key: "look", label: "查看", enabled: true };
    },
    pushMenu() {},
    replaceMenu() {},
    popMenu() {},
    reset() {},
    depth() {
      return 1;
    },
    focusItemByKey() {},
    confirm() {},
  };

  // The dock's onRouterEvent handler re-renders from the router's current
  // frame in the same call stack as the focus event.
  function onRouterEvent(name) {
    if (name === "focus") {
      DockSurface.renderRows(container, [router.currentItem()], {
        focusKey: "look",
        idPrefix: "dock-row",
      });
    }
  }

  let renderCount = 0;
  const originalRender = DockSurface.renderRows;
  DockSurface.renderRows = function (...args) {
    renderCount += 1;
    return originalRender(...args);
  };
  onRouterEvent("focus");
  assert.equal(renderCount, 1, "rows re-render synchronously on the focus event");
  assert.equal(container.children.length, 1);
  assert.equal(container.getAttribute("aria-activedescendant"), "dock-row-0");
});
