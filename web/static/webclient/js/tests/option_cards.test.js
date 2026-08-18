/*
 * DOM-level contract tests for the shared suggestion card component
 * (webclient-options-surface). `buildCard` and `buildDismissButton` are
 * exercised against a minimal DOM double so the element structure, the
 * literal-text-node rule, and the exact click contract are verified without a
 * browser.
 */
const test = require("node:test");
const assert = require("node:assert/strict");

const OptionCards = require("../elosern/option_cards.js");

// ---------------------------------------------------------------------------
// Minimal DOM double: enough element surface for the card builders.
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
    this.listeners = {};
    this.type = null;
    this.id = null;
  }

  // The real DOM keeps className and classList in sync; mirror that so the
  // builders' `className = ...` assignments and `classList.add` calls agree.
  set className(value) {
    this.classList.names = new Set(String(value || "").split(" ").filter(Boolean));
  }

  get className() {
    return Array.from(this.classList.names).join(" ");
  }

  // The real textContent includes every descendant text node.
  get textContent() {
    return this.children
      .map((child) =>
        child.nodeType === 3 ? child.value : child.textContent
      )
      .join("");
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
    return child;
  }

  get firstChild() {
    return this.children[0] || null;
  }

  addEventListener(name, handler) {
    this.listeners[name] = handler;
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
  global.document = {
    createElement(tag) {
      const element = new FakeElement(tag);
      elements.push(element);
      return element;
    },
    createTextNode(value) {
      return new FakeTextNode(value);
    },
  };
  return elements;
}

function click(element) {
  assert.equal(typeof element.listeners.click, "function", "button must carry a click listener");
  element.listeners.click();
}

function knownCard(overrides = {}) {
  return Object.assign(
    {
      kind: "known_action",
      action_code: "explore.move",
      label: "前往南門",
      params: { exit_ref: "42", current_node: "grid:capital_altoria:2:0" },
      hint: null,
    },
    overrides
  );
}

function freeformCard(overrides = {}) {
  return Object.assign(
    {
      kind: "freeform",
      action_code: "explore.talk_freeform",
      label: "我們聊聊好嗎？",
      params: { npc_id: 7 },
      hint: null,
    },
    overrides
  );
}

// ---------------------------------------------------------------------------

test("known_action cards render as native buttons with the exact label text", () => {
  installDomDouble();
  const button = OptionCards.buildCard(knownCard(), () => {});
  assert.equal(button.tagName, "button");
  assert.equal(button.type, "button");
  assert.ok(button.classList.names.has("option-card"));
  assert.ok(button.classList.names.has("option-card-known"));
  assert.ok(!button.classList.names.has("option-card-freeform"));
  const [label, hint] = button.children;
  assert.equal(label.className, "option-card-label");
  assert.equal(label.textContent, "前往南門");
  assert.equal(button.textContent, "前往南門");
  assert.equal(hint, undefined, "no hint line when the card carries none");
});

test("a present hint renders as a plain text line under the label", () => {
  installDomDouble();
  const button = OptionCards.buildCard(
    knownCard({ hint: "從南門前往王都街道" }),
    () => {}
  );
  const [label, hint] = button.children;
  assert.equal(hint.className, "option-card-hint");
  assert.equal(hint.textContent, "從南門前往王都街道");
  assert.equal(button.textContent, "前往南門從南門前往王都街道");
});

test("freeform cards differ only in their kind class and payload contract", () => {
  installDomDouble();
  const button = OptionCards.buildCard(freeformCard(), () => {});
  assert.ok(button.classList.names.has("option-card-freeform"));
  assert.ok(!button.classList.names.has("option-card-known"));
  assert.equal(button.textContent, "我們聊聊好嗎？");
});

test("clicking a card invokes the handler with the exact validated card", () => {
  installDomDouble();
  const card = knownCard();
  const clicked = [];
  const button = OptionCards.buildCard(card, (value) => clicked.push(value));
  click(button);
  assert.equal(clicked.length, 1);
  assert.equal(clicked[0], card);
});

test("the dismiss button is a separate element with its own click contract", () => {
  installDomDouble();
  let dismisses = 0;
  const button = OptionCards.buildDismissButton(() => (dismisses += 1));
  assert.equal(button.tagName, "button");
  assert.equal(button.type, "button");
  assert.ok(button.classList.names.has("suggestions-dismiss"));
  assert.equal(button.textContent, "✕ 清除建議");
  // The dismiss control carries only its label text node -- no card
  // structure, no card payload contract.
  assert.equal(
    button.children.every((child) => child.nodeType === 3),
    true,
    "the dismiss button must carry only its label text node"
  );
  click(button);
  assert.equal(dismisses, 1);
  click(button);
  assert.equal(dismisses, 2);
});
