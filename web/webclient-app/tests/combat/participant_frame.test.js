// H3 (task 6.9): the participant frame renders every payload participant
// and invents no field; the skill frame preserves server order; a
// single-sub-group category skips the group frame; every `combat.cast`
// payload is byte-identical to the pre-change payload for the same choices.

import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ParticipantFrame from "../../components/ParticipantFrame.vue";
import FoeLineup from "../../components/FoeLineup.vue";
import VitalsTrack from "../../components/VitalsTrack.vue";
import { h } from "vue";
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
      portrait_mei: { url: "/static/art/mei.png", placeholder: null, face_rect: { x: 0.25, y: 0.06, w: 0.5, h: 0.5 } },
      portrait_gob: { url: "", placeholder: { label: "肖像圖像尚未生成" }, face_rect: null },
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


  it("shows a playing round's displayed hit points for the keys it names", () => {
    // webclient-combat-beat-queue D7: a row whose `portrait_ref` is a key of
    // the displayed map states that value instead of its committed
    // `hp_current`; every other row keeps the committed value.
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(ParticipantFrame, {
      attachTo: host,
      props: {
        participants,
        artPanel,
        displayHp: { portrait_gob: 18, portrait_mei: 27 },
      },
    });
    const hp = wrapper.findAll(".participant-frame__hp").map((h) => h.text());
    expect(hp).toEqual(["80/100", "27/90", "18/45", "120/120"]);
  });

  it("restores every committed value when the round stops displaying one", async () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(ParticipantFrame, {
      attachTo: host,
      props: { participants, artPanel, displayHp: { portrait_gob: 18 } },
    });
    expect(wrapper.findAll(".participant-frame__hp").map((h) => h.text())).toEqual([
      "80/100",
      "0/90",
      "18/45",
      "120/120",
    ]);
    await wrapper.setProps({ displayHp: null });
    expect(wrapper.findAll(".participant-frame__hp").map((h) => h.text())).toEqual([
      "80/100",
      "0/90",
      "45/45",
      "120/120",
    ]);
  });

  it("renders the explicit state marker (never colour-only)", () => {
    const w = mountFrame(participants, artPanel);
    const states = w.findAll(".participant-frame__state").map((s) => s.text());
    // Only the non-active participants (小美 倒地, オーク 已敗退) carry a marker.
    expect(states).toEqual(["倒地", "已敗退"]);
  });

  it("keeps placeholder identity compact and its truthful state accessible", async () => {
    const w = mountFrame(participants, artPanel);
    expect(w.get("img.participant-frame__portrait").attributes("src")).toBe("/static/art/mei.png");
    const placeholder = w.get('[data-testid="participant-portrait-placeholder"]');
    expect(placeholder.text()).toBe("哥");
    expect(placeholder.attributes("aria-label")).toBe("哥布林，肖像圖像尚未生成");
    expect(w.findAll(".participant-frame__token")[2].text()).toBe("哥布林");
    await w.setProps({ artPanel: { available: false, portrait_catalog: artPanel.portrait_catalog } });
    expect(w.findAll("img, [data-testid='participant-portrait-placeholder']")).toHaveLength(0);
    expect(w.findAll(".participant-frame__hp").map((row) => row.text())).toEqual(["80/100", "0/90", "45/45", "120/120"]);
  });

  it("replaces a failed catalog image with its localized accessible state", async () => {
    const w = mountFrame(participants, artPanel);
    await w.get('img[src="/static/art/mei.png"]').trigger("error");
    const placeholder = w.findAll('[data-testid="participant-portrait-placeholder"]')[0];
    expect(placeholder.text()).toBe("小");
    expect(placeholder.attributes("aria-label")).toBe("小美，肖像載入失敗");
    await w.setProps({
      artPanel: {
        portrait_catalog: {
          ...artPanel.portrait_catalog,
          portrait_mei: { ...artPanel.portrait_catalog.portrait_mei, url: "/static/art/mei-v2.png" },
        },
      },
    });
    expect(w.get('img[src="/static/art/mei-v2.png"]').exists()).toBe(true);
  });

  it("keeps its scrollable frame out of sequential keyboard navigation", () => {
    const w = mountFrame(participants, artPanel);
    const frame = w.get('[data-testid="participant-frame"]');
    expect(frame.attributes("tabindex")).toBe("-1");
    expect(frame.element.tabIndex).toBe(-1);
    expect(frame.findAll("button, a, input, textarea, select, [tabindex]")).toHaveLength(0);
  });

  it("caps the decorative hairline while keeping displayed HP numerals exact", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(ParticipantFrame, {
      attachTo: host,
      props: { participants: [participants[1]], artPanel, displayHp: { portrait_mei: 120 } },
    });
    expect(wrapper.get(".participant-frame__hp").text()).toBe("120/90");
    expect(wrapper.get(".participant-frame__hairline > span").element.style.width).toBe("100%");
  });

  it("keeps placeholder and null-reference HP synchronized through playback and settlement", async () => {
    const foes = participants.filter((p) => p.team === "foes");
    wrapper = mount({
      props: ["displayHp"],
      render() {
        return h("div", [
          h(ParticipantFrame, { participants: foes, artPanel, displayHp: this.displayHp }),
          h(FoeLineup, { foes, artPanel, displayHp: this.displayHp }),
        ]);
      },
    }, { props: { displayHp: { portrait_gob: 18, f2: 0 } } });
    expect(wrapper.findAll(".participant-frame__hp").map((row) => row.text())).toEqual(["18/45", "120/120"]);
    expect(wrapper.findAll(".participant-frame__hairline > span").map((row) => row.element.style.width)).toEqual(["40%", "100%"]);
    expect(wrapper.findAll(".foe-lineup__fill").map((row) => row.element.style.width)).toEqual(["40%", "100%"]);
    await wrapper.setProps({ displayHp: null });
    expect(wrapper.findAll(".participant-frame__hp").map((row) => row.text())).toEqual(["45/45", "120/120"]);
    expect(wrapper.findAll(".foe-lineup__fill").map((row) => row.element.style.width)).toEqual(["100%", "100%"]);
  });

  it("describes zero as preparation without incrementing canonical positive counts", async () => {
    wrapper = mount(VitalsTrack, { props: { status: { combat: { mode: "hostile", round: 0 } } } });
    const ribbon = () => wrapper.get('[data-testid="status-panel__combat"]').text();
    expect(ribbon()).toContain("準備中");
    expect(ribbon()).not.toMatch(/第\\s*\\d/);
    for (const round of [1, 3, 12]) {
      await wrapper.setProps({ status: { combat: { mode: "hostile", round } } });
      expect(ribbon()).toContain(`第 ${round} 回合`);
      expect(ribbon()).not.toContain("準備中");
    }
  });

  it("offsets the resolved portrait crop by the catalog face rect", () => {
    const w = mountFrame(participants, artPanel);
    // 小美 resolves portrait_mei, whose rect centers at (50%, 31%).
    const mei = w.findAll("img.participant-frame__portrait")[0];
    expect(mei.element.style.objectPosition).toBe("50% 31%");
  });

  it("offsets foe portraits by the catalog face rect too", () => {
    const foeFramed = [
      { identity: "f1", team: "foes", token: "オーク", display_name: "オーク", hp_current: 120, hp_maximum: 120, state: "active", portrait_ref: "portrait_ork" },
    ];
    const foePanel = {
      portrait_catalog: {
        portrait_ork: { url: "/art/defaults/monster_anon.webp", placeholder: null, face_rect: { x: 0.35, y: 0.12, w: 0.4, h: 0.4 } },
      },
    };
    const w = mountFrame(foeFramed, foePanel);
    const img = w.get("img.participant-frame__portrait");
    expect(img.element.style.objectPosition).toBe("55% 32%");
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
