// Navigation-priority label placement for the minimap island (OpenSpec change
// label-minimap-exits-and-gateways; approved design
// docs/superpowers/specs/2026-10-22-minimap-auto-scale-design.md §6.4, §7).
// Pure: no Vue, no DOM.
//
// API
// ---
// `placeIslandLabels({ requests, obstacles, size, font, inset })` places one
// label block per request and returns a Map of request id -> placement.
//
// - A request is `{ id, tier, rank, x, y, footprint, lines, fallbackLines,
//   outward }`:
//   `tier` is "exit", "current" or "context"; `x`/`y` the marker centre in
//   user units; `footprint` the marker's reserved radius; `lines` the block's
//   lines (`{ text, kind }`, one or two), `fallbackLines` the same block with
//   its text truncated to the surface's `labelMax` (defaults to `lines`);
//   `outward` the bearing (degrees clockwise from north) from the current node
//   to this marker, or null; `avoid` (current only) the bearings of its
//   routes.
// - An obstacle is a box `{ x0, y0, x1, y1 }` or a circle `{ x, y, r }`, plus
//   an optional `owner` (a request id whose own label may touch it, i.e. its
//   own marker footprint).
//
// Policy
// ------
// Requests are placed in tier order exit → current → context, then by `rank`
// (default 1; a gateway exit stub passes 0 so it is placed first), then in
// payload order. Each tries eight candidate boxes around its marker, at the
// footprint plus LABEL_GAP: an exit or context label tries them nearest its
// outward bearing first (the label reads away from the player, off its own
// route); the current label tries the directions farthest from its routes
// (`avoid`, the exit bearings) first, below, above, right, left, then the
// diagonals breaking ties. A
// candidate is accepted when it lies inside the square (less `inset`) and
// clears every obstacle and every label already accepted by CLEARANCE units.
//
// When no candidate fits:
// - an exit retries with its truncated `fallbackLines`, then searches farther
//   out along the same eight directions (then anywhere in the square, nearest
//   first) and draws the truncated block with a leader line back to its
//   marker; when even that finds no free spot it keeps the in-square
//   candidate with the least overlap, still with a leader line.
//   An exit label is never dropped.
// - the current label keeps the classic placement below its marker (shifted
//   inside the square, lifted above it at the bottom edge), truncated.
// - a context label is omitted.
//
// A placement is `{ id, tier, lines: [{ text, kind, x, y }], box, leader,
// truncated, direction }` where `x` is the line's centre (text-anchor middle),
// `y` its baseline, and `leader` null or `{ x1, y1, x2, y2 }`.
import { CELL_EM, textCells } from "./mono_cells.js";

export const LABEL_GAP = 3;
export const CLEARANCE = 2;
export const ASCENT = 0.8;
export const DESCENT = 0.25;
export const LINE_STEP = 1.2;
export const LEADER_STEP = 6;
export const LEADER_REACH = 150;

const DIRECTIONS = Object.freeze([
  ["s", 0, 1, 180],
  ["n", 0, -1, 0],
  ["e", 1, 0, 90],
  ["w", -1, 0, 270],
  ["se", 1, 1, 135],
  ["ne", 1, -1, 45],
  ["sw", -1, 1, 225],
  ["nw", -1, -1, 315],
]);
const TIER_ORDER = { exit: 0, current: 1, context: 2 };
const DIAGONAL = Math.SQRT1_2;

function angleGap(a, b) {
  const d = Math.abs((((a - b) % 360) + 360) % 360);
  return d > 180 ? 360 - d : d;
}

// The eight directions, nearest the outward bearing first (ties keep the
// fixed order); the fixed order when there is no bearing.
// The current label's order: the directions farthest in bearing from every
// route leaving it first (so its name never sits on an exit's road), the
// fixed order breaking ties.
export function clearestOrder(avoid) {
  if (!Array.isArray(avoid) || avoid.length === 0) return DIRECTIONS;
  const clearance = (dir) => Math.min(...avoid.map((bearing) => angleGap(dir[3], bearing)));
  return DIRECTIONS.map((dir, i) => ({ dir, i, gap: clearance(dir) }))
    .sort((a, b) => b.gap - a.gap || a.i - b.i)
    .map((entry) => entry.dir);
}

export function candidateOrder(outward) {
  if (outward === null || outward === undefined || !Number.isFinite(outward)) return DIRECTIONS;
  return DIRECTIONS.map((dir, i) => ({ dir, i, gap: angleGap(dir[3], outward) }))
    .sort((a, b) => a.gap - b.gap || a.i - b.i)
    .map((entry) => entry.dir);
}

export function lineWidth(text, font) {
  return textCells(text) * CELL_EM * font;
}

function blockSize(lines, font) {
  const width = Math.max(0, ...lines.map((line) => lineWidth(line.text, font)));
  const height = (ASCENT + DESCENT + (lines.length - 1) * LINE_STEP) * font;
  return { width, height };
}

// The block's box with its nearest edge or corner `distance` from (x, y).
function boxAt(x, y, dir, distance, size) {
  const [, ux, uy] = dir;
  const k = ux !== 0 && uy !== 0 ? DIAGONAL : 1;
  const x0 = ux === 0 ? x - size.width / 2 : ux > 0 ? x + distance * k : x - distance * k - size.width;
  const y0 = uy === 0 ? y - size.height / 2 : uy > 0 ? y + distance * k : y - distance * k - size.height;
  return { x0, y0, x1: x0 + size.width, y1: y0 + size.height };
}

function inside(box, size, inset) {
  return box.x0 >= inset - 1e-9 && box.y0 >= inset - 1e-9 && box.x1 <= size - inset + 1e-9 && box.y1 <= size - inset + 1e-9;
}

// Overlap area of `box` grown by the clearance with an obstacle (a circle
// counts its bounding square's intersection only when the true distance is
// short of the clearance).
function overlapArea(box, other) {
  const g = CLEARANCE;
  if (other.r !== undefined) {
    const nx = Math.min(Math.max(other.x, box.x0), box.x1);
    const ny = Math.min(Math.max(other.y, box.y0), box.y1);
    const d = Math.hypot(other.x - nx, other.y - ny);
    if (d >= other.r + g - 1e-9) return 0;
    return (other.r + g - d) * (other.r + g - d) + 1e-6;
  }
  const w = Math.min(box.x1 + g, other.x1) - Math.max(box.x0 - g, other.x0);
  const h = Math.min(box.y1 + g, other.y1) - Math.max(box.y0 - g, other.y0);
  return w > 1e-9 && h > 1e-9 ? w * h : 0;
}

export function boxesClear(a, b, gap = CLEARANCE) {
  return a.x1 + gap <= b.x0 + 1e-9 || b.x1 + gap <= a.x0 + 1e-9 || a.y1 + gap <= b.y0 + 1e-9 || b.y1 + gap <= a.y0 + 1e-9;
}

function linesIn(box, lines, font) {
  const cx = (box.x0 + box.x1) / 2;
  return lines.map((line, i) => ({
    text: line.text,
    kind: line.kind,
    x: cx,
    y: box.y0 + (ASCENT + i * LINE_STEP) * font,
  }));
}

// Whether a segment passes through a box (Liang–Barsky clipping).
function segmentHitsBox(seg, box) {
  const dx = seg.x2 - seg.x1;
  const dy = seg.y2 - seg.y1;
  let t0 = 0;
  let t1 = 1;
  const edges = [
    [-dx, seg.x1 - box.x0],
    [dx, box.x1 - seg.x1],
    [-dy, seg.y1 - box.y0],
    [dy, box.y1 - seg.y1],
  ];
  for (const [p, q] of edges) {
    if (Math.abs(p) < 1e-12) {
      if (q < 0) return false;
      continue;
    }
    const r = q / p;
    if (p < 0) t0 = Math.max(t0, r);
    else t1 = Math.min(t1, r);
    if (t0 > t1) return false;
  }
  return true;
}

// A hairline from the marker footprint's edge toward the box's nearest point.
function leaderTo(request, box) {
  const nx = Math.min(Math.max(request.x, box.x0), box.x1);
  const ny = Math.min(Math.max(request.y, box.y0), box.y1);
  const dx = nx - request.x;
  const dy = ny - request.y;
  const length = Math.hypot(dx, dy);
  // A block one search step out still reads as its marker's own label.
  if (length <= request.footprint + LABEL_GAP + LEADER_STEP + 1e-6) return null;
  const start = (request.footprint + 1) / length;
  return { x1: request.x + dx * start, y1: request.y + dy * start, x2: nx, y2: ny };
}

// The classic below-marker placement, kept inside the square: shifted along x
// at a side, lifted above the marker at the bottom edge.
function classicBox(request, size, canvas, inset, font) {
  const below = boxAt(request.x, request.y, DIRECTIONS[0], request.footprint + LABEL_GAP, size);
  const shift = Math.min(Math.max(below.x0, inset), Math.max(inset, canvas - inset - size.width)) - below.x0;
  let box = { ...below, x0: below.x0 + shift, x1: below.x1 + shift };
  if (box.y1 > canvas - inset) {
    const above = boxAt(request.x, request.y, DIRECTIONS[1], request.footprint + LABEL_GAP, size);
    box = { ...box, y0: above.y0, y1: above.y1 };
  }
  void font;
  return box;
}

export function placeIslandLabels({ requests, obstacles = [], size = 240, font = 16, inset = 3 }) {
  const ordered = requests
    .map((request, order) => ({ request, order }))
    .sort(
      (a, b) =>
        (TIER_ORDER[a.request.tier] ?? 3) - (TIER_ORDER[b.request.tier] ?? 3) ||
        (a.request.rank ?? 1) - (b.request.rank ?? 1) ||
        a.order - b.order,
    )
    .map((entry) => entry.request);
  const accepted = [];
  const placements = new Map();
  const blockers = (request) => [
    ...obstacles.filter((o) => o.owner === undefined || o.owner !== request.id),
    ...accepted,
  ];
  const free = (box, request) => inside(box, size, inset) && blockers(request).every((o) => overlapArea(box, o) === 0);
  const accept = (request, box, lines, extra) => {
    accepted.push(box);
    placements.set(request.id, {
      id: request.id,
      tier: request.tier,
      lines: linesIn(box, lines, font),
      box,
      leader: null,
      truncated: false,
      direction: null,
      ...extra,
    });
  };

  for (const request of ordered) {
    const lines = request.lines.filter((line) => line.text);
    if (lines.length === 0) continue;
    const fallbackLines = (request.fallbackLines || request.lines).filter((line) => line.text);
    const order = request.tier === "current" ? clearestOrder(request.avoid) : candidateOrder(request.outward);
    const distance = request.footprint + LABEL_GAP;
    const tryAll = (block, at) => {
      const blockSz = blockSize(block, font);
      for (const dir of order) {
        const box = boxAt(request.x, request.y, dir, at, blockSz);
        if (free(box, request)) return { box, dir };
      }
      return null;
    };
    const whole = tryAll(lines, distance);
    if (whole) {
      accept(request, whole.box, lines, { direction: whole.dir[0] });
      continue;
    }
    const sameText = fallbackLines.map((l) => l.text).join("\n") === lines.map((l) => l.text).join("\n");
    if (request.tier !== "context" && !sameText) {
      const short = tryAll(fallbackLines, distance);
      if (short) {
        accept(request, short.box, fallbackLines, { direction: short.dir[0], truncated: true });
        continue;
      }
    }
    if (request.tier === "context") continue;
    const fallbackSize = blockSize(fallbackLines, font);
    if (request.tier === "current") {
      const box = classicBox(request, fallbackSize, size, inset, font);
      accept(request, box, fallbackLines, { truncated: !sameText, direction: "classic" });
      continue;
    }
    // An exit: farther out with a leader line — the directions within 45°
    // of its outward bearing first, then the rest — preferring a hairline
    // that crosses no label already placed; else the least-overlap spot.
    let spot = null;
    const near = order.filter((dir) => request.outward === null || request.outward === undefined || angleGap(dir[3], request.outward) <= 45);
    const far = order.filter((dir) => !near.includes(dir));
    for (const crossing of [false, true]) {
      for (const group of [near, far]) {
        for (let at = distance + LEADER_STEP; at <= distance + LEADER_REACH && !spot; at += LEADER_STEP) {
          for (const dir of group) {
            const box = boxAt(request.x, request.y, dir, at, fallbackSize);
            if (!free(box, request)) continue;
            const leader = leaderTo(request, box);
            if (!crossing && leader && accepted.some((other) => segmentHitsBox(leader, other))) continue;
            spot = { box, dir };
            break;
          }
        }
        if (spot) break;
      }
      if (spot) break;
    }
    if (!spot) {
      // Anywhere in the square: the free spot nearest the marker, on a
      // six-unit raster.
      let nearest = null;
      for (let y0 = inset; y0 + fallbackSize.height <= size - inset + 1e-9; y0 += LEADER_STEP) {
        for (let x0 = inset; x0 + fallbackSize.width <= size - inset + 1e-9; x0 += LEADER_STEP) {
          const box = { x0, y0, x1: x0 + fallbackSize.width, y1: y0 + fallbackSize.height };
          if (!free(box, request)) continue;
          const nx = Math.min(Math.max(request.x, box.x0), box.x1);
          const ny = Math.min(Math.max(request.y, box.y0), box.y1);
          const reach = Math.hypot(nx - request.x, ny - request.y);
          // Never over the label's own marker (not a blocker of its own).
          if (reach < request.footprint + LABEL_GAP - 1e-9) continue;
          if (!nearest || reach < nearest.reach - 1e-9) nearest = { box, dir: ["raster"], reach };
        }
      }
      spot = nearest;
    }
    if (!spot) {
      let best = null;
      for (let at = distance; at <= distance + LEADER_REACH; at += LEADER_STEP) {
        for (const dir of order) {
          const box = boxAt(request.x, request.y, dir, at, fallbackSize);
          if (!inside(box, size, inset)) continue;
          // Covering a marker costs far more than crossing a label.
          const cost = blockers(request).reduce((sum, o) => sum + overlapArea(box, o) * (o.r !== undefined ? 25 : 1), 0);
          if (!best || cost < best.cost - 1e-9) best = { box, dir, cost };
        }
      }
      spot = best ?? { box: classicBox(request, fallbackSize, size, inset, font), dir: ["classic"] };
    }
    accept(request, spot.box, fallbackLines, {
      direction: spot.dir[0],
      truncated: !sameText,
      leader: leaderTo(request, spot.box),
    });
  }
  return placements;
}
