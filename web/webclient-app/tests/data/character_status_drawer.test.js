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
});
