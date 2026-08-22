import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import StatusPanel from "../../components/StatusPanel.vue";
import {
  CHARACTER_PANEL_SAMPLE,
  STATUS_PANEL_COMBAT_SAMPLE,
  STATUS_PANEL_MINIMAL_SAMPLE,
  STATUS_PANEL_SAMPLE,
} from "../../stories/fixtures.js";

describe("StatusPanel (B3 data family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountPanel(props = {}) {
    wrapper = mount(StatusPanel, {
      props: {
        status: STATUS_PANEL_SAMPLE,
        character: CHARACTER_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders actor and location from the status payload", () => {
    const w = mountPanel();
    const actor = w.get('[data-testid="status-panel__actor"]');
    expect(actor.text()).toContain("艾倫·灰誓");
    expect(actor.text()).toContain("霧骨渡口");
  });

  it("pairs every gauge with a symbol and an explicit current / maximum value", () => {
    const w = mountPanel();
    const expected = {
      hp: { symbol: "♥", label: "生命", value: "231 / 405" },
      mp: { symbol: "❖", label: "魔力", value: "139 / 420" },
      sp: { symbol: "⚡", label: "耐力", value: "68 / 68" },
    };
    for (const [key, item] of Object.entries(expected)) {
      const gauge = w.get(`[data-testid="status-panel__gauge--${key}"]`);
      expect(gauge.text()).toContain(item.symbol);
      expect(gauge.text()).toContain(item.label);
      expect(
        gauge.find(`[data-testid="status-panel__gauge-value--${key}"]`).text(),
      ).toBe(item.value);
    }
  });

  it("renders counters, static traits, and wallet from the character payload", () => {
    const w = mountPanel();
    expect(w.get('[data-testid="status-panel__trait--atk_phys"]').text()).toContain("18");
    expect(w.get('[data-testid="status-panel__trait--agility"]').text()).toContain("20");
    expect(w.get('[data-testid="status-panel__trait--defense"]').text()).toContain("12");
    expect(w.get('[data-testid="status-panel__trait--magic_level"]').text()).toContain("31");
    expect(w.get('[data-testid="status-panel__trait--guild_merit"]').text()).toContain("140");
    expect(w.get('[data-testid="status-panel__wallet"]').text()).toBe("錢包3,240 銅");
  });

  it("renders conditions with severity markers, remaining seconds, and derived modifiers", () => {
    const w = mountPanel();
    const buff = w.get('[data-testid="status-panel__condition--fastwind"]');
    expect(buff.attributes("data-severity")).toBe("beneficial");
    expect(buff.text()).toContain("疾風");
    expect(buff.find('[data-testid="status-panel__condition-timer"]').text()).toBe("60 s");

    const harmful = w.get('[data-testid="status-panel__condition--shame_exposure"]');
    expect(harmful.attributes("data-severity")).toBe("harmful");
    // Every derived modifier pair is rendered, not just a color change.
    expect(harmful.find('[data-testid="status-panel__condition-mod--defense"]').text()).toBe("defense -15");
    expect(harmful.find('[data-testid="status-panel__condition-mod--agility"]').text()).toBe("agility -10");

    // The informational condition carries neither a timer nor modifiers.
    const info = w.get('[data-testid="status-panel__condition--fog_veil"]');
    expect(info.attributes("data-severity")).toBe("informational");
    expect(info.find('[data-testid="status-panel__condition-timer"]').exists()).toBe(false);
    expect(info.findAll('[data-testid^="status-panel__condition-mod--"]')).toHaveLength(0);
  });

  it("pairs every condition with a DOM severity glyph, not color or border alone", () => {
    const w = mountPanel();
    // The glyph is a real DOM node per severity, plus the payload's own label.
    const expected = {
      fastwind: { glyph: "▲", label: "疾風" },
      shame_exposure: { glyph: "▼", label: "高露出" },
      fog_veil: { glyph: "◆", label: "霧隱" },
    };
    for (const [code, item] of Object.entries(expected)) {
      const condition = w.get(`[data-testid="status-panel__condition--${code}"]`);
      expect(condition.find(".status-panel__condition-glyph").text()).toBe(item.glyph);
      expect(condition.text()).toContain(item.label);
    }
  });

  it("renders every counter and static trait as its canonical label plus a numeric value", () => {
    const w = mountPanel();
    const expected = {
      atk_phys: "18",
      agility: "20",
      defense: "12",
      magic_level: "31",
      guild_merit: "140",
    };
    for (const [key, value] of Object.entries(expected)) {
      const row = w.get(`[data-testid="status-panel__trait--${key}"]`);
      expect(row.find(".status-panel__trait-key").text()).not.toBe("");
      expect(row.find(".status-panel__trait-value").text()).toBe(value);
    }
  });

  it("renders the honest empty-condition line when the payload has none", () => {
    const w = mountPanel({ status: STATUS_PANEL_MINIMAL_SAMPLE });
    expect(w.get('[data-testid="status-panel__conditions-empty"]').text()).toBe("無條件");
    expect(w.findAll('[data-testid^="status-panel__condition--"]')).toHaveLength(0);
  });

  it("renders the disguise flag from the status payload, both ways", () => {
    expect(mountPanel().get('[data-testid="status-panel__disguise"]').text()).toBe("目前有偽裝");
    const w = mountPanel({ status: STATUS_PANEL_COMBAT_SAMPLE });
    const flag = w.get('[data-testid="status-panel__disguise"]');
    expect(flag.text()).toBe("無偽裝");
    expect(flag.attributes("data-active")).toBe("false");
  });

  it("renders the combat session only when the payload carries one", () => {
    expect(mountPanel().find('[data-testid="status-panel__combat"]').exists()).toBe(false);
    const w = mountPanel({ status: STATUS_PANEL_COMBAT_SAMPLE });
    const combat = w.get('[data-testid="status-panel__combat"]');
    expect(combat.attributes("data-mode")).toBe("guild_exam");
    expect(combat.text()).toBe("戰鬥中（公會考核）· 第 3 回合");
  });

  it("invents no intimate/adult block (no backing field, not mocked)", () => {
    const w = mountPanel();
    expect(w.find('[data-testid="status-panel__intimate"]').exists()).toBe(false);
    for (const word of ["親密", "興奮", "濕潤", "羞恥", "高潮", "露出部位"]) {
      expect(w.text()).not.toContain(word);
    }
  });

  it("renders only values the payloads carry", () => {
    const w = mountPanel({ status: STATUS_PANEL_MINIMAL_SAMPLE });
    expect(w.text()).toContain("405 / 405");
    expect(w.text()).toContain("420 / 420");
    // Nothing numeric beyond the payloads' own values and labels.
    expect(w.get('[data-testid="status-panel__gauge-value--hp"]').text()).toBe("405 / 405");
    expect(w.get('[data-testid="status-panel__wallet"]').text()).toBe("錢包3,240 銅");
  });
});
