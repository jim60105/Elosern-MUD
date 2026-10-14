// Character identity derivations: display-only helpers for character identity presentation.
//
// Wallet values
// are integer copper, thousands-separated for display only (no
// floating-point money).

// Integer copper, thousands-separated for display only; negative or
// non-numeric values clamp to zero (the wallet never displays negative).
export function formatCopper(value) {
  const n = Math.max(0, Number(value) || 0);
  return String(n).replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

// The neutral text symbol an empty (or whitespace-only) name renders in an
// identity/avatar initial position (unified-avatar-rendering design: "a
// neutral text symbol for an empty name"). An unidentified subject still gets
// a bounded, non-blank tile.
export const EMPTY_NAME_GLYPH = "？";

// The first Unicode grapheme cluster of the trimmed displayed name — the ONE
// shared text-initial helper for every avatar and identity placeholder
// (unified-avatar-rendering design: "the first Unicode grapheme cluster of the
// trimmed displayed name, with a neutral text symbol for an empty name").
//
// Grapheme clustering rides the standard `Intl.Segmenter` API at
// `granularity: "grapheme"` and the locale-neutral `"und"` locale. The result
// is always one complete grapheme cluster: a combining sequence, a ZWJ emoji
// sequence, a regional-indicator flag, a skin-tone modifier or an astral
// character stays whole, and an isolated surrogate is never emitted. The
// helper never splits by code unit (`substring`/`slice`) or by code point
// (`Array.from`).
//
// The target browser runtime always provides `Intl.Segmenter`. A runtime that
// does not keeps whole code points only, which still never emits half a
// surrogate pair (it cannot cluster a combining sequence there).
export function portraitGlyph(name) {
  const text = name === null || name === undefined ? "" : String(name).trim();
  if (text === "") {
    return EMPTY_NAME_GLYPH;
  }
  if (typeof Intl !== "undefined" && typeof Intl.Segmenter === "function") {
    try {
      const segmenter = new Intl.Segmenter("und", { granularity: "grapheme" });
      for (const { segment } of segmenter.segment(text)) {
        return segment;
      }
      return EMPTY_NAME_GLYPH;
    } catch {
      // An implementation that refuses to construct: keep whole code points.
    }
  }
  const chars = [...text];
  const first = chars[0];
  return first === undefined ? EMPTY_NAME_GLYPH : first;
}
