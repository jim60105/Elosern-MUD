// webclient-frontend-utils: the ONE condition label rule extracted from
// ConditionChips.vue and CharacterStatusDrawer.vue. The accessible chip name
// and the drawer roster prose MUST agree — this util now guards the single
// copy: label (or code fallback), the verbatim remaining duration (only when
// the payload supplies numeric `remaining_seconds`), every derived modifier
// pair, joined with `，`.

import { describe, expect, it } from "vitest";
import { conditionLabel } from "../../lib/condition_label.js";

function condition(overrides = {}) {
  return { label: "烈風", code: "gale", ...overrides };
}

describe("conditionLabel", () => {
  it("falls back to the condition code when no label is supplied", () => {
    expect(conditionLabel(condition({ label: null }))).toBe("gale");
    expect(conditionLabel(condition({ label: undefined }))).toBe("gale");
  });

  it("uses the label when supplied and appends the remaining seconds only for a numeric duration", () => {
    expect(conditionLabel(condition({ remaining_seconds: 60 }))).toBe("烈風，剩 60 秒");
    expect(conditionLabel(condition({ remaining_seconds: "60" }))).toBe("烈風");
    expect(conditionLabel(condition({ remaining_seconds: null }))).toBe("烈風");
  });

  it("appends every derived modifier pair in insertion order", () => {
    expect(conditionLabel(condition({ modifiers: { atk: "+3" } }))).toBe("烈風，atk +3");
    expect(conditionLabel(condition({ modifiers: { atk: "+3", def: "-2" } }))).toBe(
      "烈風，atk +3，def -2",
    );
  });

  it("joins the label, duration, and modifier parts with the `，` separator", () => {
    expect(conditionLabel(condition({ remaining_seconds: 5, modifiers: { spd: "×2" } }))).toBe(
      "烈風，剩 5 秒，spd ×2",
    );
  });
});
