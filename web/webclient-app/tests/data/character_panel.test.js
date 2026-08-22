import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import CharacterPanel from "../../components/CharacterPanel.vue";
import { CHARACTER_PANEL_SAMPLE, CHARACTER_PANEL_UNDISGUISED_SAMPLE } from "../../stories/fixtures.js";

describe("CharacterPanel (B3 data family)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountPanel(props = {}) {
    wrapper = mount(CharacterPanel, {
      props: {
        character: CHARACTER_PANEL_SAMPLE,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders the full eight-row trait table with true values", () => {
    const w = mountPanel();
    expect(w.get('[data-testid="character-panel__trait--hp"]').text()).toBe("生命231 / 405");
    expect(w.get('[data-testid="character-panel__trait--mp"]').text()).toBe("魔力139 / 420");
    expect(w.get('[data-testid="character-panel__trait--sp"]').text()).toBe("耐力68 / 68");
    // Statics and counters carry max null: the bare true value only.
    expect(w.get('[data-testid="character-panel__trait--atk_phys"]').text()).toBe("攻擊18");
    expect(w.get('[data-testid="character-panel__trait--agility"]').text()).toBe("敏捷20");
    expect(w.get('[data-testid="character-panel__trait--defense"]').text()).toBe("防禦12");
    expect(w.get('[data-testid="character-panel__trait--magic_level"]').text()).toBe("魔法階級31");
    expect(w.get('[data-testid="character-panel__trait--guild_merit"]').text()).toBe("功績140");
  });

  it("renders only equipped items with their payload display names", () => {
    const w = mountPanel();
    const items = w.findAll('[data-testid="character-panel__equipment-item"]');
    expect(items).toHaveLength(3);
    expect(items[0].attributes("data-slot")).toBe("weapon_main");
    expect(items[0].text()).toContain("短劍 · 拾遺");
    expect(items[1].attributes("data-slot")).toBe("armor");
    expect(items[1].text()).toContain("皮甲");
    expect(items[2].attributes("data-slot")).toBe("accessory");
    expect(items[2].text()).toContain("霧隱護符");
    // The empty side slot is not modeled today, so it is not invented.
    expect(w.text()).not.toContain("副手");
  });

  it("shows disguised statistics as display values distinct from the true traits", () => {
    const w = mountPanel();
    const disguise = w.get('[data-testid="character-panel__disguise"]');
    expect(disguise.attributes("data-active")).toBe("true");
    expect(disguise.text()).toContain(CHARACTER_PANEL_SAMPLE.disguise.description);

    // The displayed value is a labeled display cell, side by side with the
    // true value it describes — never merged into the trait row.
    const atk = w.get('[data-testid="character-panel__disguise--atk_phys"]');
    expect(atk.text().replace(/\s+/g, " ")).toBe("攻擊 真 18 顯 25");
    expect(atk.find('[data-testid="character-panel__disguise-true"]').text()).toBe("真 18");
    expect(atk.find('[data-testid="character-panel__disguise-displayed"]').text()).toBe("顯 25");
    const magic = w.get('[data-testid="character-panel__disguise--magic_level"]');
    expect(magic.text().replace(/\s+/g, " ")).toBe("魔法階級 真 31 顯 12");

    // The true trait rows are never substituted by the displayed values.
    expect(w.get('[data-testid="character-panel__trait--atk_phys"]').text()).toBe("攻擊18");
    expect(w.get('[data-testid="character-panel__trait--magic_level"]').text()).toBe("魔法階級31");
  });

  it("renders the honest no-disguise line and no displayed rows when inactive", () => {
    const w = mountPanel({ character: CHARACTER_PANEL_UNDISGUISED_SAMPLE });
    const disguise = w.get('[data-testid="character-panel__disguise"]');
    expect(disguise.attributes("data-active")).toBe("false");
    expect(
      w.get('[data-testid="character-panel__disguise-inactive"]').text(),
    ).toContain("目前沒有偽裝狀態");
    expect(w.findAll('[data-testid^="character-panel__disguise--"]')).toHaveLength(0);
  });

  it("renders guild rank and merit; a null rank is the honest 未加入公會 line", () => {
    expect(mountPanel().get('[data-testid="character-panel__guild-rank"]').text()).toBe("階級E");
    expect(mountPanel().get('[data-testid="character-panel__guild-merit"]').text()).toBe("功績140");
    const w = mountPanel({ character: CHARACTER_PANEL_UNDISGUISED_SAMPLE });
    expect(w.get('[data-testid="character-panel__guild-rank"]').text()).toBe("階級未加入公會");
    expect(w.get('[data-testid="character-panel__guild-merit"]').text()).toBe("功績0");
  });

  it("renders wallet in copper and the persona background only when present", () => {
    expect(mountPanel().get('[data-testid="character-panel__wallet"]').text()).toBe(
      "錢包：3,240 銅",
    );
    expect(
      mountPanel().get('[data-testid="character-panel__persona-background"]').text(),
    ).toBe(CHARACTER_PANEL_SAMPLE.persona.background);

    const w = mountPanel({ character: CHARACTER_PANEL_UNDISGUISED_SAMPLE });
    expect(w.get('[data-testid="character-panel__wallet"]').text()).toBe("錢包：0 銅");
    expect(w.find('[data-testid="character-panel__persona"]').exists()).toBe(false);
  });

  it("invents no intimate/adult block (no backing field, not mocked)", () => {
    const w = mountPanel();
    expect(w.find('[data-testid="character-panel__intimate"]').exists()).toBe(false);
    for (const word of ["親密", "興奮", "濕潤", "羞恥", "高潮", "敏感"]) {
      expect(w.text()).not.toContain(word);
    }
  });
});
