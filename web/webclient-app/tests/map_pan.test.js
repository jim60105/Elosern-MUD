// webclient-scene-transitions (design D3/D7): the minimap's FLIP pan offset.
// `panOffset` anchors the previous current node on the screen point where it
// stood, expressed in the new drawing's user units.
import { describe, expect, it } from "vitest";
import { fromScreen, islandMotion, panOffset, scaleKey, toScreen } from "../lib/map_pan.js";

// The island's fixed canvas square at the 1451x790 reference
// (retarget-desktop-viewport-contract D7).
const SQUARE = { width: 240, height: 240 };

function frame(pos, viewBox, size = SQUARE) {
  return { pos, viewBox, size };
}

describe("panOffset", () => {
  it("the same viewBox gives the plain position delta", () => {
    const vb = { x: 0, y: 0, width: 240, height: 240 };
    const offset = panOffset(frame({ x: 120, y: 120 }, vb), frame({ x: 160, y: 120 }, vb));
    expect(offset.dx).toBeCloseTo(-40, 6);
    expect(offset.dy).toBeCloseTo(0, 6);
  });

  it("a changed viewBox origin and size anchors the node on its old screen point", () => {
    const prev = frame({ x: 150, y: 90 }, { x: 40, y: 20, width: 200, height: 200 });
    const next = frame({ x: 300, y: 260 }, { x: 180, y: 160, width: 260, height: 260 });
    const offset = panOffset(prev, next);
    const startScreen = toScreen(next, { x: next.pos.x + offset.dx, y: next.pos.y + offset.dy });
    const oldScreen = toScreen(prev, prev.pos);
    expect(startScreen.x).toBeCloseTo(oldScreen.x, 6);
    expect(startScreen.y).toBeCloseTo(oldScreen.y, 6);
  });

  it("returns null when the node is missing from either placement", () => {
    const vb = { x: 0, y: 0, width: 240, height: 240 };
    expect(panOffset(frame({ x: 10, y: 10 }, vb), frame(null, vb))).toBeNull();
    expect(panOffset(null, frame({ x: 10, y: 10 }, vb))).toBeNull();
    expect(panOffset(frame({ x: 10, y: 10 }, { ...vb, width: 0 }), frame({ x: 10, y: 10 }, vb))).toBeNull();
  });

  it("the graph variant's recentred placement maps the old screen position into the new units", () => {
    // Graph: `current` is always at the drawing's centre. The previous
    // current node (at the centre before) now sits one ring out.
    const prev = frame({ x: 150, y: 150 }, { x: 0, y: 0, width: 300, height: 300 });
    const next = frame({ x: 210, y: 150 }, { x: 0, y: 0, width: 360, height: 360 });
    const offset = panOffset(prev, next);
    // The old centre (120px on screen) back in the new units, minus the new
    // position: 120 / (240 / 360) - 210.
    expect(offset.dx).toBeCloseTo(120 * (360 / 240) - 210, 6);
    expect(offset.dy).toBeCloseTo(120 * (360 / 240) - 150, 6);
  });

  it("honours the meet letterbox of a non-square viewBox", () => {
    const vb = { x: 0, y: 0, width: 400, height: 200 };
    const point = toScreen(frame(null, vb), { x: 200, y: 100 });
    // Scale 0.6, the 200-unit height letterboxed to 120px, centred in 240.
    expect(point.x).toBeCloseTo(120, 6);
    expect(point.y).toBeCloseTo(120, 6);
    const back = fromScreen(frame(null, vb), point);
    expect(back.x).toBeCloseTo(200, 6);
    expect(back.y).toBeCloseTo(100, 6);
  });
});

// animate-minimap-scale-transitions (approved minimap auto-scale design §6.5):
// the FLIP pan assumes one scale before and after; a changed island mode or
// level crossfades at full and switches at once at reduced/off.
describe("scaleKey", () => {
  it("folds an island projection's mode and level into one key", () => {
    expect(scaleKey({ mode: "uniform", level: 1500 })).toBe("uniform:1500");
    expect(scaleKey({ mode: "compressed", level: 1500 })).toBe("compressed:1500");
  });

  it("has no key without an island projection", () => {
    expect(scaleKey(null)).toBeNull();
    expect(scaleKey(undefined)).toBeNull();
    expect(scaleKey({ mode: "uniform" })).toBeNull();
    expect(scaleKey({ mode: "uniform", level: Number.NaN })).toBeNull();
  });
});

describe("islandMotion", () => {
  const step = { previousId: "a", nextId: "b" };

  it("pans an unchanged mode and level at full and reduced, and stays still at off", () => {
    const same = { ...step, previousScale: "uniform:1500", nextScale: "uniform:1500" };
    expect(islandMotion({ ...same, motionLevel: "full" })).toBe("pan");
    // Reduced keeps the existing pan path, whose travel token is 0.
    expect(islandMotion({ ...same, motionLevel: "reduced" })).toBe("pan");
    expect(islandMotion({ ...same, motionLevel: "off" })).toBe("none");
  });

  it("crossfades a changed level or mode only at full and switches at once otherwise", () => {
    for (const [previousScale, nextScale] of [
      ["uniform:1500", "uniform:2000"],
      ["compressed:1500", "uniform:1500"],
      ["uniform:300", "compressed:300"],
    ]) {
      const changed = { ...step, previousScale, nextScale };
      expect(islandMotion({ ...changed, motionLevel: "full" })).toBe("crossfade");
      expect(islandMotion({ ...changed, motionLevel: "reduced" })).toBe("switch");
      expect(islandMotion({ ...changed, motionLevel: "off" })).toBe("switch");
    }
  });

  it("compares the scale even when the current node is unchanged", () => {
    const replacement = { previousId: "a", nextId: "a", previousScale: "uniform:1500", nextScale: "uniform:2000" };
    expect(islandMotion({ ...replacement, motionLevel: "full" })).toBe("crossfade");
    expect(islandMotion({ ...replacement, motionLevel: "reduced" })).toBe("switch");
    expect(islandMotion({ ...replacement, previousScale: "uniform:2000", motionLevel: "full" })).toBe("none");
  });

  it("keeps the immediate no-shared-frame path without a previous node or island scale", () => {
    expect(islandMotion({ previousId: null, nextId: "b", previousScale: null, nextScale: "uniform:1500", motionLevel: "full" })).toBe(
      "none",
    );
    // Arriving from a coordinate-free layer: no previous scale, so no crossfade.
    expect(islandMotion({ ...step, previousScale: null, nextScale: "uniform:1500", motionLevel: "full" })).toBe("pan");
    // The radial graph and the overlay carry no island scale: their pan is unchanged.
    expect(islandMotion({ ...step, previousScale: null, nextScale: null, motionLevel: "full" })).toBe("pan");
    expect(islandMotion({ ...step, previousScale: null, nextScale: null, motionLevel: "off" })).toBe("none");
  });
});
