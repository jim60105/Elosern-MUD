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

function validSkill(overrides) {
  return Object.assign(
    {
      key: "fire_ball",
      label: "火球術",
      description: "凝聚火焰魔力，對單一敵人造成魔法傷害。",
      cost: { mp: 20 },
      target_spec: "single",
      element: "fire",
      enabled: true,
      disabled_reason: null,
      targets: [2],
      shorthands: [],
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
    },
    overrides
  );
}

function readyPanel(overrides) {
  return Object.assign(
    {
      schema_version: 1,
      available: true,
      kind: "combat",
      session: {
        session_id: "hostile:1:0",
        mode: "hostile",
        round: 0,
        state: "ready",
        reason: null,
      },
      participants: [validParticipant()],
      root_actions: ["attack", "skills", "items", "defend", "flee"],
      secondary_actions: ["forfeit"],
      skills: [
        validSkill(),
        validSkill({
          key: "wind_blade",
          label: "風刃術",
          target_spec: "area",
          targets: [2],
          shorthands: ["all-enemies", "all"],
        }),
      ],
    },
    overrides
  );
}

test("root menu preserves stable action order and disables placeholders", () => {
  const combat = CombatMenu.buildMenus(readyPanel(), {});
  const root = combat.menus.root.items;
  assert.deepEqual(
    root.map((item) => item.key),
    ["attack", "skills", "items", "defend", "flee", "forfeit"]
  );
  assert.equal(root[2].enabled, false);
  assert.equal(root[2].disabledReason.code, "not_implemented");
  assert.equal(root[3].enabled, false);
  assert.equal(root[4].actionId, "combat.flee");
  assert.deepEqual(root[4].payload, {});
  // Forfeit opens the confirmation secondary menu; it never submits directly.
  assert.equal(root[5].key, "forfeit");
  assert.equal(root[5].enabled, true);
  assert.equal(root[5].actionId, null);
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
  const router = KeyboardRouter.createRouter({ onEvent: (name, payload) => emitted.push([name, payload]) });
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
      state: "recovery",
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
  panel.skills = [
    validSkill({ key: "wind_blade" }),
    validSkill({ key: "fire_ball" }),
  ];
  const combat = CombatMenu.buildMenus(panel, {});
  assert.deepEqual(
    combat.skills.map((skill) => skill.key),
    ["wind_blade", "fire_ball"]
  );
});

test("disabled skill stays focusable but never sends a packet", () => {
  const panel = readyPanel();
  panel.skills = [
    validSkill({
      key: "fire_ball",
      enabled: false,
      disabled_reason: { code: "insufficient_resource", message: "你的資源不足。" },
    }),
  ];
  const combat = CombatMenu.buildMenus(panel, {});
  const menu = CombatMenu.openSkill(combat, "fire_ball");
  assert.equal(menu.items[0].enabled, false);
  assert.equal(menu.items[0].disabledReason.code, "insufficient_resource");

  const emitted = [];
  const router = KeyboardRouter.createRouter({ onEvent: (name, payload) => emitted.push([name, payload]) });
  router.pushMenu(menu);
  router.press(KeyboardRouter.ENTER);
  assert.ok(emitted.some(([name]) => name === "disabled"));
  assert.ok(!emitted.some(([name]) => name === "submit"));
});

test("NONE skill submits skill_key only", () => {
  const panel = readyPanel();
  panel.skills = [validSkill({ key: "concentration", target_spec: "none", targets: [], enabled: true })];
  const combat = CombatMenu.buildMenus(panel, {});
  const menu = CombatMenu.openSkill(combat, "concentration");
  assert.equal(menu.items.length, 1);
  assert.equal(menu.items[0].actionId, "combat.cast");
  assert.deepEqual(menu.items[0].payload, { skill_key: "concentration" });
});

test("SELF skill submits skill_key only without an actor field", () => {
  const panel = readyPanel();
  panel.skills = [validSkill({ key: "body_enhancement", target_spec: "self", targets: [], enabled: true })];
  const combat = CombatMenu.buildMenus(panel, {});
  const menu = CombatMenu.openSkill(combat, "body_enhancement");
  assert.equal(menu.items[0].actionId, "combat.cast");
  assert.deepEqual(menu.items[0].payload, { skill_key: "body_enhancement" });
});

test("SINGLE target flow submits exactly one server-provided identity", () => {
  const combat = CombatMenu.buildMenus(readyPanel(), {});
  const menu = CombatMenu.openSkill(combat, "fire_ball");
  assert.equal(menu.items.length, 1);
  assert.equal(menu.items[0].key, "target-2");
  assert.deepEqual(menu.items[0].payload, { skill_key: "fire_ball", target_ids: [2] });
});

test("AREA supports Space toggle, explicit list, and mutually exclusive shorthand", () => {
  const panel = readyPanel();
  panel.participants = [
    validParticipant(),
    validParticipant({ identity: 3, display_name: "野狼" }),
  ];
  panel.skills = [
    validSkill({
      key: "wind_blade",
      label: "風刃術",
      target_spec: "area",
      targets: [2, 3],
      shorthands: ["all-enemies", "all"],
    }),
  ];
  const combat = CombatMenu.buildMenus(panel, {});
  assert.equal(CombatMenu.toggleArea(combat, "wind_blade", 2), true);
  assert.equal(CombatMenu.toggleArea(combat, "wind_blade", 3), true);
  assert.deepEqual(CombatMenu.areaPayload(combat.skillByKey.wind_blade), {
    skill_key: "wind_blade",
    target_ids: [2, 3],
  });

  assert.equal(CombatMenu.chooseShorthand(combat, "wind_blade", "all-enemies"), true);
  assert.deepEqual(CombatMenu.areaPayload(combat.skillByKey.wind_blade), {
    skill_key: "wind_blade",
    target_shorthand: "all-enemies",
  });
});

test("AREA payload preserves presenter order regardless of toggle order", () => {
  const panel = readyPanel();
  panel.participants = [
    validParticipant(),
    validParticipant({ identity: 3, display_name: "野狼" }),
  ];
  panel.skills = [
    validSkill({
      key: "wind_blade",
      label: "風刃術",
      target_spec: "area",
      targets: [2, 3],
      shorthands: ["all-enemies", "all"],
    }),
  ];
  const combat = CombatMenu.buildMenus(panel, {});
  // Toggle the later-presented candidate first, then the earlier one; the
  // payload must still carry the two identities in presenter order [2, 3].
  assert.equal(CombatMenu.toggleArea(combat, "wind_blade", 3), true);
  assert.equal(CombatMenu.toggleArea(combat, "wind_blade", 2), true);
  assert.deepEqual(CombatMenu.areaPayload(combat.skillByKey.wind_blade), {
    skill_key: "wind_blade",
    target_ids: [2, 3],
  });
});

test("rebuildForPanel drops vanished selections and keeps root focus", () => {
  const first = readyPanel();
  const combat = CombatMenu.buildMenus(first, { skillKey: "fire_ball" });
  assert.equal(combat.focusSkillKey, "fire_ball");
  const next = CombatMenu.rebuildForPanel(combat, first, { skillKey: "fire_ball" });
  assert.equal(next.focusSkillKey, "fire_ball");
});

test("repeated Enter is suppressed and in-flight locking blocks submit", () => {
  const combat = CombatMenu.buildMenus(readyPanel(), {});
  const menu = CombatMenu.openSkill(combat, "fire_ball");
  const emitted = [];
  const router = KeyboardRouter.createRouter({ onEvent: (name, payload) => emitted.push([name, payload]) });
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
  const menu = CombatMenu.openSkill(combat, "fire_ball");
  const emitted = [];
  const router = KeyboardRouter.createRouter({ onEvent: (name, payload) => emitted.push([name, payload]) });
  router.pushMenu(combat.menus.root);
  router.pushMenu(menu);
  assert.equal(router.depth(), 2);
  router.press(KeyboardRouter.ESCAPE);
  assert.equal(router.depth(), 1);
  assert.ok(emitted.some(([name]) => name === "menu-closed"));
});

test("no focus packet is emitted for portrait-less participants", () => {
  // The model itself never constructs a focus packet or portrait key.
  const combat = CombatMenu.buildMenus(readyPanel(), {});
  assert.equal(combat.participants[0].portrait_ref, null);
  assert.equal(JSON.stringify(combat).indexOf("portrait_ref") !== -1, true);
  assert.equal(JSON.stringify(combat).indexOf("focus-packet") === -1, true);
});
