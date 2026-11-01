<script>
// Module scope: one serial across every mounted map, so each instance's
// route description id is unique and stable (a leaving copy included).
let routeTextSerial = 0;
</script>

<script setup>
// TravelMap (OpenSpec changes wilderness-travel-interface and
// wilderness-travel-map-ui; interface design §4): the travel stage's
// full-bleed ink map in the HudFrame `backdrop` slot.
//
// Layers, bottom to top:
//   - the hatched fog: one surface for unknown ground inside and outside
//     the window (the painted canvas is transparent where nothing is known);
//   - the world: the painted canvas (lib/travel-paint.js, exactly
//     width x 12 by height x 12 pixels, scaled by a CSS transform), the SVG
//     overlay (live-sight ring, bearing rays, hover/aim cells, landmarks,
//     hostiles, the eight neighbour targets, the party seal) and the HTML
//     chips (names, hostile count/threat, ford, aim and hover readouts), all
//     moved together by one camera translation;
//   - screen chrome: the north mark and 5 km scale at the open stage's top
//     left, and the distant-sighting cards on the safe rectangle's edge.
//
// Repaint keys: the canvas repaints only when the grid's content signature
// (`paintSignature`) changes, once per animation frame however many
// publications arrive in it. Camera, zoom, UI scale, aim, hover, walking,
// the plan and the refresh status move or redraw overlays only.
//
// The camera follows the party (centred between the header and the band)
// or, for a locked plan while not walking, fits the party, route and
// destination between the side columns (lib/travel-camera.js). Bounds are
// measured from the real HudFrame through a ResizeObserver. It glides over
// 380 ms x --motion-travel; a zoom or a new map snaps.
//
// Status (from the base change): `ready` shows the adopted map at full
// strength; `refreshing` the last map dimmed (or the fog on a first load);
// `retired` the neutral fog; `unavailable` / `invalid` the last map dimmed
// with one status line and a 重新整理 control (the player's own input).
// Focus that was inside never falls to the document when an element goes
// away: it moves to the stage section itself. One mounted live region
// speaks the state.
//
// Intents (wilderness-travel-walking-ui, design §5): the map is one
// `role="application"` focus stop. It emits pointer `hover`/`pick` and
// `zoom`, and on its own focused root: `aim(direction)` and `hold(direction)`
// for each newly pressed arrow (two arrows combine into a diagonal through
// the compass key model), `release` when a held arrow is released or the map
// blurs, `step` for Enter and `cancel` for Escape while an aim or a walk
// stands (a bare Escape bubbles). Each keyboard intent carries its event, so
// the walking owner can tell an event that already stopped a walk. Native
// key repeat emits nothing; modified and composing keys are ignored. The
// store (stores/elosern/travel.js) owns the aim, the hold and the queue.
//
// Route preview (wilderness-travel-planning-ui, design §4.3/§5): Shift with
// an arrow emits `cursor(dx, dy)` (native repeat moves on), Enter is `step`
// whatever the cursor (the input owner decides between the aim's step and
// the cursor's lock) and Escape is `cancel` while an aim, a walk, a cursor
// or a destination stands. The SVG draws the supplied `travel.plan` result
// exactly as sent: one stage mark per step (TravelGlyph `route`, the shared
// stage-display mapping, forced_sleep keeping its severe ring plus the
// crescent), faint outlines beyond `stop_index`, dimmed steps from
// `nightfall_index`, the moon on the nightfall step, the camp mark on the
// stop step and the destination outline (a double frame when locked, a
// dashed one while only previewed). The keyboard cursor is drawn as corner
// brackets, distinct from the aim's filled cell and the lock's frame. An
// empty plan draws no route. The overlay never repaints the canvas, and a
// screen-reader summary of the route describes the map.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import WorldHatchPattern from "../WorldHatchPattern.vue";
import MapNodeGlyph from "../MapNodeGlyph.vue";
import TravelGlyph from "./TravelGlyph.vue";
import { SAMPLES_PER_CELL, paintSignature, paintTravelMap } from "../../lib/travel-paint.js";
import {
  GLIDE_MS,
  ZOOM,
  bearingAngle,
  cellSize,
  fitRouteCamera,
  followCamera,
  openStage,
  projectSightings,
  safeScale,
  stepZoom,
} from "../../lib/travel-camera.js";
import { travelCellAt } from "../../lib/travel-grid.js";
import { TRAVEL_GLYPH_CELL, TRAVEL_GLYPHS } from "../../lib/map_glyphs.js";

const G_DEST = TRAVEL_GLYPHS.destination;
const G_CURSOR = TRAVEL_GLYPHS.cursor;
const G_MOON = TRAVEL_GLYPHS.moon;
import { ARROW_KEYS, directionForKeys } from "./travel-walk-model.js";
import { stageDisplay } from "./stage-display.js";
import { routeSummary } from "./leg-model.js";

const props = defineProps({
  // The decoded travel grid (lib/travel-grid.js), or null before adoption.
  grid: { type: Object, default: null },
  // ready | refreshing | unavailable | invalid | retired
  status: { type: String, default: "refreshing" },
  // The aimed neighbour as a canonical direction word ("north", ...), or null.
  aim: { type: String, default: null },
  // The committed exit row for the aim refuses it (disabled, or no exit):
  // the aimed node is drawn blocked whatever the window's node says.
  aimBlocked: { type: Boolean, default: false },
  // The committed reason a blocked aim shows in its chip (`方位・阻擋原因`).
  aimReason: { type: String, default: null },
  // The walking state, or null while standing.
  walking: { type: Object, default: null },
  // The current travel.plan result exactly as the server sent it
  // ({origin, destination, steps: [{cell, seconds, fatigue_stage}], ...}).
  plan: { type: Object, default: null },
  // During a route walk (wilderness-travel-route-ui) the committed steps
  // already walked: their marks leave the map and the thread starts at the
  // party, while the steps beyond the stop stay as the planned future.
  routeProgress: { type: Number, default: 0 },
  locked: { type: Boolean, default: false },
  // The previewed or locked destination (`view.travel.planTarget`:
  // {x, y, label, locked}), or null.
  target: { type: Object, default: null },
  // The keyboard destination cursor ({x, y, known, party, label}), or null.
  cursor: { type: Object, default: null },
  // The supplied label of the terminal sleep stage, when known.
  sleepLabel: { type: String, default: null },
  motionLevel: { type: String, default: "full" },
  // The UI scale; null reads the stage's own `--ui-scale`.
  uiScale: { type: Number, default: null },
});
const emit = defineEmits(["aim", "hover", "pick", "step", "cancel", "hold", "release", "zoom", "retry", "cursor"]);

// The accessible name states the controls (design §5).
const CONTROLS_LABEL =
  "旅行地圖：方向鍵瞄準相鄰的格子，同時按兩個方向鍵為斜向；Enter 前進一步；按住方向鍵連續前進，放開或按任意鍵停步；" +
  "Shift＋方向鍵移動目的地游標，Enter 鎖定游標所在的已探明格子並規劃路線；Esc 依序取消瞄準、游標與路線；＋／－ 縮放。";
const SHIFT_STEPS = Object.freeze({ ArrowUp: [0, 1], ArrowDown: [0, -1], ArrowLeft: [-1, 0], ArrowRight: [1, 0] });

const DIRECTIONS = Object.freeze([
  { key: "north", dx: 0, dy: 1, word: "北" },
  { key: "northeast", dx: 1, dy: 1, word: "東北" },
  { key: "east", dx: 1, dy: 0, word: "東" },
  { key: "southeast", dx: 1, dy: -1, word: "東南" },
  { key: "south", dx: 0, dy: -1, word: "南" },
  { key: "southwest", dx: -1, dy: -1, word: "西南" },
  { key: "west", dx: -1, dy: 0, word: "西" },
  { key: "northwest", dx: -1, dy: 1, word: "西北" },
]);

// ── status ───────────────────────────────────────────────────────────────

const failed = computed(() => props.status === "unavailable" || props.status === "invalid");
const showMap = computed(() => !!props.grid && props.status !== "retired");
const stateText = computed(() =>
  props.status === "invalid" ? "無法讀取這一帶的地圖。" : "這一帶的地圖暫時無法更新。",
);
// A step's ready -> refreshing -> ready cycle keeps the same line, so a
// screen reader hears "updated" when the map first arrives, recovers or
// changes title, not on every step.
let readyLine = "";
const announcement = computed(() => {
  if (failed.value) return stateText.value;
  if (!showMap.value) return "正在展開這一帶的地圖。";
  if (props.status === "ready") readyLine = `${props.grid.title ?? ""}的地圖已更新。`;
  return readyLine;
});

const root = ref(null);
const canvas = ref(null);

function focusInside() {
  const active = typeof document === "undefined" ? null : document.activeElement;
  return !!(root.value && active && active !== root.value && root.value.contains(active));
}
function keepFocus() {
  nextTick(() => {
    const active = document.activeElement;
    if (!active || active === document.body || !root.value?.contains(active)) root.value?.focus({ preventScroll: true });
  });
}
// The retry control's removal or the map's disappearance: rescue focus that
// was inside before the patch.
watch(
  () => [failed.value, showMap.value],
  () => {
    if (focusInside()) keepFocus();
  },
  { flush: "pre" },
);
function onRetry() {
  emit("retry");
  keepFocus();
}

// ── measurement ──────────────────────────────────────────────────────────

const measured = ref({ stage: { left: 0, top: 0, right: 1200, bottom: 700 }, safe: { left: 0, top: 0, right: 1200, bottom: 700 }, scale: 1 });
let observer = null;
let observed = [];

function frameParts() {
  const stage = root.value?.closest?.(".elosern-stage") ?? null;
  return {
    stage,
    header: stage?.querySelector?.('[data-testid="stage-metrics"] [data-metric="--header-h"]') ?? null,
    band: stage?.querySelector?.('[data-testid="stage-band"]') ?? null,
    left: stage?.querySelector?.('[data-testid="anchor-vitals"]') ?? null,
    right: stage?.querySelector?.('[data-testid="anchor-map"]') ?? null,
  };
}

function rectOf(el) {
  if (!el?.getBoundingClientRect) return null;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0 ? r : null;
}

function measure() {
  const el = root.value;
  if (!el) return;
  const rootRect = el.getBoundingClientRect();
  if (!(rootRect.width > 0 && rootRect.height > 0)) return;
  const parts = frameParts();
  const styleScale =
    typeof getComputedStyle === "function" ? Number.parseFloat(getComputedStyle(el).getPropertyValue("--ui-scale")) : NaN;
  const scale = safeScale(props.uiScale ?? styleScale);
  const stageRect = rectOf(parts.stage) ?? rootRect;
  const headerH = parts.header?.getBoundingClientRect?.().height;
  const band = rectOf(parts.band);
  const { stage, safe } = openStage({
    root: rootRect,
    headerBottom: Number.isFinite(headerH) && headerH > 0 ? stageRect.top + headerH : null,
    bandTop: band ? band.top : null,
    left: rectOf(parts.left),
    right: rectOf(parts.right),
    gap: 16 * scale,
  });
  measured.value = { stage, safe, scale };
}

function observe() {
  observer?.disconnect();
  observed = [];
  if (typeof ResizeObserver !== "function") return;
  observer = new ResizeObserver(() => measure());
  const parts = frameParts();
  for (const el of [root.value, parts.band, parts.left, parts.right, parts.header]) {
    if (el) {
      observer.observe(el);
      observed.push(el);
    }
  }
}

// ── camera ───────────────────────────────────────────────────────────────

const zoom = ref(ZOOM.initial);
const uiScaleNow = computed(() => safeScale(props.uiScale ?? measured.value.scale));
const baseCell = computed(() => cellSize(zoom.value, uiScaleNow.value));

const camera = computed(() => {
  const grid = props.grid;
  if (!grid) return { tx: 0, ty: 0, cellPx: baseCell.value };
  const plan = props.plan;
  if (plan && props.locked && !props.walking) {
    const points = [grid.party, ...(Array.isArray(plan.steps) ? plan.steps.map((s) => s.cell) : []), plan.destination].filter(Boolean);
    return fitRouteCamera({ points, cellPx: baseCell.value, minCellPx: 14 * uiScaleNow.value, safe: measured.value.safe });
  }
  return followCamera({ party: grid.party, cellPx: baseCell.value, stage: measured.value.stage });
});
const c = computed(() => camera.value.cellPx);

// A zoom, a new map or the first frame snaps instead of gliding.
const snapping = ref(true);
let snapFrame = 0;
function snap() {
  snapping.value = true;
  if (typeof requestAnimationFrame !== "function") return;
  cancelAnimationFrame(snapFrame);
  snapFrame = requestAnimationFrame(() => {
    snapFrame = requestAnimationFrame(() => {
      snapping.value = false;
    });
  });
}
watch(c, snap);
watch(() => props.grid?.mapId ?? null, snap);

const worldStyle = computed(() => ({
  transform: `translate(${camera.value.tx}px, ${camera.value.ty}px)`,
  "--travel-glide": `${GLIDE_MS}ms`,
}));

// ── painting ─────────────────────────────────────────────────────────────

const painted = ref(null); // { origin, width, height } of the canvas's grid
const paintCache = {};
let paintFrame = 0;
let lastSignature = null;

function paintNow() {
  paintFrame = 0;
  const grid = props.grid;
  const el = canvas.value;
  if (!grid || !el || !showMap.value) return;
  const signature = paintSignature(grid);
  if (signature === lastSignature) return;
  const w = grid.width * SAMPLES_PER_CELL;
  const h = grid.height * SAMPLES_PER_CELL;
  if (el.width !== w) el.width = w;
  if (el.height !== h) el.height = h;
  const ctx = el.getContext?.("2d") ?? null;
  if (!ctx) return;
  paintTravelMap(ctx, grid, { cache: paintCache });
  lastSignature = signature;
  painted.value = { origin: { ...grid.origin }, width: grid.width, height: grid.height };
}

function schedulePaint() {
  if (paintFrame) return;
  if (typeof requestAnimationFrame !== "function") {
    paintNow();
    return;
  }
  paintFrame = requestAnimationFrame(paintNow);
}
watch(() => [props.grid, showMap.value], schedulePaint);

const canvasStyle = computed(() => {
  const p = painted.value;
  if (!p) return { visibility: "hidden" };
  return {
    left: `${p.origin.x * c.value}px`,
    top: `${-(p.origin.y + p.height) * c.value}px`,
    transform: `scale(${c.value / SAMPLES_PER_CELL})`,
  };
});

// ── overlay model ────────────────────────────────────────────────────────

// The overlay and chip layers sit on the current grid's window, so cell
// coordinates inside them are local to its north-west corner.
const layerStyle = computed(() => {
  const grid = props.grid;
  if (!grid) return {};
  return {
    left: `${grid.origin.x * c.value}px`,
    top: `${-(grid.origin.y + grid.height) * c.value}px`,
    width: `${grid.width * c.value}px`,
    height: `${grid.height * c.value}px`,
  };
});
function lx(x) {
  return (x - props.grid.origin.x + 0.5) * c.value;
}
function ly(y) {
  return (props.grid.origin.y + props.grid.height - 1 - y + 0.5) * c.value;
}
function cellBox(x, y, inset = 1) {
  return { x: lx(x) - c.value / 2 + inset, y: ly(y) - c.value / 2 + inset, width: c.value - inset * 2, height: c.value - inset * 2 };
}
// Never below 0.75, so the smallest target stays perceivable at minimum zoom.
const glyphScale = computed(() => Math.max(0.75, c.value / TRAVEL_GLYPH_CELL));
const party = computed(() => props.grid?.party ?? null);
const partyInWindow = computed(() => !!party.value && !!travelCellAt(props.grid, party.value.x, party.value.y));
const radius = computed(() => (typeof props.grid?.groundRadius === "number" ? props.grid.groundRadius : null));

// The server's permitted label only (schema 3 `display.terrain_label`): the
// stage never maps a terrain class to a name itself.
function terrainLabel(cell) {
  return cell.display?.terrain_label ?? "";
}

// A hostile whose canonical threat is unavailable says so; no grade is guessed.
const UNKNOWN_THREAT = "威脅不明";

const neighbours = computed(() => {
  const grid = props.grid;
  if (!grid || !partyInWindow.value || props.walking) return [];
  const out = [];
  for (const d of DIRECTIONS) {
    const cell = travelCellAt(grid, grid.party.x + d.dx, grid.party.y + d.dy);
    if (!cell) continue;
    const state = !cell.known ? "unknown" : cell.node?.action ? "open" : "blocked";
    const aimedHere = props.aim === d.key && state === "open";
    out.push({ ...d, cell, state: aimedHere ? (props.aimBlocked ? "blocked" : "aimed") : state });
  }
  return out;
});
const aimed = computed(() => neighbours.value.find((n) => n.key === props.aim) ?? null);
const aimText = computed(() => {
  const n = aimed.value;
  if (!n) return "";
  if (n.state === "blocked" && props.aimReason) return `${n.word}・${props.aimReason}`;
  return `${n.word}・${n.cell.known ? terrainLabel(n.cell) : "未探明"}`;
});

const landmarks = computed(() =>
  (props.grid?.cells ?? [])
    .filter((cell) => cell.known && typeof cell.node?.landmark?.name === "string" && cell.node.landmark.name)
    .map((cell) => ({ key: `${cell.x}:${cell.y}`, x: cell.x, y: cell.y, name: cell.node.landmark.name })),
);
// One label per crossing: a ford cell within three cells of an already-labelled one of
// the same name (a crossing several cells long) adds no second chip.
const fords = computed(() => {
  const out = [];
  for (const cell of props.grid?.cells ?? []) {
    const label = cell.known && cell.ford ? cell.display?.ford_label : null;
    if (typeof label !== "string" || !label) continue;
    if (out.some((f) => f.label === label && Math.abs(f.x - cell.x) <= 3 && Math.abs(f.y - cell.y) <= 3)) continue;
    out.push({ key: `${cell.x}:${cell.y}`, x: cell.x, y: cell.y, label });
  }
  return out;
});
const hostiles = computed(() =>
  (props.grid?.entities ?? [])
    .filter((e) => e?.hostile === true && e.cell && travelCellAt(props.grid, e.cell.x, e.cell.y))
    .map((e) => ({
      id: e.id,
      x: e.cell.x,
      y: e.cell.y,
      label: e.label,
      count: Number.isSafeInteger(e.count) && e.count > 0 ? e.count : 1,
      threat: typeof e.threat === "string" && e.threat ? e.threat : null,
    })),
);

// One chip per pack: hostiles with the same supplied label and threat within
// two cells of each other share one label with their summed count. Every
// token is still drawn on its own cell; only the text is shared, so packs
// never stack chips over each other's seals.
const hostilePacks = computed(() => {
  const packs = [];
  for (const h of hostiles.value) {
    const pack = packs.find(
      (p) => p.label === h.label && p.threat === h.threat && p.members.some((m) => Math.max(Math.abs(m.x - h.x), Math.abs(m.y - h.y)) <= 2),
    );
    if (pack) pack.members.push(h);
    else packs.push({ label: h.label, threat: h.threat, members: [h] });
  }
  return packs.map((p) => {
    const count = p.members.reduce((sum, m) => sum + m.count, 0);
    const x = p.members.reduce((sum, m) => sum + m.x, 0) / p.members.length;
    const meanY = p.members.reduce((sum, m) => sum + m.y, 0) / p.members.length;
    // The chip sits on the far side of the pack from the party, so a pack
    // beside the party never hides its seal.
    const above = !!party.value && meanY > party.value.y;
    const ys = p.members.map((m) => m.y);
    return {
      key: p.members[0].id,
      label: p.label,
      count: count > 1 ? count : null,
      threat: p.threat,
      x,
      y: above ? Math.max(...ys) : Math.min(...ys),
      above,
    };
  });
});

// Static chips with a light collision pass: each chip's box is estimated
// from its text at the chip font (16 px × UI scale), and a chip that would
// cover an earlier chip or the party seal steps away from its anchor
// (upward for a chip above its mark, downward otherwise).
function textUnits(text) {
  let units = 0;
  for (const ch of text) units += ch.codePointAt(0) > 0x2e7f ? 1 : 0.58;
  return units;
}
const placedChips = computed(() => {
  if (!props.grid) return [];
  const s = uiScaleNow.value;
  const font = 16 * s;
  const h = font * 1.35 + 4 * s + 2;
  const boxes = [];
  if (partyInWindow.value) {
    const r = c.value * 0.5;
    boxes.push([lx(party.value.x) - r, ly(party.value.y) - r, lx(party.value.x) + r, ly(party.value.y) + r]);
  }
  const hits = (b) => boxes.some((o) => b[0] < o[2] && o[0] < b[2] && b[1] < o[3] && o[1] < b[3]);
  const place = (chip) => {
    const w = textUnits(chip.text) * font * 1.04 + 20 * s;
    for (let step = 0; step < 4; step += 1) {
      const top = chip.above ? chip.top - step * h : chip.top + step * h;
      const box = chip.above ? [chip.left - w / 2, top - h, chip.left + w / 2, top] : [chip.left - w / 2, top, chip.left + w / 2, top + h];
      if (!hits(box) || step === 3) {
        boxes.push(box);
        return { ...chip, top };
      }
    }
    return chip;
  };
  const out = [];
  for (const l of landmarks.value) {
    out.push(place({ key: `chip-${l.key}`, kind: "landmark", text: l.name, name: l.name, left: lx(l.x), top: ly(l.y) - c.value * 0.55, above: true }));
  }
  for (const p of hostilePacks.value) {
    const text = `${p.label}${p.count ? ` ×${p.count}` : ""}・${p.threat ?? UNKNOWN_THREAT}`;
    const top = p.above ? ly(p.y) - c.value * 0.52 : ly(p.y) + c.value * 0.48;
    out.push(place({ key: `chip-${p.key}`, kind: "hostile", text, pack: p, left: lx(p.x), top, above: p.above }));
  }
  for (const f of fords.value) {
    out.push(place({ key: `ford-${f.key}`, kind: "ford", text: f.label, label: f.label, left: lx(f.x), top: ly(f.y) + c.value * 0.5, above: false }));
  }
  return out;
});

// ── route preview (wilderness-travel-planning-ui) ──────────────────────

// One mark per supplied step, by the shared stage mapping; nothing derived.
const routeSteps = computed(() => {
  const plan = props.plan;
  if (!props.grid || !plan || !Array.isArray(plan.steps) || plan.steps.length === 0) return [];
  const stop = Number.isInteger(plan.stop_index) ? plan.stop_index : null;
  const night = Number.isInteger(plan.nightfall_index) ? plan.nightfall_index : null;
  const walked = Math.max(0, props.routeProgress | 0);
  return plan.steps.flatMap((step, index) => {
    if (index < walked) return [];
    const display = stageDisplay(step.fatigue_stage) ?? { bucket: "normal", sleep: false };
    return {
      index,
      x: step.cell.x,
      y: step.cell.y,
      stage: step.fatigue_stage,
      bucket: display.bucket,
      sleep: display.sleep,
      beyond: stop !== null && index > stop,
      night: night !== null && index >= night,
    };
  });
});
const routeMarks = computed(() => {
  const plan = props.plan;
  const steps = routeSteps.value;
  if (!steps.length) return { moon: null, camp: null };
  const at = (i) => (Number.isInteger(i) ? steps.find((s) => s.index === i) ?? null : null);
  return {
    moon: at(plan.nightfall_index),
    camp: plan.stop_reason !== "destination_reached" ? at(plan.stop_index) : null,
  };
});
// The line through the steps: solid to the stop, dashed beyond it.
const routeLines = computed(() => {
  const steps = routeSteps.value;
  if (!steps.length || !party.value) return { walked: "", beyond: "" };
  const point = (p) => `${lx(p.x)} ${ly(p.y)}`;
  const kept = steps.filter((s) => !s.beyond);
  const walked = [party.value, ...kept].map((p, i) => `${i ? "L" : "M"}${point(p)}`).join(" ");
  const rest = steps.filter((s) => s.beyond);
  const last = kept.length ? kept[kept.length - 1] : party.value;
  const beyond = rest.length ? [last, ...rest].map((p, i) => `${i ? "L" : "M"}${point(p)}`).join(" ") : "";
  return { walked, beyond };
});
const destination = computed(() => {
  const t = props.target;
  if (!props.grid || !t) return null;
  const inset = c.value * G_DEST.inset;
  const inner = c.value * G_DEST.inner;
  return {
    x: t.x,
    y: t.y,
    locked: !!t.locked,
    outer: cellBox(t.x, t.y, inset),
    inner: cellBox(t.x, t.y, inner),
    radius: c.value * G_DEST.radius,
  };
});
// The destination chip: its supplied name and the plan's step count.
const destinationChip = computed(() => {
  const d = destination.value;
  if (!d) return null;
  const plan = props.plan;
  const steps = plan && Array.isArray(plan.steps) && plan.steps.length && Number.isInteger(plan.stop_index) ? plan.stop_index + 1 : null;
  const label = props.target.label || "目的地";
  // A moon or camp mark on the destination sits above its cell: the chip
  // rises over it instead of covering it.
  const marks = routeMarks.value;
  const marked = [marks.moon, marks.camp].some((m) => m && m.x === d.x && m.y === d.y);
  return { left: lx(d.x), top: ly(d.y) - c.value * (marked ? 1.05 : 0.62), label, steps, locked: d.locked };
});
const cursorPath = computed(() => {
  const k = props.cursor;
  if (!props.grid || !k) return null;
  const half = c.value / 2 - c.value * G_CURSOR.inset;
  const arm = c.value * G_CURSOR.arm;
  const cx = lx(k.x);
  const cy = ly(k.y);
  const corner = (sx, sy) => `M${cx + sx * half} ${cy + sy * (half - arm)} L${cx + sx * half} ${cy + sy * half} L${cx + sx * (half - arm)} ${cy + sy * half}`;
  return { d: [corner(-1, -1), corner(1, -1), corner(1, 1), corner(-1, 1)].join(" "), known: !!k.known };
});
// Route marks read a little larger than the neighbour targets, so a stage
// stays legible over busy terrain at every zoom.
const routeScale = computed(() => glyphScale.value * TRAVEL_GLYPHS.route.scale);
const routeText = computed(() => routeSummary(props.plan, { label: props.target?.label ?? null, sleepLabel: props.sleepLabel }));
const routeTextId = `travel-route-${++routeTextSerial}`;

const hoverCell = ref(null);
const hoverInfo = computed(() => {
  const h = hoverCell.value;
  const grid = props.grid;
  if (!h || !grid || props.walking) return null;
  const cell = travelCellAt(grid, h.x, h.y);
  if (!cell) return null;
  if (!cell.known) return { ...h, text: "未探明", known: false };
  const name = cell.node?.landmark?.name;
  return { ...h, text: name || terrainLabel(cell), known: true };
});

// Bearing rays leave the party past its live sight.
const rays = computed(() => {
  const grid = props.grid;
  if (!grid || !partyInWindow.value) return [];
  const r = radius.value ?? 2;
  return (grid.sightings ?? [])
    .map((s, index) => ({ s, index, angle: bearingAngle(s?.bearing) }))
    .filter((item) => item.angle !== null)
    .map(({ index, angle }) => {
      const ux = Math.sin(angle);
      const uy = -Math.cos(angle);
      const ox = lx(grid.party.x);
      const oy = ly(grid.party.y);
      return {
        key: `ray-${index}`,
        x1: ox + ux * (r + 1) * c.value,
        y1: oy + uy * (r + 1) * c.value,
        x2: ox + ux * (r + 4.5) * c.value,
        y2: oy + uy * (r + 4.5) * c.value,
      };
    });
});

const sightingCards = computed(() => {
  const grid = props.grid;
  if (!grid) return [];
  const s = uiScaleNow.value;
  return projectSightings(grid.sightings ?? [], { safe: measured.value.safe, inset: { x: 120 * s, y: 38 * s } }).map(
    (item, index) => ({
      key: `${index}:${item.sighting.bearing}`,
      left: `${item.x}px`,
      top: `${item.y}px`,
      head: `${item.sighting.bearing}・約 ${item.sighting.distance_km} 公里`,
      body: item.sighting.silhouette_zh,
      name: item.sighting.name ?? null,
    }),
  );
});

const legendStyle = computed(() => {
  const s = uiScaleNow.value;
  return { left: `${measured.value.stage.left + 22 * s}px`, top: `${measured.value.stage.top + 18 * s}px` };
});
const scaleBar = computed(() => {
  const km = props.grid?.cellKm;
  return Number.isFinite(km) && km > 0 ? (5 / km) * c.value : null;
});

// ── pointer and zoom ─────────────────────────────────────────────────────

// The world layer's live on-screen origin, so a pointer mid-glide resolves
// against what is drawn, not where the camera is heading.
const world = ref(null);
function cellFromEvent(event) {
  const grid = props.grid;
  if (!grid || !world.value) return null;
  const origin = world.value.getBoundingClientRect();
  const wx = event.clientX - origin.left;
  const wy = event.clientY - origin.top;
  const x = Math.floor(wx / c.value);
  const y = Math.ceil(-wy / c.value) - 1;
  return travelCellAt(grid, x, y) ? { x, y } : null;
}
function sameCell(a, b) {
  return a === b || (!!a && !!b && a.x === b.x && a.y === b.y);
}
const interactive = computed(() => showMap.value && props.status === "ready");
function clearHover() {
  if (hoverCell.value === null) return;
  hoverCell.value = null;
  emit("hover", null);
}
// A map that stops being the current one drops its hover.
watch(interactive, (now) => {
  if (!now) clearHover();
});
function onPointerMove(event) {
  if (props.walking || !interactive.value) return;
  const cell = cellFromEvent(event);
  if (sameCell(cell, hoverCell.value)) return;
  hoverCell.value = cell;
  emit("hover", cell);
}
function onPointerLeave() {
  clearHover();
}
function onClick(event) {
  if (event.target?.closest?.(".travel-map__state")) return;
  root.value?.focus({ preventScroll: true });
  if (!interactive.value) return;
  const cell = cellFromEvent(event);
  if (cell) emit("pick", cell);
}
function zoomBy(direction) {
  const next = stepZoom(zoom.value, direction);
  if (next === zoom.value) return;
  zoom.value = next;
  emit("zoom", next);
}
// Wheel travel accumulates to one zoom step per notch (100 px of delta), so
// a trackpad's stream of small deltas does not slam the zoom to a clamp.
const WHEEL_STEP = 100;
let wheelTravel = 0;
function onWheel(event) {
  if (!showMap.value || event.deltaY === 0) return;
  event.preventDefault();
  const unit = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 800 : 1;
  if (Math.sign(event.deltaY) !== Math.sign(wheelTravel)) wheelTravel = 0;
  wheelTravel += event.deltaY * unit;
  while (Math.abs(wheelTravel) >= WHEEL_STEP) {
    zoomBy(wheelTravel < 0 ? 1 : -1);
    wheelTravel -= Math.sign(wheelTravel) * WHEEL_STEP;
  }
}
// The arrows held on the focused map, in press order.
const pressed = new Set();
function modified(event) {
  return event.ctrlKey || event.altKey || event.metaKey || event.isComposing || event.keyCode === 229;
}
function consume(event) {
  event.preventDefault();
  event.stopPropagation();
}
function onKeyDown(event) {
  if (event.target !== root.value || modified(event)) return;
  if (ARROW_KEYS.includes(event.key)) {
    if (event.shiftKey) {
      // The destination cursor: one cell per press, native repeat included.
      consume(event);
      const [dx, dy] = SHIFT_STEPS[event.key];
      emit("cursor", dx, dy, event);
      return;
    }
    consume(event);
    // Native repeat of a held arrow is no new input: the walk owner reads
    // it as the hold's continuation.
    if (event.repeat || pressed.has(event.key)) return;
    pressed.add(event.key);
    const direction = directionForKeys(pressed);
    if (direction) {
      emit("aim", direction, event);
      emit("hold", direction, event);
    }
    return;
  }
  if (event.key === "Enter") {
    consume(event);
    if (!event.repeat) emit("step", event);
    return;
  }
  if (event.key === "Escape") {
    if (!props.aim && !props.walking && !props.cursor && !props.target) return;
    consume(event);
    emit("cancel", event);
    return;
  }
  if (event.key === "+" || event.key === "=") {
    event.preventDefault();
    event.stopPropagation();
    zoomBy(1);
  } else if (event.key === "-" || event.key === "_") {
    event.preventDefault();
    event.stopPropagation();
    zoomBy(-1);
  }
}

function onKeyUp(event) {
  if (pressed.delete(event.key)) {
    event.stopPropagation();
    emit("release", event);
  }
}
function onBlur() {
  const held = pressed.size > 0;
  pressed.clear();
  if (held || props.walking) emit("release", null);
}

// ── lifecycle ────────────────────────────────────────────────────────────

function onWindowResize() {
  measure();
}
onMounted(() => {
  measure();
  observe();
  if (typeof window !== "undefined") window.addEventListener("resize", onWindowResize);
  snap();
  schedulePaint();
});
watch(() => props.uiScale, measure);
onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
  observed = [];
  if (typeof window !== "undefined") window.removeEventListener("resize", onWindowResize);
  if (typeof cancelAnimationFrame === "function") {
    cancelAnimationFrame(paintFrame);
    cancelAnimationFrame(snapFrame);
  }
  paintFrame = 0;
});

defineExpose({ focusInside, focus: () => root.value?.focus({ preventScroll: true }), el: () => root.value });
</script>

<template>
  <section
    class="travel-map"
    :class="{ 'is-night': grid?.lightPhase === 'night', 'is-walking': !!walking }"
    data-testid="travel-map"
    :data-map-status="status"
    :data-map-shown="showMap ? 'true' : 'false'"
    :data-motion="motionLevel"
    :data-zoom="zoom"
    :data-cell-px="c"
    role="application"
    :aria-label="CONTROLS_LABEL"
    :aria-describedby="routeText ? routeTextId : null"
    tabindex="0"
    ref="root"
    @pointermove="onPointerMove"
    @pointerleave="onPointerLeave"
    @click="onClick"
    @wheel="onWheel"
    @keydown="onKeyDown"
    @keyup="onKeyUp"
    @blur="onBlur"
  >
    <svg class="travel-map__fog" aria-hidden="true" focusable="false">
      <defs><WorldHatchPattern id="travel-map-fog" /></defs>
      <rect width="100%" height="100%" fill="url(#travel-map-fog)" />
    </svg>
    <div
      v-show="showMap"
      ref="world"
      class="travel-map__world"
      :class="{ 'is-snap': snapping }"
      :style="worldStyle"
      data-testid="travel-map__world"
    >
      <canvas ref="canvas" class="travel-map__canvas" :style="canvasStyle" data-testid="travel-map__canvas" aria-hidden="true"></canvas>
      <template v-if="grid">
        <svg
          class="travel-map__overlay"
          :style="layerStyle"
          :width="grid.width * c"
          :height="grid.height * c"
          aria-hidden="true"
          focusable="false"
          data-testid="travel-map__overlay"
        >
          <circle
            v-if="radius !== null && partyInWindow"
            class="travel-map__sight"
            data-testid="travel-map__sight"
            :cx="lx(party.x)"
            :cy="ly(party.y)"
            :r="(radius + 0.5) * c"
          />
          <line v-for="ray in rays" :key="ray.key" class="travel-map__ray" :x1="ray.x1" :y1="ray.y1" :x2="ray.x2" :y2="ray.y2" />
          <rect
            v-if="hoverInfo"
            class="travel-map__hover"
            :class="{ 'is-fog': !hoverInfo.known }"
            data-testid="travel-map__hover"
            v-bind="cellBox(hoverInfo.x, hoverInfo.y, 1)"
            rx="2"
          />
          <rect
            v-if="aimed && aimed.state === 'aimed'"
            class="travel-map__aim-cell"
            v-bind="cellBox(aimed.cell.x, aimed.cell.y, 1)"
            rx="3"
          />
          <g
            v-if="destination"
            class="travel-map__destination"
            :class="{ 'is-locked': destination.locked }"
            data-testid="travel-map__destination"
            :data-locked="destination.locked ? 'true' : 'false'"
          >
            <rect class="travel-map__destination-outer" v-bind="destination.outer" :rx="destination.radius" />
            <rect v-if="destination.locked" class="travel-map__destination-inner" v-bind="destination.inner" :rx="destination.radius * 0.6" />
          </g>
          <g v-if="routeSteps.length" class="travel-map__route" data-testid="travel-map__route">
            <path v-if="routeLines.walked" class="travel-map__route-casing" :d="routeLines.walked" />
            <path v-if="routeLines.walked" class="travel-map__route-line" :d="routeLines.walked" />
            <path v-if="routeLines.beyond" class="travel-map__route-line is-beyond" :d="routeLines.beyond" />
            <g
              v-for="step in routeSteps"
              :key="`route-${step.index}`"
              class="travel-map__route-step"
              :class="{ 'is-beyond': step.beyond, 'is-night': step.night }"
              :transform="`translate(${lx(step.x)} ${ly(step.y)})`"
              data-testid="travel-map__route-step"
              :data-index="step.index"
              :data-stage="step.stage"
              :data-bucket="step.bucket"
              :data-sleep="step.sleep ? 'true' : null"
              :data-beyond="step.beyond ? 'true' : null"
              :data-night="step.night ? 'true' : null"
            >
              <TravelGlyph kind="route" :state="step.bucket" :sleep="step.sleep" :faint="step.beyond" :size="routeScale" />
            </g>
            <g
              v-if="routeMarks.moon"
              :transform="`translate(${lx(routeMarks.moon.x) - c * G_MOON.lift} ${ly(routeMarks.moon.y) - c * G_MOON.lift})`"
              data-testid="travel-map__route-moon"
              :data-index="routeMarks.moon.index"
            >
              <TravelGlyph kind="moon" :size="routeScale" />
            </g>
            <g
              v-if="routeMarks.camp"
              :transform="`translate(${lx(routeMarks.camp.x) + c * G_MOON.lift} ${ly(routeMarks.camp.y) - c * G_MOON.lift})`"
              data-testid="travel-map__route-camp"
              :data-index="routeMarks.camp.index"
            >
              <TravelGlyph kind="camp" :size="routeScale" />
            </g>
          </g>
          <path
            v-if="cursorPath"
            class="travel-map__cursor"
            :class="{ 'is-fog': !cursorPath.known }"
            :d="cursorPath.d"
            data-testid="travel-map__cursor"
          />
          <g v-for="l in landmarks" :key="l.key" :transform="`translate(${lx(l.x)} ${ly(l.y)})`">
            <TravelGlyph kind="landmark" :size="glyphScale * 2.2" test-id="travel-map__landmark" />
          </g>
          <g v-for="h in hostiles" :key="h.id" :transform="`translate(${lx(h.x)} ${ly(h.y)})`">
            <TravelGlyph kind="hostile" :size="glyphScale" test-id="travel-map__hostile" />
          </g>
          <g v-for="n in neighbours" :key="n.key" :transform="`translate(${lx(n.cell.x)} ${ly(n.cell.y)})`">
            <TravelGlyph kind="neighbour" :state="n.state" :size="glyphScale" test-id="travel-map__neighbour" />
          </g>
          <g v-if="partyInWindow" class="travel-map__party" :transform="`translate(${lx(party.x)} ${ly(party.y)})`">
            <MapNodeGlyph state="party" :size="glyphScale" :test-ids="{ marker: 'travel-map__party' }" />
          </g>
        </svg>
        <div class="travel-map__chips" :style="layerStyle" aria-hidden="true">
          <template v-for="chip in placedChips" :key="chip.key">
            <div
              v-if="chip.kind === 'landmark'"
              class="tm-chip tm-chip--gold"
              data-side="above"
              :style="{ left: `${chip.left}px`, top: `${chip.top}px` }"
            >{{ chip.name }}</div>
            <div
              v-else-if="chip.kind === 'hostile'"
              class="tm-chip tm-chip--seal"
              :data-side="chip.above ? 'above' : null"
              :style="{ left: `${chip.left}px`, top: `${chip.top}px` }"
              data-testid="travel-map__hostile-chip"
            >{{ chip.pack.label }}<template v-if="chip.pack.count"> ×{{ chip.pack.count }}</template>・<b v-if="chip.pack.threat">{{ chip.pack.threat }}</b><i v-else class="tm-chip__unknown">{{ UNKNOWN_THREAT }}</i></div>
            <div
              v-else
              class="tm-chip tm-chip--quiet"
              :style="{ left: `${chip.left}px`, top: `${chip.top}px` }"
            >{{ chip.label }}</div>
          </template>
          <div
            v-if="aimed"
            class="tm-chip tm-chip--aim"
            :class="{ 'is-blocked': aimed.state !== 'aimed' }"
            data-testid="travel-map__aim-chip"
            :data-side="aimed.dx >= 0 ? 'right' : 'left'"
            :style="{ left: `${lx(aimed.cell.x) + (aimed.dx >= 0 ? c * 0.7 : -c * 0.7)}px`, top: `${ly(aimed.cell.y)}px` }"
          >{{ aimText }}</div>
          <div
            v-if="destinationChip"
            class="tm-chip tm-chip--route"
            :class="{ 'is-locked': destinationChip.locked }"
            data-side="above"
            data-testid="travel-map__destination-chip"
            :style="{ left: `${destinationChip.left}px`, top: `${destinationChip.top}px` }"
          ><span class="tm-chip__flag" aria-hidden="true">{{ destinationChip.locked ? "◆" : "◇" }}</span>{{ destinationChip.label }}<template v-if="destinationChip.steps">・{{ destinationChip.steps }} 步</template></div>
          <div
            v-if="!aimed && hoverInfo && !(destination && destination.x === hoverInfo.x && destination.y === hoverInfo.y)"
            class="tm-chip"
            :class="hoverInfo.known ? 'tm-chip--paper' : 'tm-chip--quiet'"
            data-side="above"
            data-testid="travel-map__hover-chip"
            :style="{ left: `${lx(hoverInfo.x)}px`, top: `${ly(hoverInfo.y) - c * 0.6}px` }"
          >{{ hoverInfo.text }}</div>
        </div>
      </template>
    </div>
    <div v-if="showMap" class="tm-legend" :style="legendStyle" aria-hidden="true" data-testid="travel-map__legend">
      <svg class="tm-legend__rose" viewBox="-20 -20 40 40">
        <circle r="15" class="tm-legend__ring" />
        <path d="M0 -17 L4 0 L0 4 L-4 0 Z" class="tm-legend__north" />
        <path d="M0 17 L4 0 L0 -4 L-4 0 Z" class="tm-legend__south" />
        <path d="M-17 0 L0 -2.5 L17 0 L0 2.5 Z" class="tm-legend__south" />
      </svg>
      <span class="tm-legend__n">北</span>
      <span v-if="scaleBar !== null" class="tm-legend__scale">
        <span class="tm-legend__bar" data-testid="travel-map__scale-bar" :style="{ width: `${scaleBar}px` }"></span>
        5 公里
      </span>
    </div>
    <template v-if="showMap">
      <div
        v-for="card in sightingCards"
        :key="card.key"
        class="tm-sighting"
        data-testid="travel-map__sighting"
        :style="{ left: card.left, top: card.top }"
      >
        <span class="tm-sighting__bearing">{{ card.head }}</span>
        <span class="tm-sighting__what">{{ card.body }}<template v-if="card.name">（{{ card.name }}）</template></span>
      </div>
    </template>
    <p class="travel-map__live" role="status" data-testid="travel-map__live">{{ announcement }}</p>
    <p v-if="routeText" :id="routeTextId" class="travel-map__live" data-testid="travel-map__route-text">{{ routeText }}</p>
    <div v-if="failed" class="travel-map__state" data-testid="travel-map__state">
      <span class="travel-map__state-text">{{ stateText }}</span>
      <button
        type="button"
        class="travel-map__retry"
        data-testid="travel-map__retry"
        @click="onRetry"
        @keydown.enter.stop
        @keydown.space.stop
      >重新整理</button>
    </div>
  </section>
</template>

<style>
/* The full-bleed ink ground: the one hatched fog surface under the map, so
   unknown land inside and outside the window reads as one cloth. */
.travel-map {
  position: absolute;
  inset: 0;
  z-index: 0;
  overflow: hidden;
  outline: none;
  cursor: crosshair;
  background:
    radial-gradient(90% 80% at 50% 42%, #221f1a 0%, #161411 52%, var(--ink-950) 100%);
}
/* The focus ring is an inset frame around the open stage, clear of the
   header and the band. */
.travel-map:focus-visible::after {
  content: "";
  position: absolute;
  inset: calc(var(--header-h) + 6px * var(--ui-scale)) calc(6px * var(--ui-scale)) calc(var(--band-h) + 6px * var(--ui-scale));
  border: 1px solid rgba(228, 200, 142, 0.42);
  border-radius: var(--radius);
  box-shadow: inset 0 0 0 1px rgba(228, 200, 142, 0.12);
  pointer-events: none;
}
.travel-map__live {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}
.travel-map__fog {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
}
/* The world layer: one translation moves the canvas, the overlay and the
   chips together. It glides at full motion and lands at once otherwise. */
.travel-map__world {
  /* The camera glide in ms; the inline style binds GLIDE_MS, and an unbound
     layer lands at once like the snap states. */
  --travel-glide: 0ms;
  position: absolute;
  left: 0;
  top: 0;
  width: 0;
  height: 0;
  transition:
    transform calc(var(--travel-glide) * var(--motion-travel)) var(--ease-standard),
    opacity var(--motion-base) var(--ease-standard),
    filter var(--motion-base) var(--ease-standard);
  will-change: transform;
}
.travel-map__world.is-snap,
.travel-map[data-motion="off"] .travel-map__world {
  transition: opacity var(--motion-base) var(--ease-standard), filter var(--motion-base) var(--ease-standard);
}
.travel-map[data-motion="off"] .travel-map__world {
  transition: none;
}
/* A map that is not the current one yet is drawn as memory: dimmed and
   drained, so the stale image never reads as the present. */
.travel-map:not([data-map-status="ready"]) .travel-map__world {
  opacity: 0.55;
  filter: saturate(0.45) brightness(0.8);
}
.travel-map__canvas {
  position: absolute;
  transform-origin: 0 0;
  image-rendering: auto;
}
.travel-map__overlay,
.travel-map__chips {
  position: absolute;
  overflow: visible;
  pointer-events: none;
}

.travel-map__sight {
  fill: none;
  stroke: rgba(242, 236, 223, 0.26);
  stroke-width: 1;
  stroke-dasharray: 2 6;
}
.travel-map.is-night .travel-map__sight {
  stroke: rgba(170, 190, 230, 0.36);
}
.travel-map__ray {
  stroke: rgba(228, 200, 142, 0.5);
  stroke-width: 1.2;
  stroke-dasharray: 1 6;
  stroke-linecap: round;
}
.travel-map__hover {
  fill: rgba(242, 236, 223, 0.06);
  stroke: rgba(242, 236, 223, 0.5);
  stroke-width: 1;
}
.travel-map__hover.is-fog {
  fill: none;
  stroke: rgba(242, 236, 223, 0.24);
  stroke-dasharray: 3 3;
}
.travel-map__aim-cell {
  fill: rgba(228, 200, 142, 0.14);
  stroke: var(--gold-400);
  stroke-width: 1.2;
}

/* The route preview (wilderness-travel-planning-ui): a faint gold thread
   through the steps (dashed past the stop), the stage marks above it,
   dimmed from nightfall; the destination frame and the keyboard cursor. */
/* The thread is paper-gold on an ink casing, so it never reads as the
   painted road's gold dash beneath it. */
.travel-map__route-casing {
  fill: none;
  stroke: rgba(11, 13, 16, 0.55);
  stroke-width: 4.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.travel-map__route-line {
  fill: none;
  stroke: rgba(242, 222, 170, 0.78);
  stroke-width: 1.6;
  stroke-linecap: round;
  stroke-linejoin: round;
}
.travel-map__route-line.is-beyond {
  stroke: rgba(186, 181, 174, 0.3);
  stroke-width: 1.4;
  stroke-dasharray: 2 5;
}
.travel-map__route-step.is-night {
  opacity: 0.6;
}
.travel-map__route-step.is-beyond {
  opacity: 0.55;
}
.travel-map.is-walking .travel-map__route {
  opacity: 0.8;
}
.travel-map__destination-outer {
  fill: rgba(228, 200, 142, 0.08);
  stroke: var(--gold-400);
  stroke-width: 1.4;
  stroke-dasharray: 4 3;
}
.travel-map__destination.is-locked .travel-map__destination-outer {
  fill: rgba(228, 200, 142, 0.14);
  stroke-width: 1.8;
  stroke-dasharray: none;
  filter: drop-shadow(0 0 4px rgba(228, 200, 142, 0.35));
}
.travel-map__destination-inner {
  fill: none;
  stroke: rgba(242, 222, 170, 0.7);
  stroke-width: 1;
}
.travel-map__cursor {
  fill: none;
  stroke: var(--paper-50);
  stroke-width: 2;
  stroke-linecap: square;
  filter: drop-shadow(0 0 3px rgba(0, 0, 0, 0.9));
}
.travel-map__cursor.is-fog {
  stroke: var(--paper-400);
  stroke-dasharray: 2 2;
}

.tm-chip {
  position: absolute;
  transform: translate(-50%, 0);
  white-space: nowrap;
  padding: calc(2px * var(--ui-scale)) calc(9px * var(--ui-scale));
  border-radius: calc(4px * var(--ui-scale));
  font: var(--text-xs)/1.35 var(--f-sans);
  letter-spacing: 0.04em;
  pointer-events: none;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.45);
}
.tm-chip[data-side="right"] {
  transform: translate(0, -50%);
}
.tm-chip[data-side="left"] {
  transform: translate(-100%, -50%);
}
.tm-chip[data-side="above"] {
  transform: translate(-50%, -100%);
}
.tm-chip--gold {
  color: var(--gold-300);
  background: rgba(15, 17, 21, 0.88);
  border: 1px solid rgba(143, 113, 60, 0.9);
  font-family: var(--f-serif);
}
.tm-chip--seal {
  color: #f2d6d0;
  background: rgba(52, 16, 18, 0.9);
  border: 1px solid var(--seal-600);
}
.tm-chip--seal b {
  font-weight: 600;
  color: #ffb4a6;
}
/* An unavailable threat reads as a quieter, dotted aside: a distinct shape,
   not just a paler colour, so it never passes for a grade. */
.tm-chip__unknown {
  font-style: normal;
  color: rgba(242, 214, 208, 0.72);
  border-bottom: 1px dotted rgba(242, 214, 208, 0.55);
}
.tm-chip--quiet {
  color: var(--paper-400);
  background: rgba(15, 17, 21, 0.72);
  border: 1px dashed rgba(186, 181, 174, 0.3);
}
.tm-chip--paper {
  color: var(--paper-50);
  background: rgba(15, 17, 21, 0.86);
  border: 1px solid rgba(242, 236, 223, 0.25);
}
.tm-chip--aim {
  color: var(--gold-300);
  background: rgba(15, 17, 21, 0.9);
  border: 1px solid var(--gold-600);
}
/* The destination chip: dashed while only previewed, a gold plate once
   locked; the flag differs by shape (open or filled diamond). */
.tm-chip--route {
  color: var(--gold-300);
  background: rgba(15, 17, 21, 0.86);
  border: 1px dashed rgba(185, 154, 96, 0.7);
  font-family: var(--f-serif);
}
.tm-chip--route.is-locked {
  background: linear-gradient(180deg, rgba(36, 30, 20, 0.94), rgba(15, 17, 21, 0.94));
  border: 1px solid var(--gold-500);
}
.tm-chip__flag {
  margin-right: calc(6px * var(--ui-scale));
  color: var(--gold-400);
}
.tm-chip--aim.is-blocked {
  color: var(--paper-400);
  border-style: dashed;
  border-color: var(--paper-700);
}

/* Orientation: a north mark and a five-kilometre bar at the open stage's
   top left, in the band ornament's gold. */
.tm-legend {
  position: absolute;
  z-index: 1;
  display: grid;
  grid-template-columns: auto auto;
  align-items: center;
  column-gap: calc(10px * var(--ui-scale));
  row-gap: calc(4px * var(--ui-scale));
  pointer-events: none;
}
.tm-legend__rose {
  width: calc(44px * var(--ui-scale));
  height: calc(44px * var(--ui-scale));
  grid-row: span 2;
  filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.5));
}
.tm-legend__ring {
  fill: rgba(11, 13, 16, 0.72);
  stroke: rgba(185, 154, 96, 0.6);
  stroke-width: 0.8;
}
.tm-legend__north {
  fill: var(--gold-400);
}
.tm-legend__south {
  fill: rgba(186, 181, 174, 0.45);
}
.tm-legend__n {
  font: var(--text-xs)/1 var(--f-display);
  color: var(--gold-400);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
}
.tm-legend__scale {
  display: grid;
  gap: calc(3px * var(--ui-scale));
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--paper-300);
  text-shadow: 0 1px 4px rgba(0, 0, 0, 0.8);
}
.tm-legend__bar {
  display: block;
  height: calc(5px * var(--ui-scale));
  border: 1px solid rgba(201, 196, 185, 0.7);
  border-top: 0;
  transition: width var(--motion-base) var(--ease-standard);
}
/* Distant sightings: cards on the safe rectangle's edge along their bearing. */
.tm-sighting {
  position: absolute;
  z-index: 1;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: calc(1px * var(--ui-scale));
  padding: calc(5px * var(--ui-scale)) calc(12px * var(--ui-scale));
  border-radius: calc(6px * var(--ui-scale));
  background: linear-gradient(180deg, rgba(20, 19, 22, 0.92), rgba(12, 13, 16, 0.92));
  border: 1px solid rgba(185, 154, 96, 0.55);
  box-shadow: 0 4px 18px rgba(0, 0, 0, 0.5);
  pointer-events: none;
  white-space: nowrap;
}
.tm-sighting__bearing {
  font: var(--text-xs)/1.3 var(--f-sans);
  color: var(--gold-400);
  letter-spacing: 0.06em;
}
.tm-sighting__what {
  font: var(--text-sm)/1.3 var(--f-serif);
  color: var(--paper-50);
}
.travel-map.is-night .tm-sighting {
  border-color: rgba(170, 190, 230, 0.5);
}
.travel-map.is-night .tm-sighting__bearing {
  color: #c8d4ee;
}

/* The failure line: a quiet ink plate centred in the open stage, between the
   header and the band, with the gold hairline of the shared islands. */
.travel-map__state {
  position: absolute;
  left: 50%;
  top: calc(var(--header-h) + (100% - var(--header-h) - var(--band-h)) / 2);
  transform: translate(-50%, -50%);
  z-index: 2;
  display: flex;
  align-items: center;
  gap: calc(14px * var(--ui-scale));
  padding: calc(10px * var(--ui-scale)) calc(12px * var(--ui-scale)) calc(10px * var(--ui-scale)) calc(18px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.38);
  border-radius: var(--radius);
  background: var(--panel);
  box-shadow: var(--shadow);
  backdrop-filter: blur(6px);
  font: var(--text-sm)/1.4 var(--f-serif);
  color: var(--paper-200);
  white-space: nowrap;
  cursor: default;
}
.travel-map__retry {
  flex: none;
  min-height: calc(36px * var(--ui-scale));
  padding: 0 calc(14px * var(--ui-scale));
  border: 1px solid var(--gold-600);
  border-radius: var(--radius-sm);
  background: rgba(185, 154, 96, 0.1);
  color: var(--gold-300);
  font: var(--text-sm)/1 var(--f-sans);
  cursor: pointer;
  transition: background var(--motion-fast) var(--ease-standard), border-color var(--motion-fast) var(--ease-standard);
}
.travel-map__retry:hover {
  background: rgba(185, 154, 96, 0.2);
  border-color: var(--gold-400);
}
.travel-map__retry:focus-visible {
  outline: none;
  box-shadow: var(--focus);
}
</style>
