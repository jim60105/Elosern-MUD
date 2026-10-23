import { describe, expect, it } from "vitest";
import { fitMarkerName } from "../../composables/use-map-lattice-render.js";
import { textCells } from "../../lib/mono_cells.js";

// Edge-marker name fit in cells (webclient-map-label-cell-budget D3).
describe("fitMarkerName", () => {
  const oneStep = () => 1;

  it("draws a name whole when its cells equal the budget, and fits it one below", () => {
    expect(fitMarkerName("北門 Gate", 9)).toBe("北門 Gate");
    const fitted = fitMarkerName("北門 Gate", 8);
    expect(fitted).toBe("北… Gate");
    expect(textCells(fitted)).toBeLessThanOrEqual(8);
  });

  it("keeps a qualifier and truncates the head in cells", () => {
    expect(fitMarkerName("西部丘陵與谷地（南門）", 14)).toBe("西部…（南門）");
    expect(fitMarkerName("西部丘陵與谷地（南門）", 11)).toBe("西…（南門）");
    // One cell short of a wide head before the qualifier: the qualifier path
    // yields nothing and the head-and-tail form takes over.
    expect(fitMarkerName("西部丘陵與谷地（南門）", 10)).toBe("西…南門）");
  });

  it("treats a qualifier-only name as an ordinary head and tail", () => {
    expect(fitMarkerName("（南門）", 8)).toBe("（南門）");
    expect(fitMarkerName("（南門）", 7)).toBe("（…門）");
  });

  it("matches the old glyph fit for all-wide names at a 2g-cell budget", () => {
    const label = "灰鬮荒原第一南關隘道前哨站營";
    for (let g = 3; g < Array.from(label).length; g += 1) {
      const chars = Array.from(label);
      const old = chars[0] + "…" + chars.slice(chars.length - (g - 2)).join("");
      expect(fitMarkerName(label, 2 * g), `g=${g}`).toBe(old);
    }
  });

  it("fills an odd budget with a narrow head glyph when one fits", () => {
    const fitted = fitMarkerName("Old北門Gate", 9);
    expect(textCells(fitted)).toBeLessThanOrEqual(9);
    expect(fitted).toBe("Ol…門Gate");
  });

  it("drops the name when no head, ellipsis and tail fit", () => {
    expect(fitMarkerName("地圖甲", 4)).toBe("");
    expect(fitMarkerName("地圖甲", 2)).toBe("");
  });

  it("counts one step per glyph for a vertical stack", () => {
    expect(fitMarkerName("西部丘陵與谷地（南門）", 11, oneStep)).toBe("西部丘陵與谷地（南門）");
    expect(fitMarkerName("西部丘陵與谷地（南門）", 8, oneStep)).toBe("西部丘…（南門）");
  });

  it("holds eleven wide glyphs in a 22-cell budget and truncates twelve", () => {
    expect(fitMarkerName("灰鬮荒原第一南關隘道前", 22)).toBe("灰鬮荒原第一南關隘道前");
    const twelve = fitMarkerName("灰鬮荒原第一南關隘道前哨", 22);
    expect(twelve).toBe("灰…原第一南關隘道前哨");
    expect(textCells(twelve)).toBeLessThanOrEqual(22);
  });
});
