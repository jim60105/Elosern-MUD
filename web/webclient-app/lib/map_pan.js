// The minimap's FLIP pan offset (OpenSpec change webclient-scene-transitions,
// design D3). Pure: no Vue, no DOM.
//
// Every move recomputes the minimap's placement, so there is no shared world
// frame to scroll a camera across. Instead the drawing starts translated so
// the previous current node sits exactly where it stood on screen, then eases
// to its committed placement. `panOffset` returns that starting translation
// in the NEW drawing's user units.
//
// A frame is `{ pos: {x, y}, viewBox: {x, y, width, height}, size: {width,
// height} }`: the node's position in user units, the drawing's viewBox, and
// the canvas's CSS size. The mapping honours SVG's default
// `preserveAspectRatio="xMidYMid meet"` (uniform scale, centred letterbox).

function finite(value) {
  return typeof value === "number" && Number.isFinite(value);
}

function validFrame(frame) {
  return (
    !!frame &&
    !!frame.pos &&
    finite(frame.pos.x) &&
    finite(frame.pos.y) &&
    !!frame.viewBox &&
    finite(frame.viewBox.x) &&
    finite(frame.viewBox.y) &&
    finite(frame.viewBox.width) &&
    finite(frame.viewBox.height) &&
    frame.viewBox.width > 0 &&
    frame.viewBox.height > 0 &&
    !!frame.size &&
    finite(frame.size.width) &&
    finite(frame.size.height) &&
    frame.size.width > 0 &&
    frame.size.height > 0
  );
}

// The user-unit → CSS-pixel mapping of one frame.
function fit(frame) {
  const { viewBox, size } = frame;
  const scale = Math.min(size.width / viewBox.width, size.height / viewBox.height);
  return {
    scale,
    offsetX: (size.width - viewBox.width * scale) / 2,
    offsetY: (size.height - viewBox.height * scale) / 2,
  };
}

export function toScreen(frame, pos) {
  const m = fit(frame);
  return {
    x: m.offsetX + (pos.x - frame.viewBox.x) * m.scale,
    y: m.offsetY + (pos.y - frame.viewBox.y) * m.scale,
  };
}

export function fromScreen(frame, point) {
  const m = fit(frame);
  return {
    x: frame.viewBox.x + (point.x - m.offsetX) / m.scale,
    y: frame.viewBox.y + (point.y - m.offsetY) / m.scale,
  };
}

// The translation, in `next`'s user units, that puts the node at
// `next.pos` back on the screen point where it stood in `prev`. `null` when
// either frame is missing or degenerate (the node left the placement: a
// teleport or a new area shows the new placement at once).
export function panOffset(prev, next) {
  if (!validFrame(prev) || !validFrame(next)) {
    return null;
  }
  const anchored = fromScreen(next, toScreen(prev, prev.pos));
  return { dx: anchored.x - next.pos.x, dy: anchored.y - next.pos.y };
}
