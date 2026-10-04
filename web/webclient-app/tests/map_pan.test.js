// webclient-scene-transitions (design D3/D7): the minimap's FLIP pan offset.
// `panOffset` anchors the previous current node on the screen point where it
// stood, expressed in the new drawing's user units.
import { describe, expect, it } from "vitest";
import { fromScreen, panOffset, toScreen } from "../lib/map_pan.js";

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
