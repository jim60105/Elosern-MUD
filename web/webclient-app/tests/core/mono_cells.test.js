import { describe, expect, it } from "vitest";
import { CELL_EM, ONE_CELL_RUNS, codePointCells, textCells } from "../../lib/mono_cells.js";
import manifest from "../../fonts/jimmonotc/codepoints.json";

// Monospace cell measure (webclient-map-label-cell-budget D1): one cell for a
// code point the bundled face draws narrow, two for everything else.
describe("mono_cells", () => {
  it("declares one cell as the manifest's Latin cell advance", () => {
    expect(CELL_EM).toBeCloseTo(manifest.cell_advance.advance / manifest.cell_advance.upem, 12);
  });

  it("counts code points the face draws narrow as one cell", () => {
    for (const ch of ["A", "z", "0", " ", "…", "─", "│"]) {
      expect(codePointCells(ch.codePointAt(0)), ch).toBe(1);
    }
  });

  it("counts CJK, fullwidth forms and symbols the face lacks as two cells", () => {
    for (const ch of ["中", "（", "）", "①", "★", "℃", "　", "𠮷"]) {
      expect(codePointCells(ch.codePointAt(0)), ch).toBe(2);
    }
  });

  it("sums per code point, not per UTF-16 unit", () => {
    expect(textCells("霧骨渡口…")).toBe(9);
    expect(textCells("北門 Gate")).toBe(9);
    expect(textCells("𠮷野")).toBe(4);
    expect(textCells("")).toBe(0);
    expect(textCells(null)).toBe(0);
  });

  it("keeps the generated runs sorted and disjoint", () => {
    for (let i = 0; i < ONE_CELL_RUNS.length; i += 1) {
      const [lo, hi] = ONE_CELL_RUNS[i];
      expect(lo).toBeLessThanOrEqual(hi);
      if (i > 0) expect(lo).toBeGreaterThan(ONE_CELL_RUNS[i - 1][1] + 1);
    }
  });
});
