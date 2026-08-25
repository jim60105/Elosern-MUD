import { describe, expect, it } from "vitest";
import {
  MAGIC_RANK_BANDS,
  formatCopper,
  magicRankTitle,
  portraitGlyph,
} from "../../components/character-identity.js";

// H2 (webclient-hud-02-status-islands), design D3: the duplicated display
// rank-band table must match `world/rules/progression.py::MAGIC_RANK_BANDS`
// (學徒 0–15 / 術師 16–30 / 大師 31–70 / 賢者 71–90 / 主宰 90+), scanned in
// order, so level 90 resolves to 賢者 exactly as the server's own comment
// requires.

describe("character-identity (H2 head-card derivations)", () => {
  it("pins every band boundary of the duplicated rank table", () => {
    expect(magicRankTitle(0)).toBe("學徒");
    expect(magicRankTitle(15)).toBe("學徒");
    expect(magicRankTitle(16)).toBe("術師");
    expect(magicRankTitle(30)).toBe("術師");
    expect(magicRankTitle(31)).toBe("大師");
    expect(magicRankTitle(70)).toBe("大師");
    expect(magicRankTitle(71)).toBe("賢者");
    expect(magicRankTitle(95)).toBe("主宰");
  });

  it("resolves the 90 edge to 賢者 (the in-order scan, not 主宰)", () => {
    expect(magicRankTitle(90)).toBe("賢者");
  });

  it("handles non-numeric levels", () => {
    expect(magicRankTitle(null)).toBe("未知");
    expect(magicRankTitle(undefined)).toBe("未知");
    expect(magicRankTitle("x")).toBe("未知");
  });

  it("rejects numeric coercions of booleans and blank strings", () => {
    // Number(true) === 1 and Number(" ") === 0 would otherwise coerce a
    // boolean or blank input into a real rank; both must read 未知.
    expect(magicRankTitle(true)).toBe("未知");
    expect(magicRankTitle(false)).toBe("未知");
    expect(magicRankTitle("   ")).toBe("未知");
    // Numeric edges still resolve: 0 is a valid 學徒 level, negative
    // levels read 未知 (no band starts below 0), and 95 is 主宰.
    expect(magicRankTitle(0)).toBe("學徒");
    expect(magicRankTitle(-1)).toBe("未知");
  });

  it("keeps the table's bands and ranges intact", () => {
    expect(MAGIC_RANK_BANDS).toEqual([
      { title: "學徒", lower: 0, upper: 15 },
      { title: "術師", lower: 16, upper: 30 },
      { title: "大師", lower: 31, upper: 70 },
      { title: "賢者", lower: 71, upper: 90 },
      { title: "主宰", lower: 90, upper: null },
    ]);
  });

  it("formats integer copper with thousands separators only", () => {
    expect(formatCopper(3240)).toBe("3,240");
    expect(formatCopper(0)).toBe("0");
    expect(formatCopper(123456)).toBe("123,456");
    expect(formatCopper(-5)).toBe("0");
    expect(formatCopper(null)).toBe("0");
  });

  it("derives the portrait glyph as the first grapheme of the display name", () => {
    expect(portraitGlyph("艾倫·灰誓")).toBe("艾");
    expect(portraitGlyph("")).toBe("");
    expect(portraitGlyph(null)).toBe("");
    expect(portraitGlyph(undefined)).toBe("");
  });

  it("segregates ZWJ / combining sequences as single graphemes", () => {
    // A ZWJ sequence (family emoji style) must yield one grapheme, not a
    // stray code point.
    const family = "\u2764\uFE0F";
    expect(portraitGlyph(family)).toBe(family);
  });
});
