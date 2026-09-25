// Shared box-drawing range check (design D5, webclient-message-pages).
// A box-drawing line is one whose text carries any U+2500..U+257F code
// point (the `─`..`╿` range); the escaped form is the single copy.
export const BOX_DRAWING = /[\u2500-\u257f]/;

export function isBoxDrawing(text) {
  return BOX_DRAWING.test(text == null ? "" : String(text));
}
