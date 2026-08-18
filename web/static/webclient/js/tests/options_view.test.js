/*
 * Pure view-model tests for the exploration dock's suggestions section
 * (webclient-options-surface). `buildOptionsView` is DOM-independent, so the
 * four v5 statuses, the missing-section compatibility guard, the card-list
 * passthrough, and the zero-card degraded empty-state are all exercised
 * without a browser.
 */
const test = require("node:test");
const assert = require("node:assert/strict");

const OptionCards = require("../elosern/option_cards.js");

function panel(suggestions) {
  return {
    schema_version: 5,
    available: true,
    kind: "exploration",
    affordances: [],
    suggestions,
  };
}

function card(actionCode, label) {
  return { kind: "known_action", action_code: actionCode, label, params: {} };
}

test("generating maps to a visible status with no cards and no empty-state", () => {
  const view = OptionCards.buildOptionsView(panel({ status: "generating" }));
  assert.deepEqual(view, {
    status: "generating",
    cards: [],
    visible: true,
    emptyState: false,
  });
});

test("unavailable maps to a hidden status", () => {
  const view = OptionCards.buildOptionsView(panel({ status: "unavailable" }));
  assert.deepEqual(view, {
    status: "unavailable",
    cards: [],
    visible: false,
    emptyState: false,
  });
});

test("ready passes the validated card list through unchanged", () => {
  const cards = [
    card("explore.move", "前往南門"),
    card("explore.look", "查看四周"),
    { kind: "freeform", action_code: "explore.talk_freeform", label: "我們聊聊好嗎？", params: { npc_id: 7 } },
  ];
  const view = OptionCards.buildOptionsView(panel({ status: "ready", cards }));
  assert.deepEqual(view, {
    status: "ready",
    cards,
    visible: true,
    emptyState: false,
  });
});

test("degraded with cards is visible and never an empty state", () => {
  const cards = [card("explore.look", "查看四周")];
  const view = OptionCards.buildOptionsView(panel({ status: "degraded", cards }));
  assert.deepEqual(view, {
    status: "degraded",
    cards,
    visible: true,
    emptyState: false,
  });
});

test("zero-card degraded maps to the empty-state fallback", () => {
  const view = OptionCards.buildOptionsView(panel({ status: "degraded", cards: [] }));
  assert.deepEqual(view, {
    status: "degraded",
    cards: [],
    visible: true,
    emptyState: true,
  });
});

test("a missing suggestions field maps to hidden as a compatibility guard", () => {
  const view = OptionCards.buildOptionsView({
    schema_version: 5,
    available: true,
    kind: "exploration",
    affordances: [],
  });
  assert.deepEqual(view, {
    status: "unavailable",
    cards: [],
    visible: false,
    emptyState: false,
  });
});

test("an absent or malformed panel maps to hidden", () => {
  assert.equal(OptionCards.buildOptionsView(null).visible, false);
  assert.equal(OptionCards.buildOptionsView(undefined).visible, false);
  assert.equal(OptionCards.buildOptionsView({}).visible, false);
  assert.equal(
    OptionCards.buildOptionsView(panel({ status: "bogus" })).visible,
    false
  );
  assert.equal(OptionCards.buildOptionsView(panel(null)).visible, false);
});

test("the signature derives status, count, and full card content", () => {
  const ready = {
    status: "ready",
    cards: [
      card("explore.move", "前往南門"),
      card("explore.look", "查看四周"),
      { kind: "freeform", action_code: "explore.talk_freeform", label: "我們聊聊好嗎？", params: { npc_id: 7 } },
    ],
  };
  assert.equal(
    OptionCards.suggestionsSignature(ready),
    "ready:3:" +
      "known_action|explore.move|前往南門||" +
      "+known_action|explore.look|查看四周||" +
      "+freeform|explore.talk_freeform|我們聊聊好嗎？|npc_id=7|"
  );
  assert.equal(
    OptionCards.suggestionsSignature({ status: "generating" }),
    "generating:0:"
  );
  assert.equal(
    OptionCards.suggestionsSignature({ status: "unavailable" }),
    "unavailable:0:"
  );
});

test("the signature is sensitive to label, hint, and params changes", () => {
  const ready = {
    status: "ready",
    cards: [
      card("explore.move", "前往南門"),
      card("explore.look", "查看四周"),
    ],
  };
  const base = OptionCards.suggestionsSignature(ready);
  // A regenerated set can keep the same action codes while changing labels,
  // hints, or params: the section must re-render (stale cards would keep old
  // click payloads).
  assert.notEqual(
    OptionCards.suggestionsSignature({
      status: "ready",
      cards: [
        card("explore.move", "換個標籤"),
        card("explore.look", "查看四周"),
      ],
    }),
    base
  );
  assert.notEqual(
    OptionCards.suggestionsSignature({
      status: "ready",
      cards: [
        { kind: "known_action", action_code: "explore.move", label: "前往南門", params: { exit_ref: "42", current_node: "grid:capital_altoria:2:0" }, hint: "加了說明" },
        card("explore.look", "查看四周"),
      ],
    }),
    base
  );
  assert.notEqual(
    OptionCards.suggestionsSignature({
      status: "ready",
      cards: [
        card("explore.move", "前往南門"),
        { kind: "known_action", action_code: "explore.look", label: "查看四周", params: { room: true } },
      ],
    }),
    base
  );
});

test("the signature is null for an absent or malformed envelope", () => {
  assert.equal(OptionCards.suggestionsSignature(null), null);
  assert.equal(OptionCards.suggestionsSignature(undefined), null);
  assert.equal(OptionCards.suggestionsSignature("ready"), null);
  assert.equal(OptionCards.suggestionsSignature({}), null);
});
