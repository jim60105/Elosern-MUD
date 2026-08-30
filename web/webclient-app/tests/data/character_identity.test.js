import { describe, expect, it } from "vitest";
import { formatCopper, portraitGlyph } from "../../components/character-identity.js";

// H2 (webclient-hud-02-status-islands), design D3. The duplicated magic-rank
// band table and ``magicRankTitle()`` are deleted (magic-power-static-rename):
// the retired magic-rank ladder named the XP system being removed, so the head
// card carries no magic-derived rank word and no client-side table remains to
// pin against ``world/rules/progression.py``.

describe("character-identity (H2 head-card derivations)", () => {
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
