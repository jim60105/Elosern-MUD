import { describe, expect, it } from "vitest";
import { LOW_HP_THRESHOLD, gaugeRatio, isLowHp } from "../../components/vitals.js";

// H2 (webclient-hud-02-status-islands), design D4/D5: the vitals
// presentation derivations. The 25% low-HP threshold is a presentation
// constant (no server field expresses "low health"), and the trailing (ghost)
// bar rule holds only previously committed ratios of the same gauge.

describe("vitals (H2 presentation derivations)", () => {
  it("computes the per-gauge ratio in percent", () => {
    expect(gaugeRatio({ current: 231, maximum: 405 })).toBeCloseTo(57.04, 1);
    expect(gaugeRatio({ current: 139, maximum: 420 })).toBeCloseTo(33.1, 1);
    expect(gaugeRatio({ current: 68, maximum: 68 })).toBe(100);
  });

  it("yields null for a missing or malformed gauge and 0 for a non-positive maximum", () => {
    expect(gaugeRatio(null)).toBeNull();
    expect(gaugeRatio({})).toBeNull();
    expect(gaugeRatio({ current: 5, maximum: 0 })).toBe(0);
    expect(gaugeRatio({ current: 5, maximum: -1 })).toBe(0);
  });

  it("derives the low-HP state from the hp ratio against the 25% threshold", () => {
    expect(LOW_HP_THRESHOLD).toBe(0.25);
    // At or below the threshold → low.
    expect(
      isLowHp({ hp: { current: 100, maximum: 405 } }),
    ).toBe(true); // 24.69%
    // Exactly at the threshold (102/408 = 25%) is low; just above it is not.
    expect(
      isLowHp({ hp: { current: 102, maximum: 408 } }),
    ).toBe(true);
    expect(
      isLowHp({ hp: { current: 103, maximum: 408 } }),
    ).toBe(false);
    // An unavailable or absent resources object is not low HP by default.
    expect(isLowHp(null)).toBe(false);
    expect(isLowHp({})).toBe(false);
  });
});
