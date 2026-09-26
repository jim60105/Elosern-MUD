// webclient-motion-level (design D1/D10): the pure motion-level resolver.
//
// The store is the only resolver (design D1): it calls `resolveMotionLevel`
// once per apply and writes the effective level to `<html data-motion>`. This
// test pins the whole truth table — every stored level against both operating
// system states, the unset state, and an invalid stored value.
import { describe, expect, it } from "vitest";

import { MOTION_LEVELS, resolveMotionLevel } from "../lib/motion_level.js";

describe("motion level resolver", () => {
  it("names exactly the three levels, full first", () => {
    expect(MOTION_LEVELS).toEqual(["full", "reduced", "off"]);
  });

  it("returns the stored level when one is stored, whatever the OS requests", () => {
    for (const stored of MOTION_LEVELS) {
      for (const osRequestsReduce of [true, false]) {
        expect(resolveMotionLevel(stored, osRequestsReduce)).toBe(stored);
      }
    }
  });

  it("follows the operating system while nothing is stored", () => {
    expect(resolveMotionLevel(null, true)).toBe("reduced");
    expect(resolveMotionLevel(null, false)).toBe("full");
    // No `matchMedia` (jsdom with no mock) reports no reduce request.
    expect(resolveMotionLevel(null, false)).toBe("full");
  });

  it("treats a stored value outside the three levels as nothing stored", () => {
    for (const stored of ["dim", "FULL", "On", 1, true, "", undefined, {}]) {
      expect(resolveMotionLevel(stored, true)).toBe("reduced");
      expect(resolveMotionLevel(stored, false)).toBe("full");
    }
  });

  it("resolves every stored x OS combination to one of the three levels", () => {
    for (const stored of [null, ...MOTION_LEVELS, "dim"]) {
      for (const osRequestsReduce of [true, false]) {
        expect(MOTION_LEVELS).toContain(resolveMotionLevel(stored, osRequestsReduce));
      }
    }
  });
});
