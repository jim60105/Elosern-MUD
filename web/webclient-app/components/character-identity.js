// Character identity derivations (H2, webclient-hud-02-status-islands,
// design D2/D3/D11): display-only helpers for the character head card.
//
// The duplicated magic-rank band table and ``magicRankTitle()`` are deleted
// (magic-power-static-rename): the retired magic-rank ladder names the XP
// system being removed, so the head card's rank line is guild-rank-only
// until the title-system change line owns title presentation. Wallet values
// are integer copper, thousands-separated for display only (no
// floating-point money).

// Integer copper, thousands-separated for display only; negative or
// non-numeric values clamp to zero (the wallet never displays negative).
export function formatCopper(value) {
  const n = Math.max(0, Number(value) || 0);
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// The head card's portrait is a glyph, never an image: the first Unicode
// grapheme of the display name (grapheme-correct for ZWJ/combining
// sequences). An empty or absent name renders an empty tile rather than a
// substitute character.
export function portraitGlyph(name) {
  if (name === null || name === undefined || name === "") {
    return "";
  }
  const text = String(name);
  if (typeof Intl !== "undefined" && typeof Intl.Segmenter === "function") {
    try {
      const segmenter = new Intl.Segmenter("zh-Hant", { granularity: "grapheme" });
      for (const { segment } of segmenter.segment(text)) {
        return segment;
      }
      return "";
    } catch {
      // Grapheme segmentation unavailable: fall back to the first code point.
    }
  }
  const chars = [...text];
  const first = chars[0];
  if (first === undefined) {
    return "";
  }
  // Keep any extenders (variation selectors U+FE00–FE0F, ZWJ/U+200D,
  // ZWNJ/U+200C, and combining marks) glued to the first code point, so
  // ZWJ / combining / variation sequences stay one grapheme even without
  // full ICU.
  let glyph = first;
  for (let i = 1; i < chars.length; i++) {
    const cp = chars[i].codePointAt(0);
    const isExtender =
      (cp >= 0x300 && cp <= 0x36f) ||
      cp === 0x200c ||
      cp === 0x200d ||
      (cp >= 0xfe00 && cp <= 0xfe0f) ||
      (cp >= 0x1ab0 && cp <= 0x1ab9) ||
      (cp >= 0x20d0 && cp <= 0x20f0);
    if (isExtender) {
      glyph += chars[i];
    } else {
      break;
    }
  }
  return glyph;
}
