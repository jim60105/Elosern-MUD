import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import PartyStrip from "../../components/PartyStrip.vue";
import {
  PARTY_PANEL_SAMPLE,
  PARTY_PANEL_EMPTY_SAMPLE,
  PARTY_PANEL_FULL_SAMPLE,
  PARTY_COMBAT_PARTICIPANTS_SAMPLE,
  ART_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

// webclient-align-05-party-hud: the left-HUD companion quickbar (.comps).
// Renders the committed party slots, HP hairline bars, bond stages,
// combat token prefix by identity join, missing-portrait glyph fallback,
// and dashed invite slot padding up to four.

describe("PartyStrip (left-HUD companion quickbar)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountStrip(props = {}) {
    wrapper = mount(PartyStrip, {
      props: {
        slots: PARTY_PANEL_SAMPLE.slots,
        combatParticipants: PARTY_COMBAT_PARTICIPANTS_SAMPLE,
        artPanel: ART_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("mirrors the committed party slots with count N / 4 and invite padding", () => {
    const w = mountStrip();
    expect(w.get('[data-testid="party-strip__header"]').text()).toContain("同伴");
    expect(w.get('[data-testid="party-strip__count"]').text()).toBe("2 / 4");

    const slots = w.findAll('[data-testid^="party-strip__slot-"]');
    expect(slots).toHaveLength(2);

    const emptySlots = w.findAll('[data-testid="party-strip__empty-slot"]');
    expect(emptySlots).toHaveLength(2);

    // Verify first slot (蕾娜)
    const s1 = w.get('[data-testid="party-strip__slot-101"]');
    expect(s1.get('[data-testid="party-strip__name"]').text()).toBe("蕾娜");
    expect(s1.get('[data-testid="party-strip__state"]').text()).toContain("180/220");
    expect(s1.get('[data-testid="party-strip__state"]').text()).toContain("親睦");

    // Verify second slot (幽)
    const s2 = w.get('[data-testid="party-strip__slot-102"]');
    expect(s2.get('[data-testid="party-strip__name"]').text()).toBe("幽");
    expect(s2.get('[data-testid="party-strip__state"]').text()).toContain("144/160");
    expect(s2.get('[data-testid="party-strip__state"]').text()).toContain("信賴");

    // No numeric affinity appears anywhere in the output
    expect(w.text()).not.toMatch(/70|affinity|數值/);
  });

  it("joins combat tokens by identity", () => {
    const w = mountStrip({
      slots: PARTY_PANEL_SAMPLE.slots,
      combatParticipants: [
        { identity: 101, token: "a2", display_name: "蕾娜" },
        // companion 102 is not in combat participants
      ],
    });

    const s1 = w.get('[data-testid="party-strip__slot-101"]');
    expect(s1.find('[data-testid="party-strip__token"]').exists()).toBe(true);
    expect(s1.get('[data-testid="party-strip__token"]').text()).toBe("a2");

    const s2 = w.get('[data-testid="party-strip__slot-102"]');
    expect(s2.find('[data-testid="party-strip__token"]').exists()).toBe(false);
  });

  it("shows no token prefix when combatParticipants is empty (non-combat)", () => {
    const w = mountStrip({
      slots: PARTY_PANEL_SAMPLE.slots,
      combatParticipants: [],
    });

    for (const slot of w.findAll('[data-testid^="party-strip__slot-"]')) {
      expect(slot.find('[data-testid="party-strip__token"]').exists()).toBe(false);
    }
  });

  it("falls back to the initial letter when portrait_ref is null", () => {
    const w = mountStrip({
      slots: [
        {
          identity: 102,
          display_name: "幽",
          portrait_ref: null,
          hp_current: 144,
          hp_maximum: 160,
          bond_stage: "信賴",
        },
      ],
      artPanel: null,
    });

    const s = w.get('[data-testid="party-strip__slot-102"]');
    expect(s.find("img").exists()).toBe(false);
    expect(s.get(".av-glyph").text()).toBe("幽");
  });

  it("renders an img when portrait_ref resolves in artPanel", () => {
    const artPanel = {
      portrait_catalog: {
        p_reina: { url: "/media/portraits/reina.png" },
      },
    };
    const w = mountStrip({
      slots: [
        {
          identity: 101,
          display_name: "蕾娜",
          portrait_ref: "p_reina",
          hp_current: 180,
          hp_maximum: 220,
          bond_stage: "親睦",
        },
      ],
      artPanel,
    });

    const img = w.get('[data-testid="party-strip__slot-101"] img');
    expect(img.attributes("src")).toBe("/media/portraits/reina.png");
  });

  it("renders four dashed invite cells and 0 / 4 for an empty party", () => {
    const w = mountStrip({
      slots: PARTY_PANEL_EMPTY_SAMPLE.slots,
    });
    expect(w.get('[data-testid="party-strip__count"]').text()).toBe("0 / 4");
    expect(w.findAll('[data-testid^="party-strip__slot-"]')).toHaveLength(0);
    expect(w.findAll('[data-testid="party-strip__empty-slot"]')).toHaveLength(4);
  });

  it("renders zero dashed invite cells and 4 / 4 for a full party", () => {
    const w = mountStrip({
      slots: PARTY_PANEL_FULL_SAMPLE.slots,
    });
    expect(w.get('[data-testid="party-strip__count"]').text()).toBe("4 / 4");
    expect(w.findAll('[data-testid^="party-strip__slot-"]')).toHaveLength(4);
    expect(w.findAll('[data-testid="party-strip__empty-slot"]')).toHaveLength(0);
  });

  it("handles zero or invalid hp_maximum gracefully without NaN", () => {
    const w = mountStrip({
      slots: [
        {
          identity: 999,
          display_name: "測試",
          portrait_ref: null,
          hp_current: 0,
          hp_maximum: 0,
          bond_stage: "初識",
        },
      ],
    });
    const fill = w.get('[data-testid="party-strip__slot-999"] .f');
    expect(fill.attributes("style")).toContain("width: 0%");
  });

  it("activating island or slots emits open-drawer without mutating or dispatching", async () => {
    const w = mountStrip();

    // Click strip root
    await w.get('[data-testid="party-strip"]').trigger("click");
    expect(w.emitted("open-drawer")).toHaveLength(1);

    // Click slot
    await w.get('[data-testid="party-strip__slot-101"]').trigger("click");
    expect(w.emitted("open-drawer")).toHaveLength(2);

    // Click empty slot
    const emptySlots = w.findAll('[data-testid="party-strip__empty-slot"]');
    await emptySlots[0].trigger("click");
    expect(w.emitted("open-drawer")).toHaveLength(3);

    // Keyboard trigger (Enter on strip)
    await w.get('[data-testid="party-strip"]').trigger("keydown.enter");
    expect(w.emitted("open-drawer")).toHaveLength(4);
  });
});
