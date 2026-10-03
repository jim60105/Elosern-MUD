import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ConditionChips from "../../components/ConditionChips.vue";
import { STATUS_PANEL_SAMPLE } from "../../stories/fixtures.js";

// H2 (webclient-hud-02-status-islands), design D6/D7/D8; vitals-bar-redesign
// design D3: the chromeless condition icon row. One glyph-only icon per
// committed condition (no window, no header, no visible name or duration),
// whose accessible name carries the label, the remaining duration (only when
// the payload supplies it, verbatim — never counted down client-side) and
// every derived modifier. The same prose opens in a `role="tooltip"` on hover
// or keyboard focus, closing on leave, blur, or Escape — Escape is consumed
// only while a tooltip is open. Visible icons are capped at 6; the remainder
// stays reachable through the `+N` icon's bounded disclosure.

const CONDITIONS = STATUS_PANEL_SAMPLE.conditions;

function manyConditions(count) {
  return Array.from({ length: count }, (_, i) => ({
    code: `cond_${i}`,
    label: `狀態${i + 1}`,
    severity: ["beneficial", "informational", "warning", "harmful", "critical"][i % 5],
    ...(i % 4 === 0 ? { remaining_seconds: i * 10 } : {}),
    ...(i % 3 === 0 ? { modifiers: { agility: "-10%" } } : {}),
  }));
}

describe("ConditionChips (chromeless condition icon row)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountChips(props = {}, attach = false) {
    wrapper = mount(ConditionChips, {
      ...(attach ? { attachTo: document.body.appendChild(document.createElement("div")) } : {}),
      props: {
        conditions: CONDITIONS,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders one icon per committed condition with its severity glyph", () => {
    const w = mountChips();
    const chips = w.findAll('[data-testid^="status-panel__condition--"]');
    expect(chips).toHaveLength(CONDITIONS.length);
    // The five severities map to five distinct shapes (design D6): the
    // warning glyph is `▽`, distinct from the harmful `▼`, so no two
    // severities are separated by colour alone.
    const glyphOf = (code) =>
      w.get(`[data-testid="status-panel__condition--${code}"] .glyph`).text();
    expect(glyphOf("fastwind")).toBe("▲");
    expect(glyphOf("fog_veil")).toBe("◆");
    expect(glyphOf("shame_exposure")).toBe("▼");
  });

  it("carries the label, duration, and every modifier in the icon's accessible name", () => {
    const w = mountChips();
    const buff = w.get('[data-testid="status-panel__condition--fastwind"]');
    const name = buff.attributes("aria-label");
    expect(name).toContain("疾風");
    expect(name).toContain("剩 60 秒");
    const harmful = w.get('[data-testid="status-panel__condition--shame_exposure"]');
    const harmfulName = harmful.attributes("aria-label");
    expect(harmfulName).toContain("高露出");
    expect(harmfulName).toContain("防禦 -15");
    expect(harmfulName).toContain("敏捷 -10");
  });

  const tooltip = () => document.querySelector('[data-testid="status-panel__condition-tooltip"]');

  it("shows only the glyph on each icon: no window header, no visible name, no duration", () => {
    const w = mountChips();
    expect(w.text()).not.toContain("狀態");
    for (const condition of CONDITIONS) {
      const icon = w.get(`[data-testid="status-panel__condition--${condition.code}"]`);
      expect(icon.element.tagName).toBe("BUTTON");
      expect(icon.text()).toBe(icon.get(".glyph").text());
      expect(icon.text()).not.toContain(condition.label);
      expect(icon.find('[data-testid="status-panel__condition-timer"]').exists()).toBe(false);
    }
    // Nothing opens until the player points at or focuses an icon.
    expect(tooltip()).toBeNull();
  });

  it("opens the tooltip on hover with the label, the verbatim duration, and the readable modifiers", async () => {
    const w = mountChips({}, true);
    const harmful = w.get('[data-testid="status-panel__condition--shame_exposure"]');
    await harmful.trigger("mouseenter");
    const tip = tooltip();
    expect(tip).not.toBeNull();
    expect(tip.getAttribute("role")).toBe("tooltip");
    expect(tip.textContent).toContain("高露出");
    expect(tip.querySelector('[data-testid="status-panel__condition-mod--defense"]').textContent).toBe("防禦 -15");
    expect(harmful.attributes("aria-describedby")).toBe(tip.id);
    await harmful.trigger("mouseleave");
    expect(tooltip()).toBeNull();
    expect(harmful.attributes("aria-describedby")).toBeUndefined();

    // fastwind carries remaining_seconds: 60 → the tooltip states it verbatim.
    await w.get('[data-testid="status-panel__condition--fastwind"]').trigger("mouseenter");
    expect(tooltip().querySelector('[data-testid="status-panel__condition-timer"]').textContent).toBe("剩 60 秒");
    await w.get('[data-testid="status-panel__condition--fastwind"]').trigger("mouseleave");
    // fog_veil carries no duration → no duration line, no substitute value.
    await w.get('[data-testid="status-panel__condition--fog_veil"]').trigger("mouseenter");
    expect(tooltip().querySelector('[data-testid="status-panel__condition-timer"]')).toBeNull();
  });

  it("does not count the duration down between revisions", async () => {
    const w = mountChips({}, true);
    await w.get('[data-testid="status-panel__condition--fastwind"]').trigger("focus");
    // No timer of any kind runs: the tooltip keeps the payload's value until
    // a new committed revision replaces the payload.
    await new Promise((resolve) => setTimeout(resolve, 1100));
    expect(tooltip().querySelector('[data-testid="status-panel__condition-timer"]').textContent).toBe("剩 60 秒");
  });

  it("opens the same tooltip on keyboard focus and closes it on blur", async () => {
    const w = mountChips({}, true);
    const icon = w.get('[data-testid="status-panel__condition--fastwind"]');
    await icon.trigger("focus");
    expect(tooltip().textContent).toContain("疾風");
    expect(icon.attributes("aria-describedby")).toBe(tooltip().id);
    await icon.trigger("blur");
    expect(tooltip()).toBeNull();
  });

  it("consumes Escape only while a tooltip is open", async () => {
    const w = mountChips({}, true);
    const icon = w.get('[data-testid="status-panel__condition--fastwind"]');
    const reached = [];
    const outer = (event) => reached.push(event.key);
    document.body.addEventListener("keydown", outer);
    try {
      // Nothing of the row's own is open: Escape falls through to the shell.
      await icon.trigger("keydown", { key: "Escape" });
      expect(reached).toEqual(["Escape"]);
      // An open tooltip claims Escape and closes.
      await icon.trigger("focus");
      expect(tooltip()).not.toBeNull();
      await icon.trigger("keydown", { key: "Escape" });
      expect(tooltip()).toBeNull();
      expect(reached).toEqual(["Escape"]);
      // Closed again: the next Escape is the shell's.
      await icon.trigger("keydown", { key: "Escape" });
      expect(reached).toEqual(["Escape", "Escape"]);
    } finally {
      document.body.removeEventListener("keydown", outer);
    }
  });

  it("closes the tooltip when its condition stops being committed or the dock hides", async () => {
    const w = mountChips({}, true);
    await w.get('[data-testid="status-panel__condition--fastwind"]').trigger("mouseenter");
    expect(tooltip()).not.toBeNull();
    await w.setProps({ conditions: CONDITIONS.filter((c) => c.code !== "fastwind") });
    expect(tooltip()).toBeNull();
    await w.get('[data-testid="status-panel__condition--fog_veil"]').trigger("mouseenter");
    expect(tooltip()).not.toBeNull();
    await w.setProps({ revealed: false });
    expect(tooltip()).toBeNull();
  });

  it("caps visible icons at 6 and discloses the remainder in a bounded, scrollable region", async () => {
    const w = mountChips({ conditions: manyConditions(12) });
    const visibleChips = w.findAll(".chip:not(.more)");
    expect(visibleChips).toHaveLength(6);
    // Six visible icons + one `+N` overflow icon stating the hidden count.
    const overflow = w.get('[data-testid="status-panel__condition-overflow"]');
    expect(overflow.text()).toBe("+6");
    expect(overflow.attributes("aria-expanded")).toBe("false");

    await overflow.trigger("click");
    expect(w.get('[data-testid="status-panel__condition-disclosure"]').exists()).toBe(true);
    expect(w.findAll(".detail-row")).toHaveLength(6);
    expect(overflow.attributes("aria-expanded")).toBe("true");

    // Re-activation collapses the disclosure.
    await overflow.trigger("click");
    expect(w.find('[data-testid="status-panel__condition-disclosure"]').exists()).toBe(false);

    // Escape collapses it (component-scoped, so it never steals the shell's
    // drawer or full-log Escape).
    await overflow.trigger("click");
    await overflow.trigger("keydown", { key: "Escape" });
    expect(w.find('[data-testid="status-panel__condition-disclosure"]').exists()).toBe(false);
  });

  it("discloses 8 committed conditions as a +2 icon with two disclosure rows", async () => {
    const w = mountChips({ conditions: manyConditions(8) });
    const visibleChips = w.findAll(".chip:not(.more)");
    expect(visibleChips).toHaveLength(6);
    const overflow = w.get('[data-testid="status-panel__condition-overflow"]');
    expect(overflow.text()).toBe("+2");
    await overflow.trigger("click");
    expect(w.get('[data-testid="status-panel__condition-disclosure"]').exists()).toBe(true);
    expect(w.findAll(".detail-row")).toHaveLength(2);
  });

  it("never sizes an icon by its label and keeps long names complete in the name and tooltip", async () => {
    // Six long server labels plus one overflow: no icon shows its name, the
    // accessible name and the tooltip carry the whole label and localized
    // modifiers, and the overflow row reaches the seventh.
    const long = [
      "高度興奮敏捷與準度減損",
      "精準魔力控制魔力消耗降低",
      "魔法陣理解施法準度提升",
      "隨從武藝訓練攻擊提升",
      "靜電麻痺微階鎖定行動",
      "轉生祝福‧悠花敏捷提升",
      "連閃麻痺微階鎖定行動",
    ].map((label, i) => ({
      code: `long_${i}`,
      label,
      severity: "harmful",
      ...(i === 1 ? { modifiers: { mp_cost: "-10%" } } : {}),
      ...(i === 6 ? { modifiers: { actions_per_turn: 0, chance: 30 } } : {}),
    }));
    const w = mountChips({ conditions: long }, true);
    const chips = w.findAll("button.chip:not(.more)");
    expect(chips).toHaveLength(6);
    chips.forEach((chip, i) => {
      expect(chip.text()).toBe("▼");
      expect(chip.attributes("aria-label")).toContain(long[i].label);
    });
    expect(chips[1].attributes("aria-label")).toBe("精準魔力控制魔力消耗降低，魔力消耗 -10%");
    await chips[1].trigger("focus");
    expect(tooltip().textContent).toContain("精準魔力控制魔力消耗降低");
    expect(tooltip().querySelector('[data-testid="status-panel__condition-mod--mp_cost"]').textContent).toBe("魔力消耗 -10%");
    await chips[1].trigger("blur");
    await w.get('[data-testid="status-panel__condition-overflow"]').trigger("click");
    const row = w.get('[data-testid="status-panel__condition-disclosure"] [data-testid="status-panel__condition--long_6"]');
    expect(row.text()).toContain("連閃麻痺微階鎖定行動");
    expect(row.get('[data-testid="status-panel__condition-mod--actions_per_turn"]').text()).toBe("每回合行動 0");
    expect(row.get('[data-testid="status-panel__condition-mod--chance"]').text()).toBe("觸發機率 30");
  });

  it("renders no icon row when the committed list is empty", () => {
    const w = mountChips({ conditions: [] });
    expect(w.find('[data-testid="status-panel__conditions"]').exists()).toBe(false);
    expect(w.find('[data-testid="status-panel__conditions-empty"]').exists()).toBe(false);
    expect(w.find("button").exists()).toBe(false);
  });
});
