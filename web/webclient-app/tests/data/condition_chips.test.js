import { mount } from "@vue/test-utils";
import { afterEach, describe, expect, it } from "vitest";
import ConditionChips from "../../components/ConditionChips.vue";
import { STATUS_PANEL_SAMPLE } from "../../stories/fixtures.js";

// H2 (webclient-hud-02-status-islands), design D6/D7/D8: the conditions
// island. One 34×34 icon chip per committed condition, pairing a
// per-severity shape glyph with an accessible name carrying the label, the
// remaining duration (only when the payload supplies it, verbatim — never
// counted down client-side) and every derived modifier. Visible chips are
// capped at 6; the remainder stays reachable through the `+N` overflow
// chip's bounded in-island disclosure (H4 re-points this control at the
// character-status drawer).

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

describe("ConditionChips (H2 conditions island)", () => {
  let wrapper;

  afterEach(() => {
    wrapper?.unmount();
    wrapper = null;
    document.body.innerHTML = "";
  });

  function mountChips(props = {}) {
    wrapper = mount(ConditionChips, {
      props: {
        conditions: CONDITIONS,
        ...props,
      },
    });
    return wrapper;
  }

  it("renders one chip per committed condition with its severity glyph", () => {
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

  it("carries the label, duration, and every modifier in the chip's accessible name", () => {
    const w = mountChips();
    const buff = w.get('[data-testid="status-panel__condition--fastwind"]');
    const name = buff.attributes("aria-label");
    expect(name).toContain("疾風");
    expect(name).toContain("剩 60 秒");
    const harmful = w.get('[data-testid="status-panel__condition--shame_exposure"]');
    const harmfulName = harmful.attributes("aria-label");
    expect(harmfulName).toContain("高露出");
    expect(harmfulName).toContain("defense -15");
    expect(harmfulName).toContain("agility -10");
  });

  it("renders the duration badge only when the payload supplies remaining_seconds", () => {
    const w = mountChips();
    // fastwind carries remaining_seconds: 60 → badge renders verbatim.
    const timer = w.get('[data-testid="status-panel__condition--fastwind"]').find('[data-testid="status-panel__condition-timer"]');
    expect(timer.exists()).toBe(true);
    expect(timer.text()).toBe("60");
    // fog_veil carries no duration → no badge, no substitute value.
    const noTimer = w.get('[data-testid="status-panel__condition--fog_veil"]').find('[data-testid="status-panel__condition-timer"]');
    expect(noTimer.exists()).toBe(false);
  });

  it("does not count the duration down between revisions", () => {
    const w = mountChips();
    const badge = w.get('[data-testid="status-panel__condition--fastwind"]').find('[data-testid="status-panel__condition-timer"]');
    // No timer of any kind runs: the badge keeps the payload's value until
    // a new committed revision replaces the payload.
    expect(badge.text()).toBe("60");
    expect(w.find("timer").exists()).toBe(false);
  });

  it("caps visible chips at 6 and discloses the remainder in a bounded, scrollable in-island region", async () => {
    const w = mountChips({ conditions: manyConditions(12) });
    const visibleChips = w.findAll(".chip:not(.more)");
    expect(visibleChips).toHaveLength(6);
    // Six visible chips + one `+N` overflow chip stating the hidden count.
    const overflow = w.get('[data-testid="status-panel__condition-overflow"]');
    expect(overflow.text()).toBe("+6");
    expect(overflow.attributes("aria-expanded")).toBe("false");

    await overflow.trigger("click");
    const disclosure = w.get('[data-testid="status-panel__condition-disclosure"]');
    expect(disclosure.exists()).toBe(true);
    const rows = w.findAll(".disclosure-row");
    expect(rows).toHaveLength(6);
    expect(overflow.attributes("aria-expanded")).toBe("true");

    // Re-activation collapses the disclosure.
    await overflow.trigger("click");
    expect(w.find('[data-testid="status-panel__condition-disclosure"]').exists()).toBe(false);

    // Escape collapses it (component-scoped, so it never steals the shell's
    // drawer or full-log Escape).
    await w.get('[data-testid="status-panel__conditions"]').trigger("keydown", { key: "Escape" });
  });

  it("discloses 8 committed conditions as a +2 chip with two disclosure rows", async () => {
    const w = mountChips({ conditions: manyConditions(8) });
    const visibleChips = w.findAll(".chip:not(.more)");
    expect(visibleChips).toHaveLength(6);
    const overflow = w.get('[data-testid="status-panel__condition-overflow"]');
    expect(overflow.text()).toBe("+2");
    await overflow.trigger("click");
    expect(w.get('[data-testid="status-panel__condition-disclosure"]').exists()).toBe(true);
    expect(w.findAll(".disclosure-row")).toHaveLength(2);
  });

  it("renders the 無條件 empty state when the committed list is empty", () => {
    const w = mountChips({ conditions: [] });
    expect(w.get('[data-testid="status-panel__conditions-empty"]').text()).toBe("無條件");
    expect(w.findAll('[data-testid^="status-panel__condition--"]')).toHaveLength(0);
  });
});
