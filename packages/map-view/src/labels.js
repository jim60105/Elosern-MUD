// Label measurement, collision and greedy placement in frame pixels. A host
// supplies the candidates (`{ id, lines, priority }` plus whatever its own
// projection needs), the pixel projection and the text measurer; this module
// decides overlap, road crossing and the fallback order. Labels are never
// truncated or shrunk: one that fits nowhere is hidden.

import { requireFrame, requirePositive } from "./values.js";

/** Rough width of a label at fontPx (CJK one em, Latin about 0.58 em). */
export function estimateTextWidth(text, fontPx, letterSpacingEm = 0) {
  let em = 0;
  for (const ch of text) {
    const code = ch.codePointAt(0);
    em += (code > 0x2e80 ? 1 : ch === " " ? 0.3 : 0.58) + letterSpacingEm;
  }
  return em * fontPx;
}

/** Do two `{left, top, right, bottom}` boxes overlap? Touching edges do not. */
export function rectsOverlap(a, b) {
  return a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;
}

// Liang-Barsky: does the segment cross the box?
function segmentHitsBox(seg, box) {
  const dx = seg.x2 - seg.x1;
  const dy = seg.y2 - seg.y1;
  let t0 = 0;
  let t1 = 1;
  const clip = (p, q) => {
    if (p === 0) return q >= 0;
    const r = q / p;
    if (p < 0) {
      if (r > t1) return false;
      if (r > t0) t0 = r;
    } else {
      if (r < t0) return false;
      if (r < t1) t1 = r;
    }
    return true;
  };
  return (
    clip(-dx, seg.x1 - box.left) &&
    clip(dx, box.right - seg.x1) &&
    clip(-dy, seg.y1 - box.top) &&
    clip(dy, box.bottom - seg.y1) &&
    t0 <= t1
  );
}

/**
 * Greedy navigation-priority label placement in frame pixels. Each label
 * tries above its marker, then below, right, left and the four diagonals,
 * preferring a spot clear of every drawn road (`segments`) before one that
 * crosses a road; a label that fits nowhere clear of higher-priority labels
 * and every marker is hidden, never truncated or shrunk.
 *
 * `mustPlace(entry)` names the labels that are always drawn (they may only be
 * clamped inside the frame); the default reserves priority 0 and 1 for them.
 * The selected label is priority 0, the scope's current position priority 1.
 *
 * Returns `[{ id, lines, anchor, x, y, lineHeight, box, priority }]` in
 * placement order.
 */
export function placeLabels(candidates, project2d, frame, {
  fontPx = 16,
  measure = estimateTextWidth,
  markerRadius = 12,
  obstacles = [],
  segments = [],
  mustPlace = (entry) => entry.priority <= 1,
} = {}) {
  requireFrame(frame);
  requirePositive(fontPx, "fontPx");
  requirePositive(markerRadius, "markerRadius");
  const lineHeight = Math.round(fontPx * 1.3);
  // A rendered line's glyph box spans about 1.19 em above the baseline and
  // 0.31 em below it (CJK faces), so boxes match what the browser paints.
  const ascent = Math.round(fontPx * 1.19);
  const glyphHeight = Math.round(fontPx * 1.5);
  const gap = Math.round(fontPx * 0.45);
  // Breathing room kept between two drawn labels.
  const spacing = Math.round(fontPx * 0.2);
  const padded = (box) => ({
    left: box.left - spacing,
    right: box.right + spacing,
    top: box.top - spacing,
    bottom: box.bottom + spacing,
  });
  const markers = obstacles.map((p) => ({
    left: p.x - markerRadius,
    right: p.x + markerRadius,
    top: p.y - markerRadius,
    bottom: p.y + markerRadius,
    id: p.id,
  }));
  const placedBoxes = [];
  const out = [];
  for (const entry of candidates) {
    const p = project2d(entry);
    const width = Math.max(...entry.lines.map((line) => measure(line, fontPx))) + 4;
    const height = (entry.lines.length - 1) * lineHeight + glyphHeight;
    const options = [
      { anchor: "middle", left: p.x - width / 2, top: p.y - markerRadius - gap - height },
      { anchor: "middle", left: p.x - width / 2, top: p.y + markerRadius + gap },
      { anchor: "start", left: p.x + markerRadius + gap, top: p.y - height / 2 },
      { anchor: "end", left: p.x - markerRadius - gap - width, top: p.y - height / 2 },
      { anchor: "start", left: p.x + markerRadius * 0.7, top: p.y - markerRadius * 0.7 - gap - height },
      { anchor: "end", left: p.x - markerRadius * 0.7 - width, top: p.y - markerRadius * 0.7 - gap - height },
      { anchor: "start", left: p.x + markerRadius * 0.7, top: p.y + markerRadius * 0.7 + gap },
      { anchor: "end", left: p.x - markerRadius * 0.7 - width, top: p.y + markerRadius * 0.7 + gap },
    ];
    const must = mustPlace(entry);
    let chosen = null;
    // Passes: clear of roads, then across roads, then (for the always-drawn
    // labels only) across other markers, never across another label.
    const passes = must ? [[true, true], [false, true], [false, false]] : [[true, true], [false, true]];
    for (const [avoidRoads, avoidMarkers] of passes) {
      for (const option of options) {
        const box = { left: option.left, top: option.top, right: option.left + width, bottom: option.top + height };
        const inside = box.left >= 0 && box.top >= 0 && box.right <= frame.width && box.bottom <= frame.height;
        if (!inside) continue;
        const blocked =
          placedBoxes.some((other) => rectsOverlap(padded(box), other)) ||
          (avoidMarkers && markers.some((marker) => marker.id !== entry.id && rectsOverlap(box, marker))) ||
          (avoidRoads && segments.some((seg) => segmentHitsBox(seg, box)));
        if (!blocked) {
          chosen = { ...option, box };
          break;
        }
      }
      if (chosen) break;
    }
    if (!chosen && must) {
      // Last resort: clamp each spot inside the frame and take the first that
      // clears every placed label; only when none does, the spot above.
      const clamped = options.map((option) => {
        const left = Math.min(Math.max(0, option.left), Math.max(0, frame.width - width));
        const top = Math.min(Math.max(0, option.top), Math.max(0, frame.height - height));
        return { anchor: "middle", left, top, box: { left, top, right: left + width, bottom: top + height } };
      });
      chosen = clamped.find((option) => !placedBoxes.some((other) => rectsOverlap(padded(option.box), other))) ?? clamped[0];
    }
    if (!chosen) continue;
    placedBoxes.push(chosen.box);
    const x = chosen.anchor === "middle" ? chosen.left + width / 2 : chosen.anchor === "start" ? chosen.left : chosen.left + width;
    out.push({
      id: entry.id,
      lines: entry.lines,
      anchor: chosen.anchor,
      x,
      y: chosen.top + ascent,
      lineHeight,
      box: chosen.box,
      priority: entry.priority,
    });
  }
  return out;
}
