/*
 * exploration panel v1 (design D10): discriminator, bounds, affordance shapes, closed action codes.
 *
 * Split sibling of the original protocol.test.js; shared fixtures live in
 * ./protocol_support.js and ./protocol_fixtures.js.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const Protocol = require("../elosern/protocol.js");
const { unavailableStatusPanel, update } = require("./protocol_support.js");
const { validContextActionsExplorationPanel, validExplorationAffordance, validExplorationKeyword, validExplorationLookEntity, validExplorationLookObject, validExplorationMoveRow, validExplorationPanel, validExplorationTarget } = require("./protocol_fixtures.js");



test("validates the exploration panel available/unavailable discriminator", () => {
  assert.deepEqual(
    Protocol.validatePanel(
      "exploration",
      Protocol.PANEL_ALLOWLIST.exploration,
      unavailableStatusPanel({ schema_version: 2 })
    ),
    unavailableStatusPanel({ schema_version: 2 })
  );
  assert.doesNotThrow(() => Protocol.validateExplorationPanel(validExplorationPanel()));
  assert.throws(() => Protocol.validateExplorationPanel(validExplorationPanel({ extra: 1 })));
  assert.throws(() => Protocol.validateExplorationPanel(validExplorationPanel({ kind: "services" })));
  assert.throws(() =>
    Protocol.validateExplorationPanel(validExplorationPanel({ schema_version: 1 }))
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(validExplorationPanel({ schema_version: 3 }))
  );
});

test("enforces exploration D10 bounds", () => {
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        move: Array(Protocol.EXPLORATION_MAX_MOVE_EXITS + 1).fill(validExplorationMoveRow()),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        move: [validExplorationMoveRow({ exit_ref: "x".repeat(Protocol.EXPLORATION_MAX_EXIT_REF + 1) })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        move: [validExplorationMoveRow({ exit_ref: "中文" })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        move: [validExplorationMoveRow({ destination: "not:a:node" })],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        look: {
          ...validExplorationPanel().look,
          entities: Array(Protocol.EXPLORATION_MAX_LOOK_ENTITIES + 1).fill(validExplorationLookEntity()),
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        look: {
          ...validExplorationPanel().look,
          objects: Array(Protocol.EXPLORATION_MAX_LOOK_OBJECTS + 1).fill(validExplorationLookObject()),
        },
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: Array(Protocol.EXPLORATION_MAX_INTERACT_TARGETS + 1).fill(validExplorationTarget()),
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: Array(Protocol.EXPLORATION_MAX_AFFORDANCES + 1).fill(
              {
                kind: "action",
                action_id: "explore.engage",
                label: "戰鬥",
                enabled: true,
                disabled_reason: null,
              }
            ),
          }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            keywords: Array(Protocol.EXPLORATION_MAX_SCRIPTED_KEYWORDS + 1).fill(
              validExplorationKeyword()
            ),
          }),
        ],
      })
    )
  );
});

test("affordance shapes are exact in the exploration panel", () => {
  // navigate never carries an action_id; action never carries a surface.
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: [
              {
                kind: "navigate",
                action_id: "explore.talk_scripted",
                surface: "guild",
                label: "公會服務",
                enabled: true,
                disabled_reason: null,
              },
            ],
          }),
        ],
      })
    )
  );
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: [
              {
                kind: "action",
                surface: "guild",
                label: "公會服務",
                enabled: true,
                disabled_reason: null,
              },
            ],
          }),
        ],
      })
    )
  );
  // Keywords require a talk_scripted affordance on the target.
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: [
              validExplorationAffordance({ action_id: "explore.engage" }),
            ],
          }),
        ],
      })
    )
  );
  // explore.take is outside the closed action set.
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: [
              {
                kind: "action",
                action_id: "explore.take",
                label: "拾取",
                enabled: true,
                disabled_reason: null,
              },
            ],
          }),
        ],
      })
    )
  );
  // explore.party_kick is outside the closed action set.
  assert.throws(() =>
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            affordances: [
              {
                kind: "action",
                action_id: "explore.party_kick",
                label: "踢出",
                enabled: true,
                disabled_reason: null,
              },
            ],
          }),
        ],
      })
    )
  );
});

test("party invite and leave affordances are closed exploration actions", () => {
  assert.ok(
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            keywords: [],
            affordances: [
              validExplorationAffordance({
                action_id: "explore.party_invite",
                label: "邀請",
              }),
            ],
          }),
        ],
      })
    )
  );
  assert.ok(
    Protocol.validateExplorationPanel(
      validExplorationPanel({
        interact: [
          validExplorationTarget({
            keywords: [],
            affordances: [
              validExplorationAffordance({
                action_id: "explore.party_leave",
                label: "解散",
              }),
            ],
          }),
        ],
      })
    )
  );
});

test("possession affordances are closed exploration and context actions with exact npc_id params", () => {
  // update on vocabulary change: ACTION_CODE_ALLOWLIST in web/webclient/presentation/affordances.py
  const EXPECTED_ACTION_CODES = [
    "explore.move",
    "explore.look",
    "explore.talk_scripted",
    "explore.talk_freeform",
    "explore.party_invite",
    "explore.party_leave",
    "explore.engage",
    "explore.wait",
    "explore.possess",
    "explore.possess_release",
    "explore.deliver",
  ];
  assert.deepEqual(Protocol.CONTEXT_ACTIONS_ACTION_CODES, EXPECTED_ACTION_CODES);

  // EXPLORATION_ACTION_IDS is intentionally the target-scoped subset (affordances requiring an
  // NPC target identity). explore.move, explore.look, and explore.wait are omitted because they
  // are never emitted as per-target affordances. Update if target-scoped vocabulary changes.
  const EXPECTED_EXPLORATION_ACTION_IDS = [
    "explore.talk_scripted",
    "explore.talk_freeform",
    "explore.party_invite",
    "explore.party_leave",
    "explore.engage",
    "explore.possess",
    "explore.possess_release",
    "explore.deliver",
  ];
  assert.deepEqual(Protocol.EXPLORATION_ACTION_IDS, EXPECTED_EXPLORATION_ACTION_IDS);

  for (const actionId of ["explore.possess", "explore.possess_release"]) {
    // Valid vectors through params validator
    assert.deepEqual(
      Protocol.validateContextActionsAffordanceParams(actionId, { npc_id: 1 }),
      { npc_id: 1 }
    );
    assert.deepEqual(
      Protocol.validateContextActionsAffordanceParams(actionId, { npc_id: 42 }),
      { npc_id: 42 }
    );
    assert.deepEqual(
      Protocol.validateContextActionsAffordanceParams(actionId, { npc_id: Protocol.MAX_SAFE_INTEGER }),
      { npc_id: Protocol.MAX_SAFE_INTEGER }
    );

    // Invalid vectors through params validator
    const invalidParams = [
      {},
      { npc_id: 0 },
      { npc_id: -1 },
      { npc_id: 1.5 },
      { npc_id: "42" },
      { npc_id: true },
      { npc_id: null },
      { npc_id: 1, extra: "junk" },
      { npc_id: Protocol.MAX_SAFE_INTEGER + 1 },
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

    // Drive real context_actions exploration panel validation
    const label = actionId === "explore.possess" ? "附身" : "歸位";
    const panel = validContextActionsExplorationPanel({
      affordances: [
        {
          action_id: actionId,
          label,
          params: { npc_id: 5 },
          freeform: false,
          navigation: false,
          enabled: true,
          disabled_reason: null,
        },
      ],
    });
    assert.doesNotThrow(() => Protocol.validateContextActionsPanel(panel));

    // Malformed params in panel must reject
    const badPanel = validContextActionsExplorationPanel({
      affordances: [
        {
          action_id: actionId,
          label,
          params: { npc_id: 0 },
          freeform: false,
          navigation: false,
          enabled: true,
          disabled_reason: null,
        },
      ],
    });
    assert.throws(() => Protocol.validateContextActionsPanel(badPanel));

    // Drive real exploration panel validation
    assert.ok(
      Protocol.validateExplorationPanel(
        validExplorationPanel({
          interact: [
            validExplorationTarget({
              keywords: [],
              affordances: [
                validExplorationAffordance({
                  action_id: actionId,
                  label,
                }),
              ],
            }),
          ],
        })
      )
    );
  }
});
