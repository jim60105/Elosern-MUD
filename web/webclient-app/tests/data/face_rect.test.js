import { describe, expect, it } from "vitest";
import { faceObjectPosition } from "../../components/face-rect.js";

describe("faceObjectPosition (gallery face_rect → object-position)", () => {
  it("maps the rect center to the object-position pair", () => {
    expect(faceObjectPosition({ x: 0.25, y: 0.06, w: 0.5, h: 0.5 })).toBe("50% 31%");
    expect(faceObjectPosition({ x: 0.3, y: 0.1, w: 0.4, h: 0.4 })).toBe("50% 30%");
    expect(faceObjectPosition({ x: 0, y: 0, w: 1, h: 1 })).toBe("50% 50%");
  });

  it("defaults to the centered crop for null, non-finite, or malformed rects", () => {
    expect(faceObjectPosition(null)).toBe("50% 50%");
    expect(faceObjectPosition(undefined)).toBe("50% 50%");
    expect(faceObjectPosition({ x: Number.NaN, y: 0, w: 0.5, h: 0.5 })).toBe("50% 50%");
    expect(faceObjectPosition({ x: -0.1, y: 0, w: 0.5, h: 0.5 })).toBe("50% 50%");
    expect(faceObjectPosition({ x: 0.6, y: 0, w: 0.5, h: 0.5 })).toBe("50% 50%");
    expect(faceObjectPosition({ x: 0, y: 0, w: 0, h: 0.5 })).toBe("50% 50%");
    expect(faceObjectPosition({ x: 0, y: 0.6, w: 0.5, h: 0.5 })).toBe("50% 50%");
  });

  it("pins the boundary rounding tolerance at the rect edge", () => {
    // A center of 0.999995 serializes as 100%: the maximum rounding
    // displacement is 0.005 percentage points for a well-formed rect.
    expect(faceObjectPosition({ x: 0, y: 0.99999, w: 0.00002, h: 0.00001 })).toBe("0% 100%");
  });
});
