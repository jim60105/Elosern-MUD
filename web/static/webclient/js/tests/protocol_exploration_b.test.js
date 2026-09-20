/*
 * exploration panel affordance closures: delivery vectors, portrait_ref exactness, worst-case envelope fit.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { SYNTH_ITEM } = require("./support/synthetic-data.js");
const { VALID_EPOCH, serverTime } = require("./protocol_support.js");
const { validContextActionsExplorationPanel, validExplorationAffordance, validExplorationKeyword, validExplorationLookEntity, validExplorationLookObject, validExplorationMoveRow, validExplorationPanel, validExplorationTarget } = require("./protocol_fixtures.js");

test("the delivery affordance is closed exploration and context actions with exact npc_id and item_key params", () => {
  const actionId = "explore.deliver";
  // Valid vectors through the params validator (mirrors the Python
  // _require_ascii_identifier: 1..64 ASCII characters).
  assert.deepEqual(
    Protocol.validateContextActionsAffordanceParams(actionId, {
      npc_id: 5,
      item_key: SYNTH_ITEM.id,
    }),
    { npc_id: 5, item_key: SYNTH_ITEM.id }
  );
  assert.deepEqual(
    Protocol.validateContextActionsAffordanceParams(actionId, {
      npc_id: Protocol.MAX_SAFE_INTEGER,
      item_key: "a",
    }),
    { npc_id: Protocol.MAX_SAFE_INTEGER, item_key: "a" }
  );

  // Invalid vectors: extra, missing, mistyped, out-of-bound, non-ASCII.
  const invalidParams = [
    {},
    { npc_id: 5 },
    { item_key: SYNTH_ITEM.id },
    { npc_id: 5, item_key: SYNTH_ITEM.id, extra: "junk" },
    { npc_id: 0, item_key: SYNTH_ITEM.id },
    { npc_id: -1, item_key: SYNTH_ITEM.id },
    { npc_id: 1.5, item_key: SYNTH_ITEM.id },
    { npc_id: "5", item_key: SYNTH_ITEM.id },
    { npc_id: true, item_key: SYNTH_ITEM.id },
    { npc_id: null, item_key: SYNTH_ITEM.id },
    { npc_id: 5, item_key: "" },
    { npc_id: 5, item_key: SYNTH_ITEM.display },
    { npc_id: 5, item_key: "x".repeat(65) },
    { npc_id: 5, item_key: 7 },
    { npc_id: 5, item_key: null },
    "not an object",
    null,
    [1],
  ];
  for (const bad of invalidParams) {
    assert.throws(
      () => Protocol.validateContextActionsAffordanceParams(actionId, bad),
      undefined,
      `Expected ${actionId} with ${JSON.stringify(bad)} to throw`
    );
  }

  // Drive the real context_actions exploration panel validation.
  const panel = validContextActionsExplorationPanel({
    affordances: [
      {
        action_id: actionId,
        label: `交付 ${SYNTH_ITEM.display} 給 灰婆婆`,
        params: { npc_id: 5, item_key: SYNTH_ITEM.id },
        freeform: false,
        navigation: false,
        enabled: true,
        disabled_reason: null,
      },
    ],
  });
  assert.doesNotThrow(() => Protocol.validateContextActionsPanel(panel));

  const badPanel = validContextActionsExplorationPanel({
    affordances: [
      {
        action_id: actionId,
        label: `交付 ${SYNTH_ITEM.display} 給 灰婆婆`,
        params: { npc_id: 5, item_key: SYNTH_ITEM.display },
        freeform: false,
        navigation: false,
        enabled: true,
        disabled_reason: null,
      },
    ],
  });
  assert.throws(() => Protocol.validateContextActionsPanel(badPanel));

  // Drive the real exploration panel validation (target-scoped affordance).
  assert.ok(
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            keywords: [],
            affordances: [
              validExplorationAffordance({
                action_id: actionId,
                label: `交付 ${SYNTH_ITEM.display} 給 灰婆婆`,
                  params: { npc_id: 5, item_key: SYNTH_ITEM.id },
              }),
            ],
          }),
        ],
      })
    )
  );
});

test("exploration portrait_ref must be null and entries exact", () => {
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({ interact: [validExplorationTarget({ portrait_ref: "cat:goblin" })] })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        look: {
          ...validExplorationPanel().look,
          entities: [validExplorationLookEntity({ portrait_ref: "cat:goblin" })],
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(validExplorationPanel({ quests: { available: "yes" } }))
  );
});

test("worst-case exploration payload fits the envelope and all-ceilings fails closed", () => {
  const interact = [];
  for (let i = 0; i < Protocol.EXPLORATION_MAX_INTERACT_TARGETS; i++) {
    const affordances = [validExplorationAffordance()];
    for (let j = 1; j < Protocol.EXPLORATION_MAX_AFFORDANCES; j++) {
      affordances.push({
        kind: "action",
        action_id: "explore.engage",
        label: "戰鬥",
        enabled: true,
        disabled_reason: null,
      });
    }
    interact.push(
      validExplorationTarget({
        identity: i + 1,
        affordances,
        keywords: Array(Protocol.EXPLORATION_MAX_SCRIPTED_KEYWORDS).fill(
          validExplorationKeyword()
        ),
      })
    );
  }
  const worst = validExplorationPanel({
    move: Array(Protocol.EXPLORATION_MAX_MOVE_EXITS).fill(validExplorationMoveRow()),
    look: {
      room: { identity: 3, display_name: "南門", room: true },
      entities: Array(Protocol.EXPLORATION_MAX_LOOK_ENTITIES).fill(validExplorationLookEntity()),
      objects: Array(Protocol.EXPLORATION_MAX_LOOK_OBJECTS).fill(validExplorationLookObject()),
    },
    interact,
  });
  const normalized = Protocol.validateExplorationPanel(worst);
  assert.ok(Protocol.jsonByteSize(normalized) <= Protocol.MAX_CANONICAL_JSON_BYTES);

  const overInteract = [];
  for (let i = 0; i < Protocol.EXPLORATION_MAX_INTERACT_TARGETS; i++) {
    overInteract.push(
      validExplorationTarget({
        identity: i + 1,
        affordances: Array(Protocol.EXPLORATION_MAX_AFFORDANCES).fill(
          validExplorationAffordance({ label: "交談".repeat(60) })
        ),
        keywords: Array(Protocol.EXPLORATION_MAX_SCRIPTED_KEYWORDS).fill(
          validExplorationKeyword({
            keyword_id: "k".repeat(Protocol.EXPLORATION_MAX_KEYWORD_ID),
            label: "話".repeat(Protocol.EXPLORATION_MAX_KEYWORD_LABEL),
          })
        ),
      })
    );
  }
  const over = validExplorationPanel({ interact: overInteract });
  assert.throws(() => Protocol.validateExplorationPanel(over), /envelope/);
});

test("exploration and character are in the production panel allowlist", () => {
  assert.equal(Protocol.PANEL_ALLOWLIST.exploration, 2);
  assert.equal(Protocol.PANEL_ALLOWLIST.character, 7);
  const envelope = {
    protocol_version: 1,
    presentation_epoch: VALID_EPOCH,
    revision: 1,
    mode: "exploration",
    panels: { exploration: { ...validExplorationPanel(), kind: "bogus" } },
    layout_version: 1,
    server_time: serverTime(),
  };
  const store = Protocol.createStore();
  store.beginTransport(1);
  const accepted = store.receive(1, "ui_snapshot", [envelope], {});
  assert.equal(accepted.accepted, false);
  assert.equal(accepted.reason, "invalid");
});

