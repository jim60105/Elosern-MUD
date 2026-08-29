import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import CharacterStatusDrawer from "../../components/CharacterStatusDrawer.vue";
import {
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_SAMPLE,
  CHARACTER_PANEL_SAMPLE,
  CHARACTER_PANEL_UNDISGUISED_SAMPLE,
} from "../../stories/fixtures.js";

// CharacterStatusDrawer (H4, task 5.8;
// relocate-inventory-drawer-essentials): the 角色狀態 drawer body. The
// status sections (vitals + the FULL condition roster) render in every mode
// from the committed `status` payload; the `character`-backed sections show
// the registry-owned reason (and invent nothing) when the `character` panel
// is unavailable. The 親密狀態 (intimate-status) section renders as a
// collapsed-by-default `<details>` disclosure when the committed `character`
// v5 payload's `intimate` field is present, and is entirely absent from the
// DOM when it is `null` or the `character` panel is unavailable (never a
// placeholder or a collapsed-empty widget). The equipment doll and the
// single drawer-layer wallet now live in the inventory drawer, so this body
// renders no doll and no wallet figure.

const CHARACTER_UNAVAILABLE = {
  schema_version: 5,
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

  it("marks the character-backed sections with the registry-owned reason instead of hiding them", () => {
    const w = mountDrawer({ character: CHARACTER_UNAVAILABLE });
    // The status sections still render (vitals + conditions).
    expect(w.get('[data-testid="character-status-drawer__vitals"]').exists()).toBe(true);
    expect(w.get('[data-testid="character-status-drawer__conditions"]').exists()).toBe(true);
    // The drawer-level registry-owned reason.
    const reason = w.get('[data-testid="character-status-drawer__unavailable"]');
    expect(reason.text()).toBe("你已離開角色");
    expect(reason.attributes("data-reason-code")).toBe("no_puppet");
    // The character-backed section shells stay visible, each marked with the
    // same reason; no value rows are fabricated.
    expect(w.findAll('[data-testid^="character-status-drawer__trait--"]').length).toBe(0);
    expect(w.find('[data-testid="character-status-drawer__traits"]').exists()).toBe(true);
    expect(w.get('[data-testid="character-status-drawer__traits-unavailable"]').text()).toBe("你已離開角色");
    // The equipment doll and the wallet moved to the inventory drawer
    // (relocate-inventory-drawer-essentials): this body renders neither.
    expect(w.find('[data-testid="equipment-doll"]').exists()).toBe(false);
    expect(w.find('[data-testid="character-status-drawer__wallet"]').exists()).toBe(false);
    expect(w.find('[data-testid="character-status-drawer__guild"]').exists()).toBe(true);
    expect(w.get('[data-testid="character-status-drawer__guild-unavailable"]').exists()).toBe(true);
    expect(w.find('[data-testid="character-status-drawer__disguise"]').exists()).toBe(true);
    expect(w.get('[data-testid="character-status-drawer__disguise-unavailable"]').exists()).toBe(true);
    expect(w.find('[data-testid="character-status-drawer__persona"]').exists()).toBe(true);
    expect(w.get('[data-testid="character-status-drawer__persona-unavailable"]').exists()).toBe(true);
    // The intimate section is entirely absent from the DOM when the
    // `character` panel is unavailable — no placeholder or collapsed-empty
    // widget stands in for it.
    expect(w.find('[data-testid="character-status-drawer__intimate"]').exists()).toBe(false);
  });

  it("renders the 親密狀態 section as a collapsed-by-default disclosure (expandable)", async () => {
    const w = mountDrawer();
    const details = w.get('[data-testid="character-status-drawer__intimate"]');
    // Collapsed by default: the native <details> element carries no `open`
    // attribute; clicking the summary expands it.
    expect(details.attributes("open")).toBeUndefined();
    const summary = w.get('[data-testid="character-status-drawer__intimate-summary"]');
    await summary.trigger("click");
    expect(details.attributes("open")).toBe("");
  });

  it("renders the six intimate values and the vocabulary-closed hint verbatim", () => {
    const w = mountDrawer();
    expect(w.get('[data-testid="character-status-drawer__intimate--arousal"]').text()).toContain("中等");
    expect(w.get('[data-testid="character-status-drawer__intimate--wetness"]').text()).toContain("微濕");
    expect(w.get('[data-testid="character-status-drawer__intimate--shame"]').text()).toContain("輕微");
    // The effective-exposure pin (render-equipment-breakdown-webclient D2,
    // non-vacuous): the fixture's worn 修女聖袍 biases the stored base 「低」
    // to the effective 「中等」, and the wire never carries the base. The
    // assertion is scoped to the exposure row itself so no other row's
    // wording can satisfy it.
    const exposureRow = w.get('[data-testid="character-status-drawer__intimate--exposure"]');
    expect(exposureRow.text()).toContain("中等");
    expect(exposureRow.text()).not.toContain("低");
    expect(w.get('[data-testid="character-status-drawer__intimate--climax_phase"]').text()).toContain("未達");
    expect(w.get('[data-testid="character-status-drawer__intimate--climax_today"]').text()).toContain("2 次");
    expect(w.get('[data-testid="character-status-drawer__intimate-hint"]').text()).toBe("詞彙封閉；數值依設定折線/級別顯示。");
  });

  it("omits the intimate section entirely when the character panel's intimate field is null", () => {
    const w = mountDrawer({ character: CHARACTER_PANEL_UNDISGUISED_SAMPLE });
    expect(w.find('[data-testid="character-status-drawer__intimate"]').exists()).toBe(false);
    expect(w.text()).not.toContain("親密");
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
    expect(labels).toHaveLength(7);
    // DOM order (設計稿 #dr-status): vitals, traits, guild counters,
    // conditions, disguise, intimate status, persona.
    expect(labels.map((el) => el.text())).toEqual(["生命量", "屬性", "計數 · 公會", "狀態", "偽裝", "親密狀態", "背景"]);
  });

  it("renders every section in the 設計稿 DOM order", () => {
    const host = document.createElement("div");
    document.body.appendChild(host);
    wrapper = mount(CharacterStatusDrawer, {
      props: {
        status: STATUS_PANEL_SAMPLE,
        character: CHARACTER_PANEL_SAMPLE,
        lowHp: false,
      },
      attachTo: host,
    });
    // The equipment doll and wallet no longer belong to this body
    // (relocate-inventory-drawer-essentials): the section order is
    // vitals → traits → guild → conditions → disguise → 親密狀態 → 背景.
    const selectors = [
      '[data-testid="character-status-drawer__vitals"]',
      '[data-testid="character-status-drawer__traits"]',
      '[data-testid="character-status-drawer__guild"]',
      '[data-testid="character-status-drawer__conditions"]',
      '[data-testid="character-status-drawer__disguise"]',
      '[data-testid="character-status-drawer__intimate"]',
      '[data-testid="character-status-drawer__persona"]',
    ];
    const els = selectors.map((sel) => wrapper.find(sel).element);
    for (let i = 1; i < els.length; i += 1) {
      // a.compareDocumentPosition(b) masks b's position relative to a;
      // an element that renders after a sets the FOLLOWING bit.
      const pos = els[i - 1].compareDocumentPosition(els[i]);
      expect(pos & Node.DOCUMENT_POSITION_FOLLOWING).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
    }
  });

  it("keeps the full condition roster in combat when the character panel is unavailable", () => {
    const w = mountDrawer({ status: STATUS_PANEL_COMBAT_SAMPLE, character: CHARACTER_UNAVAILABLE });
    expect(w.get('[data-testid="character-status-drawer__vitals"]').exists()).toBe(true);
    // The complete condition roster renders in combat (the status panel is
    // available in every mode).
    expect(w.get('[data-testid="character-status-drawer__conditions"]').exists()).toBe(true);
    expect(w.get('[data-testid="character-status-drawer__condition--combat_focus"]').exists()).toBe(true);
    const reason = w.get('[data-testid="character-status-drawer__unavailable"]');
    expect(reason.text()).toBe("你已離開角色");
    // The character-backed sections are marked with the registry-owned
    // reason, not hidden.
    expect(w.find('[data-testid="character-status-drawer__traits"]').exists()).toBe(true);
    expect(w.get('[data-testid="character-status-drawer__traits-unavailable"]').exists()).toBe(true);
    // The equipment doll and the wallet moved to the inventory drawer
    // (relocate-inventory-drawer-essentials): this body renders neither.
    expect(w.find('[data-testid="equipment-doll"]').exists()).toBe(false);
    expect(w.find('[data-testid="character-status-drawer__wallet"]').exists()).toBe(false);
    expect(w.find('[data-testid="character-status-drawer__guild"]').exists()).toBe(true);
    expect(w.get('[data-testid="character-status-drawer__guild-unavailable"]').exists()).toBe(true);
    expect(w.find('[data-testid="character-status-drawer__disguise"]').exists()).toBe(true);
    expect(w.get('[data-testid="character-status-drawer__disguise-unavailable"]').exists()).toBe(true);
    expect(w.find('[data-testid="character-status-drawer__persona"]').exists()).toBe(true);
    // The intimate section is entirely absent in combat, where the `character`
    // panel is unavailable.
    expect(w.find('[data-testid="character-status-drawer__intimate"]').exists()).toBe(false);
  });

  it("renders vitals, traits and guild counters as bordered card tiles in a two-column grid", () => {
    const w = mountDrawer();
    // Four grids: vitals, traits, guild counters, and the intimate section.
    expect(w.findAll(".character-status-drawer__statgrid").length).toBe(4);
    const vitals = w.findAll('[data-testid^="character-status-drawer__vital--"]');
    expect(vitals).toHaveLength(3);
    // The 屬性 section renders exactly the four true-attribute rows; the
    // gauge (hp/mp/sp) and guild-merit values are owned by the 生命量 and
    // 計數・公會 sections, so they are not repeated under 屬性.
    for (const key of ["atk_phys", "agility", "defense", "magic_level"]) {
      expect(w.find(`[data-testid="character-status-drawer__trait--${key}"]`).exists()).toBe(true);
    }
    for (const key of ["hp", "mp", "sp", "guild_merit"]) {
      expect(w.find(`[data-testid="character-status-drawer__trait--${key}"]`).exists()).toBe(false);
    }
    // The 設計稿 abbreviates magic_level to 魔階 and the guild rank row
    // reads 公會階級.
    expect(w.get('[data-testid="character-status-drawer__trait--magic_level"]').text()).toContain("魔階");
    expect(w.get('[data-testid="character-status-drawer__guild-rank"]').text()).toContain("公會階級");
    // The vitals labels agree with VitalsTrack and the 設計稿: 魔力/耐力.
    expect(w.get('[data-testid="character-status-drawer__vital--mp"]').text()).toContain("魔力");
    expect(w.get('[data-testid="character-status-drawer__vital--sp"]').text()).toContain("耐力");
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
