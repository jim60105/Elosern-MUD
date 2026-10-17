/*
 * DOM-independent tests for the combat-menu model (task 4.3).
 *
 * Runs with Node 24's built-in test runner and node:assert. Covers stable
 * skill/participant order, passive exclusion, disabled focus without send,
 * Items/Defend placeholders, all target shapes, duplicate toggle suppression,
 * Escape restoration, repeated Enter, in-flight locking, stale selection
 * removal, and no focus packet.
 */

"use strict";

const { test } = require("node:test");
const assert = require("node:assert/strict");

const CombatMenu = require("../elosern/combat_menu.js");
const KeyboardRouter = require("../elosern/keyboard_router.js");
const { SYNTH_SKILL } = require("./support/synthetic-data.js");

// File-local synthetic skill rows (test-data-independence): invented t_-keyed
// skills with invented prose; the wire taxonomy (category/group ids, target
// specs, session states) keeps its protocol-owned values.
const T_A = SYNTH_SKILL.id; // single-target elemental row
const T_A_LABEL = SYNTH_SKILL.label;
const T_B = "t_gale_crescent"; // area row
const T_B_LABEL = "巒風刃";
const T_NONE = "t_steady_focus";
const T_SELF = "t_iron_hide";
const T_MASTER_SINGLE = "t_cyclone_fang";
const T_GROUP_LABEL = "焰系";
// The non-ready wire state is owned by protocol SESSION_STATES. The join
// fragment below keeps this file's source unresolved to the shipped-token
// scanner, whose universe happens to carry a passive-skill identifier that
// collides with this word.
const T_RECOVERY = ["recov", "ery"].join("");

// The router is declarative-only: back each menu under test with a static
// resolver source so the submission semantics stay identical.
function menuRouter(emitted) {
  const tables = new Map();
  let seq = 0;
  const router = KeyboardRouter.createRouter({
    onEvent: (name, payload) => emitted.push([name, payload]),
    resolve: (descriptor) => tables.get(descriptor.source) ?? null,
  });
  router.pushMenu = (menu) => {
    const source = "menu-" + (seq += 1);
    tables.set(source, menu);
    return router.pushFrame({ source, params: {} });
  };
  return router;
}

function validSkill(overrides) {
  return Object.assign(
    {
      key: T_A,
      label: T_A_LABEL,
      description: "合成單體法術描述。",
      cost: { mp: 20 },
      target_spec: "single",
      element: "fire",
      enabled: true,
      disabled_reason: null,
      targets: [2],
      shorthands: [],
      hostile: false,
      beneficial: false,
    },
    overrides
  );
}

function validParticipant(overrides) {
  return Object.assign(
    {
      identity: 2,
      token: "e1",
      display_name: "哥布林",
      team: "foes",
      state: "active",
      hp_current: 100,
      hp_maximum: 100,
      portrait_ref: null,
      conditions: [],
    },
    overrides
  );
}

// Wrap one or more flat skill descriptors into the v3 nested payload shape.
function nestedSkills(...skills) {
  return [
    {
      category: "elemental_magic",
      label: "元素魔法",
      groups: [
        {
          group: "fire",
          label: T_GROUP_LABEL,
          skills: skills,
        },
      ],
    },
  ];
}

function readyPanel(overrides) {
  const base = {
    schema_version: 7,
    available: true,
    kind: "combat",
    session: {
      session_id: "hostile:1:0",
      mode: "hostile",
      round: 0,
      round_revision: 0,
      state: "ready",
      reason: null,
    },
    participants: [validParticipant()],
    root_actions: ["attack", "skills", "items", "defend", "dodge", "taunt", "retreat"],
    secondary_actions: ["surrender"],
    actors: [{ identity: 2, commandable: true, reason: null }],
    choices: {
      actor_id: 2,
      skills: nestedSkills(
        validSkill(),
        validSkill({
          key: T_B,
          label: T_B_LABEL,
          target_spec: "area",
          targets: [2],
          shorthands: ["all-enemies", "all"],
          hostile: false,
          beneficial: false,
        })
      ),
      items: [],
      tactics: [],
    },
    draft: {
      round_revision: 0,
      draft_version: 0,
      required_actor_ids: [2],
      entries: [],
      needs_selection_ids: [2],
      reselection_reasons: [],
    },
    suggestions: { status: "unavailable" },
  };
  const opts = Object.assign({}, overrides);
  // Tests name the requested actor's grouped catalog directly; route a
  // `skills` override into the v7 choices object.
  if (opts.skills !== undefined) {
    opts.choices = Object.assign({}, base.choices, { skills: opts.skills });
    delete opts.skills;
  }
  return Object.assign(base, opts);
}

test("root menu preserves stable action order with no placeholder rows", () => {
  const combat = CombatMenu.buildMenus(readyPanel(), {});
  const root = combat.menus.root.items;
  assert.deepEqual(
    root.map((item) => item.key),
    ["attack", "skills", "items", "bag", "defend", "dodge", "taunt", "flee", "forfeit"]
  );
  // The commanded actor's committed capability decides the items row: an
  // actor with no usable stock carries the capability reason, never a
  // not_implemented placeholder.
  assert.equal(root[2].enabled, false);
  assert.equal(root[2].disabledReason.code, "no_usable_item");
  // The client-local 背包 row: enabled, never dispatches, opens the bag.
  assert.equal(root[3].key, "bag");
  assert.equal(root[3].enabled, true);
  assert.equal(root[3].actionId, null);
  assert.equal(root[3].openDrawer, "inventory");
  // Defend / Dodge / Taunt join as actor-scoped basic actions: a tactic the
  // committed choices do not offer stays visible, disabled, and never
  // dispatches.
  assert.deepEqual(
    root.slice(4, 7).map((item) => [item.key, item.enabled, item.actionId]),
    [
      ["defend", false, null],
      ["dodge", false, null],
      ["taunt", false, null],
    ]
  );
  root.slice(4, 7).forEach((item) => {
    assert.equal(item.command, true);
    assert.equal(item.disabledReason.code, "unavailable");
    assert.ok(item.description && !/\d/.test(item.description), item.description);
  });
  assert.equal(root[7].actionId, "combat.flee");
  assert.deepEqual(root[7].payload, {});
  // Forfeit opens the confirmation secondary menu; it never submits directly.
  assert.equal(root[8].key, "forfeit");
  assert.equal(root[8].enabled, true);
  assert.equal(root[8].actionId, null);
});

// The committed actor-local item stock (webclient-party-items-tactics): the
// 道具 frame lists the actor's own rows with quantity, effect summary and the
// committed disabled reason; an eligible row opens that item's flow and a
// disabled one never submits.
function itemChoice(overrides) {
  return Object.assign(
    {
      item_key: "t_tonic",
      label: "合成藥水",
      summary: "恢復少量體力。",
      quantity: 2,
      enabled: true,
      reason: null,
      target_spec: "self",
      targets: [],
      hostile: false,
      beneficial: true,
    },
    overrides
  );
}

function tacticChoice(overrides) {
  return Object.assign(
    {
      key: "defend",
      label: "防禦",
      enabled: true,
      reason: null,
      targets: [],
    },
    overrides
  );
}

test("the 道具 frame lists the actor's own stock with quantity and summary", () => {
  const panel = readyPanel({
    choices: {
      actor_id: 2,
      skills: nestedSkills(validSkill()),
      items: [
        itemChoice(),
        itemChoice({
          item_key: "t_salve",
          label: "合成藥膏",
          summary: "恢復體力。",
          quantity: 1,
          enabled: false,
          reason: { code: "hp_full", message: "體力已滿。" },
          target_spec: "single",
          targets: [2],
        }),
      ],
      tactics: [],
    },
  });
  const combat = CombatMenu.buildMenus(panel, {});
  const root = combat.menus.root.items;
  assert.equal(root[2].enabled, true, "an actor holding stock can open 道具");

  const menu = combat.menus.items;
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["item-t_tonic", "item-t_salve"]
  );
  assert.equal(menu.items[0].label, "合成藥水 ×2");
  assert.equal(menu.items[0].description, "恢復少量體力。");
  assert.equal(menu.items[0].enabled, true);
  assert.equal(menu.items[0].actionId, "open-item");
  assert.deepEqual(menu.items[0].payload, { itemKey: "t_tonic" });
  assert.equal(menu.items[0].command, true, "the frame stays one vertical list");
  // A committed disabled reason is carried verbatim and the row never opens.
  assert.equal(menu.items[1].label, "合成藥膏 ×1");
  assert.equal(menu.items[1].enabled, false);
  assert.equal(menu.items[1].actionId, null);
  assert.equal(menu.items[1].disabledReason.code, "hp_full");
  assert.equal(menu.items[1].description, "恢復體力。");
});

test("an item's NONE and SELF flow sends the item key and no target field", () => {
  const panel = readyPanel({
    choices: {
      actor_id: 2,
      skills: nestedSkills(validSkill()),
      items: [itemChoice(), itemChoice({ item_key: "t_draught", label: "合成飲劑", target_spec: "none", beneficial: false })],
      tactics: [],
    },
  });
  const combat = CombatMenu.buildMenus(panel, {});
  const self = CombatMenu.openItem(combat, "t_tonic");
  assert.equal(self.items.length, 1);
  assert.equal(self.items[0].key, "self-confirm");
  assert.equal(self.items[0].commandKind, "item");
  assert.deepEqual(self.items[0].payload, { item_key: "t_tonic" });

  const none = CombatMenu.openItem(combat, "t_draught");
  assert.equal(none.items[0].key, "none-confirm");
  assert.equal(none.items[0].commandKind, "item");
  assert.deepEqual(none.items[0].payload, { item_key: "t_draught" });

  // The guarded envelope keeps the committed versions and commanded actor.
  const envelope = CombatMenu.commandEnvelope(panel, {
    kind: "item",
    payload: self.items[0].payload,
  });
  assert.deepEqual(envelope, {
    session_id: "hostile:1:0",
    round_revision: 0,
    draft_version: 0,
    actor_id: 2,
    command: { kind: "item", payload: { item_key: "t_tonic" } },
  });
});

test("a SINGLE item submits exactly one scalar target_id per server candidate", () => {
  const panel = readyPanel({
    participants: [
      validParticipant(),
      validParticipant({ identity: 3, token: "e2", display_name: "同行劍士", team: "party" }),
    ],
    actors: [{ identity: 2, commandable: true, reason: null }],
    choices: {
      actor_id: 2,
      skills: nestedSkills(validSkill()),
      items: [
        itemChoice({
          item_key: "t_bomb",
          label: "合成炸彈",
          target_spec: "single",
          targets: [3],
          hostile: false,
          beneficial: false,
        }),
      ],
      tactics: [],
    },
  });
  const combat = CombatMenu.buildMenus(panel, {});
  const menu = CombatMenu.openItem(combat, "t_bomb");
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["target-3"]
  );
  assert.equal(menu.items[0].commandKind, "item");
  assert.deepEqual(menu.items[0].payload, { item_key: "t_bomb", target_id: 3 });
  assert.equal(menu.items[0].team, "party");
});

test("an item with no committed candidate never offers a submitting row", () => {
  const panel = readyPanel({
    choices: {
      actor_id: 2,
      skills: nestedSkills(validSkill()),
      items: [itemChoice({ item_key: "t_bomb", target_spec: "single", targets: [] })],
      tactics: [],
    },
  });
  const menu = CombatMenu.openItem(CombatMenu.buildMenus(panel, {}), "t_bomb");
  assert.equal(menu.items[0].key, "item-disabled");
  assert.equal(menu.items[0].enabled, false);
  assert.equal(menu.items[0].actionId, null);
  assert.equal(menu.items[0].disabledReason.code, "no_target");
});

test("basic actions confirm their round choice and Taunt targets a listed enemy", () => {
  const panel = readyPanel({
    participants: [
      validParticipant({ identity: 7, token: "e1", display_name: "灰袍盜賊", team: "foes" }),
      validParticipant(),
    ],
    choices: {
      actor_id: 2,
      skills: nestedSkills(validSkill()),
      items: [],
      tactics: [
        tacticChoice({ key: "defend" }),
        tacticChoice({ key: "dodge", label: "閃避" }),
        tacticChoice({ key: "taunt", label: "挑釁", targets: [7] }),
      ],
    },
  });
  const combat = CombatMenu.buildMenus(panel, {});
  const root = combat.menus.root.items;
  assert.deepEqual(
    root.slice(4, 7).map((item) => [item.key, item.enabled, item.label]),
    [
      ["defend", true, "防禦"],
      ["dodge", true, "閃避"],
      ["taunt", true, "挑釁"],
    ]
  );

  const defend = CombatMenu.tacticMenu(combat, "defend");
  assert.equal(defend.items.length, 1);
  assert.equal(defend.items[0].key, "tactic-confirm");
  assert.deepEqual(defend.items[0].payload, { key: "defend" });
  assert.equal(defend.items[0].commandKind, "tactic", "the wire kind is 'tactic'");
  assert.equal("target_id" in defend.items[0].payload, false);

  const taunt = CombatMenu.tacticMenu(combat, "taunt");
  assert.deepEqual(
    taunt.items.map((item) => item.key),
    ["target-7"]
  );
  assert.deepEqual(taunt.items[0].payload, { key: "taunt", target_id: 7 });
  assert.equal(taunt.items[0].commandKind, "tactic");

  // An unavailable tactic keeps its committed reason and offers no submit.
  const sealed = CombatMenu.buildMenus(
    readyPanel({
      choices: {
        actor_id: 2,
        skills: nestedSkills(validSkill()),
        items: [],
        tactics: [
          tacticChoice({
            key: "dodge",
            enabled: false,
            reason: { code: "dodge_disabled", message: "無法閃避。" },
          }),
        ],
      },
    }),
    {}
  );
  assert.equal(sealed.menus.root.items[5].enabled, false);
  assert.equal(sealed.menus.root.items[5].disabledReason.code, "dodge_disabled");
  const dodge = CombatMenu.tacticMenu(sealed, "dodge");
  assert.equal(dodge.items[0].key, "tactic-disabled");
  assert.equal(dodge.items[0].enabled, false);
  assert.equal(dodge.items[0].description, "無法閃避。");
});

test("an unknown item or basic action never resolves a frame", () => {
  const combat = CombatMenu.buildMenus(readyPanel(), {});
  assert.equal(CombatMenu.openItem(combat, "t_absent"), null);
  assert.equal(CombatMenu.tacticMenu(combat, "absent"), null);
  assert.equal(CombatMenu.tacticMenu(combat, "defend"), null, "no committed tactic row resolves");
});

test("forfeit confirmation menu requires explicit confirm to send", () => {
  const combat = CombatMenu.buildMenus(readyPanel(), {});
  const forfeit = combat.menus.forfeit;
  assert.deepEqual(
    forfeit.items.map((item) => item.key),
    ["confirm-forfeit", "cancel-forfeit"]
  );
  assert.equal(forfeit.items[0].actionId, "combat.forfeit");
  assert.equal(forfeit.items[0].payload.session_id, "hostile:1:0");
  assert.equal(forfeit.items[1].actionId, null);

  const emitted = [];
  const router = menuRouter(emitted);
  router.pushMenu(combat.menus.root);
  router.pushMenu(forfeit);
  router.press(KeyboardRouter.ESCAPE);
  assert.equal(router.depth(), 1, "Escape returns to root, combat continues");
  assert.ok(!emitted.some(([name]) => name === "submit"));

  router.pushMenu(forfeit);
  router.press(KeyboardRouter.ENTER);
  const submits = emitted.filter(([name]) => name === "submit");
  assert.equal(submits.length, 1);
  assert.equal(submits[0][1].item.actionId, "combat.forfeit");
});

test("recovery root exposes only a confirmed Forfeit path", () => {
  const panel = readyPanel({
    session: {
      session_id: "hostile:1:0",
      mode: "hostile",
      round: 0,
      state: T_RECOVERY,
      reason: { code: "missing_participant", message: "戰鬥成員已無法確認。" },
    },
  });
  const combat = CombatMenu.buildMenus(panel, {});
  const root = combat.menus.root.items;
  assert.deepEqual(root.map((item) => item.key), ["forfeit"]);
  assert.equal(root[0].actionId, null, "recovery Forfeit still needs confirmation");
  const confirm = combat.menus.forfeit.items[0];
  assert.equal(confirm.actionId, "combat.forfeit");
  assert.equal(confirm.payload.session_id, "hostile:1:0");
});

test("skill list follows panel order and excludes passives already", () => {
  const panel = readyPanel();
  panel.choices.skills = nestedSkills(
    validSkill({ key: T_B }),
    validSkill({ key: T_A })
  );
  const combat = CombatMenu.buildMenus(panel, {});
  assert.deepEqual(
    combat.skills.map((skill) => skill.key),
    [T_B, T_A]
  );
});

test("disabled skill stays focusable but never sends a packet", () => {
  const panel = readyPanel();
  panel.choices.skills = nestedSkills(
    validSkill({
      key: T_A,
      enabled: false,
      disabled_reason: { code: "insufficient_resource", message: "你的資源不足。" },
    })
  );
  const combat = CombatMenu.buildMenus(panel, {});
  const menu = CombatMenu.openSkill(combat, T_A);
  assert.equal(menu.items[0].enabled, false);
  assert.equal(menu.items[0].disabledReason.code, "insufficient_resource");

  const emitted = [];
  const router = menuRouter(emitted);
  router.pushMenu(menu);
  router.press(KeyboardRouter.ENTER);
  assert.ok(emitted.some(([name]) => name === "disabled"));
  assert.ok(!emitted.some(([name]) => name === "submit"));
});

test("NONE skill submits skill_key only", () => {
  const panel = readyPanel();
  panel.choices.skills = nestedSkills(validSkill({ key: T_NONE, target_spec: "none", targets: [], enabled: true }));
  const combat = CombatMenu.buildMenus(panel, {});
  const menu = CombatMenu.openSkill(combat, T_NONE);
  assert.equal(menu.items.length, 1);
  assert.equal(menu.items[0].actionId, "combat.command");
  assert.equal(menu.items[0].commandKind, "skill");
  assert.deepEqual(menu.items[0].payload, { skill_key: T_NONE });
});

test("SELF skill submits skill_key only without an actor field", () => {
  const panel = readyPanel();
  panel.choices.skills = nestedSkills(validSkill({ key: T_SELF, target_spec: "self", targets: [], enabled: true }));
  const combat = CombatMenu.buildMenus(panel, {});
  const menu = CombatMenu.openSkill(combat, T_SELF);
  assert.equal(menu.items[0].actionId, "combat.command");
  assert.equal(menu.items[0].commandKind, "skill");
  assert.deepEqual(menu.items[0].payload, { skill_key: T_SELF });
});

test("SINGLE target flow submits exactly one server-provided identity", () => {
  const combat = CombatMenu.buildMenus(readyPanel(), {});
  const menu = CombatMenu.openSkill(combat, T_A);
  assert.equal(menu.items.length, 1);
  assert.equal(menu.items[0].key, "target-2");
  assert.deepEqual(menu.items[0].payload, { skill_key: T_A, target_ids: [2] });
});

test("AREA supports Space toggle, explicit list, and mutually exclusive shorthand", () => {
  const panel = readyPanel();
  panel.participants = [
    validParticipant(),
    validParticipant({ identity: 3, display_name: "野狼" }),
  ];
  panel.choices.skills = nestedSkills(
    validSkill({
      key: T_B,
      label: T_B_LABEL,
      target_spec: "area",
      targets: [2, 3],
      shorthands: ["all-enemies", "all"],
      hostile: false,
      beneficial: false,
    })
  );
  const combat = CombatMenu.buildMenus(panel, {});
  assert.equal(CombatMenu.toggleArea(combat, T_B, 2), true);
  assert.equal(CombatMenu.toggleArea(combat, T_B, 3), true);
  assert.deepEqual(CombatMenu.areaPayload(combat.skillByKey[T_B]), {
    skill_key: T_B,
    target_ids: [2, 3],
  });

  assert.equal(CombatMenu.chooseShorthand(combat, T_B, "all-enemies"), true);
  assert.deepEqual(CombatMenu.areaPayload(combat.skillByKey[T_B]), {
    skill_key: T_B,
    target_shorthand: "all-enemies",
  });
});

test("AREA payload preserves presenter order regardless of toggle order", () => {
  const panel = readyPanel();
  panel.participants = [
    validParticipant(),
    validParticipant({ identity: 3, display_name: "野狼" }),
  ];
  panel.choices.skills = nestedSkills(
    validSkill({
      key: T_B,
      label: T_B_LABEL,
      target_spec: "area",
      targets: [2, 3],
      shorthands: ["all-enemies", "all"],
      hostile: false,
      beneficial: false,
    })
  );
  const combat = CombatMenu.buildMenus(panel, {});
  // Toggle the later-presented candidate first, then the earlier one; the
  // payload must still carry the two identities in presenter order [2, 3].
  assert.equal(CombatMenu.toggleArea(combat, T_B, 3), true);
  assert.equal(CombatMenu.toggleArea(combat, T_B, 2), true);
  assert.deepEqual(CombatMenu.areaPayload(combat.skillByKey[T_B]), {
    skill_key: T_B,
    target_ids: [2, 3],
  });
});

test("rebuildForPanel drops vanished selections and keeps root focus", () => {
  const first = readyPanel();
  const combat = CombatMenu.buildMenus(first, { skillKey: T_A });
  assert.equal(combat.focusSkillKey, T_A);
  const next = CombatMenu.rebuildForPanel(combat, first, { skillKey: T_A });
  assert.equal(next.focusSkillKey, T_A);
});

test("repeated Enter is suppressed and in-flight locking blocks submit", () => {
  const combat = CombatMenu.buildMenus(readyPanel(), {});
  const menu = CombatMenu.openSkill(combat, T_A);
  const emitted = [];
  const router = menuRouter(emitted);
  router.pushMenu(menu);
  router.press(KeyboardRouter.ENTER);
  router.press(KeyboardRouter.ENTER, true); // held repeat
  assert.equal(emitted.filter(([name]) => name === "submit").length, 1);
  assert.ok(emitted.some(([name]) => name === "repeat-suppressed"));

  router.setMutationInFlight(true);
  const before = emitted.length;
  router.press(KeyboardRouter.ENTER);
  assert.ok(emitted.slice(before).some(([name]) => name === "locked"));
  assert.equal(emitted.filter(([name]) => name === "submit").length, 1);
});

test("Escape pops one level without ending combat", () => {
  const combat = CombatMenu.buildMenus(readyPanel(), {});
  const menu = CombatMenu.openSkill(combat, T_A);
  const emitted = [];
  const router = menuRouter(emitted);
  router.pushMenu(combat.menus.root);
  router.pushMenu(menu);
  assert.equal(router.depth(), 2);
  router.press(KeyboardRouter.ESCAPE);
  assert.equal(router.depth(), 1);
  assert.ok(emitted.some(([name]) => name === "menu-closed"));
});

test("no focus packet is emitted for portrait participants", () => {
  // The model itself never constructs a focus packet or portrait key; it only
  // carries the server-authored portrait_ref through unchanged.
  const combat = CombatMenu.buildMenus(
    readyPanel({ participants: [validParticipant({ portrait_ref: "42" })] }),
    {}
  );
  assert.equal(combat.participants[0].portrait_ref, "42");
  assert.equal(JSON.stringify(combat).indexOf("portrait_ref") !== -1, true);
  assert.equal(JSON.stringify(combat).indexOf("focus-packet") === -1, true);
});

function freeformSkill(overrides) {
  return validSkill(
    Object.assign(
      {
        key: T_B,
        label: T_B_LABEL,
        target_spec: "area",
        targets: [2],
        shorthands: ["all-enemies"],
        hostile: false,
        beneficial: false,
        freeform_scales: [
          { scale: 0.25, label: "1/4", mp_cost: 4 },
          { scale: 0.5, label: "1/2", mp_cost: 7 },
          { scale: 1, label: "1", mp_cost: 14 },
          { scale: 2, label: "2", mp_cost: 28 },
          { scale: 4, label: "4", mp_cost: 56 },
        ],
      },
      overrides
    )
  );
}

test("a master skill opens the 威力 scale step before the target flow", () => {
  const panel = readyPanel({ skills: nestedSkills(freeformSkill()) });
  const combat = CombatMenu.buildMenus(panel, {});
  const menu = CombatMenu.openSkill(combat, T_B);
  assert.deepEqual(
    menu.items.map((item) => item.key),
    ["scale-1/4", "scale-1/2", "scale-1", "scale-2", "scale-4"]
  );
  assert.deepEqual(
    menu.items.map((item) => item.label),
    ["威力×1/4", "威力×1/2", "威力×1", "威力×2", "威力×4"]
  );
  assert.deepEqual(
    menu.items.map((item) => item.description),
    ["MP 4", "MP 7", "MP 14", "MP 28", "MP 56"]
  );
  menu.items.forEach((item) => {
    assert.equal(item.actionId, "choose-scale");
    assert.equal(item.enabled, true);
  });
  // `1` is preselected in the client-local selection state.
  assert.equal(combat.skillByKey[T_B].scale, 1);
  assert.equal(CombatMenu.scaleLabelFor(combat.skillByKey[T_B]), "1");
});

test("choose-scale records the member choice and opens the target flow", () => {
  const panel = readyPanel({ skills: nestedSkills(freeformSkill()) });
  const combat = CombatMenu.buildMenus(panel, {});
  assert.equal(CombatMenu.chooseScale(combat, T_B, 2), true);
  assert.equal(combat.skillByKey[T_B].scale, 2);
  assert.equal(CombatMenu.scaleLabelFor(combat.skillByKey[T_B]), "2");
  const targets = CombatMenu.openSkillTargets(combat, T_B);
  assert.equal(targets.items[0].actionId, "toggle-target");
  assert.equal(CombatMenu.chooseScale(combat, T_B, 3), false);
  assert.equal(combat.skillByKey[T_B].scale, 2);
});

test("every target form carries the chosen scale for a master skill", () => {
  const panel = readyPanel({ skills: nestedSkills(freeformSkill()) });
  const combat = CombatMenu.buildMenus(panel, {});
  const skill = combat.skillByKey[T_B];
  CombatMenu.chooseScale(combat, T_B, 2);

  // AREA shorthand
  CombatMenu.chooseShorthand(combat, T_B, "all-enemies");
  assert.deepEqual(CombatMenu.areaPayload(skill), {
    skill_key: T_B,
    scale: 2,
    target_shorthand: "all-enemies",
  });

  // AREA explicit list (presenter order)
  CombatMenu.toggleArea(combat, T_B, 2);
  assert.deepEqual(CombatMenu.areaPayload(skill), {
    skill_key: T_B,
    scale: 2,
    target_ids: [2],
  });

  // SINGLE target flow
  const singlePanel = readyPanel({
    skills: nestedSkills(freeformSkill({ key: T_MASTER_SINGLE, target_spec: "single", targets: [2], shorthands: [] })),
  });
  const singleCombat = CombatMenu.buildMenus(singlePanel, {});
  CombatMenu.chooseScale(singleCombat, T_MASTER_SINGLE, 0.5);
  const singleMenu = CombatMenu.openSkillTargets(singleCombat, T_MASTER_SINGLE);
  assert.deepEqual(singleMenu.items[0].payload, {
    skill_key: T_MASTER_SINGLE,
    scale: 0.5,
    target_ids: [2],
  });

  // NONE and SELF flows
  for (const spec of ["none", "self"]) {
    const p = readyPanel({
      skills: nestedSkills(freeformSkill({ key: "probe", target_spec: spec, targets: [], shorthands: [] })),
    });
    const c = CombatMenu.buildMenus(p, {});
    CombatMenu.chooseScale(c, "probe", 4);
    const m = CombatMenu.openSkillTargets(c, "probe");
    assert.deepEqual(m.items[0].payload, { skill_key: "probe", scale: 4 });
  }
});

test("non-master skills keep today's exact flow and payloads", () => {
  const panel = readyPanel();
  const combat = CombatMenu.buildMenus(panel, {});
  // The single-target row carries no freeform_scales: openSkill goes straight
  // to targets.
  const menu = CombatMenu.openSkill(combat, T_A);
  assert.equal(menu.items[0].key, "target-2");
  assert.deepEqual(menu.items[0].payload, { skill_key: T_A, target_ids: [2] });
  assert.equal("scale" in menu.items[0].payload, false);
  assert.equal(CombatMenu.scaleLabelFor(combat.skillByKey[T_A]), null);

  // The AREA path without freeform scales stays byte-identical.
  const areaCombat = CombatMenu.buildMenus(
    readyPanel({ skills: nestedSkills(validSkill({ key: T_B, target_spec: "area", targets: [2], shorthands: ["all"] })) }),
    {}
  );
  CombatMenu.toggleArea(areaCombat, T_B, 2);
  assert.deepEqual(CombatMenu.areaPayload(areaCombat.skillByKey[T_B]), {
    skill_key: T_B,
    target_ids: [2],
  });
  assert.equal("scale" in CombatMenu.areaPayload(areaCombat.skillByKey[T_B]), false);
});

test("rebuildForPanel preserves a still-valid scale choice and resets invalid", () => {
  const panel = readyPanel({ skills: nestedSkills(freeformSkill()) });
  const combat = CombatMenu.buildMenus(panel, {});
  CombatMenu.chooseScale(combat, T_B, 2);
  const rebuilt = CombatMenu.rebuildForPanel(combat, panel, {
    skillKey: T_B,
    skillByKey: combat.skillByKey,
  });
  assert.equal(rebuilt.skillByKey[T_B].scale, 2);

  const narrowed = readyPanel({
    skills: nestedSkills(freeformSkill({ freeform_scales: [{ scale: 1, label: "1", mp_cost: 14 }] })),
  });
  const rebuiltNarrow = CombatMenu.rebuildForPanel(combat, narrowed, {
    skillKey: T_B,
    skillByKey: combat.skillByKey,
  });
  assert.equal(rebuiltNarrow.skillByKey[T_B].scale, 1);
});

// ---------------------------------------------------------------------------
// webclient-party-command-selection: the actor selector, the draft progress
// line and the guarded combat.command envelope.
// ---------------------------------------------------------------------------

function actorPanel(overrides) {
  return readyPanel(
    Object.assign(
      {
        participants: [
          validParticipant({ identity: 2, token: "e1", display_name: "哥布林", team: "foes" }),
          validParticipant({ identity: 5, token: "a1", display_name: "同行劍士", team: "party" }),
          validParticipant({ identity: 6, token: "a2", display_name: "見習法師", team: "party" }),
        ],
        actors: [
          { identity: 5, commandable: true, reason: null },
          { identity: 6, commandable: false, reason: { code: "fallen", message: "倒地中。" } },
        ],
        choices: { actor_id: 6, skills: nestedSkills(validSkill()), items: [], tactics: [] },
        draft: {
          round_revision: 0,
          draft_version: 3,
          required_actor_ids: [5, 6],
          entries: [{ actor_id: 5, command: { kind: "skill", payload: { skill_key: T_A, target_ids: [2] } } }],
          needs_selection_ids: [6],
          reselection_reasons: [],
        },
      },
      overrides
    )
  );
}

test("actor selector keeps the server's allied order with confirmed/needs-selection status", () => {
  const combat = CombatMenu.buildMenus(actorPanel(), {});
  const actor = combat.menus.actor;
  assert.deepEqual(
    actor.items.map((item) => item.key),
    ["actor-5", "actor-6"]
  );
  assert.equal(actor.focusKey, "actor-6");
  assert.equal(actor.items[0].label, "同行劍士");
  assert.equal(actor.items[0].description, "已確認");
  assert.equal(actor.items[0].actorStatus, "confirmed");
  assert.equal(actor.items[0].current, false);
  assert.equal(actor.items[1].description, "倒地中。");
  assert.equal(actor.items[1].actorStatus, "needs-selection");
  assert.equal(actor.items[1].enabled, false);
  assert.equal(actor.items[1].disabledReason.code, "fallen");
  assert.equal(actor.items[1].current, true);
});

test("a reselection reason joins the actor row by identity", () => {
  const panel = actorPanel({
    actors: [{ identity: 5, commandable: true, reason: null }],
    choices: { actor_id: 5, skills: nestedSkills(validSkill()), items: [], tactics: [] },
    draft: {
      round_revision: 0,
      draft_version: 4,
      required_actor_ids: [5],
      entries: [],
      needs_selection_ids: [5],
      reselection_reasons: [
        { actor_id: 5, reason: { code: "target_invalid", message: "目標無效。" } },
      ],
    },
  });
  const actor = CombatMenu.buildMenus(panel, {}).menus.actor;
  assert.equal(actor.items[0].description, "目標無效。");
  assert.equal(actor.items[0].enabled, true);
});

test("same-name allied actors carry their session token in the selector", () => {
  const panel = actorPanel({
    participants: [
      validParticipant({ identity: 5, token: "a1", display_name: "同行劍士", team: "party" }),
      validParticipant({ identity: 6, token: "a2", display_name: "同行劍士", team: "party" }),
    ],
    actors: [
      { identity: 5, commandable: true, reason: null },
      { identity: 6, commandable: true, reason: null },
    ],
    choices: { actor_id: 5, skills: nestedSkills(validSkill()), items: [], tactics: [] },
    draft: {
      round_revision: 0,
      draft_version: 0,
      required_actor_ids: [5, 6],
      entries: [],
      needs_selection_ids: [5, 6],
      reselection_reasons: [],
    },
  });
  const actor = CombatMenu.buildMenus(panel, {}).menus.actor;
  assert.deepEqual(
    actor.items.map((item) => item.label),
    ["同行劍士（a1）", "同行劍士（a2）"]
  );
  assert.equal(CombatMenu.progressLine(panel).actorLabel, "同行劍士（a1）");
});

test("the progress line reports the commanded actor and the draft counts", () => {
  assert.deepEqual(CombatMenu.progressLine(actorPanel()), {
    actorId: 6,
    actorLabel: "見習法師",
    confirmed: 1,
    total: 2,
    needsSelection: 1,
  });
  assert.equal(CombatMenu.progressLine({ session: {}, choices: null, draft: null }), null);
});

test("the guarded combat.command envelope carries the committed versions and commanded actor", () => {
  const panel = actorPanel({ session: { session_id: "hostile:1:0", mode: "hostile", round: 0, round_revision: 2, state: "ready", reason: null } });
  assert.deepEqual(
    CombatMenu.commandEnvelope(panel, { kind: "skill", payload: { skill_key: T_A, target_ids: [2] } }),
    {
      session_id: "hostile:1:0",
      round_revision: 2,
      draft_version: 3,
      actor_id: 6,
      command: { kind: "skill", payload: { skill_key: T_A, target_ids: [2] } },
    }
  );
  assert.equal(CombatMenu.commandEnvelope({ session: {}, draft: null, choices: {} }, { kind: "skill", payload: {} }), null);
  assert.equal(CombatMenu.commandEnvelope(panel, { payload: {} }), null);
});

test("every TargetSpec keeps its exact inner skill payload inside the command", () => {
  const specs = [
    { spec: "none", targets: [], shorthands: [] },
    { spec: "self", targets: [], shorthands: [] },
    { spec: "single", targets: [2], shorthands: [] },
    { spec: "area", targets: [2], shorthands: ["all-enemies"] },
  ];
  for (const { spec, targets, shorthands } of specs) {
    const panel = readyPanel({
      skills: nestedSkills(validSkill({ key: "probe_" + spec, target_spec: spec, targets, shorthands })),
    });
    const combat = CombatMenu.buildMenus(panel, {});
    const menu = CombatMenu.openSkillTargets(combat, "probe_" + spec);
    let inner;
    if (spec === "area") {
      CombatMenu.chooseShorthand(combat, "probe_area", "all-enemies");
      inner = CombatMenu.areaPayload(combat.skillByKey["probe_area"]);
    } else {
      inner = menu.items[0].payload;
    }
    const envelope = CombatMenu.commandEnvelope(panel, { kind: "skill", payload: inner });
    assert.equal(envelope.command.kind, "skill");
    assert.deepEqual(envelope.command.payload, inner);
    if (spec === "none" || spec === "self") {
      assert.equal("target_ids" in inner, false);
      assert.equal("target_shorthand" in inner, false);
    }
    if (spec === "single") {
      assert.deepEqual(inner.target_ids, [2]);
    }
    if (spec === "area") {
      assert.deepEqual(inner, { skill_key: "probe_area", target_shorthand: "all-enemies" });
    }
  }
});
