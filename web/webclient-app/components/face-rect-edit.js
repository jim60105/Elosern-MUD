// Geometry is relative to the original rendered image, never its letterbox.
const MIN_AREA_EDGE = 0.001;
const clamp = (n, low, high) => Math.min(high, Math.max(low, n));

export function clampFaceRect(rect) {
  const x = clamp(Number.isFinite(rect.x) ? rect.x : 0, 0, 1 - MIN_AREA_EDGE);
  const y = clamp(Number.isFinite(rect.y) ? rect.y : 0, 0, 1 - MIN_AREA_EDGE);
  return {
    x, y,
    w: clamp(Number.isFinite(rect.w) ? rect.w : MIN_AREA_EDGE, MIN_AREA_EDGE, 1 - x),
    h: clamp(Number.isFinite(rect.h) ? rect.h : MIN_AREA_EDGE, MIN_AREA_EDGE, 1 - y),
  };
}

export function moveFaceRect(rect, dx, dy) {
  return { ...rect, x: clamp(rect.x + dx, 0, 1 - rect.w), y: clamp(rect.y + dy, 0, 1 - rect.h) };
}

export function resizeFaceRect(rect, dx, dy) {
  return clampFaceRect({ ...rect, w: rect.w + dx, h: rect.h + dy });
}

export function faceCropStyle(rect) {
  return {
    width: `${100 / rect.w}%`, height: `${100 / rect.h}%`,
    left: `${-rect.x * 100 / rect.w}%`, top: `${-rect.y * 100 / rect.h}%`,
  };
}
