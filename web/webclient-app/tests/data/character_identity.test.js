import { describe, expect, it } from "vitest";
import {
  EMPTY_NAME_GLYPH,
  formatCopper,
  portraitGlyph,
} from "../../components/character-identity.js";

// H2 (webclient-hud-02-status-islands), design D3. The duplicated magic-rank
// band table and ``magicRankTitle()`` are deleted (magic-power-static-rename):
// the retired magic-rank ladder named the XP system being removed, so the head
// card carries no magic-derived rank word and no client-side table remains to
// pin against ``world/rules/progression.py``.
//
// unified-avatar-rendering owns the grapheme policy now: the shared text-initial
// helper trims the displayed name, keeps whole grapheme clusters (Intl.Segmenter
// at granularity "grapheme") and renders a neutral symbol for an empty name.

describe("character-identity (shared text-initial derivations)", () => {
  it("formats integer copper with thousands separators only", () => {
    expect(formatCopper(3240)).toBe("3,240");
    expect(formatCopper(0)).toBe("0");
    expect(formatCopper(123456)).toBe("123,456");
    expect(formatCopper(-5)).toBe("0");
    expect(formatCopper(null)).toBe("0");
  });

  it("derives the initial as the first grapheme of the trimmed name", () => {
    // The defect this detects: an untrimmed leading space would make the
    // initial a blank/space character instead of the name's own first glyph.
    expect(portraitGlyph("艾倫‧灰誓")).toBe("艾");
    expect(portraitGlyph("  艾倫")).toBe("艾");
    expect(portraitGlyph("𠮟婆婆")).toBe("𠮟");
  });

  it("renders the neutral symbol for an empty or whitespace-only name", () => {
    // The defect: a blank tile where an unidentified subject stands.
    expect(EMPTY_NAME_GLYPH).not.toBe("");
    expect(portraitGlyph("")).toBe(EMPTY_NAME_GLYPH);
    expect(portraitGlyph("   ")).toBe(EMPTY_NAME_GLYPH);
    expect(portraitGlyph("\n\t ")).toBe(EMPTY_NAME_GLYPH);
    expect(portraitGlyph(null)).toBe(EMPTY_NAME_GLYPH);
    expect(portraitGlyph(undefined)).toBe(EMPTY_NAME_GLYPH);
  });

  it("keeps combining, ZWJ, flag and variation sequences whole", () => {
    // Each expectation is the whole cluster the source string starts with: a
    // code-unit or code-point split would return only its first element.
    const combining = "\u0045\u0301\u0300"; // E + two combining accents
    expect(portraitGlyph(combining)).toBe("\u0045\u0301\u0300");
    const zwj = "\u{1F469}\u200D\u{1F4BB}"; // woman technologist
    expect(portraitGlyph(zwj)).toBe(zwj);
    const family = "\u2764\uFE0F"; // heart + variation selector
    expect(portraitGlyph(family)).toBe(family);
    const flag = "\u{1F1F9}\u{1F1FC}"; // regional-indicator pair (Taiwan)
    expect(portraitGlyph(flag)).toBe(flag);
    const tone = "\u{1F44D}\u{1F3FD}"; // thumbs up + skin-tone modifier
    expect(portraitGlyph(tone)).toBe(tone);
  });

  it("never emits an isolated surrogate when Intl.Segmenter is unavailable", () => {
    const original = Intl.Segmenter;
    // A runtime without the standard API: the helper keeps whole code points,
    // so an astral character is never half a surrogate pair.
    // eslint-disable-next-line no-param-reassign
    Intl.Segmenter = undefined;
    try {
      expect(portraitGlyph("𠮟婆婆")).toBe("𠮟");
      expect(portraitGlyph("艾倫")).toBe("艾");
      expect(portraitGlyph("  ")).toBe(EMPTY_NAME_GLYPH);
      const glyph = portraitGlyph("𠮟");
      expect(glyph.length).toBe(2);
      expect(glyph.charCodeAt(0)).toBeGreaterThanOrEqual(0xd800);
      expect(glyph.charCodeAt(1)).toBeGreaterThanOrEqual(0xdc00);
    } finally {
      Intl.Segmenter = original;
    }
  });
});
