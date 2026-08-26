import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import CharacterStatusDrawer from "../../components/CharacterStatusDrawer.vue";
import {
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_SAMPLE,
  CHARACTER_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

// CharacterStatusDrawer (H4, task 5.8): the 角色狀態 drawer body. The
// status sections (vitals + the FULL condition roster) render in every mode
// from the committed `status` payload; the `character`-backed sections show
// the registry-owned reason (and invent nothing) when the `character` panel
// is unavailable. The 親密狀態 block the 設計稿 shows has no backing field
// and is absent.

const CHARACTER_UNAVAILABLE = {
  schema_version: 3,
  available: false,
  kind: "character",
  reason: { code: "no_puppet", message: "你已離開角色" },
};

describe("CharacterStatusDrawer", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountDrawer(props = {}) {
    wrapper = mount(CharacterStatusDrawer, {
      props: {
        status: STATUS_PANEL_SAMPLE,
        character: CHARACTER_PANEL_SAMPLE,
        lowHp: false,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the status vitals and the FULL condition roster (no 6-chip cap)", () => {
    const w = mountDrawer();
    // Vitals: the three gauge values.
    for (const key of ["hp", "mp", "sp"]) {
      expect(w.get(`[data-testid="character-status-drawer__vital-value--${key}"]`).text()).toBeTruthy();
    }
    // The full roster: STATUS_PANEL_SAMPLE has 3 conditions, all rendered.
    const conditions = w.findAll('[data-testid^="character-status-drawer__condition--"]');
    expect(conditions).toHaveLength(3);
    // Each row carries its non-colour severity glyph + label.
    for (const row of conditions) {
      expect(row.text().length).toBeGreaterThan(0);
    }
    // A condition with modifiers renders every derived-modifier value.
    const exposure = w.get('[data-testid="character-status-drawer__condition--shame_exposure"]');
    expect(exposure.text()).toContain("defense -15");
    expect(exposure.text()).toContain("agility -10");
    // A condition with a duration renders the remaining seconds verbatim.
    expect(w.get('[data-testid="character-status-drawer__condition--fastwind"]').text()).toContain("剩 60 秒");
  });

  it("renders the status sections when the character panel is unavailable, inventing nothing", () => {
    const w = mountDrawer({ character: CHARACTER_UNAVAILABLE });
    // The status sections still render (vitals + conditions).
    expect(w.get('[data-testid="character-status-drawer__vitals"]').exists()).toBe(true);
    expect(w.get('[data-testid="character-status-drawer__conditions"]').exists()).toBe(true);
    // The registry-owned reason is shown; no trait/equipment/disguise/guild
    // rows are fabricated.
    const reason = w.get('[data-testid="character-status-drawer__unavailable"]');
    expect(reason.text()).toBe("你已離開角色");
    expect(reason.attributes("data-reason-code")).toBe("no_puppet");
    expect(w.findAll('[data-testid^="character-status-drawer__trait--"]').length).toBe(0);
    expect(w.find('[data-testid="character-status-drawer__equipment"]').exists()).toBe(false);
    expect(w.find('[data-testid="character-status-drawer__guild"]').exists()).toBe(false);
  });

  it("invents no 親密狀態 block (no arousal / wetness / shame / exposure / climax element)", () => {
    const w = mountDrawer();
    for (const word of ["親密", "興奮", "濕潤", "羞恥", "高潮", "露出部位", "敏感度", "處女"]) {
      expect(w.text()).not.toContain(word);
    }
  });

  it("renders the disguise 真值 / 顯示 comparison with the standing combat-on-true-traits note", () => {
    const w = mountDrawer();
    // CHARACTER_PANEL_SAMPLE has an active disguise with displayed values.
    const disguise = w.get('[data-testid="character-status-drawer__disguise"]');
    expect(disguise.attributes("data-active")).toBe("true");
    // The standing statement: combat always resolves on true traits.
    expect(w.get('[data-testid="character-status-drawer__disguise-note"]').text()).toContain("真值");
  });

  it("marks every drawer section with a labelled small-caps heading", () => {
    const w = mountDrawer();
    const labels = w.findAll(".character-status-drawer__section-label");
    expect(labels).toHaveLength(6);
    // DOM order: vitals, conditions, traits, disguise, guild, persona.
    expect(labels.map((el) => el.text())).toEqual(["生命量", "狀態", "屬性", "偽裝", "計數 · 公會", "背景"]);
  });

  it("renders vitals, traits and guild counters as bordered card tiles in a two-column grid", () => {
    const w = mountDrawer();
    // Three grids: vitals, traits, guild counters.
    expect(w.findAll(".character-status-drawer__statgrid").length).toBe(3);
    const vitals = w.findAll('[data-testid^="character-status-drawer__vital--"]');
    expect(vitals).toHaveLength(3);
    const traits = w.findAll('[data-testid^="character-status-drawer__trait--"]');
    expect(traits).toHaveLength(CHARACTER_PANEL_SAMPLE.traits.length);
    expect(w.find('[data-testid="character-status-drawer__guild-rank"]').exists()).toBe(true);
    expect(w.find('[data-testid="character-status-drawer__guild-merit"]').exists()).toBe(true);
  });

  it("renders each condition as a severity-tinted pill keeping all row content in a muted suffix", () => {
    const w = mountDrawer();
    const pills = w.findAll(".character-status-drawer__pill");
    expect(pills).toHaveLength(STATUS_PANEL_SAMPLE.conditions.length);
    for (const pill of pills) {
      const severity = pill.attributes("data-severity");
      expect(pill.classes()).toContain(`character-status-drawer__pill--${severity}`);
      expect(pill.find(".character-status-drawer__condition-stat").exists()).toBe(true);
    }
    // Nothing is dropped: the exposure pill still carries every modifier,
    // the fastwind pill still carries its duration.
    const exposure = w.get('[data-testid="character-status-drawer__condition--shame_exposure"]');
    expect(exposure.text()).toContain("defense -15");
    expect(exposure.text()).toContain("agility -10");
    const fastwind = w.get('[data-testid="character-status-drawer__condition--fastwind"]');
    expect(fastwind.text()).toContain("剩 60 秒");
  });

  it("keeps the 危險 marker beside the HP label on a low-HP tile", () => {
    const w = mountDrawer({ lowHp: true });
    const danger = w.get('[data-testid="character-status-drawer__vital-danger"]');
    expect(danger.text()).toBe("危險");
    const hpTile = w.get('[data-testid="character-status-drawer__vital--hp"]');
    expect(hpTile.text()).toContain("危險");
  });
});
