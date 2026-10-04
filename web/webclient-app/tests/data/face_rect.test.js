import { describe, expect, it } from "vitest";
import { faceCropStyle, faceObjectPosition } from "../../components/face-rect.js";

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

describe("faceCropStyle (small-avatar face_rect → zoom crop)", () => {
  it("enlarges the image to 1/w × 1/h and anchors it at the rect origin", () => {
    // w = h = 0.4 → a 2.5× enlargement; the anchors are -x·(1/w) and -y·(1/h),
    // so the rect's own image region lands on the frame's box.
    expect(faceCropStyle({ x: 0.3, y: 0.1, w: 0.4, h: 0.4 })).toEqual({
      width: "250%",
      height: "250%",
      left: "-75%",
      top: "-25%",
      objectPosition: "50% 50%",
    });
  });

  it("anchors an off-center rect by its own origin, not the image center", () => {
    // Mandatory asymmetric fixture: every other repo fixture is horizontally
    // centered, so only an off-center rect separates this anchoring from the
    // wrong center-based formula.
    expect(faceCropStyle({ x: 0.6, y: 0.1, w: 0.2, h: 0.2 })).toEqual({
      width: "500%",
      height: "500%",
      left: "-300%",
      top: "-50%",
      objectPosition: "50% 50%",
    });
  });

  it("zooms a whole-image rect to identity", () => {
    expect(faceCropStyle({ x: 0, y: 0, w: 1, h: 1 })).toEqual({
      width: "100%",
      height: "100%",
      left: "0%",
      top: "0%",
      objectPosition: "50% 50%",
    });
  });

  it("clamps the enlargement at 8× per axis and anchors from the clamped factor", () => {
    // 1/0.02 == 50 clamps to the 8× cap on both axes; the anchors stay
    // derived from the clamped factor so the window remains coherent.
    expect(faceCropStyle({ x: 0.49, y: 0.49, w: 0.02, h: 0.02 })).toEqual({
      width: "800%",
      height: "800%",
      left: "-392%",
      top: "-392%",
      objectPosition: "50% 50%",
    });
    // Mixed axes: 1/0.1 == 10 clamps to 800%, 1/0.2 == 5 stays at 500%.
    expect(faceCropStyle({ x: 0.1, y: 0.1, w: 0.1, h: 0.2 })).toEqual({
      width: "800%",
      height: "500%",
      left: "-80%",
      top: "-50%",
      objectPosition: "50% 50%",
    });
    // w == 1/8 sits exactly on the cap and is not clamped down.
    expect(faceCropStyle({ x: 0, y: 0, w: 0.125, h: 0.125 })).toEqual({
      width: "800%",
      height: "800%",
      left: "0%",
      top: "0%",
      objectPosition: "50% 50%",
    });
  });

  it("returns only the caller's centered fallback for every rejected rect", () => {
    const rejected = [
      null,
      undefined,
      { x: Number.NaN, y: 0, w: 0.5, h: 0.5 },
      { x: Number.POSITIVE_INFINITY, y: 0, w: 0.5, h: 0.5 },
      { x: "0.1", y: 0, w: 0.5, h: 0.5 },
      { x: -0.1, y: 0, w: 0.5, h: 0.5 },
      { x: 1.1, y: 0, w: 0.5, h: 0.5 },
      { x: 0.6, y: 0, w: 0.5, h: 0.5 },
      { x: 0, y: 0.6, w: 0.5, h: 0.5 },
      { x: 0, y: 0, w: 0, h: 0.5 },
      { x: 0, y: 0, w: 0.5, h: 0 },
      { x: 0, y: 0, w: -0.5, h: 0.5 },
      { x: 0, y: 0, h: 0.5 },
    ];
    for (const rect of rejected) {
      // Exact object equality: a rejected rect must carry no zoom property.
      expect(faceCropStyle(rect, "50% 30%")).toEqual({ objectPosition: "50% 30%" });
      expect(faceCropStyle(rect)).toEqual({ objectPosition: "50% 50%" });
    }
  });
});
