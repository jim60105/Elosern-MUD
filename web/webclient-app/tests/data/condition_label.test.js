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

  it("names known modifier keys, gives unknown keys a neutral name, and keeps every value verbatim", () => {
    // Known rulebook keys read in the game's stat vocabulary; an unknown key
    // (or one that only exists on Object.prototype) keeps its value under the
    // neutral 其他修正, and no sign, unit or digit is added or dropped.
    expect(
      conditionLabel(
        condition({
          modifiers: { agility: "-10%", accuracy: -15, actions_per_turn: 0, t_unknown: 0.25, constructor: "+1" },
        }),
      ),
    ).toBe("烈風，敏捷 -10%，準度 -15，每回合行動 0，其他修正 0.25，其他修正 +1");
  });

  it("joins the label, duration, and modifier parts with the `，` separator", () => {
    expect(conditionLabel(condition({ remaining_seconds: 5, modifiers: { heal_gain: "+10%" } }))).toBe(
      "烈風，剩 5 秒，治療量 +10%",
    );
  });
});
