// Geometry is relative to the original rendered image, never its letterbox.
export const MIN_AREA_EDGE = 0.001;
export const DEFAULT_ANCHOR = { x: 0.25, y: 0.06, w: 0.5, h: 0.5 };

export const clamp = (n, low, high) => Math.min(high, Math.max(low, n));

export function defaultFaceRect(dims = null) {
  if (!dims || !dims.width || !dims.height) {
    return { ...DEFAULT_ANCHOR };
  }
  const { width, height } = dims;
  return {
    x: 0.25,
    y: 0.06,
    w: 0.5,
    h: 0.5 * width / height,
  };
}

export function clampFaceRect(rect, dims = null) {
  let x = clamp(Number.isFinite(rect.x) ? rect.x : 0, 0, 1 - MIN_AREA_EDGE);
  let y = clamp(Number.isFinite(rect.y) ? rect.y : 0, 0, 1 - MIN_AREA_EDGE);
  let w = clamp(Number.isFinite(rect.w) ? rect.w : MIN_AREA_EDGE, MIN_AREA_EDGE, 1 - x);
  let h = clamp(Number.isFinite(rect.h) ? rect.h : MIN_AREA_EDGE, MIN_AREA_EDGE, 1 - y);

  if (!dims || !dims.width || !dims.height) {
    return { x, y, w, h };
  }

  const { width, height } = dims;
  // Shrink the longer pixel axis to make it square
  const pixelW = w * width;
  const pixelH = h * height;
  if (pixelW > pixelH) {
    w = pixelH / width;
  } else if (pixelH > pixelW) {
    h = pixelW / height;
  }

  // Re-clamp within bounds
  const maxW = Math.min(1 - x, (1 - y) * height / width);
  w = clamp(w, MIN_AREA_EDGE, Math.max(MIN_AREA_EDGE, maxW));
  h = w * width / height;

  return { x, y, w, h };
}

export function moveFaceRect(rect, dx, dy) {
  return {
    ...rect,
    x: clamp(rect.x + dx, 0, 1 - rect.w),
    y: clamp(rect.y + dy, 0, 1 - rect.h),
  };
}

export function resizeFaceRect(rect, dx, dy, dims = null) {
  if (!dims || !dims.width || !dims.height) {
    return clampFaceRect({ ...rect, w: rect.w + dx, h: rect.h + dy });
  }
  const { width, height } = dims;
  // Width axis drives resize: w increases by dx, h = w * width / height
  const maxW = Math.min(1 - rect.x, (1 - rect.y) * height / width);
  const w = clamp(rect.w + dx, MIN_AREA_EDGE, Math.max(MIN_AREA_EDGE, maxW));
  const h = w * width / height;
  return { x: rect.x, y: rect.y, w, h };
}

export function editFaceRectField(rect, field, value, dims = null) {
  const num = Number.isFinite(value) ? value : 0;
  if (!dims || !dims.width || !dims.height) {
    return clampFaceRect({ ...rect, [field]: num });
  }
  const { width, height } = dims;
  if (field === "x" || field === "y") {
    const next = { ...rect, [field]: num };
    return clampFaceRect(next, dims);
  }
  if (field === "w") {
    const maxW = Math.min(1 - rect.x, (1 - rect.y) * height / width);
    const w = clamp(num, MIN_AREA_EDGE, Math.max(MIN_AREA_EDGE, maxW));
    const h = w * width / height;
    return { x: rect.x, y: rect.y, w, h };
  }
  if (field === "h") {
    const maxH = Math.min(1 - rect.y, (1 - rect.x) * width / height);
    const h = clamp(num, MIN_AREA_EDGE, Math.max(MIN_AREA_EDGE, maxH));
    const w = h * height / width;
    return { x: rect.x, y: rect.y, w, h };
  }
  return { ...rect };
}

export function refitFaceRectOnLoad(rect, dims) {
  if (!dims || !dims.width || !dims.height) {
    return { ...rect };
  }
  const { width, height } = dims;
  const centerY = rect.y + rect.h / 2;
  const centerX = rect.x + rect.w / 2;
  // Preserve center and height span, re-square width
  const h = clamp(rect.h, MIN_AREA_EDGE, 1);
  const w = h * height / width;
  const x = clamp(centerX - w / 2, 0, 1 - w);
  const y = clamp(centerY - h / 2, 0, 1 - h);
  return clampFaceRect({ x, y, w, h }, dims);
}

export function faceCropStyle(rect) {
  return {
    width: `${100 / rect.w}%`,
    height: `${100 / rect.h}%`,
    left: `${-rect.x * 100 / rect.w}%`,
    top: `${-rect.y * 100 / rect.h}%`,
  };
}
