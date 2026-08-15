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

// Wrap one or more flat skill descriptors into the v3 nested payload shape.
function nestedSkills(...skills) {
  return [
    {
      category: "elemental_magic",
      label: "元素魔法",
      groups: [
        {
          group: "fire",
          label: "火",
          skills: skills,
        },
      ],
    },
  ];
}

function readyPanel(overrides) {
  return Object.assign(
    {
      schema_version: 3,
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
      skills: nestedSkills(
        validSkill(),
        validSkill({
          key: "wind_blade",
          label: "風刃術",
          target_spec: "area",
          targets: [2],
          shorthands: ["all-enemies", "all"],
        })
      ),
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
  panel.skills = nestedSkills(
    validSkill({ key: "wind_blade" }),
    validSkill({ key: "fire_ball" })
  );
  const combat = CombatMenu.buildMenus(panel, {});
  assert.deepEqual(
    combat.skills.map((skill) => skill.key),
    ["wind_blade", "fire_ball"]
  );
});

test("disabled skill stays focusable but never sends a packet", () => {
  const panel = readyPanel();
  panel.skills = nestedSkills(
    validSkill({
      key: "fire_ball",
      enabled: false,
      disabled_reason: { code: "insufficient_resource", message: "你的資源不足。" },
    })
  );
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
  panel.skills = nestedSkills(validSkill({ key: "concentration", target_spec: "none", targets: [], enabled: true }));
  const combat = CombatMenu.buildMenus(panel, {});
  const menu = CombatMenu.openSkill(combat, "concentration");
  assert.equal(menu.items.length, 1);
  assert.equal(menu.items[0].actionId, "combat.cast");
  assert.deepEqual(menu.items[0].payload, { skill_key: "concentration" });
});

test("SELF skill submits skill_key only without an actor field", () => {
  const panel = readyPanel();
  panel.skills = nestedSkills(validSkill({ key: "body_enhancement", target_spec: "self", targets: [], enabled: true }));
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
  panel.skills = nestedSkills(
    validSkill({
      key: "wind_blade",
      label: "風刃術",
      target_spec: "area",
      targets: [2, 3],
      shorthands: ["all-enemies", "all"],
    })
  );
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
  panel.skills = nestedSkills(
    validSkill({
      key: "wind_blade",
      label: "風刃術",
      target_spec: "area",
      targets: [2, 3],
      shorthands: ["all-enemies", "all"],
    })
  );
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
        key: "wind_blade",
        label: "風刃術",
        target_spec: "area",
        targets: [2],
        shorthands: ["all-enemies"],
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
  const menu = CombatMenu.openSkill(combat, "wind_blade");
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
  assert.equal(combat.skillByKey.wind_blade.scale, 1);
  assert.equal(CombatMenu.scaleLabelFor(combat.skillByKey.wind_blade), "1");
});

test("choose-scale records the member choice and opens the target flow", () => {
  const panel = readyPanel({ skills: nestedSkills(freeformSkill()) });
  const combat = CombatMenu.buildMenus(panel, {});
  assert.equal(CombatMenu.chooseScale(combat, "wind_blade", 2), true);
  assert.equal(combat.skillByKey.wind_blade.scale, 2);
  assert.equal(CombatMenu.scaleLabelFor(combat.skillByKey.wind_blade), "2");
  const targets = CombatMenu.openSkillTargets(combat, "wind_blade");
  assert.equal(targets.items[0].actionId, "toggle-target");
  assert.equal(CombatMenu.chooseScale(combat, "wind_blade", 3), false);
  assert.equal(combat.skillByKey.wind_blade.scale, 2);
});

test("every target form carries the chosen scale for a master skill", () => {
  const panel = readyPanel({ skills: nestedSkills(freeformSkill()) });
  const combat = CombatMenu.buildMenus(panel, {});
  const skill = combat.skillByKey.wind_blade;
  CombatMenu.chooseScale(combat, "wind_blade", 2);

  // AREA shorthand
  CombatMenu.chooseShorthand(combat, "wind_blade", "all-enemies");
  assert.deepEqual(CombatMenu.areaPayload(skill), {
    skill_key: "wind_blade",
    scale: 2,
    target_shorthand: "all-enemies",
  });

  // AREA explicit list (presenter order)
  CombatMenu.toggleArea(combat, "wind_blade", 2);
  assert.deepEqual(CombatMenu.areaPayload(skill), {
    skill_key: "wind_blade",
    scale: 2,
    target_ids: [2],
  });

  // SINGLE target flow
  const singlePanel = readyPanel({
    skills: nestedSkills(freeformSkill({ key: "tornado_blade", target_spec: "single", targets: [2], shorthands: [] })),
  });
  const singleCombat = CombatMenu.buildMenus(singlePanel, {});
  CombatMenu.chooseScale(singleCombat, "tornado_blade", 0.5);
  const singleMenu = CombatMenu.openSkillTargets(singleCombat, "tornado_blade");
  assert.deepEqual(singleMenu.items[0].payload, {
    skill_key: "tornado_blade",
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
  // fire_ball carries no freeform_scales: openSkill goes straight to targets.
  const menu = CombatMenu.openSkill(combat, "fire_ball");
  assert.equal(menu.items[0].key, "target-2");
  assert.deepEqual(menu.items[0].payload, { skill_key: "fire_ball", target_ids: [2] });
  assert.equal("scale" in menu.items[0].payload, false);
  assert.equal(CombatMenu.scaleLabelFor(combat.skillByKey.fire_ball), null);

  // The AREA path without freeform scales stays byte-identical.
  const areaCombat = CombatMenu.buildMenus(
    readyPanel({ skills: nestedSkills(validSkill({ key: "wind_blade", target_spec: "area", targets: [2], shorthands: ["all"] })) }),
    {}
  );
  CombatMenu.toggleArea(areaCombat, "wind_blade", 2);
  assert.deepEqual(CombatMenu.areaPayload(areaCombat.skillByKey.wind_blade), {
    skill_key: "wind_blade",
    target_ids: [2],
  });
  assert.equal("scale" in CombatMenu.areaPayload(areaCombat.skillByKey.wind_blade), false);
});

test("rebuildForPanel preserves a still-valid scale choice and resets invalid", () => {
  const panel = readyPanel({ skills: nestedSkills(freeformSkill()) });
  const combat = CombatMenu.buildMenus(panel, {});
  CombatMenu.chooseScale(combat, "wind_blade", 2);
  const rebuilt = CombatMenu.rebuildForPanel(combat, panel, {
    skillKey: "wind_blade",
    skillByKey: combat.skillByKey,
  });
  assert.equal(rebuilt.skillByKey.wind_blade.scale, 2);

  const narrowed = readyPanel({
    skills: nestedSkills(freeformSkill({ freeform_scales: [{ scale: 1, label: "1", mp_cost: 14 }] })),
  });
  const rebuiltNarrow = CombatMenu.rebuildForPanel(combat, narrowed, {
    skillKey: "wind_blade",
    skillByKey: combat.skillByKey,
  });
  assert.equal(rebuiltNarrow.skillByKey.wind_blade.scale, 1);
});
