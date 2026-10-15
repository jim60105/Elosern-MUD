// The combat formation engine (OpenSpec change
// webclient-combat-formation-engine, design D1, D2, D3 and D5): one pure,
// DOM-free function that places every combat figure box, plate slot and
// target-marker slot for a party of 1-5 figures against 1-(16 - party) foes,
// with one figure scale shared by both sides.
//
// Coordinates are stage pixels: x from the stage's left edge, y from its top.
// `S` is the desktop chrome factor (`--ui-scale`); every fixed chrome length
// below is multiplied by it, while the figure size follows `actor-h`.
//
// Invariants (asserted by tests/core/combat_formation.test.js wherever `fits`
// is true):
// - every figure box on both sides is `scale × actor-h` tall and two thirds of
//   that wide, and `scale` is a rung of SCALE_LADDER (never below SCALE_FLOOR);
// - the dead-centre gap `[C - card/2 - 16·S, C + card/2 + 16·S]` holds no box,
//   plate slot or marker slot; the party stands left of it and the foes right
//   of it, each inside the stage's 16·S side gutters;
// - plate slots on a side are pairwise at least 2·S apart, across ranks too;
// - every plate slot and the 24·S marker slot above it stay at least 8·S below
//   the top band;
// - no plate slot touches the vitals dock, and the dock covers at most the
//   lowest 40% of any party box;
// - no head is ever covered (webclient-combat-formation): no plate or marker
//   slot overlaps any figure's head (the central HEAD_WIDTH × top HEAD_HEIGHT
//   of its box), a front-rank box never reaches a back-rank head, and the
//   heads of one rank stay apart, and each figure's beat step (`lunge`) is
//   cut to the space before the next head toward the centre, so a figure
//   acting in a round never leans its head over a neighbour's; lower bodies
//   may be covered. The rule holds for every resting layout and at the beat step's
//   peak; a glide between two layouts and a foe fading where it stood are
//   transitions, not layouts;
// - a floor plate (see below) stays FLOOR_CLEARANCE above the command-line
//   row and, for the party, above the vitals dock.
//
// Policy: walk SCALE_LADDER from the largest rung; at each rung each side takes
// one rank if it fits, else two ranks if they fit. The first rung where both
// sides fit with `full` slots wins; failing that, the ladder is walked again
// allowing `compact` slots. When nothing fits (a stage smaller than the
// supported viewports) the floor-scale, two-rank, compact formation is
// returned with `fits: false`.
//
// Figure order: the first figure of a side (the controlled figure, or the
// first foe in presenter order) stands at the side's outer edge; later figures
// step toward the centre. With two ranks the front rank holds the first
// `ceil(n/2)` figures and the back rank the rest, lifted up-stage and offset
// half a step toward the centre so its figures show between the front ones.
//
// Plate placement: a plate stands above its figure's head, except in the
// front rank of a two-rank side, where a plate above the head would lie
// across the back rank's faces; those plates stand on the side's floor line
// (FLOOR_CLEARANCE above the command-line row, and for the party above the
// vitals dock), over their own figures' lower bodies.
//
// Only `formationInputFromStage` reads CSS-derived values; `combatFormation`
// reads nothing but its input object.

export const SCALE_LADDER = Object.freeze([0.9, 0.84, 0.78, 0.72, 0.66, 0.6, 0.55, 0.5]);
export const SCALE_FLOOR = 0.5;
// The command card's width (webclient-combat-command-card-centred), in px·S.
export const CARD_WIDTH = 264;
// The clear gutter on each side of the card, in px·S.
export const CARD_GUTTER = 16;
// The stage's outer side gutter, in px·S.
export const STAGE_GUTTER = 16;
// The side's home inset: the group's outer edge, as a fraction of the stage
// width, when the group fits there.
export const HOME_INSET = 0.06;
// A figure box's width as a fraction of its height (the portrait anchor).
export const FIGURE_ASPECT = 2 / 3;
// The largest horizontal step between neighbouring figures of a rank, as a
// fraction of the figure width.
export const RANK_STEP = 0.62;
// How far a back rank stands up-stage, as a fraction of `actor-h`.
export const BACK_RANK_LIFT = 0.27;
// Plate slots, in px·S.
export const FULL_SLOT = Object.freeze({ width: 112, height: 52 });
export const COMPACT_SLOT = Object.freeze({ width: 72, height: 36 });
// The gap between a figure box's top and its plate, and between two plate
// lines, in px·S.
export const PLATE_GAP = 4;
// The least distance between two plate slots, in px·S.
export const PLATE_SEPARATION = 2;
// The target-marker slot: a square pointer target directly above the plate.
export const MARKER_SIZE = 24;
// The least clearance between any plate or marker slot and the top band.
export const TOP_BAND_CLEARANCE = 8;
// The most of a party box (its lowest part) the vitals dock may cover.
export const DOCK_COVER_MAX = 0.4;
// A figure's head, as fractions of its box: the central HEAD_WIDTH of its
// width and the top HEAD_HEIGHT of its height (webclient-combat-formation:
// no head is ever covered — not by a plate, a marker or another figure).
export const HEAD_WIDTH = 0.3;
export const HEAD_HEIGHT = 0.22;
// The beat step (`--motion-beat-lunge`, 12px·S): a figure acting in a combat
// round leans at most this far toward the centre. Each figure's `lunge` is
// that distance cut to the clear space between its head and the next head of
// its rank toward the centre, so a step never brings one head over another.
export const BEAT_STEP = 12;
// The command-line row docked on the band's top edge (`--command-line-h`), in
// px·S, used when the input does not measure it.
export const COMMAND_LINE_HEIGHT = 44;
// The clearance between a floor plate and the command-line row or the vitals
// dock below it, in px·S.
export const FLOOR_CLEARANCE = 8;

// Floating-point slack for comparisons against exact edges.
const EPSILON = 1e-6;

function rect(left, top, width, height) {
  return { left, top, width, height };
}

function right(box) {
  return box.left + box.width;
}

function bottom(box) {
  return box.top + box.height;
}

// The least distance between two rectangles (0 when they touch or overlap),
// measured per axis (Chebyshev): two diagonal neighbours count as close as
// their larger axis gap, which is never more than their true distance, so
// the 2px·S rule errs on the side of more air.
function separation(a, b) {
  const dx = Math.max(a.left - right(b), b.left - right(a), 0);
  const dy = Math.max(a.top - bottom(b), b.top - bottom(a), 0);
  return Math.max(dx, dy);
}

function overlaps(a, b) {
  return a.left < right(b) - EPSILON && b.left < right(a) - EPSILON
    && a.top < bottom(b) - EPSILON && b.top < bottom(a) - EPSILON;
}

// A figure box's head (see HEAD_WIDTH / HEAD_HEIGHT).
export function headOf(box) {
  return rect(
    box.left + ((1 - HEAD_WIDTH) / 2) * box.width,
    box.top,
    HEAD_WIDTH * box.width,
    HEAD_HEIGHT * box.height,
  );
}

function intersectsOrTouches(a, b) {
  return a.left <= right(b) && b.left <= right(a) && a.top <= bottom(b) && b.top <= bottom(a);
}

// A figure count: a whole number of at least 0, else a TypeError. Counts
// outside the supported range (party 1-5, foes 1-(16 - party)) are laid out by
// the same rules; `fits` speaks only to the geometry, and keeping the counts in
// range is the caller's contract.
function count(name, value) {
  const n = Number(value);
  if (value === null || value === "" || typeof value === "boolean" || !Number.isInteger(n) || n < 0) {
    throw new TypeError(`combat formation: input.${name} is not a whole number of at least 0`);
  }
  return n;
}

// The horizontal zones and the gap, from the input.
function zonesFor(input) {
  const S = input.uiScale;
  const centre = input.stageWidth / 2;
  const half = input.cardWidth / 2 + CARD_GUTTER * S;
  return {
    centre,
    gap: { left: centre - half, right: centre + half },
    party: { left: STAGE_GUTTER * S, right: centre - half },
    foes: { left: centre + half, right: input.stageWidth - STAGE_GUTTER * S },
  };
}

// One side laid out at one scale, rank count and slot form. Always returns
// geometry; `ok` says whether every fit condition holds.
function layoutSide(input, zone, side, n, scale, ranks, form) {
  const S = input.uiScale;
  const slotSize = form === "compact" ? COMPACT_SLOT : FULL_SLOT;
  const slotWidth = slotSize.width * S;
  const slotHeight = slotSize.height * S;
  const gap = PLATE_GAP * S;
  const markerSize = MARKER_SIZE * S;
  const height = scale * input.actorHeight;
  const width = height * FIGURE_ASPECT;
  const zoneWidth = zone.right - zone.left;
  const frontCount = ranks === 2 ? Math.ceil(n / 2) : n;
  const backCount = n - frontCount;
  const shift = backCount > 0 ? 0.5 : 0;
  const units = frontCount - 1 + shift;
  const rawStep = units > 0 ? Math.min(RANK_STEP * width, (zoneWidth - width) / units) : 0;
  const step = Math.max(0, rawStep);
  const span = width + units * step;
  let ok = n === 0 || (rawStep >= -EPSILON && width <= zoneWidth + EPSILON);

  // The outer edge sits at the home inset when the group fits there, and is
  // pushed toward the outer gutter otherwise, never into the gap.
  const home = Math.max(HOME_INSET * input.stageWidth, STAGE_GUTTER * S);
  let outer;
  if (side === "party") {
    outer = Math.max(zone.left, Math.min(home, zone.right - span));
  } else {
    outer = Math.min(zone.right, Math.max(input.stageWidth - home, zone.left + span));
  }

  // Where a figure's plate stands: above its head, except in the front rank of
  // a two-rank side, whose plates would otherwise lie across the back rank's
  // faces. Those stand on the floor line instead, over their own figures'
  // lower bodies, clear of the command-line row (and, for the party, of the
  // vitals dock) below them.
  let floorBottom = input.bandTop - input.commandLineHeight - FLOOR_CLEARANCE * S;
  if (side === "party" && input.vitalsDock) {
    floorBottom = Math.min(floorBottom, input.vitalsDock.top - FLOOR_CLEARANCE * S);
  }

  const lineFor = (rankSize) => {
    if (rankSize <= 1 || step + EPSILON >= slotWidth + gap) return { lines: 1, ok: true };
    if (2 * step + EPSILON >= slotWidth + gap) return { lines: 2, ok: true };
    return { lines: 2, ok: false };
  };
  const frontLines = lineFor(frontCount);
  const backLines = lineFor(backCount);
  ok = ok && frontLines.ok && backLines.ok;

  const figures = [];
  for (let index = 0; index < n; index += 1) {
    const rank = index < frontCount ? 0 : 1;
    const position = rank === 0 ? index : index - frontCount;
    const offset = (position + (rank === 1 ? 0.5 : 0)) * step;
    const left = side === "party" ? outer + offset : outer - offset - width;
    const lift = rank === 1 ? BACK_RANK_LIFT * input.actorHeight : 0;
    const box = rect(left, input.bandTop - lift - height, width, height);
    const lines = rank === 0 ? frontLines.lines : backLines.lines;
    const line = lines === 2 ? position % 2 : 0;
    const centreX = left + width / 2;
    const onFloor = backCount > 0 && rank === 0;
    const plateBottom = (onFloor ? floorBottom : box.top - gap) - line * (slotHeight + gap);
    const plate = { ...rect(centreX - slotWidth / 2, plateBottom - slotHeight, slotWidth, slotHeight), form, line };
    const marker = rect(centreX - markerSize / 2, plate.top - markerSize, markerSize, markerSize);
    figures.push({ index, rank, box, plate, marker, z: n - index, floor: onFloor });
  }

  // The beat step each figure may take toward the centre: BEAT_STEP·S, cut to
  // the clear space before the next head of its rank (the next figure toward
  // the centre). The innermost figure of a rank leans into its gutter, which is
  // wider than the step.
  for (const figure of figures) {
    const next = figures.find((other) => other.rank === figure.rank && other.index === figure.index + 1);
    let lunge = BEAT_STEP * S;
    if (next) {
      const own = headOf(figure.box);
      const theirs = headOf(next.box);
      const clear = side === "party" ? theirs.left - right(own) : own.left - right(theirs);
      lunge = Math.max(0, Math.min(lunge, clear));
    }
    figure.lunge = lunge;
  }

  if (ok) ok = sideFits(input, zone, side, figures);
  return { ok, ranks: backCount > 0 ? 2 : 1, form, step, figures };
}

function sideFits(input, zone, side, figures) {
  const S = input.uiScale;
  const ceiling = input.topBandBottom + TOP_BAND_CLEARANCE * S;
  const dock = input.vitalsDock;
  for (const figure of figures) {
    for (const box of [figure.box, figure.plate, figure.marker]) {
      if (box.left < zone.left - EPSILON || right(box) > zone.right + EPSILON) return false;
      if (bottom(box) > input.bandTop + EPSILON) return false;
    }
    if (figure.marker.top < ceiling - EPSILON) return false;
    if (dock && intersectsOrTouches(figure.plate, dock)) return false;
    if (dock && side === "party") {
      const horizontal = Math.min(right(figure.box), right(dock)) - Math.max(figure.box.left, dock.left);
      const coverTop = Math.max(figure.box.top, dock.top);
      const coverBottom = Math.min(bottom(figure.box), bottom(dock));
      if (horizontal > EPSILON && coverBottom - coverTop > EPSILON) {
        // The covered part must lie within the box's lowest 40%.
        if (coverTop < bottom(figure.box) - DOCK_COVER_MAX * figure.box.height - EPSILON) return false;
      }
    }
  }
  // No head is covered: no plate or marker slot on the side overlaps any
  // figure's head, a figure in front of another (an earlier rank) never
  // reaches its head, and within a rank neighbours' heads stay apart.
  for (const figure of figures) {
    const head = headOf(figure.box);
    for (const other of figures) {
      if (overlaps(head, other.plate) || overlaps(head, other.marker)) return false;
      if (other === figure) continue;
      const occluder = other.rank < figure.rank ? other.box : other.rank === figure.rank ? headOf(other.box) : null;
      if (occluder && overlaps(head, occluder)) return false;
    }
    // A floor plate never sits on its own figure's head band either, and
    // stays above the command-line row.
    if (figure.floor && bottom(figure.plate) > input.bandTop - input.commandLineHeight + EPSILON) return false;
  }
  const least = PLATE_SEPARATION * S;
  for (let a = 0; a < figures.length; a += 1) {
    for (let b = a + 1; b < figures.length; b += 1) {
      if (separation(figures[a].plate, figures[b].plate) < least - EPSILON) return false;
    }
  }
  return true;
}

// One side at one scale: one rank if it fits, else two ranks if they fit;
// the slot form falls back to `compact` only when it is allowed.
function fitSide(input, zone, side, n, scale, allowCompact) {
  const forms = allowCompact ? ["full", "compact"] : ["full"];
  for (const ranks of [1, 2]) {
    if (ranks === 2 && n < 2) continue;
    for (const form of forms) {
      const result = layoutSide(input, zone, side, n, scale, ranks, form);
      if (result.ok) return result;
    }
  }
  return null;
}

// The required numeric inputs; a missing or non-finite one throws instead of
// yielding a silent NaN formation.
const REQUIRED = ["stageWidth", "stageHeight", "uiScale", "bandTop", "actorHeight", "topBandBottom"];

function normalise(input) {
  for (const name of REQUIRED) {
    const value = input?.[name];
    if (value === null || value === "" || typeof value === "boolean" || !Number.isFinite(Number(value))) {
      throw new TypeError(`combat formation: input.${name} is not a finite number`);
    }
  }
  const uiScale = Number(input.uiScale);
  if (uiScale <= 0) throw new TypeError("combat formation: input.uiScale must be greater than 0");
  const cardWidth = Number.isFinite(Number(input.cardWidth)) && Number(input.cardWidth) > 0
    ? Number(input.cardWidth)
    : CARD_WIDTH * uiScale;
  const dock = input.vitalsDock;
  return {
    stageWidth: Number(input.stageWidth),
    stageHeight: Number(input.stageHeight),
    uiScale,
    bandTop: Number(input.bandTop),
    actorHeight: Number(input.actorHeight),
    topBandBottom: Number(input.topBandBottom),
    cardWidth,
    vitalsDock: dock ? rect(Number(dock.left), Number(dock.top), Number(dock.width), Number(dock.height)) : null,
    commandLineHeight: input.commandLineHeight != null && input.commandLineHeight !== ""
      && Number.isFinite(Number(input.commandLineHeight)) && Number(input.commandLineHeight) >= 0
      ? Number(input.commandLineHeight)
      : COMMAND_LINE_HEIGHT * uiScale,
    partyCount: count("partyCount", input.partyCount),
    foeCount: count("foeCount", input.foeCount),
  };
}

function strip(result) {
  const { ok, ...rest } = result;
  return rest;
}

// The formation for one input:
// {
//   stageWidth, stageHeight, uiScale, bandTop, actorHeight, topBandBottom,
//   cardWidth?   (default 264·S),
//   vitalsDock?  { left, top, width, height } in stage px, or null,
//   partyCount, foeCount
// }
// Returns { fits, scale, centre, gap: { left, right }, party, foes }, where
// each side is { ranks, form, step, figures } and each figure is
// { index, rank (0 front, 1 back), box, plate (+ form, line), marker, z }.
export function combatFormation(rawInput) {
  const input = normalise(rawInput);
  const zones = zonesFor(input);
  const frame = { centre: zones.centre, gap: zones.gap };
  for (const allowCompact of [false, true]) {
    for (const scale of SCALE_LADDER) {
      const party = fitSide(input, zones.party, "party", input.partyCount, scale, allowCompact);
      if (!party) continue;
      const foes = fitSide(input, zones.foes, "foes", input.foeCount, scale, allowCompact);
      if (!foes) continue;
      return { fits: true, scale, ...frame, party: strip(party), foes: strip(foes) };
    }
  }
  return {
    fits: false,
    scale: SCALE_FLOOR,
    ...frame,
    party: strip(layoutSide(input, zones.party, "party", input.partyCount, SCALE_FLOOR, 2, "compact")),
    foes: strip(layoutSide(input, zones.foes, "foes", input.foeCount, SCALE_FLOOR, 2, "compact")),
  };
}

// The input adapter (the only place that reads CSS values). `stageRect` and
// `vitalsRect` are viewport rectangles (DOMRect-like `{ left, top, width,
// height }`). `styles` gives RESOLVED values for `--ui-scale` (a number) and
// `--actor-h`, `--band-h`, `--header-h` (px lengths), either through a
// CSSStyleDeclaration-like `getPropertyValue` or as a plain record of numbers
// or strings keyed by those names. An unregistered custom property's computed
// value is its unresolved token text (`min(62vh, …)`), so the caller reads the
// lengths where they are resolved (for example a probe box whose height is
// `var(--actor-h)`, measured with getBoundingClientRect); an unresolved value
// throws a TypeError rather than yielding a silent NaN geometry.
// The bands are measured from the stage box's own edges, as HudFrame lays them
// out: the top band (`--header-h`) is the stage's top strip and the bottom
// band (`--band-h`) its bottom strip; the vitals rectangle is converted into
// stage coordinates. `counts` is `{ party, foes }`.
export function formationInputFromStage(stageRect, styles, vitalsRect, counts) {
  if (!stageRect || !counts) throw new TypeError("combat formation: the stage rectangle and the counts are required");
  const read = (name, unit) => {
    const value = typeof styles?.getPropertyValue === "function" ? styles.getPropertyValue(name) : styles?.[name];
    const raw = String(value ?? "").trim();
    const pattern = unit ? /^(-?\d+(?:\.\d+)?)(px)?$/ : /^(-?\d+(?:\.\d+)?)$/;
    const match = pattern.exec(raw);
    if (!match) throw new TypeError(`combat formation: ${name} is not a resolved ${unit ? "px length" : "number"}: "${raw}"`);
    return Number(match[1]);
  };
  const uiScale = read("--ui-scale", false);
  const actorHeight = read("--actor-h", true);
  const bandHeight = read("--band-h", true);
  const headerHeight = read("--header-h", true);
  // Optional: the command-line row's height; absent, the engine uses its
  // 44px·S default.
  const hasCommandLine = typeof styles?.getPropertyValue === "function"
    ? String(styles.getPropertyValue("--command-line-h") ?? "").trim() !== ""
    : styles?.["--command-line-h"] !== undefined;
  const commandLineHeight = hasCommandLine ? read("--command-line-h", true) : undefined;
  const stageWidth = Number(stageRect.width);
  const stageHeight = Number(stageRect.height);
  const vitalsDock = vitalsRect && vitalsRect.width > 0 && vitalsRect.height > 0
    ? rect(
      vitalsRect.left - stageRect.left,
      vitalsRect.top - stageRect.top,
      Number(vitalsRect.width),
      Number(vitalsRect.height),
    )
    : null;
  return {
    stageWidth,
    stageHeight,
    uiScale,
    bandTop: stageHeight - bandHeight,
    actorHeight,
    topBandBottom: headerHeight,
    cardWidth: CARD_WIDTH * uiScale,
    commandLineHeight,
    vitalsDock,
    partyCount: counts.party,
    foeCount: counts.foes,
  };
}
