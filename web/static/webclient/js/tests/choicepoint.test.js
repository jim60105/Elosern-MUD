/*
 * Narrative choice-point Node suite (webclient-options-choicepoints).
 *
 * Covers the pure transition table, the stream-end block controller (the
 * movable end-block invariant: text lands before the block, the block stays
 * last, one scroll/unread decision per narrative text event), the render
 * adapter against a fake container, and the dock/stream envelope parity.
 * Modules are loaded with a minimal DOM double following the repo's Node
 * conventions; nothing here needs a browser.
 */
const test = require("node:test");
const assert = require("node:assert/strict");

const Logic = require("../elosern/choicepoint_logic.js");
const StreamEndBlock = require("../elosern/stream_end_block.js");
const ChoicePoints = require("../plugins/choice_points.js");

// ---------------------------------------------------------------------------
// Minimal DOM double (repo convention): elements with classList, text nodes,
// child ordering, insertBefore, and click listeners.
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
    // Layout contribution: a container that models scroll geometry grows its
    // scrollHeight by each child's height on append/insert, exactly like the
    // real DOM, so at-bottom decisions are computed against honest geometry.
    this.height = 20;
  }

  setAttribute(name, value) {
    this.attributes[name] = String(value);
  }

  getAttribute(name) {
    return this.attributes[name] || null;
  }

  _grow(delta) {
    if (this.scrollHeight !== undefined && delta !== undefined) {
      this.scrollHeight += delta;
    }
  }

  appendChild(child) {
    if (child.nodeType === 11) {
      const nodes = child.children.slice();
      for (const node of nodes) {
        if (node.parentNode) {
          node.parentNode.removeChild(node);
        }
        node.parentNode = this;
        this.children.push(node);
        this._grow(node.height);
        if (node.nodeType === 3) {
          this.textContent += node.value;
        }
      }
      return child;
    }
    if (child.parentNode) {
      child.parentNode.removeChild(child);
    }
    child.parentNode = this;
    this.children.push(child);
    this._grow(child.height);
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
    this._grow(-(child.height || 0));
    child.parentNode = null;
    return child;
  }

  insertBefore(child, reference) {
    const nodes = child.nodeType === 11 ? child.children.slice() : [child];
    for (const node of nodes) {
      if (node.parentNode) {
        node.parentNode.removeChild(node);
      }
      node.parentNode = this;
      const index = reference ? this.children.indexOf(reference) : -1;
      if (index === -1) {
        this.children.push(node);
      } else {
        this.children.splice(index, 0, node);
      }
      this._grow(node.height);
    }
    return child;
  }

  get firstChild() {
    return this.children[0] || null;
  }

  get lastChild() {
    return this.children[this.children.length - 1] || null;
  }

  addEventListener(name, handler) {
    this.listeners[name] = handler;
  }

  click() {
    if (typeof this.listeners.click === "function") {
      this.listeners.click({ detail: 1, target: this });
    }
  }
}

class FakeTextNode {
  constructor(value) {
    this.nodeType = 3;
    this.value = String(value);
  }
}

// A DocumentFragment double: children flatten into the container on
// append/insert, exactly like the real DOM moves fragment children.
class FakeFragment {
  constructor() {
    this.nodeType = 11;
    this.children = [];
    this.parentNode = null;
  }

  appendChild(child) {
    if (child.parentNode) {
      child.parentNode.removeChild(child);
    }
    child.parentNode = this;
    this.children.push(child);
    return child;
  }

  removeChild(child) {
    const index = this.children.indexOf(child);
    if (index !== -1) {
      this.children.splice(index, 1);
    }
    child.parentNode = null;
    return child;
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
  };
  const windowDouble = { Elosern: {} };
  global.window = windowDouble;
  global.document = documentDouble;
  return { window: windowDouble, elements };
}

// ---------------------------------------------------------------------------
// Shared fixtures.
// ---------------------------------------------------------------------------

function explorationState(suggestions) {
  return {
    panels: {
      context_actions: {
        schema_version: 5,
        available: true,
        kind: "exploration",
        affordances: [],
        suggestions,
      },
    },
  };
}

function combatState() {
  return {
    panels: {
      context_actions: {
        schema_version: 5,
        available: true,
        kind: "combat",
        affordances: [],
      },
    },
  };
}

function absentState() {
  return { panels: {} };
}

function card(actionCode, label) {
  return { kind: "known_action", action_code: actionCode, label, params: {} };
}

function freeformCard(label) {
  return {
    kind: "freeform",
    action_code: "explore.talk_freeform",
    label,
    params: { npc_id: 7 },
  };
}

// A fake narrative container with controllable scroll geometry.
function makeContainer() {
  const container = new FakeElement("div");
  container.scrollHeight = 500;
  container.clientHeight = 100;
  container.scrollTop = 400; // at the bottom: 500 - 400 - 100 = 0 < 8
  return container;
}

function atBottom(container) {
  return (
    container.scrollHeight - container.scrollTop - container.clientHeight < 8
  );
}

// A stream-end block controller bound to a fake container, recording the
// scroll/unread decisions.
function makeBlockHarness() {
  const container = makeContainer();
  let unread = 0;
  const block = StreamEndBlock.createStreamEndBlock(container, {
    atBottom: () => atBottom(container),
    scrollToBottom: () => {
      container.scrollTop = container.scrollHeight;
    },
    onUnread: () => {
      unread += 1;
    },
  });
  return { container, block, unread: () => unread };
}

// A recording action client shared by the dock twin and the stream layer.
function makeActions() {
  const calls = [];
  return {
    calls,
    submit(actionId, payload, display) {
      calls.push({ actionId, payload, display });
      return "request-1";
    },
  };
}

// The render-level harness: the layer bound to a real controller over a fake
// container, real OptionCards, and a recording action client.
function makeLayerHarness() {
  installDomDouble();
  const OptionCards = require("../elosern/option_cards.js");
  const actions = makeActions();
  // The browser action client lives at window.Elosern.actions; the dock twin
  // resolves it there, so parity tests share one recording client.
  window.Elosern.actions = actions;
  const { container, block, unread } = makeBlockHarness();
  const facade = {
    appendInput: () => false,
    mountChoicePoint: (element) => block.mount(element),
    moveChoicePointToEnd: () => block.moveToEnd(),
    replaceChoicePoint: (element) => block.replace(element),
    unmountChoicePoint: () => block.unmount(),
  };
  const layer = ChoicePoints.createChoicePointLayer({
    getFacade: () => facade,
    getCards: () => OptionCards,
    getActions: () => actions,
    getLogic: () => Logic,
  });
  return { layer, container, block, actions, unread, OptionCards };
}

// Depth-first collect of every clickable button inside a subtree (cards live
// in the wrap child, the dismiss control is a direct child of the group).
function collectButtons(root) {
  const found = [];
  (function walk(node) {
    if (!node || !node.children) {
      return;
    }
    for (const child of node.children) {
      if (child.listeners && typeof child.listeners.click === "function") {
        found.push(child);
      }
      walk(child);
    }
  })(root);
  return found;
}

// ---------------------------------------------------------------------------
// Task 1.4: facade shape contract (appendInput plus the four block ops).
// ---------------------------------------------------------------------------

test("the narrativeInput facade keeps appendInput and gains the four block ops", () => {
  installDomDouble();
  delete require.cache[require.resolve("../plugins/goldenlayout.js")];
  require("../plugins/goldenlayout.js");
  const facade = window.Elosern.narrativeInput;
  assert.equal(typeof facade.appendInput, "function");
  assert.equal(typeof facade.mountChoicePoint, "function");
  assert.equal(typeof facade.moveChoicePointToEnd, "function");
  assert.equal(typeof facade.replaceChoicePoint, "function");
  assert.equal(typeof facade.unmountChoicePoint, "function");
});

// ---------------------------------------------------------------------------
// Task 2.2 / 4.1: the pure transition table.
// ---------------------------------------------------------------------------

test("the reducer keeps the finite stream states", () => {
  assert.equal(Logic.nextChoicePointState("absent", { status: "generating" }), "generating");
  assert.equal(Logic.nextChoicePointState("absent", { status: "ready", cards: [] }), "ready");
  assert.equal(Logic.nextChoicePointState("generating", { status: "generating" }), "generating");
  assert.equal(Logic.nextChoicePointState("ready", { status: "ready", cards: [] }), "ready");
  assert.equal(Logic.nextChoicePointState("generating", { status: "ready", cards: [] }), "ready");
  assert.equal(Logic.nextChoicePointState("ready", { status: "generating" }), "generating");
});

test("every elimination path resolves to absent", () => {
  const paths = [
    { status: "degraded", cards: [] },
    { status: "unavailable" },
    { status: "bogus" },
    { status: 42 },
    {},
    null,
    undefined,
  ];
  for (const committed of paths) {
    assert.equal(Logic.nextChoicePointState("generating", committed), "absent", JSON.stringify(committed));
    assert.equal(Logic.nextChoicePointState("ready", committed), "absent", JSON.stringify(committed));
    assert.equal(Logic.nextChoicePointState("absent", committed), "absent", JSON.stringify(committed));
  }
});

test("repeated identical commits are idempotent", () => {
  for (const status of ["generating", "ready"]) {
    const committed = { status, cards: status === "ready" ? [card("explore.look", "查看四周")] : undefined };
    assert.equal(
      Logic.nextChoicePointState(Logic.nextChoicePointState("absent", committed), committed),
      status
    );
  }
});

test("the transition edge maps (previous, next) to the DOM operation", () => {
  assert.equal(Logic.transitionEdge("absent", "absent"), "none");
  assert.equal(Logic.transitionEdge("generating", "generating"), "none");
  assert.equal(Logic.transitionEdge("ready", "ready"), "none");
  assert.equal(Logic.transitionEdge("absent", "generating"), "mount");
  assert.equal(Logic.transitionEdge("absent", "ready"), "mount");
  assert.equal(Logic.transitionEdge("generating", "ready"), "replace");
  assert.equal(Logic.transitionEdge("ready", "generating"), "replace");
  assert.equal(Logic.transitionEdge("generating", "absent"), "unmount");
  assert.equal(Logic.transitionEdge("ready", "absent"), "unmount");
});

test("committedSuggestions derives the sentinel from the committed panel", () => {
  installDomDouble();
  const { layer } = makeLayerHarness();
  assert.equal(layer.committedSuggestions(absentState()), null);
  assert.equal(layer.committedSuggestions(combatState()), null);
  assert.equal(layer.committedSuggestions({ panels: null }), null);
  assert.equal(layer.committedSuggestions({}), null);
  assert.equal(
    layer.committedSuggestions({
      panels: { context_actions: { available: true, kind: "exploration" } },
    }),
    null
  );
  assert.equal(
    layer.committedSuggestions(explorationState({ status: "generating" })).status,
    "generating"
  );
  assert.deepEqual(
    layer.committedSuggestions(explorationState({ status: "unavailable" })),
    { status: "unavailable" }
  );
});

// ---------------------------------------------------------------------------
// Task 4.1: render-level lifecycle (generating line once, in-place ready
// replacement, removal leaves the container contiguous).
// ---------------------------------------------------------------------------

test("generating mounts one muted line, then ready replaces it in place", () => {
  const { layer, container, actions } = makeLayerHarness();
  layer.handleNotification(absentState());
  assert.equal(container.children.length, 0, "no block before any commit");

  layer.handleNotification(explorationState({ status: "generating" }));
  assert.equal(container.children.length, 1);
  assert.equal(container.children[0].className, "choicepoint-block choicepoint-generating");
  assert.equal(container.children[0].textContent, "AI 正在構思建議…");
  assert.equal(container.children[0].getAttribute("role"), null);

  // A second generating commit renders nothing new (the line stands).
  layer.handleNotification(explorationState({ status: "generating" }));
  assert.equal(container.children.length, 1, "generating -> generating renders nothing new");

  const cards = [card("explore.look", "查看四周"), freeformCard("我們聊聊好嗎？")];
  layer.handleNotification(explorationState({ status: "ready", cards }));
  assert.equal(container.children.length, 1, "ready replaces the line in place, never stacks");
  const group = container.children[0];
  assert.equal(group.className, "choicepoint-block choicepoint-ready");
  const buttons = collectButtons(group);
  assert.equal(buttons.length, 3, "two cards plus the dismiss control");
  assert.equal(actions.calls.length, 0, "rendering never dispatches");

  // ready -> ready is a no-op.
  layer.handleNotification(explorationState({ status: "ready", cards }));
  assert.equal(container.children.length, 1, "ready -> ready never duplicates");
});

test("a ready block mounts directly from absent without a line", () => {
  const { layer, container } = makeLayerHarness();
  const cards = [card("explore.look", "查看四周")];
  layer.handleNotification(explorationState({ status: "ready", cards }));
  assert.equal(container.children.length, 1);
  assert.equal(container.children[0].className, "choicepoint-block choicepoint-ready");
  assert.equal(container.children[0].textContent, "", "no generating line text inside");
});

test("elimination paths remove the block and leave the container contiguous", () => {
  const { layer, container } = makeLayerHarness();
  const cards = [card("explore.look", "查看四周")];
  layer.handleNotification(explorationState({ status: "generating" }));
  layer.handleNotification(explorationState({ status: "ready", cards }));
  assert.equal(container.children.length, 1);

  const eliminations = [
    explorationState({ status: "degraded", cards }),
    explorationState({ status: "unavailable" }),
    explorationState({ status: "mystery" }),
    combatState(),
    absentState(),
    { panels: { context_actions: { available: false, reason: "nope" } } },
  ];
  for (const state of eliminations) {
    layer.handleNotification(explorationState({ status: "ready", cards }));
    layer.handleNotification(state);
    assert.equal(container.children.length, 0, "no block remains after " + JSON.stringify(state));
    assert.equal(container.children.length, 0, "container stays contiguous with no placeholder");
  }
});

test("a transport reset removes a ready block synchronously on its own notification", () => {
  const { layer, container } = makeLayerHarness();
  layer.handleNotification(explorationState({ status: "ready", cards: [card("explore.look", "查看四周")] }));
  assert.equal(container.children.length, 1);
  // `beginTransport` clears the panels and notifies; the layer resolves the
  // cleared snapshot to absence during that same notification — no later
  // snapshot is needed, so a retired-epoch block never stays clickable.
  layer.handleNotification(absentState());
  assert.equal(container.children.length, 0, "removed on the reset notification itself");
  // A fresh generation then mounts a new block from scratch.
  layer.handleNotification(explorationState({ status: "generating" }));
  assert.equal(container.children.length, 1);
  assert.equal(
    container.children[0].className,
    "choicepoint-block choicepoint-generating"
  );
});

test("degraded commits never render a block at any point", () => {
  const { layer, container } = makeLayerHarness();
  layer.handleNotification(explorationState({ status: "degraded", cards: [card("explore.look", "查看四周")] }));
  assert.equal(container.children.length, 0, "degraded never enters the stream from absent");
  layer.handleNotification(explorationState({ status: "generating" }));
  layer.handleNotification(explorationState({ status: "degraded", cards: [card("explore.look", "查看四周")] }));
  assert.equal(container.children.length, 0, "degraded after ready removes the stream block");
});

test("a ready -> generating transition replaces the stale group with the line", () => {
  const { layer, container } = makeLayerHarness();
  layer.handleNotification(explorationState({ status: "ready", cards: [card("explore.move", "前往南門")] }));
  assert.equal(container.children.length, 1);
  layer.handleNotification(explorationState({ status: "generating" }));
  assert.equal(container.children.length, 1, "replacement is in place, never stacked");
  assert.equal(
    container.children[0].className,
    "choicepoint-block choicepoint-generating",
    "the stale ready group is gone"
  );
});

// ---------------------------------------------------------------------------
// Task 1.3: the stream-end block controller — one scroll/unread decision per
// text event, relocation never increments, scrolled-away state preserved.
// ---------------------------------------------------------------------------

test("append without a block keeps the old single decision semantics", () => {
  const { container, block, unread } = makeBlockHarness();
  block.appendNode(new FakeElement("div")); // at bottom -> scroll
  assert.equal(container.scrollTop, container.scrollHeight);
  assert.equal(unread(), 0);

  container.scrollTop = 200; // scrolled away
  block.appendNode(new FakeElement("div"));
  assert.equal(container.scrollTop, 200, "scrolled-away state preserved");
  assert.equal(unread(), 1, "exactly one unread increment per text event");
});

test("each narrative text event counts exactly once with a block mounted", () => {
  const { container, block, unread } = makeBlockHarness();
  block.mount(new FakeElement("div"));
  container.scrollTop = 200;
  for (let i = 0; i < 3; i += 1) {
    block.appendNode(new FakeElement("div"));
  }
  assert.equal(unread(), 3, "one unread increment per committed text event");
  assert.equal(container.scrollTop, 200, "scrolled-away viewport untouched");
});

test("relocation never increments the unread count and never scrolls", () => {
  const { container, block, unread } = makeBlockHarness();
  const node = new FakeElement("div");
  block.mount(node);
  container.scrollTop = 150;
  const before = unread();
  // Displace the block (a defensive path; appends normally keep it last).
  container.appendChild(new FakeElement("div"));
  assert.equal(block.moveToEnd(), true);
  assert.equal(block.moveToEnd(), false, "already last is a no-op");
  assert.equal(container.lastChild, node);
  assert.equal(unread(), before, "relocation never increments");
  assert.equal(container.scrollTop, 150, "relocation never scrolls");
});

test("text appended after a ready block moves the block to the new end", () => {
  const { container, block } = makeBlockHarness();
  const blockNode = new FakeElement("div");
  block.mount(blockNode);
  const lines = ["look output", "talk reply", "scene-flavor push"];
  for (const text of lines) {
    const line = new FakeElement("div");
    line.className = "out";
    block.appendNode(line);
    assert.equal(container.lastChild, blockNode, "block stays last after " + text);
  }
  assert.deepEqual(
    container.children.map((child) => String(child.className || "")),
    ["out", "out", "out", ""],
    "later text lands before the block, the block stays last"
  );
});

test("multiple appends and one block in any order keep the block last", () => {
  const { container, block } = makeBlockHarness();
  block.appendNode(new FakeElement("div"));
  block.appendNode(new FakeElement("div"));
  block.mount(new FakeElement("div"));
  block.appendNode(new FakeElement("div"));
  block.moveToEnd();
  block.appendNode(new FakeElement("div"));
  const classes = container.children.map((child) => String(child.className || ""));
  assert.equal(classes[classes.length - 1], "", "the block is always last");
});

test("unmount after appends leaves the narrative sequence exact", () => {
  const { container, block } = makeBlockHarness();
  const first = new FakeElement("div");
  first.className = "a";
  block.appendNode(first);
  const blockNode = new FakeElement("div");
  block.mount(blockNode);
  const second = new FakeElement("div");
  second.className = "b";
  block.appendNode(second);
  block.unmount();
  assert.deepEqual(
    container.children.map((child) => child.className),
    ["a", "b"],
    "no placeholder or gap remains after removal"
  );
});

test("mount/replace/unmount are safe no-ops without a mounted block", () => {
  const { container, block } = makeBlockHarness();
  assert.equal(block.replace(new FakeElement("div")), false);
  assert.equal(block.unmount(), false);
  assert.equal(block.moveToEnd(), false);
  assert.equal(container.children.length, 0);
});

test("mount is idempotent: a second mount replaces, never duplicates", () => {
  const { container, block } = makeBlockHarness();
  const first = new FakeElement("div");
  first.className = "one";
  block.mount(first);
  const second = new FakeElement("div");
  second.className = "two";
  block.mount(second);
  assert.equal(container.children.length, 1);
  assert.equal(container.children[0].className, "two", "the first block was replaced in place");
});

test("replace swaps in place without moving the block", () => {
  const { container, block } = makeBlockHarness();
  const before = new FakeElement("div");
  block.mount(before);
  const line = new FakeElement("div");
  block.appendNode(line);
  const after = new FakeElement("div");
  block.replace(after);
  assert.equal(container.lastChild, after, "the replacement keeps the end position");
  assert.equal(container.children.indexOf(after), 1, "the replacement kept the in-place position");
});

test("mount and replace keep the end visible when the viewport is at the bottom", () => {
  const { container, block } = makeBlockHarness();
  block.mount(new FakeElement("div"));
  assert.equal(container.scrollTop, container.scrollHeight, "mount at bottom scrolls to keep the end visible");
  block.replace(new FakeElement("div"));
  assert.equal(container.scrollTop, container.scrollHeight, "replace at bottom keeps the end visible");
});

test("the precomputed decision pin holds for input events", () => {
  const { container, block, unread } = makeBlockHarness();
  block.mount(new FakeElement("div"));
  // The input path computes the decision before its divider insertion and
  // pins it: even though the controller would now see the bottom, the pinned
  // value is honored exactly once.
  block.appendNode(new FakeElement("div"), false);
  assert.equal(unread(), 1);
  block.appendNode(new FakeElement("div"), true);
  assert.equal(container.scrollTop, container.scrollHeight);
  assert.equal(unread(), 1);
});

test("an input event (divider + line fragment) keeps the block last", () => {
  const { container, block, unread } = makeBlockHarness();
  const blockNode = new FakeElement("div");
  block.mount(blockNode);
  container.scrollTop = 200; // scrolled away
  const fragment = new FakeFragment();
  const divider = new FakeElement("div");
  divider.className = "narrative-divider";
  fragment.appendChild(divider);
  const line = new FakeElement("div");
  line.className = "inp";
  fragment.appendChild(line);
  block.appendNode(fragment, false);
  assert.equal(
    container.lastChild,
    blockNode,
    "the choice-point block stays last after an input event"
  );
  assert.deepEqual(
    container.children.map((child) => String(child.className || "")),
    ["narrative-divider", "inp", ""],
    "divider and line land before the block, in order, block last"
  );
  assert.equal(unread(), 1, "the whole input event counts exactly once");
});

// ---------------------------------------------------------------------------
// Task 4.3: dock/stream envelope parity (byte-identical requests, identical
// echo behavior — the card path never passes a display descriptor, so the
// CommandEcho bridge resolves to null exactly like the dock twin).
// ---------------------------------------------------------------------------

function dockTwin() {
  delete require.cache[require.resolve("../plugins/exploration_dock.js")];
  require("../plugins/exploration_dock.js");
  return window.Elosern.explorationDock;
}

test("a failed facade mount leaves the state unadvanced; the next commit retries", () => {
  installDomDouble();
  const OptionCards = require("../elosern/option_cards.js");
  const actions = makeActions();
  const container = makeContainer();
  const block = StreamEndBlock.createStreamEndBlock(container, {
    atBottom: () => atBottom(container),
    scrollToBottom: () => {
      container.scrollTop = container.scrollHeight;
    },
    onUnread: () => {},
  });
  let allowMount = false;
  const facade = {
    appendInput: () => false,
    mountChoicePoint: (element) => (allowMount ? block.mount(element) : false),
    moveChoicePointToEnd: () => block.moveToEnd(),
    replaceChoicePoint: (element) => block.replace(element),
    unmountChoicePoint: () => block.unmount(),
  };
  const layer = ChoicePoints.createChoicePointLayer({
    getFacade: () => facade,
    getCards: () => OptionCards,
    getActions: () => actions,
    getLogic: () => Logic,
  });
  layer.handleNotification(explorationState({ status: "generating" }));
  assert.equal(container.children.length, 0, "the failed mount leaves no block");
  assert.equal(
    layer.previousState(),
    "absent",
    "a failed op never advances the remembered state"
  );
  allowMount = true;
  layer.handleNotification(explorationState({ status: "generating" }));
  assert.equal(container.children.length, 1, "the next commit retries the mount");
  assert.equal(layer.previousState(), "generating");
});

test("a failed unmount keeps the block state until the next commit retries", () => {
  installDomDouble();
  const OptionCards = require("../elosern/option_cards.js");
  const actions = makeActions();
  const container = makeContainer();
  const block = StreamEndBlock.createStreamEndBlock(container, {
    atBottom: () => atBottom(container),
    scrollToBottom: () => {
      container.scrollTop = container.scrollHeight;
    },
    onUnread: () => {},
  });
  let allowUnmount = true;
  const facade = {
    appendInput: () => false,
    mountChoicePoint: (element) => block.mount(element),
    moveChoicePointToEnd: () => block.moveToEnd(),
    replaceChoicePoint: (element) => block.replace(element),
    unmountChoicePoint: () => (allowUnmount ? block.unmount() : false),
  };
  const layer = ChoicePoints.createChoicePointLayer({
    getFacade: () => facade,
    getCards: () => OptionCards,
    getActions: () => actions,
    getLogic: () => Logic,
  });
  layer.handleNotification(explorationState({ status: "generating" }));
  assert.equal(container.children.length, 1);
  allowUnmount = false;
  layer.handleNotification(absentState());
  assert.equal(container.children.length, 1, "the failed unmount removes nothing");
  assert.equal(
    layer.previousState(),
    "generating",
    "the remembered state stays put after a failed unmount"
  );
  allowUnmount = true;
  layer.handleNotification(absentState());
  assert.equal(container.children.length, 0, "the next commit retries the unmount");
  assert.equal(layer.previousState(), "absent");
});

test("a stream card and its dock twin dispatch byte-identical envelopes", () => {
  const { layer, container, actions } = makeLayerHarness();
  const dock = dockTwin();
  const params = { exit_ref: "42", current_node: "grid:capital_altoria:2:0" };
  const knownWithParams = {
    kind: "known_action",
    action_code: "explore.move",
    label: "前往南門",
    params,
  };

  // Stream path: click the built card button through the shared factory.
  layer.handleNotification(
    explorationState({ status: "ready", cards: [knownWithParams] })
  );
  const streamButton = collectButtons(container.children[0]).find(
    (button) => button.className === "option-card"
  );
  streamButton.click();
  assert.deepEqual(actions.calls[0], {
    actionId: "explore.move",
    payload: params,
    display: undefined,
  });

  // Dock twin click through the exploration dock's own submit path.
  dock._submitCard(knownWithParams);
  assert.deepEqual(actions.calls[1], {
    actionId: "explore.move",
    payload: params,
    display: undefined,
  });
  assert.deepEqual(actions.calls[0], actions.calls[1], "byte-identical requests");
});

test("stream and dock freeform cards send the identical talk payload once each", () => {
  const { layer, container, actions } = makeLayerHarness();
  const dock = dockTwin();
  const freeform = freeformCard("我們聊聊好嗎？");
  layer.handleNotification(explorationState({ status: "ready", cards: [freeform] }));
  const cardButton = collectButtons(container.children[0]).find(
    (button) => button.className === "option-card"
  );
  const expected = {
    actionId: "explore.talk_freeform",
    payload: { npc_id: 7, speech: "我們聊聊好嗎？" },
    display: undefined,
  };
  cardButton.click();
  assert.deepEqual(actions.calls[0], expected, "stream card payload");
  dock._submitCard(freeform);
  assert.deepEqual(actions.calls[1], expected, "dock twin payload");
  assert.equal(actions.calls.length, 2, "exactly one dispatch per activation, no raw second echo");
});

test("stream known card dispatches the same envelope as the dock twin", () => {
  const { layer, container, actions } = makeLayerHarness();
  const dock = dockTwin();
  const known = card("explore.look", "查看四周");
  layer.handleNotification(explorationState({ status: "ready", cards: [known] }));
  const cardButton = collectButtons(container.children[0]).find(
    (button) => button.className === "option-card"
  );
  cardButton.click();
  assert.deepEqual(actions.calls[0], {
    actionId: "explore.look",
    payload: {},
    display: undefined,
  });
  dock._submitCard(known);
  assert.deepEqual(actions.calls[1], {
    actionId: "explore.look",
    payload: {},
    display: undefined,
  });
  assert.equal(actions.calls.length, 2);
});

test("the stream dismiss control dispatches options.dismiss exactly like the dock", () => {
  const { layer, container, actions } = makeLayerHarness();
  const dock = dockTwin();
  layer.handleNotification(explorationState({ status: "ready", cards: [card("explore.look", "查看四周")] }));
  const dismiss = collectButtons(container.children[0]).find(
    (button) => button.textContent === "✕ 清除建議"
  );
  dismiss.click();
  assert.deepEqual(actions.calls[0], {
    actionId: "options.dismiss",
    payload: {},
    display: undefined,
  });
  dock._submitDismiss();
  assert.deepEqual(actions.calls[1], {
    actionId: "options.dismiss",
    payload: {},
    display: undefined,
  });
});

test("a locked action client rejects stream card clicks by the same admission rule", () => {
  const { layer, container, actions } = makeLayerHarness();
  // The layer itself never bypasses the client: a locked client returns null
  // from submit, and the click handler simply doesn't dispatch again. The
  // stream path goes through the exact same `actions.submit` entry point.
  actions.submit = () => null;
  layer.handleNotification(explorationState({ status: "ready", cards: [card("explore.look", "查看四周")] }));
  const cardButton = collectButtons(container.children[0]).find(
    (button) => button.className === "option-card"
  );
  cardButton.click();
  assert.equal(actions.calls.length, 0, "the locked client rejects the stream click");
});

// ---------------------------------------------------------------------------
// Task 2.4: readiness gate and single subscription.
// ---------------------------------------------------------------------------

function makeFakeController() {
  const listeners = [];
  return {
    listeners,
    subscribe(listener) {
      listeners.push(listener);
      return () => {
        const index = listeners.indexOf(listener);
        if (index !== -1) {
          listeners.splice(index, 1);
        }
      };
    },
    getState() {
      return absentState();
    },
  };
}

test("the readiness gate is a bounded no-op until every contract is present", () => {
  installDomDouble();
  const OptionCards = require("../elosern/option_cards.js");
  const controller = makeFakeController();
  const errors = [];
  const log = { error: (message) => errors.push(message) };

  const missing = ChoicePoints.createChoicePoints({
    controller,
    log,
  });
  // No store on window yet: the gate reports the diagnostic and subscribes
  // nothing.
  missing.start();
  assert.equal(controller.listeners.length, 0, "no subscription while dependencies are missing");
  assert.equal(errors.length, 1, "exactly one bounded diagnostic");

  // With everything present the layer subscribes exactly once.
  window.Elosern.OptionCards = OptionCards;
  window.Elosern.narrativeInput = {
    appendInput: () => false,
    mountChoicePoint: () => false,
    moveChoicePointToEnd: () => false,
    replaceChoicePoint: () => false,
    unmountChoicePoint: () => false,
  };
  window.Elosern.actions = { submit: () => null };
  const ready = ChoicePoints.createChoicePoints({ controller, log });
  ready.start();
  ready.start();
  assert.equal(controller.listeners.length, 1, "one subscription per page");
  assert.equal(errors.length, 1, "no further diagnostics once ready");
});
