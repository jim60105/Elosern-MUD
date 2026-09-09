// face-rect.js — pure mapping from the wire `face_rect` to a CSS
// object-position pair (gallery payload consumption, design §6/D9).
//
// Under `object-fit: cover`, CSS aligns the image's p% point with the
// frame's p% point, so positioning at the rect center keeps the marked
// face center inside the visible window for any frame aspect. The server
// never crops or stores a second image; the offset is presentation-only.
//
// The rectangle must be a well-formed normalized rect (x >= 0, y >= 0,
// w > 0, h > 0, x + w <= 1, y + h <= 1); anything else — including the
// `null` placeholder rect — falls back to the centered crop the client
// rendered before this field existed.

export function faceObjectPosition(rect) {
  const fields = [rect?.x, rect?.y, rect?.w, rect?.h];
  if (fields.some((value) => typeof value !== "number" || !Number.isFinite(value))) {
    return "50% 50%";
  }
  const [x, y, w, h] = fields;
  const wellFormed = x >= 0 && y >= 0 && w > 0 && h > 0 && x + w <= 1 && y + h <= 1;
  if (!wellFormed) {
    return "50% 50%";
  }
  // Two-decimal rounding: keeps float noise (0.06 + 0.25 style sums) out of
  // the emitted percentage string while preserving sub-percent precision.
  const pct = (fraction) => Math.round(fraction * 10000) / 100;
  return `${pct(x + w / 2)}% ${pct(y + h / 2)}%`;
}
