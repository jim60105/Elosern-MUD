// Pure view math for the full-map fit view (design D1–D4,
// openspec/changes/webclient-full-map-fit-view).
// Dependency-free ES module operating over:
//   view:  { s, x, y, fitted }  (scale, origin in user units, fitted flag)
//   frame: { vw, vh, W, H }     (viewport content box and canvas size)

export const FIT_INSET = 12;
export const MAX_SCALE = 2;
export const ZOOM_STEP = 1.25;
export const DRAG_THRESHOLD = 4;

/**
 * Calculates the fitted view for a given frame.
 * Scale is bounded by 1 so small payloads are not magnified.
 * The canvas is centred within the viewport window.
 */
export function fitView(frame) {
  const { vw, vh, W, H } = frame;
  const sFit = Math.max(
    1e-4,
    Math.min(1, (vw - 2 * FIT_INSET) / W, (vh - 2 * FIT_INSET) / H),
  );
  const spanX = vw / sFit;
  const spanY = vh / sFit;
  const x = (W - spanX) / 2;
  const y = (H - spanY) / 2;
  return { s: sFit, x, y, fitted: true };
}

/**
 * Scale bounds for zooming: min is the fitted scale, max is MAX_SCALE (or sFit if larger).
 */
export function scaleBounds(frame) {
  const { vw, vh, W, H } = frame;
  const sFit = Math.max(
    1e-4,
    Math.min(1, (vw - 2 * FIT_INSET) / W, (vh - 2 * FIT_INSET) / H),
  );
  return {
    min: sFit,
    max: Math.max(MAX_SCALE, sFit),
  };
}

/**
 * Clamps view scale and origin against canvas frame boundaries.
 * Preserves the view's fitted flag.
 */
export function clampView(view, frame) {
  const { vw, vh, W, H } = frame;
  const bounds = scaleBounds(frame);
  const s = Math.max(bounds.min, Math.min(bounds.max, view.s));
  const spanX = vw / s;
  const spanY = vh / s;

  let x;
  if (spanX >= W) {
    x = (W - spanX) / 2;
  } else {
    x = Math.max(0, Math.min(W - spanX, view.x));
  }

  let y;
  if (spanY >= H) {
    y = (H - spanY) / 2;
  } else {
    y = Math.max(0, Math.min(H - spanY, view.y));
  }

  return { s, x, y, fitted: view.fitted };
}

/**
 * Zooms about an anchor point in viewport pixels (defaulting to viewport centre).
 * Invariant: the user coordinate under anchorPx remains under anchorPx after scaling.
 */
export function zoomAt(view, factor, anchorPx, frame) {
  const anchor = anchorPx ?? { x: frame.vw / 2, y: frame.vh / 2 };
  const userX = view.x + anchor.x / view.s;
  const userY = view.y + anchor.y / view.s;
  const bounds = scaleBounds(frame);
  const targetS = Math.max(bounds.min, Math.min(bounds.max, view.s * factor));
  const newX = userX - anchor.x / targetS;
  const newY = userY - anchor.y / targetS;
  return clampView({ s: targetS, x: newX, y: newY, fitted: false }, frame);
}

/**
 * Pans the view following a pointer displacement (dxPx, dyPx).
 * Moving pointer by +dxPx moves content right (+dxPx), so origin shifts by -dxPx / s.
 */
export function panBy(view, dxPx, dyPx, frame) {
  const newX = view.x - dxPx / view.s;
  const newY = view.y - dyPx / view.s;
  return clampView({ s: view.s, x: newX, y: newY, fitted: false }, frame);
}

/**
 * Centres the window on a specific user point at current scale.
 */
export function centreOn(view, point, frame) {
  const spanX = frame.vw / view.s;
  const spanY = frame.vh / view.s;
  const newX = point.x - spanX / 2;
  const newY = point.y - spanY / 2;
  return clampView({ s: view.s, x: newX, y: newY, fitted: false }, frame);
}

/**
 * Reveals a bounding box with minimal shift at the current scale, preserving view position
 * if the box is already fully visible within marginPx.
 */
export function revealBox(view, box, marginPx = 0, frame) {
  const left = box.left !== undefined ? box.left : box.x;
  const top = box.top !== undefined ? box.top : box.y;
  const right = box.right !== undefined ? box.right : box.x + box.width;
  const bottom = box.bottom !== undefined ? box.bottom : box.y + box.height;

  const m = (marginPx ?? 0) / view.s;
  const spanX = frame.vw / view.s;
  const spanY = frame.vh / view.s;

  let newX = view.x;
  if (spanX - 2 * m < right - left) {
    newX = (left + right) / 2 - spanX / 2;
  } else if (left < newX + m) {
    newX = left - m;
  } else if (right > newX + spanX - m) {
    newX = right + m - spanX;
  }

  let newY = view.y;
  if (spanY - 2 * m < bottom - top) {
    newY = (top + bottom) / 2 - spanY / 2;
  } else if (top < newY + m) {
    newY = top - m;
  } else if (bottom > newY + spanY - m) {
    newY = bottom + m - spanY;
  }

  return clampView({ s: view.s, x: newX, y: newY, fitted: false }, frame);
}

/**
 * Adjusts view on viewport frame resize: refits if fitted, otherwise keeps the centre point
 * and clamps the scale to the new bounds. Preserves fitted flag.
 */
export function resizeView(view, oldFrame, newFrame) {
  if (view.fitted) {
    return fitView(newFrame);
  }
  const centreUserX = view.x + (oldFrame.vw / view.s) / 2;
  const centreUserY = view.y + (oldFrame.vh / view.s) / 2;
  const bounds = scaleBounds(newFrame);
  const newS = Math.max(bounds.min, Math.min(bounds.max, view.s));
  const newX = centreUserX - (newFrame.vw / newS) / 2;
  const newY = centreUserY - (newFrame.vh / newS) / 2;
  return clampView({ s: newS, x: newX, y: newY, fitted: view.fitted }, newFrame);
}

/**
 * Returns SVG viewBox attribute string "x y vw/s vh/s".
 */
export function viewBoxOf(view, frame) {
  const spanX = frame.vw / view.s;
  const spanY = frame.vh / view.s;
  return `${view.x} ${view.y} ${spanX} ${spanY}`;
}
