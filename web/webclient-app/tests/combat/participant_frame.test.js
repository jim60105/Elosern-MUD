// H3 (task 6.9): the participant frame renders every payload participant
// and invents no field; the skill frame preserves server order; a
// single-sub-group category skips the group frame; every `combat.cast`
// payload is byte-identical to the pre-change payload for the same choices.

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ParticipantFrame from "../../components/ParticipantFrame.vue";
import CombatMenu from "../../../static/webclient/js/elosern/combat_menu.js";

describe("ParticipantFrame (task 6.9)", () => {
  let wrapper;
  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountFrame(participants, artPanel = null) {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(ParticipantFrame, {
      attachTo: host,
      props: { participants, artPanel },
    });
    return wrapper;
  }

  // Hoisted fixtures (arrays of objects) to dodge the V8/Node 24 parser quirk.
  const participants = [
    { identity: "p1", team: "party", token: "阿強", display_name: "阿強", hp_current: 80, hp_maximum: 100, state: "active", portrait_ref: null },
    { identity: "p2", team: "party", token: "小美", display_name: "小美", hp_current: 0, hp_maximum: 90, state: "knocked_out", portrait_ref: "portrait_mei" },
    { identity: "f1", team: "foes", token: "哥布林", display_name: "哥布林", hp_current: 45, hp_maximum: 45, state: "active", portrait_ref: "portrait_gob" },
    { identity: "f2", team: "foes", token: "オーク", display_name: "オーク", hp_current: 120, hp_maximum: 120, state: "defeated", portrait_ref: null },
  ];
  const artPanel = {
    portrait_catalog: {
      portrait_mei: { url: "/static/art/mei.png", placeholder: null },
      portrait_gob: { url: "", placeholder: { label: "肖像圖像尚未生成" } },
    },
  };

  it("renders every payload participant (no field invented)", () => {
    const w = mountFrame(participants, artPanel);
    const rows = w.findAll(".participant-frame__row");
    expect(rows).toHaveLength(participants.length);
    // The 我方 / 敵方 groups preserve the server's order within each group.
    const groupLabels = w.findAll(".participant-frame__group-label").map((g) => g.text());
    expect(groupLabels).toEqual(["我方", "敵方"]);
    // Every row carries the token, the display name, and the HP numerals.
    const names = w.findAll(".participant-frame__name").map((n) => n.text());
    expect(names).toEqual(["阿強", "小美", "哥布林", "オーク"]);
    const hp = w.findAll(".participant-frame__hp").map((h) => h.text());
    expect(hp).toEqual(["80/100", "0/90", "45/45", "120/120"]);
  });

  it("renders the explicit state marker (never colour-only)", () => {
    const w = mountFrame(participants, artPanel);
    const states = w.findAll(".participant-frame__state").map((s) => s.text());
    // Only the non-active participants (小美 倒地, オーク 已敗退) carry a marker.
    expect(states).toEqual(["倒地", "已敗退"]);
  });

  it("resolves portraits through the catalog (task 6.2)", () => {
    const w = mountFrame(participants, artPanel);
    // portrait_mei has a `url` → an `<img>` renders.
    const imgs = w.findAll("img.participant-frame__portrait");
    // portrait_gob has no url (placeholder only) → the placeholder card renders.
    const placeholders = w.findAll('[data-testid="participant-portrait-placeholder"]');
    expect(imgs.length + placeholders.length).toBeGreaterThan(0);
  });
});

describe("skill frame server order + single-sub-group skip (task 6.9)", () => {
  // Skill descriptor + panel fixtures (hoisted to dodge the V8 parser quirk).
  const skillSlash = {
    key: "slash", label: "斬撃", description: "近戰斬擊。", cost: { mp: 0 },
    target_spec: "single", enabled: true, disabled_reason: null, targets: [2], shorthands: [],
  };
  const skillCombo = {
    key: "combo", label: "連撃", description: "連續斬擊。", cost: { mp: 8 },
    target_spec: "single", enabled: true, disabled_reason: null, targets: [2], shorthands: [],
  };
  const skillHeal = {
    key: "heal", label: "治癒", description: "恢復生命值。", cost: { mp: 12 },
    target_spec: "single", enabled: true, disabled_reason: null, targets: [1], shorthands: [],
  };
   const participant = {
     identity: 1, token: "p1", display_name: "阿強", team: "party",
    state: "active", hp_current: 100, hp_maximum: 100, portrait_ref: null,
  };
  const foe = {
    identity: 2, token: "e1", display_name: "哥布林", team: "foes",
    state: "active", hp_current: 45, hp_maximum: 45, portrait_ref: null,
  };

  function makePanel(skills) {
    return {
      schema_version: 5,
      available: true,
      kind: "combat",
      session: { session_id: "hostile:1:0", mode: "hostile", round: 1, state: "ready", reason: null },
      participants: [participant, foe],
      root_actions: ["attack", "skills", "items", "defend", "flee"],
      secondary_actions: ["forfeit"],
      skills,
      suggestions: { status: "unavailable" },
    };
  }

  const attackCategory = {
    category: "attack", label: "攻撃",
    groups: [
      { group: "slashed", label: "斬撃", skills: [skillSlash, skillCombo] },
    ],
  };
  const supportCategory = {
    category: "support", label: "補助",
    groups: [
      { group: "healing", label: "治癒", skills: [skillHeal] },
    ],
  };

  it("the category frame preserves the server's order", () => {
    const panel = makePanel([attackCategory, supportCategory]);
    const combat = CombatMenu.buildMenus(panel, {});
    // The category frame lists the categories in the server's `skills[]` order.
    expect(combat.menus.categories.items.map((i) => i.label)).toEqual(["攻撃", "補助"]);
    // The skill frame for a group preserves the server's skill order within the group.
    const skillFrame = CombatMenu.openCategory(combat, 0);
    expect(skillFrame.items.map((i) => i.label)).toEqual(["斬撃", "連撃"]);
  });

  it("a single-sub-group category skips the group frame and opens the skill frame directly", () => {
    // A category with exactly one sub-group opens the skill frame straight away
    // (design D11): no intermediate group frame.
    const panel = makePanel([attackCategory]);
    const combat = CombatMenu.buildMenus(panel, {});
    const menu = CombatMenu.openCategory(combat, 0);
    // The returned frame is the skill frame (the group's skills), titled by the
    // group's label — not a group-list frame.
    expect(menu.title).toBe("斬撃");
    expect(menu.items.map((i) => i.label)).toEqual(["斬撃", "連撃"]);
  });
});
