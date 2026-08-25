// Character identity derivations (H2, webclient-hud-02-status-islands,
// design D2/D3/D11): display-only helpers for the character head card.
//
// The magic rank title duplicates `world/rules/progression.py`'s
// MAGIC_RANK_BANDS with the same in-order scan, so a level of exactly 90
// resolves to 賢者 exactly as the server's own resolution requires. Wallet
// values are integer copper, thousands-separated for display only (no
// floating-point money).

export const MAGIC_RANK_BANDS = [
  { title: "學徒", lower: 0, upper: 15 },
  { title: "術師", lower: 16, upper: 30 },
  { title: "大師", lower: 31, upper: 70 },
  { title: "賢者", lower: 71, upper: 90 },
  { title: "主宰", lower: 90, upper: null },
];

// Scan in band order: the first band whose range contains the level wins,
// so the overlapping edge (90) resolves to 賢者, matching the server's
// magic_rank_title semantics.
export function magicRankTitle(level) {
  if (
    level === null ||
    level === undefined ||
    level === "" ||
    level === false ||
    level === true ||
    (typeof level === "string" && level.trim() === "")
  ) {
    return "未知";
  }
  const value = Number(level);
  if (!Number.isFinite(value)) {
    return "未知";
  }
  for (const band of MAGIC_RANK_BANDS) {
    if (value >= band.lower && (band.upper === null || value <= band.upper)) {
      return band.title;
    }
  }
  return "未知";
}

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
