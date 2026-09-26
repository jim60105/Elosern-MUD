// webclient-scene-transitions (design D3/D7): the minimap's FLIP pan offset.
// `panOffset` anchors the previous current node on the screen point where it
// stood, expressed in the new drawing's user units.
import { describe, expect, it } from "vitest";
import { fromScreen, panOffset, toScreen } from "../lib/map_pan.js";

const SQUARE = { width: 208, height: 208 };

function frame(pos, viewBox, size = SQUARE) {
  return { pos, viewBox, size };
}

describe("panOffset", () => {
  it("the same viewBox gives the plain position delta", () => {
    const vb = { x: 0, y: 0, width: 208, height: 208 };
    const offset = panOffset(frame({ x: 104, y: 104 }, vb), frame({ x: 144, y: 104 }, vb));
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
    const vb = { x: 0, y: 0, width: 208, height: 208 };
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
    // The old centre (104px on screen) back in the new units, minus the new
    // position: 104 / (208 / 360) - 210.
    expect(offset.dx).toBeCloseTo(104 * (360 / 208) - 210, 6);
    expect(offset.dy).toBeCloseTo(104 * (360 / 208) - 150, 6);
  });

  it("honours the meet letterbox of a non-square viewBox", () => {
    const vb = { x: 0, y: 0, width: 400, height: 200 };
    const point = toScreen(frame(null, vb), { x: 200, y: 100 });
    // Scale 0.52, the 200-unit height letterboxed to 104px, centred in 208.
    expect(point.x).toBeCloseTo(104, 6);
    expect(point.y).toBeCloseTo(104, 6);
    const back = fromScreen(frame(null, vb), point);
    expect(back.x).toBeCloseTo(200, 6);
    expect(back.y).toBeCloseTo(100, 6);
  });
});
