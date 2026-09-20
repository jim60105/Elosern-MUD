/*
 * context_actions combat/recovery panel schema: valid payloads, exploration form, suggestions envelopes.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { deepMerge, snapshot } = require("./protocol_support.js");
const { validCombatPanel, validContextActionsExplorationPanel, validRecoveryPanel } = require("./protocol_fixtures.js");



test("validates the available context_actions combat panel", () => {
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(validCombatPanel()));
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(validRecoveryPanel()));
  // The registered production allowlist must advertise the same version the
  // server ships (mirror of web.webclient.presentation.registry).
  assert.equal(Protocol.PANEL_ALLOWLIST.context_actions, 5);
});

test("validates the available context_actions exploration form", () => {
  const affordance = {
    action_id: "explore.talk_scripted",
    label: "註冊",
    params: { npc_id: 5, keyword_id: "註冊" },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  };
  const panel = validContextActionsExplorationPanel({
    affordances: [
      {
        action_id: "explore.look",
        label: "南門",
        params: { room: true },
        freeform: false,
        navigation: false,
        enabled: true,
        disabled_reason: null,
      },
      affordance,
      {
        surface: "guild",
        label: "公會服務",
        navigation: true,
        enabled: true,
        disabled_reason: null,
      },
    ],
  });
  const normalized = Protocol.validateContextActionsPanel(panel);
  assert.equal(normalized.schema_version, 5);
  assert.equal(normalized.kind, "exploration");
  assert.equal(normalized.affordances.length, 3);
  assert.deepEqual(normalized.affordances[0].params, { room: true });
  assert.equal(normalized.affordances[1].freeform, false);
  assert.equal(normalized.affordances[2].navigation, true);
  assert.deepEqual(normalized.suggestions, { status: "unavailable" });
  // Cross-form contamination rejects on both sides.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      Object.assign(deepMerge(panel, {}), { session: {}, skills: [] })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      Object.assign(deepMerge(validCombatPanel(), {}), { affordances: [affordance] })
    )
  );
  // Malformed entries reject atomically.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [Object.assign({}, affordance, { action_id: "explore.interact" })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [
          Object.assign({}, affordance, {
            params: { npc_id: 5, keyword_id: "註冊", extra: 1 },
          }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [
          {
            surface: "bank",
            label: "公會",
            navigation: true,
            enabled: true,
            disabled_reason: null,
          },
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [Object.assign({}, affordance, { enabled: false, disabled_reason: null })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [Object.assign({}, affordance, { freeform: "yes" })],
      })
    )
  );
  // The 320-entry bound rejects.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: new Array(321).fill(affordance),
      })
    )
  );
  // The freeform entry accepts exactly the binding shape.
  assert.doesNotThrow(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [
          {
            action_id: "explore.talk_freeform",
            label: "自由交談",
            params: { npc_id: 9 },
            freeform: true,
            navigation: false,
            enabled: true,
            disabled_reason: null,
          },
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [
          {
            action_id: "explore.talk_freeform",
            label: "自由交談",
            params: { npc_id: 9, speech: "你好" },
            freeform: true,
            navigation: false,
            enabled: true,
            disabled_reason: null,
          },
        ],
      })
    )
  );
  // The freeform flag must pair with the action code on both sides.
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [Object.assign({}, affordance, { freeform: true })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      validContextActionsExplorationPanel({
        affordances: [
          {
            action_id: "explore.talk_freeform",
            label: "自由交談",
            params: { npc_id: 9 },
            freeform: false,
            navigation: false,
            enabled: true,
            disabled_reason: null,
          },
        ],
      })
    )
  );
});

test("validates suggestions envelopes per status", () => {
  // generating/unavailable carry only status.
  assert.deepEqual(Protocol.validateSuggestions({ status: "generating" }), {
    status: "generating",
  });
  assert.deepEqual(Protocol.validateSuggestions({ status: "unavailable" }), {
    status: "unavailable",
  });
  // ready requires 3..5 cards; degraded accepts 0..5.
  const card = {
    kind: "known_action",
    action_code: "explore.look",
    label: "查看房間",
    params: { room: true },
  };
  const readyCards = [
    card,
    { ...card, label: "前往東邊" },
    { ...card, label: "與路人交談" },
  ];
  assert.deepEqual(
    Protocol.validateSuggestions({ status: "ready", cards: readyCards }),
    { status: "ready", cards: readyCards.map((c) => Object.assign({}, c, { hint: null })) }
  );
  assert.doesNotThrow(() =>
    Protocol.validateSuggestions({ status: "degraded", cards: [] })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "ready", cards: [] })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "ready", cards: readyCards.slice(0, 2) })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: new Array(6).fill(card),
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "degraded", cards: new Array(6).fill(card) })
  );
  // Unknown status, extra/missing keys reject.
  assert.throws(() => Protocol.validateSuggestions({ status: "bogus" }));
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "generating", cards: [] })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "unavailable", cards: [] })
  );
  assert.throws(() => Protocol.validateSuggestions({ status: "ready" }));
  assert.throws(() =>
    Protocol.validateSuggestions({ status: "ready", cards: readyCards, extra: 1 })
  );
  // A freeform card must pin explore.talk_freeform with the binding shape.
  assert.doesNotThrow(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        { ...card, label: "自由交談" },
        {
          kind: "freeform",
          action_code: "explore.talk_freeform",
          label: "隨意聊聊",
          params: { npc_id: 9 },
        },
        { ...card, label: "查看怪物" },
      ],
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        {
          kind: "freeform",
          action_code: "explore.move",
          label: "自由交談",
          params: { npc_id: 9 },
        },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        {
          kind: "freeform",
          action_code: "explore.talk_freeform",
          label: "自由交談",
          params: { npc_id: 9, speech: "你好" },
        },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  // Non-CJK or over-long labels, over-long hints reject.
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        { ...card, label: "hello" },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        { ...card, label: "很".repeat(25) },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        { ...card, hint: "很".repeat(61) },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  // Other booleans in params reject; the room-survey boolean is accepted.
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        {
          ...card,
          params: { room: false },
        },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
  assert.throws(() =>
    Protocol.validateSuggestions({
      status: "ready",
      cards: [
        {
          ...card,
          params: { room: true, extra: 1 },
        },
        card,
        { ...card, label: "與路人交談" },
      ],
    })
  );
});

test("a 300-affordance exploration form passes the global envelope gate", () => {
  const affordance = {
    action_id: "explore.look",
    label: "南門",
    params: { room: true },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  };
  const panel = validContextActionsExplorationPanel({
    affordances: new Array(300).fill(affordance),
  });
  // The global list ceiling (MAX_LIST_ITEMS) must clear the maximal
  // affordance list or the client would reject every snapshot for a large
  // room before panel validation ever runs.
  assert.doesNotThrow(() => Protocol.checkEnvelope(panel));
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(panel));
  assert.throws(() =>
    Protocol.validateContextActionsPanel(
      Object.assign({}, panel, {
        affordances: new Array(Protocol.CONTEXT_ACTIONS_MAX_AFFORDANCES + 1).fill(affordance),
      })
    )
  );
});
