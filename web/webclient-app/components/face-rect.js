// face-rect.js — pure mappings from the wire `face_rect` to CSS, shared by
// every framed-portrait surface.
//
// Two mappings sit on one well-formedness gate:
// - faceObjectPosition(rect) is the recenters-only cover crop: the gallery
//   cards, the gallery detail rail, the combat participant frame, the party
//   strip, the dialogue host avatar, the interact/dock avatars, and
//   ReferenceArtwork keep this treatment.
// - faceCropStyle(rect, fallbackPosition) is the small-avatar zoom crop: the
//   top-bar character switcher's pill and per-row thumbnails and the party
//   drawer's per-companion avatar, which enlarge and anchor the image so the
//   marked rectangle substantially fills the frame.
//
// Under `object-fit: cover`, CSS aligns the image's p% point with the
// frame's p% point, so positioning at the rect center keeps the marked face
// center inside the visible window for any frame aspect. At a 22–52px avatar
// frame that window still spans most of a full-body portrait, so the
// small-avatar set instead enlarges the image to 1/w × 1/h of the frame and
// anchors it at -x/w and -y/h of the frame, letting the frame's own overflow
// clipping show just the rectangle's region. The enlargement is capped per
// axis so a degenerate rect cannot request an unbounded image box.
//
// The server stores rectangles verbatim and never crops or derives a second
// image; both mappings are presentation-only and ignore `stage`.
//
// The rectangle must be a well-formed normalized rect (x >= 0, y >= 0,
// w > 0, h > 0, x + w <= 1, y + h <= 1); anything else — including the
// `null` placeholder rect — falls back to the centered crop the client
// rendered before this field existed.

// Zoom-crop enlargement ceiling per axis, expressed as the frame-relative
// factor (8 → an 800% image box).
const MAX_CROP_FACTOR = 8;

// Two-decimal rounding: keeps float noise (0.06 + 0.25 style sums) out of
// the emitted percentage string while preserving sub-percent precision.
const pct = (fraction) => Math.round(fraction * 10000) / 100;

// The single source of truth for well-formedness: the normalized rect, or
// `null` for a null/undefined rect, a non-number or non-finite field, a
// field outside [0, 1], an edge-crossing rect, or a non-positive w/h.
function normalizedRect(rect) {
  const fields = [rect?.x, rect?.y, rect?.w, rect?.h];
  if (fields.some((value) => typeof value !== "number" || !Number.isFinite(value))) {
    return null;
  }
  const [x, y, w, h] = fields;
  const wellFormed = x >= 0 && y >= 0 && w > 0 && h > 0 && x + w <= 1 && y + h <= 1;
  if (!wellFormed) {
    return null;
  }
  return { x, y, w, h };
}

export function faceObjectPosition(rect) {
  const normalized = normalizedRect(rect);
  if (!normalized) {
    return "50% 50%";
  }
  const { x, y, w, h } = normalized;
  return `${pct(x + w / 2)}% ${pct(y + h / 2)}%`;
}

// The enlarge-and-anchor crop style for the small-avatar set. A rejected rect
// carries the caller's centered `objectPosition` alone, so a malformed rect
// renders exactly the centered cover crop those surfaces showed before this
// mapping existed: the caller's frame clips with `overflow: hidden` and its
// image class rule sizes the absolute box to that frame's padding box, so no
// container alignment and no inline property can displace or resize it.
//
// The sizes and anchors land the rectangle's region on the frame's box exactly
// for the pixel-square rectangle the authoring path enforces; for a legacy
// non-square rectangle the same anchor composes the frame from the rectangle,
// with a bounded sliver cropped on the one overflowing axis.
export function faceCropStyle(rect, fallbackPosition = "50% 50%") {
  const normalized = normalizedRect(rect);
  if (!normalized) {
    return { objectPosition: fallbackPosition };
  }
  const { x, y, w, h } = normalized;
  const factorW = Math.min(1 / w, MAX_CROP_FACTOR);
  const factorH = Math.min(1 / h, MAX_CROP_FACTOR);
  return {
    width: `${pct(factorW)}%`,
    height: `${pct(factorH)}%`,
    left: `${pct(-x * factorW)}%`,
    top: `${pct(-y * factorH)}%`,
    // Inert for an exact pixel-square rect (the box already matches the
    // source aspect); it centers the crop box for a legacy non-square one.
    objectPosition: "50% 50%",
  };
}
