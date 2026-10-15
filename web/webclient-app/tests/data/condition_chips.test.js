import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it, vi } from "vitest";
import { nextTick } from "vue";
import { conditionLabel } from "../../lib/condition_label.js";
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
    provenance: { kind: "non_equipment", equipment_sources: [] }, severity: ["beneficial", "informational", "warning", "harmful", "critical"][i % 5],
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

  it("keeps duplicate-code tooltip and overflow detail local to each instance", async () => {
    const attached = {
      code: "t_shared", label: "合成警告", severity: "harmful", remaining_seconds: 17,
      modifiers: { defense: -15 },
      provenance: { kind: "equipment", equipment_sources: [{ item_key: "t_a", label: "合成護符" }] },
    };
    const independent = { ...attached, remaining_seconds: 120, provenance: { kind: "non_equipment", equipment_sources: [] } };
    const w = mountChips({ conditions: [attached, independent, ...manyConditions(4), attached, independent] }, true);
    const icons = w.findAll('[data-testid="status-panel__condition--t_shared"]');
    await icons[0].trigger("focus");
    expect(tooltip().textContent).toContain("合成護符");
    expect(tooltip().textContent).toContain("剩 17 秒");
    expect(icons[0].attributes("aria-label")).toContain("裝備來源：合成護符");
    expect(icons[1].attributes("aria-describedby")).toBeUndefined();
    await icons[1].trigger("focus");
    expect(tooltip().textContent).toContain("剩 120 秒");
    expect(tooltip().textContent).not.toContain("合成護符");
    await w.get('[data-testid="status-panel__condition-overflow"]').trigger("click");
    const overflow = w.get('[data-testid="status-panel__condition-disclosure"]').findAll(".detail-row");
    expect(overflow[0].attributes("aria-label")).toBe(icons[0].attributes("aria-label"));
    expect(overflow[0].text()).toContain("裝備來源：合成護符");
    expect(overflow[1].text()).toContain("剩 120 秒");
    await w.setProps({ conditions: [independent, attached] });
    expect(tooltip()).toBeNull();
  });

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
      provenance: { kind: "non_equipment", equipment_sources: [] }, severity: "harmful",
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

  // webclient-combat-figure-plates (design D2/D3): the props the plates use,
  // and the tooltip kept inside the viewport.
  it("keeps every icon in the tab order by default and none with tabbable=false", () => {
    const w = mountChips({ conditions: manyConditions(8) });
    expect(w.findAll("button").every((b) => b.attributes("tabindex") === undefined)).toBe(true);
    const w2 = mount(ConditionChips, { props: { conditions: manyConditions(8), tabbable: false } });
    expect(w2.findAll("button")).toHaveLength(7);
    expect(w2.findAll("button").every((b) => b.attributes("tabindex") === "-1")).toBe(true);
    w2.unmount();
  });

  it("names a participant row (no provenance) by its label alone", () => {
    expect(conditionLabel({ code: "poison", label: "中毒", severity: "harmful" })).toBe("中毒");
  });

  it("gives the plate variant its own hooks, a cap, and a +N tooltip instead of the disclosure", async () => {
    const w = mountChips({ conditions: manyConditions(5), variant: "plate", cap: 3 }, true);
    expect(w.find('[data-testid="status-panel__conditions"]').exists()).toBe(false);
    expect(w.find('[data-testid="figure-plate__conditions"]').exists()).toBe(true);
    expect(w.findAll(".chip:not(.more)")).toHaveLength(3);
    const more = w.get('[data-testid="figure-plate__condition-overflow"]');
    expect(more.text()).toBe("+2");
    expect(more.attributes("aria-expanded")).toBeUndefined();
    expect(more.attributes("aria-label")).toBe(`另有 2 個狀態：${manyConditions(5).slice(3).map(conditionLabel).join("；")}`);
    await more.trigger("click");
    expect(w.find('[data-testid="figure-plate__condition-disclosure"]').exists()).toBe(false);
    await more.trigger("focus");
    const tip = document.querySelector('[data-testid="figure-plate__condition-tooltip"]');
    expect([...tip.querySelectorAll(".detail-label")].map((n) => n.textContent)).toEqual(["狀態4", "狀態5"]);
    expect(more.attributes("aria-describedby")).toBe(tip.id);
    // Escape closes it and is consumed.
    const reached = [];
    const outer = (event) => reached.push(event.key);
    document.body.addEventListener("keydown", outer);
    try {
      await more.trigger("keydown", { key: "Escape" });
      expect(document.querySelector('[data-testid="figure-plate__condition-tooltip"]')).toBeNull();
      expect(reached).toEqual([]);
    } finally {
      document.body.removeEventListener("keydown", outer);
    }
  });

  it("shifts a tooltip left inside the viewport and flips it below an icon near the top", async () => {
    const rects = new Map();
    const original = Element.prototype.getBoundingClientRect;
    const spy = vi.spyOn(Element.prototype, "getBoundingClientRect").mockImplementation(function rect() {
      const r = rects.get(this.getAttribute("role") === "tooltip" ? "tip" : this.getAttribute("data-testid"));
      return r ? { ...r, x: r.left, y: r.top, right: r.left + r.width, bottom: r.top + r.height, toJSON() {} } : original.call(this);
    });
    try {
      const width = window.innerWidth;
      rects.set("tip", { left: 0, top: 0, width: 200, height: 60 });
      rects.set("figure-plate__condition--cond_0", { left: width - 30, top: 300, width: 24, height: 24 });
      rects.set("figure-plate__condition--cond_1", { left: 100, top: 20, width: 24, height: 24 });
      const w = mountChips({ conditions: manyConditions(2), variant: "plate" }, true);
      await w.get('[data-testid="figure-plate__condition--cond_0"]').trigger("mouseenter");
      await nextTick();
      await nextTick();
      let tip = document.querySelector('[data-testid="figure-plate__condition-tooltip"]');
      expect(parseFloat(tip.style.left)).toBe(width - 4 - 200);
      expect(tip.getAttribute("data-placement")).toBe("above");
      // The tick still points at the icon's centre.
      expect(parseFloat(tip.style.getPropertyValue("--tip-tick"))).toBe(width - 30 + 12 - (width - 204));
      await w.get('[data-testid="figure-plate__condition--cond_0"]').trigger("mouseleave");
      await w.get('[data-testid="figure-plate__condition--cond_1"]').trigger("mouseenter");
      await nextTick();
      await nextTick();
      tip = document.querySelector('[data-testid="figure-plate__condition-tooltip"]');
      expect(tip.getAttribute("data-placement")).toBe("below");
      expect(tip.style.top).toBe(`${20 + 24 + 6}px`);
      expect(tip.style.bottom).toBe("");
      expect(tip.classList.contains("condition-tip--below")).toBe(true);
    } finally {
      spy.mockRestore();
    }
  });

  it("closes on a window resize, and on a scroll only of the document or a container of the icon", async () => {
    const host = document.body.appendChild(document.createElement("div"));
    const log = document.body.appendChild(document.createElement("div"));
    const w = mount(ConditionChips, { attachTo: host, props: { conditions: manyConditions(2), variant: "plate" } });
    const icon = w.get('[data-testid="figure-plate__condition--cond_0"]');
    const tip = () => document.querySelector('[data-testid="figure-plate__condition-tooltip"]');
    await icon.trigger("mouseenter");
    log.dispatchEvent(new Event("scroll"));
    await nextTick();
    expect(tip()).not.toBeNull();
    host.dispatchEvent(new Event("scroll"));
    await nextTick();
    expect(tip()).toBeNull();
    await icon.trigger("mouseenter");
    window.dispatchEvent(new Event("resize"));
    await nextTick();
    expect(tip()).toBeNull();
    w.unmount();
  });

  it("lets a plate tooltip claim Escape wherever focus is, and only while open", async () => {
    const outside = document.body.appendChild(document.createElement("button"));
    const w = mountChips({ conditions: manyConditions(2), variant: "plate" }, true);
    const reached = [];
    const outer = (event) => reached.push(event.key);
    document.addEventListener("keydown", outer);
    try {
      outside.focus();
      await w.get('[data-testid="figure-plate__condition--cond_0"]').trigger("mouseenter");
      outside.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
      await nextTick();
      expect(document.querySelector('[data-testid="figure-plate__condition-tooltip"]')).toBeNull();
      expect(reached).toEqual([]);
      outside.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape", bubbles: true, cancelable: true }));
      expect(reached).toEqual(["Escape"]);
    } finally {
      document.removeEventListener("keydown", outer);
    }
  });
});
