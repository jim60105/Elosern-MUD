<script setup>
// The area tab's map (OpenSpec change render-area-map-view; approved design
// docs/superpowers/specs/2026-10-22-world-map-drawer-design.md §6.2-§6.5).
// It draws one validated `area_map` v2 body and nothing else:
//   - grid: the settlement's metre coordinates at one uniform scale under
//     pan and zoom (@elosern/map-view), with no compressed mode;
//   - instance / interior: coordinate-free rooms on the minimap's radial
//     placement (no metric position is ever fabricated);
//   - wilderness: the server's 41 x 41 window (wilderness-area-map-reveal):
//     revealed terrain decoded from the run-length rows (remembered cells
//     without a visit drawn dimmer than walked ones), the unknown remainder
//     as fog, the live-sight ring of the server's radius, live-sight
//     entities, distant sightings pinned to the frame rim, and the sparse
//     nodes (current, visits, steps, gates) over the terrain.
// Metric views carry a scale-true dot field (dots on round world multiples)
// and a scale caption that share one formatter, so both always state the
// same real distance. Fog is the server's: only payload nodes and roads are
// drawn, and a commission that points into fog adds nothing.
//
// Selection: a node selects on click or Enter/Space; its reading (kind, full
// name, state, gate far side, bearing/distance, commissions) renders in the
// `detail` slot, by default AreaMapDetail. 前往 exists only for the
// server's move descriptor on a node one road from the current node, and
// emits `move` once with `{ exit_ref, destination, current_node }` — the
// opaque descriptor plus this payload's canonical current node, the exact
// `explore.move` source; no route is ever derived from geometry.
//
// Host contract (MapDrawer, redesign-map-drawer): `v-model:view`
// (`{ signature, cx, cy, span }`, scoped by `${layer}|${frame.key}|${unit}`)
// and `v-model:selected` keep per-tab session memory; a supplied view whose
// signature differs from the payload's is ignored and the opening fit
// replaces it, and a new map clears the selection. The exposed `zoomIn`,
// `zoomOut`, `recentre`, `showWhole`, `panBy`, `stops` and `stopLabel` drive
// the host's floating pill and keyboard (arrows, ＋/－, C, 0). Arrow keys
// on a focused node move focus spatially to the nearest node that way (the
// map follows it); Shift+arrows are left to the host's pan. This component
// requests no data and owns no drawer chrome.
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import AreaMapDetail from "./AreaMapDetail.vue";
import MapNodeGlyph from "./MapNodeGlyph.vue";
import MapCommissionGlyph from "./MapCommissionGlyph.vue";
import {
  DRAG_THRESHOLD_PX,
  cellRect,
  cellOf,
  centreOn,
  estimateTextWidth,
  nearestStop,
  nextStop,
  panByPixels,
  placeLabels,
  previousStop,
  project,
  scaleBar,
  spanLimits,
  wheelFactor,
  zoomAt,
  zoomBy,
} from "@elosern/map-view";
import { DETAIL_DRAWER_WIDTH, usableRect } from "../lib/map_chrome.js";
import { AREA_CELL_GLYPH_SCALE } from "../lib/map_glyphs.js";
import { GAME_MAP_THEME_VARS } from "../lib/map_theme.js";
import {
  DOT_MIN_GAP_PX,
  LABEL_FONT_PX,
  adjacentIds,
  areaDotField,
  areaStops,
  areaUnit,
  decodeWindow,
  entityMarks,
  isRadialLayer,
  labelCandidates,
  leadsToOf,
  nodeAccessibleName,
  nodeDetail,
  openingView,
  placeNodes,
  sightCaption,
  sightingMarks,
  travelAction,
  viewSignature,
  wholeView,
} from "../lib/area_map_view.js";

const props = defineProps({
  // A validated area_map v1 body in its available form.
  area: { type: Object, required: true },
  // Controlled view `{ signature, cx, cy, span }`; undefined = uncontrolled.
  view: { type: Object, default: undefined },
  // Controlled selected node id; undefined = uncontrolled.
  selected: { type: String, default: undefined },
  // Render the selection reading inside the map (the host may supply its own).
  showDetail: { type: Boolean, default: true },
  // The host cannot send a move yet (a request in flight, or this body is
  // older than the committed position): 前往 waits, visibly, and sends nothing.
  moveBusy: { type: Boolean, default: false },
});
const emit = defineEmits(["update:view", "update:selected", "select", "move"]);

// A 0x0 first paint (jsdom, a hidden host) keeps a sane provisional frame;
// the opening fit is recomputed once the real frame is measured.
const FALLBACK_FRAME = Object.freeze({ width: 960, height: 600 });
// The smallest measured box the opening fit (96 px margins) can use.
const MIN_FRAME_PX = 240;

let instanceCounter = 0;
const uid = `area-map-${(instanceCounter += 1)}-${Math.random().toString(36).slice(2, 8)}`;

const surface = ref(null);
const svgEl = ref(null);
const frame = ref(FALLBACK_FRAME);
const measured = ref(false);
const uiScale = ref(1);

function readUiScale() {
  if (typeof window === "undefined" || typeof document === "undefined") return 1;
  const raw = Number.parseFloat(window.getComputedStyle(document.documentElement).getPropertyValue("--ui-scale"));
  return Number.isFinite(raw) && raw > 0 ? raw : 1;
}

// ── geometry ────────────────────────────────────────────────────────────

const signature = computed(() => viewSignature(props.area));
const unit = computed(() => areaUnit(props.area));
const radial = computed(() => isRadialLayer(props.area));
const isWild = computed(() => props.area.layer === "wilderness");
const placed = computed(() => placeNodes(props.area));
const placedById = computed(() => new Map(placed.value.map((entry) => [entry.node.id, entry])));
const adjacent = computed(() => adjacentIds(props.area));
const stops = computed(() => areaStops(props.area, placed.value, frame.value));
const limits = computed(() => spanLimits(stops.value));

const localView = ref(null);
// True while the shown view is the automatic opening fit (no user input yet).
let viewIsOpening = false;

function sameSignature(view) {
  return !!view && view.signature === signature.value && [view.cx, view.cy, view.span].every(Number.isFinite) && view.span > 0;
}

function commitView(next, { opening = false } = {}) {
  const view = Object.freeze({ signature: signature.value, cx: next.cx, cy: next.cy, span: next.span });
  viewIsOpening = opening;
  localView.value = view;
  emit("update:view", view);
}

function openView() {
  commitView(openingView(props.area, placed.value, frame.value, stops.value), { opening: true });
}

function adoptOrOpen() {
  if (sameSignature(props.view)) {
    localView.value = props.view;
    viewIsOpening = false;
    return;
  }
  if (sameSignature(localView.value)) return;
  openView();
}
adoptOrOpen();

watch(
  () => props.view,
  (next) => {
    if (sameSignature(next) && next !== localView.value) {
      localView.value = next;
      viewIsOpening = false;
    }
  },
);

const view = computed(() => (sameSignature(localView.value) ? localView.value : openingView(props.area, placed.value, frame.value, stops.value)));

// ── selection ───────────────────────────────────────────────────────────

const localSelected = ref(props.selected ?? null);
const focusedId = ref(null);

watch(
  () => props.selected,
  (next) => {
    if (next !== undefined) localSelected.value = next ?? null;
  },
);

const selectedId = computed(() =>
  localSelected.value && placedById.value.has(localSelected.value) ? localSelected.value : null,
);

const detail = computed(() => (selectedId.value ? nodeDetail(props.area, placed.value, selectedId.value) : null));
const detailShown = computed(() => props.showDetail && !!detail.value);

function setSelected(id) {
  const next = id && placedById.value.has(id) ? id : null;
  if (localSelected.value === next) return;
  localSelected.value = next;
  emit("update:selected", next);
  emit("select", next ? nodeDetail(props.area, placed.value, next) : null);
}

// A new map (layer, key or unit) never inherits the old view or selection.
watch(signature, () => {
  localView.value = null;
  focusedId.value = null;
  adoptOrOpen();
  // A host restoring this tab's own selection keeps it; anything else clears.
  const kept = props.selected && placedById.value.has(props.selected) ? props.selected : null;
  if (kept) localSelected.value = kept;
  else setSelected(null);
  moveSent = false;
});

// A republished body that no longer holds the selection drops it.
watch(placedById, (byId) => {
  if (localSelected.value && !byId.has(localSelected.value)) setSelected(null);
  if (focusedId.value && !byId.has(focusedId.value)) focusedId.value = null;
});

// ── projection for drawing ──────────────────────────────────────────────

const usable = computed(() => usableRect(frame.value, { drawerOpen: detailShown.value, drawerWidth: DETAIL_DRAWER_WIDTH }));

const projected = computed(() =>
  placed.value.map((entry) => ({ ...entry, p: project(view.value, frame.value, entry) })),
);

// Paint order depends on the payload only: re-sorting on selection would move
// the focused node's element and drop keyboard focus.
const paintRank = (node) => {
  if (node.visibility === "current") return 8;
  if (travelAction(props.area, node, adjacent.value)) return 6;
  if (leadsToOf(node)) return 5;
  return node.visibility === "visited" ? 3 : 1;
};

const questNodeIds = computed(
  () =>
    new Set(
      props.area.quest_markers
        .filter((marker) => marker.destination.kind === "node")
        .map((marker) => marker.destination.node_id)
        .filter((id) => placedById.value.has(id)),
    ),
);

// Screen directions (radians) of the roads leaving each drawn node, so the
// commission pin can sit in the clearest diagonal instead of on a road.
const roadAngles = computed(() => {
  const out = new Map();
  if (isWild.value) return out;
  const byId = new Map(projected.value.map((entry) => [entry.node.id, entry.p]));
  const add = (from, to) => {
    const a = byId.get(from);
    const b = byId.get(to);
    if (!a || !b || (a.x === b.x && a.y === b.y)) return;
    if (!out.has(from)) out.set(from, []);
    out.get(from).push(Math.atan2(b.y - a.y, b.x - a.x));
  };
  for (const edge of props.area.edges) {
    add(edge.source, edge.destination);
    add(edge.destination, edge.source);
  }
  return out;
});

const QUEST_PIN_OFFSET = 12;
const QUEST_DIAGONALS = [
  [1, -1],
  [-1, -1],
  [1, 1],
  [-1, 1],
];

function questOffset(id, distance) {
  const angles = roadAngles.value.get(id) ?? [];
  let best = QUEST_DIAGONALS[0];
  let bestClearance = -1;
  for (const [sx, sy] of QUEST_DIAGONALS) {
    const theta = Math.atan2(sy, sx);
    let clearance = Math.PI;
    for (const angle of angles) {
      const diff = Math.abs(((theta - angle + 3 * Math.PI) % (2 * Math.PI)) - Math.PI);
      clearance = Math.min(clearance, diff);
    }
    if (clearance > bestClearance + 1e-6) {
      bestClearance = clearance;
      best = [sx, sy];
    }
  }
  return { dx: best[0] * distance, dy: best[1] * distance };
}

const nodeDraws = computed(() =>
  projected.value
    .map((entry) => {
      const { node } = entry;
      const draw = {
        id: node.id,
        x: entry.p.x,
        y: entry.p.y,
        visibility: node.visibility,
        gate: leadsToOf(node) !== "",
        travel: !!travelAction(props.area, node, adjacent.value),
        quest: questNodeIds.value.has(node.id),
        selected: node.id === selectedId.value,
        name: nodeAccessibleName(props.area, node),
        rank: paintRank(node),
        questAt: !isWild.value && questNodeIds.value.has(node.id) ? questOffset(node.id, QUEST_PIN_OFFSET) : null,
        cell: null,
      };
      if (isWild.value) {
        const { col, row } = cellOf(entry);
        const r = cellRect(view.value, frame.value, col, row);
        const inset = Math.min(3, (r.right - r.left) * 0.06);
        draw.cell = {
          x: r.left + inset,
          y: r.top + inset,
          width: Math.max(1, r.right - r.left - 2 * inset),
          height: Math.max(1, r.bottom - r.top - 2 * inset),
        };
      }
      return draw;
    })
    .sort((a, b) => a.rank - b.rank),
);

const edgeDraws = computed(() => {
  if (isWild.value) return [];
  const byId = new Map(projected.value.map((entry) => [entry.node.id, entry]));
  const walked = (node) => node.visibility === "visited" || node.visibility === "current";
  return props.area.edges
    .map((edge, i) => {
      const a = byId.get(edge.source);
      const b = byId.get(edge.destination);
      if (!a || !b) return null;
      return {
        key: `${edge.source}>${edge.destination}#${i}`,
        x1: a.p.x,
        y1: a.p.y,
        x2: b.p.x,
        y2: b.p.y,
        walked: walked(a.node) && walked(b.node),
        travel:
          (edge.source === props.area.current_node && !!travelAction(props.area, b.node, adjacent.value)) ||
          (edge.destination === props.area.current_node && !!travelAction(props.area, a.node, adjacent.value)),
      };
    })
    .filter(Boolean);
});

// ── the wilderness window ───────────────────────────────────────────────

function screenRect(col, row) {
  return cellRect(view.value, frame.value, col, row);
}

// One cell's side in screen pixels at the current view.
const cellPx = computed(() => {
  if (!isWild.value) return 0;
  const r = screenRect(0, 0);
  return Math.abs(r.right - r.left);
});

const windowDraw = computed(() => {
  if (!isWild.value) return null;
  const { min_x: x, min_y: y, width, height } = props.area.window;
  const sw = screenRect(x, y);
  const ne = screenRect(x + width - 1, y + height - 1);
  return { x: sw.left, y: ne.top, width: ne.right - sw.left, height: sw.bottom - ne.top };
});

// Revealed cells only (unknown runs draw nothing over the fog), culled to the
// frame. Relief: a higher band reads lighter; a remembered cell (revealed,
// never walked) keeps its terrain but sits back behind a dimmer wash.
const terrainDraws = computed(() => {
  if (!isWild.value) return [];
  const { width, height } = frame.value;
  const out = [];
  for (const cell of decodeWindow(props.area)) {
    const r = screenRect(cell.x, cell.y);
    if (r.right < 0 || r.left > width || r.bottom < 0 || r.top > height) continue;
    const relief = cell.band / 15;
    out.push({
      key: cell.key,
      cell,
      x: r.left,
      y: r.top,
      width: Math.max(0.5, r.right - r.left),
      height: Math.max(0.5, r.bottom - r.top),
      opacity: cell.state === "remembered" ? 0.5 + relief * 0.3 : 0.78 + relief * 0.22,
    });
  }
  return out;
});

const markReliefs = computed(() => cellPx.value >= 12);

const sightRing = computed(() => {
  if (!isWild.value) return null;
  const here = placedById.value.get(props.area.current_node);
  if (!here) return null;
  const p = project(view.value, frame.value, here);
  return { cx: p.x, cy: p.y, r: (props.area.ground_radius + 0.5) * cellPx.value };
});

const entityDraws = computed(() => {
  if (!isWild.value) return [];
  const size = Math.max(4, Math.min(13 * uiScale.value, cellPx.value * 0.24));
  return entityMarks(props.area).map((mark) => ({ ...mark, p: project(view.value, frame.value, mark), size }));
});

const hostileCount = computed(() => entityDraws.value.filter((mark) => mark.hostile).length);
const sightLine = computed(() => sightCaption(props.area));

// Distant sightings sit on the usable frame's rim along their compass bearing
// from the current cell, so the player reads "something stands that way"
// without a fabricated position.
const SIGHTING_INSET_PX = 40;
const sightingDraws = computed(() => {
  if (!isWild.value) return [];
  const here = placedById.value.get(props.area.current_node);
  if (!here) return [];
  const origin = project(view.value, frame.value, here);
  const inset = SIGHTING_INSET_PX * uiScale.value;
  const r = usable.value;
  const box = { left: r.left + inset, right: r.right - inset, top: r.top + inset, bottom: r.bottom - inset * 2.2 };
  return sightingMarks(props.area).map((mark) => {
    const dx = Math.sin(mark.angle);
    const dy = -Math.cos(mark.angle);
    const ox = Math.min(Math.max(origin.x, box.left), box.right);
    const oy = Math.min(Math.max(origin.y, box.top), box.bottom);
    const reach = [
      dx > 1e-9 ? (box.right - ox) / dx : Infinity,
      dx < -1e-9 ? (box.left - ox) / dx : Infinity,
      dy > 1e-9 ? (box.bottom - oy) / dy : Infinity,
      dy < -1e-9 ? (box.top - oy) / dy : Infinity,
    ];
    const t = Math.max(0, Math.min(...reach));
    const x = ox + dx * t;
    const y = oy + dy * t;
    const anchor = dx > 0.35 ? "end" : dx < -0.35 ? "start" : "middle";
    const textX = x - dx * 18 * uiScale.value + (anchor === "end" ? -6 : anchor === "start" ? 6 : 0);
    const textY = dy > 0.35 ? y - 30 * uiScale.value : y + 24 * uiScale.value;
    return { ...mark, x, y, deg: (mark.angle * 180) / Math.PI, anchor, textX, textY };
  });
});

const dots = computed(() => areaDotField(props.area, view.value, frame.value, DOT_MIN_GAP_PX * uiScale.value));
const scale = computed(() => (unit.value ? scaleBar(view.value, frame.value, unit.value, 120 * uiScale.value) : null));

// ── labels ──────────────────────────────────────────────────────────────

const fontPx = computed(() => LABEL_FONT_PX * uiScale.value);
const measureCache = new Map();
let measureContext;
function measureText(text, px) {
  const key = `${px}|${text}`;
  if (measureCache.has(key)) return measureCache.get(key);
  if (measureContext === undefined) {
    measureContext = null;
    const jsdom = typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent || "");
    if (!jsdom && typeof document !== "undefined") {
      try {
        measureContext = document.createElement("canvas").getContext("2d");
      } catch {
        // observability: ignore R2: a canvas-less host falls back to the glyph-class estimate
        measureContext = null;
      }
    }
  }
  let width = estimateTextWidth(text, px);
  if (measureContext) {
    measureContext.font = `700 ${px}px "Noto Sans TC", "Noto Serif TC", sans-serif`;
    width = measureContext.measureText(text).width;
  }
  // The labels' 0.04em letter spacing, plus a small safety margin.
  width = width * 1.04 + [...text].length * 0.04 * px;
  measureCache.set(key, width);
  return width;
}

// Web fonts land after the first paint: re-measure once they are ready.
const fontsVersion = ref(0);

const labelDraws = computed(() => {
  void fontsVersion.value;
  const candidates = labelCandidates(props.area, placed.value, selectedId.value);
  const labelFrame = {
    width: Math.max(1, frame.value.width - (detailShown.value ? DETAIL_DRAWER_WIDTH : 0)),
    height: frame.value.height,
  };
  const obstacles = projected.value
    .filter((entry) => !isWild.value || entry.node.id === props.area.current_node || leadsToOf(entry.node))
    .map((entry) => ({ id: entry.node.id, x: entry.p.x, y: entry.p.y }));
  // Commission pins are obstacles too, so no name is drawn over its pin.
  for (const draw of nodeDraws.value) {
    if (!draw.questAt) continue;
    obstacles.push({ id: `quest:${draw.id}`, x: draw.x + draw.questAt.dx, y: draw.y + draw.questAt.dy });
  }
  const placedLabels = placeLabels(candidates, (entry) => project(view.value, frame.value, entry), labelFrame, {
    fontPx: fontPx.value,
    measure: measureText,
    markerRadius: (isWild.value ? 10 : 12) * uiScale.value,
    obstacles,
    segments: edgeDraws.value,
  });
  const byId = placedById.value;
  return placedLabels.map((label) => {
    const node = byId.get(label.id).node;
    return {
      ...label,
      visibility: node.visibility,
      gateLine: label.lines.length > 1 || (label.lines[0] ?? "").startsWith("通往 "),
    };
  });
});

// ── pointer: drag pans, wheel zooms, click selects ──────────────────────

let drag = null;

function surfacePoint(event) {
  const rect = surface.value?.getBoundingClientRect?.();
  return { x: (event.clientX ?? 0) - (rect?.left ?? 0), y: (event.clientY ?? 0) - (rect?.top ?? 0) };
}

function onPointerDown(event) {
  if (event.button !== undefined && event.button !== 0) return;
  const target = event.target?.closest?.("[data-node-id]");
  drag = {
    pointerId: event.pointerId,
    x: event.clientX ?? 0,
    y: event.clientY ?? 0,
    view: view.value,
    moved: false,
    nodeId: target ? target.getAttribute("data-node-id") : null,
  };
  try {
    if (event.pointerId !== undefined) surface.value?.setPointerCapture?.(event.pointerId);
  } catch {
    // observability: ignore R2: a synthetic pointer without an active pointer id cannot be captured
  }
}

function onPointerMove(event) {
  if (!drag) return;
  const dx = (event.clientX ?? 0) - drag.x;
  const dy = (event.clientY ?? 0) - drag.y;
  if (!drag.moved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) return;
  drag.moved = true;
  commitView(panByPixels(drag.view, frame.value, dx, dy));
}

function onPointerUp() {
  if (!drag) return;
  const { moved, nodeId } = drag;
  drag = null;
  if (moved) return;
  if (nodeId) {
    focusedId.value = nodeId;
    setSelected(nodeId);
  } else {
    setSelected(null);
  }
}

function onPointerCancel() {
  drag = null;
}

function onWheel(event) {
  commitView(zoomBy(view.value, frame.value, wheelFactor(event.deltaY ?? 0), surfacePoint(event), limits.value));
}

// ── keyboard on nodes ───────────────────────────────────────────────────

const tabStopId = computed(() => {
  const candidates = [focusedId.value, selectedId.value, props.area.current_node];
  return candidates.find((id) => id && placedById.value.has(id));
});

function nodeElement(id) {
  for (const el of svgEl.value?.querySelectorAll?.("[data-node-id]") ?? []) {
    if (el.getAttribute("data-node-id") === id) return el;
  }
  return null;
}

function ensureVisible(id) {
  const entry = placedById.value.get(id);
  if (!entry) return;
  const p = project(view.value, frame.value, entry);
  const r = usable.value;
  if (p.x < r.left || p.x > r.right || p.y < r.top || p.y > r.bottom) {
    commitView(centreOn(view.value, frame.value, entry, r));
  }
}

function focusNode(id) {
  focusedId.value = id;
  ensureVisible(id);
  nodeElement(id)?.focus?.();
}

const ARROWS = { ArrowRight: [1, 0], ArrowLeft: [-1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] };

// The nearest node within 60 degrees of the arrow's screen direction.
function spatialNeighbour(fromId, [ux, uy]) {
  const from = projected.value.find((entry) => entry.node.id === fromId);
  if (!from) return null;
  let best = null;
  let bestScore = Infinity;
  for (const entry of projected.value) {
    if (entry.node.id === fromId) continue;
    const dx = entry.p.x - from.p.x;
    const dy = entry.p.y - from.p.y;
    const along = dx * ux + dy * uy;
    if (along <= 0) continue;
    const across = Math.abs(dx * uy - dy * ux);
    if (across > along * Math.tan(Math.PI / 3)) continue;
    const score = along + 2 * across;
    if (score < bestScore) {
      bestScore = score;
      best = entry.node.id;
    }
  }
  return best;
}

function onNodeKeydown(event, id) {
  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    event.stopPropagation();
    focusedId.value = id;
    setSelected(id);
    return;
  }
  if (event.key === "Home") {
    event.preventDefault();
    event.stopPropagation();
    focusNode(props.area.current_node);
    return;
  }
  const direction = ARROWS[event.key];
  if (!direction || event.shiftKey || event.altKey || event.ctrlKey || event.metaKey) return;
  event.preventDefault();
  event.stopPropagation();
  const next = spatialNeighbour(id, direction);
  if (next) focusNode(next);
}

function onNodeFocus(id) {
  focusedId.value = id;
}

function onRootKeydown(event) {
  if (event.key === "Escape" && selectedId.value) {
    event.stopPropagation();
    const id = selectedId.value;
    setSelected(null);
    focusNode(id);
  }
}

// ── travel and detail actions ───────────────────────────────────────────

// One 前往 per published body: a double click or key repeat sends nothing
// more until the server republishes the area.
let moveSent = false;
watch(
  () => props.area,
  () => {
    moveSent = false;
  },
);
// A host that held the move until its refresh landed releases the guard too.
watch(
  () => props.moveBusy,
  (busy) => {
    if (!busy) moveSent = false;
  },
);

function onDetailMove(action) {
  if (moveSent || props.moveBusy) return;
  const node = placedById.value.get(selectedId.value)?.node;
  const current = travelAction(props.area, node, adjacent.value);
  // Only the selected node's live descriptor travels; a stale card sends nothing.
  if (!current || current !== action) return;
  moveSent = true;
  emit("move", {
    exit_ref: current.exit_ref,
    destination: current.destination,
    current_node: props.area.current_node,
  });
}

function centreNode(id) {
  const entry = placedById.value.get(id);
  if (entry) commitView(centreOn(view.value, frame.value, entry, usable.value));
}

function closeDetail() {
  const id = selectedId.value;
  setSelected(null);
  if (id) focusNode(id);
}

const announcement = computed(() => (detail.value ? `已選取：${detail.value.title}` : ""));

// ── host controls ───────────────────────────────────────────────────────

function rectCentre() {
  const r = usable.value;
  return { x: (r.left + r.right) / 2, y: (r.top + r.bottom) / 2 };
}

function zoomIn() {
  const stop = nextStop(stops.value, view.value.span);
  if (stop) commitView(zoomAt(view.value, frame.value, stop.span, rectCentre(), limits.value));
}

function zoomOut() {
  const stop = previousStop(stops.value, view.value.span);
  if (stop) commitView(zoomAt(view.value, frame.value, stop.span, rectCentre(), limits.value));
}

function recentre() {
  centreNode(props.area.current_node);
}

function showWhole() {
  commitView(wholeView(props.area, placed.value, frame.value, usable.value));
}

function panBy(dxPx, dyPx) {
  commitView(panByPixels(view.value, frame.value, dxPx, dyPx));
}

const stopLabel = computed(() => nearestStop(stops.value, view.value.span).label);

defineExpose({ zoomIn, zoomOut, recentre, showWhole, panBy, stops, stopLabel, detail, view, frame, detailShown });

// ── frame measurement ───────────────────────────────────────────────────

let observer = null;
function applyFrame(width, height) {
  uiScale.value = readUiScale();
  // A host still laying out (a 0x0 or sliver box while the drawer mounts)
  // is not a frame to fit in: keep the provisional one until it is real.
  if (!(width >= MIN_FRAME_PX) || !(height >= MIN_FRAME_PX)) return;
  const changed = width !== frame.value.width || height !== frame.value.height;
  frame.value = Object.freeze({ width, height });
  const first = !measured.value;
  measured.value = true;
  // The provisional fit is replaced by the real one until the player acts.
  if ((first || changed) && viewIsOpening) openView();
}

onMounted(() => {
  document.fonts?.ready?.then(() => {
    measureCache.clear();
    fontsVersion.value += 1;
  });
  const el = surface.value;
  applyFrame(el?.clientWidth ?? 0, el?.clientHeight ?? 0);
  if (typeof ResizeObserver !== "undefined" && el) {
    observer = new ResizeObserver((entries) => {
      const box = entries[0]?.contentRect;
      if (box) applyFrame(Math.round(box.width), Math.round(box.height));
    });
    observer.observe(el);
  }
});

onBeforeUnmount(() => {
  observer?.disconnect();
  observer = null;
});
</script>

<template>
  <div
    class="area-map"
    :class="[`area-map--${area.layer}`, { 'has-detail': detailShown }]"
    :style="GAME_MAP_THEME_VARS"
    data-testid="area-map"
    :data-layer="area.layer"
    @keydown="onRootKeydown"
  >
    <div
      ref="surface"
      class="area-map__surface"
      data-testid="area-map__surface"
      @pointerdown="onPointerDown"
      @pointermove="onPointerMove"
      @pointerup="onPointerUp"
      @pointercancel="onPointerCancel"
      @wheel.prevent="onWheel"
    >
      <svg
        ref="svgEl"
        class="area-map__svg"
        data-testid="area-map__svg"
        :width="frame.width"
        :height="frame.height"
        :viewBox="`0 0 ${frame.width} ${frame.height}`"
        role="group"
        :aria-label="`${area.title}：${radial ? '房間關係示意' : '依實際距離繪製'}`"
      >
        <defs>
          <pattern
            v-if="dots"
            :id="`${uid}-dots`"
            patternUnits="userSpaceOnUse"
            :x="dots.offsetX - dots.spacingPx / 2"
            :y="dots.offsetY - dots.spacingPx / 2"
            :width="dots.spacingPx"
            :height="dots.spacingPx"
          >
            <circle class="area-map__dot" :cx="dots.spacingPx / 2" :cy="dots.spacingPx / 2" r="1.35" />
          </pattern>
          <pattern :id="`${uid}-fog`" patternUnits="userSpaceOnUse" width="9" height="9" patternTransform="rotate(35)">
            <rect class="area-map__fog-wash" width="9" height="9" />
            <line class="area-map__fog-line" x1="0" y1="0" x2="0" y2="9" />
          </pattern>
          <pattern :id="`${uid}-hatch`" patternUnits="userSpaceOnUse" width="5" height="5" patternTransform="rotate(-45)">
            <line class="area-map__hatch-line" x1="0" y1="0" x2="0" y2="5" />
          </pattern>
          <radialGradient :id="`${uid}-vignette`" cx="50%" cy="48%" r="75%">
            <stop offset="0.55" stop-color="#0a0908" stop-opacity="0" />
            <stop offset="1" stop-color="#0a0908" stop-opacity="0.62" />
          </radialGradient>
        </defs>

        <rect
          v-if="dots"
          class="area-map__dot-field"
          data-testid="area-map__dot-field"
          :data-step-metres="dots.stepMetres"
          :data-spacing-px="dots.spacingPx"
          x="0"
          y="0"
          :width="frame.width"
          :height="frame.height"
          :fill="`url(#${uid}-dots)`"
          aria-hidden="true"
        />

        <g v-if="windowDraw" class="area-map__window" aria-hidden="true" data-testid="area-map__window">
          <!-- The unknown remainder of the window: an even fog wash. -->
          <rect class="area-map__fog" :x="windowDraw.x" :y="windowDraw.y" :width="windowDraw.width" :height="windowDraw.height" :fill="`url(#${uid}-fog)`" />
          <rect
            v-for="cell in terrainDraws"
            :key="cell.key"
            class="area-map__terrain"
            :class="[`t-${cell.cell.terrain}`, `is-${cell.cell.state}`, { 'is-blocked': !cell.cell.passable }]"
            data-testid="area-map__terrain"
            :data-cell="cell.key"
            :data-terrain="cell.cell.terrain"
            :x="cell.x"
            :y="cell.y"
            :width="cell.width"
            :height="cell.height"
            :fill-opacity="cell.opacity"
          />
          <template v-if="markReliefs">
            <template v-for="cell in terrainDraws" :key="`m-${cell.key}`">
              <rect v-if="cell.cell.terrain === 'ridge' || cell.cell.terrain === 'settlement'" class="area-map__hatch" :x="cell.x" :y="cell.y" :width="cell.width" :height="cell.height" :fill="`url(#${uid}-hatch)`" />
              <path
                v-else-if="cell.cell.tier >= 2"
                class="area-map__relief"
                :class="`is-tier-${cell.cell.tier}`"
                :d="`M${cell.x + cell.width * 0.3} ${cell.y + cell.height * 0.66} L${cell.x + cell.width * 0.5} ${cell.y + cell.height * 0.36} L${cell.x + cell.width * 0.7} ${cell.y + cell.height * 0.66}`"
              />
              <line v-if="cell.cell.ford" class="area-map__ford" :x1="cell.x + cell.width * 0.15" :y1="cell.y + cell.height * 0.5" :x2="cell.x + cell.width * 0.85" :y2="cell.y + cell.height * 0.5" />
            </template>
          </template>
          <rect class="area-map__window-frame" :x="windowDraw.x" :y="windowDraw.y" :width="windowDraw.width" :height="windowDraw.height" />
          <circle v-if="sightRing" class="area-map__sight-ring" data-testid="area-map__sight-ring" :cx="sightRing.cx" :cy="sightRing.cy" :r="sightRing.r" />
        </g>

        <g class="area-map__roads" aria-hidden="true">
          <g v-for="edge in edgeDraws" :key="edge.key" class="area-map__road" :class="{ 'is-walked': edge.walked, 'is-frontier': !edge.walked, 'is-travel': edge.travel }">
            <line class="area-map__road-casing" :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" />
            <line class="area-map__road-core" :x1="edge.x1" :y1="edge.y1" :x2="edge.x2" :y2="edge.y2" />
          </g>
        </g>

        <g class="area-map__nodes">
          <g
            v-for="node in nodeDraws"
            :key="node.id"
            class="area-map__node"
            :class="[
              `is-${node.visibility}`,
              { 'is-gate': node.gate, 'is-travel': node.travel, 'is-selected': node.selected, 'has-quest': node.quest },
            ]"
            :data-node-id="node.id"
            data-testid="area-map__node"
            role="button"
            :tabindex="node.id === tabStopId ? 0 : -1"
            :aria-label="node.name"
            :aria-pressed="node.selected ? 'true' : 'false'"
            :aria-current="node.visibility === 'current' ? 'location' : null"
            @keydown="onNodeKeydown($event, node.id)"
            @focus="onNodeFocus(node.id)"
          >
            <template v-if="node.cell">
              <rect
                class="area-map__cell"
                :x="node.cell.x"
                :y="node.cell.y"
                :width="node.cell.width"
                :height="node.cell.height"
                rx="2"
              />
              <!-- The cell's marks are the shared glyphs at the cell scale:
                   the here-seal or the gate arch (MapNodeGlyph), and the
                   commission diamond, moved to the cell's corner beside
                   either of them. The cell rect itself states travel. -->
              <circle
                v-if="node.visibility === 'visited' && !node.gate && !node.quest"
                class="area-map__trail"
                :cx="node.x"
                :cy="node.y"
                :r="Math.max(1.6, Math.min(4.5, node.cell.width * 0.08))"
              />
              <g v-if="node.visibility === 'current' || node.gate || node.quest" :transform="`translate(${node.x} ${node.y})`">
                <MapNodeGlyph
                  v-if="node.visibility === 'current' || node.gate"
                  :state="node.visibility"
                  :gate="node.gate"
                  :selected="node.selected"
                  :size="AREA_CELL_GLYPH_SCALE"
                />
                <g v-if="node.quest" :transform="node.visibility === 'current' || node.gate ? 'translate(11 -11)' : null">
                  <MapCommissionGlyph :size="AREA_CELL_GLYPH_SCALE" />
                </g>
              </g>
            </template>
            <g v-else :transform="`translate(${node.x} ${node.y})`">
              <circle class="area-map__hit" r="20" />
              <circle v-if="node.selected" class="area-map__selected-ring" r="13" />
              <MapNodeGlyph :state="node.visibility" :gate="node.gate" :travel="node.travel" :selected="node.selected" />
              <g v-if="node.questAt" :transform="`translate(${node.questAt.dx} ${node.questAt.dy})`">
                <MapCommissionGlyph />
              </g>
            </g>
          </g>
        </g>

        <g v-if="entityDraws.length" class="area-map__entities" aria-hidden="true">
          <g
            v-for="mark in entityDraws"
            :key="mark.id"
            class="area-map__entity"
            :class="`is-${mark.kind}`"
            data-testid="area-map__entity"
            :data-kind="mark.kind"
            :transform="`translate(${mark.p.x} ${mark.p.y})`"
          >
            <title>{{ mark.label }}</title>
            <path v-if="mark.hostile" class="area-map__entity-mark" :d="`M0 ${-mark.size} L${mark.size * 0.8} 0 L0 ${mark.size} L${-mark.size * 0.8} 0 Z`" />
            <circle v-else class="area-map__entity-mark" :r="mark.size * 0.72" />
            <circle v-if="mark.hostile" class="area-map__entity-core" :r="mark.size * 0.26" />
          </g>
        </g>

        <g class="area-map__labels" aria-hidden="true">
          <text
            v-for="label in labelDraws"
            :key="`label-${label.id}`"
            class="area-map__label"
            :class="[`is-${label.visibility}`, { 'is-gate-label': label.gateLine }]"
            data-testid="area-map__label"
            :data-label-for="label.id"
            :x="label.x"
            :y="label.y"
            :text-anchor="label.anchor"
          >
            <tspan
              v-for="(line, i) in label.lines"
              :key="i"
              :x="label.x"
              :dy="i === 0 ? 0 : label.lineHeight"
              :class="{ 'area-map__label-gate': line.startsWith('通往 ') }"
            >{{ line }}</tspan>
          </text>
        </g>

        <rect class="area-map__vignette" x="0" y="0" :width="frame.width" :height="frame.height" :fill="`url(#${uid}-vignette)`" aria-hidden="true" />

        <g v-if="sightingDraws.length" class="area-map__sightings" aria-hidden="true">
          <g v-for="mark in sightingDraws" :key="mark.key" class="area-map__sighting" data-testid="area-map__sighting" :data-bearing="mark.bearing">
            <g :transform="`translate(${mark.x} ${mark.y}) rotate(${mark.deg}) scale(${1.3 * uiScale})`">
              <path class="area-map__sighting-arrow" d="M0 -11 L7 4 L0 0 L-7 4 Z" />
            </g>
            <text class="area-map__sighting-text" :x="mark.textX" :y="mark.textY" :text-anchor="mark.anchor">
              <tspan :x="mark.textX" class="area-map__sighting-head">{{ mark.head }}</tspan>
              <tspan :x="mark.textX" :dy="fontPx * 1.25">{{ mark.body }}</tspan>
            </text>
          </g>
        </g>
      </svg>

      <div class="area-map__legend" data-testid="area-map__legend">
        <p v-if="isWild" class="area-map__district" data-testid="area-map__district">{{ area.district_name }}</p>
        <p v-if="isWild" class="area-map__sight" data-testid="area-map__sight">
          <span>{{ sightLine }}</span>
          <span v-if="hostileCount" class="area-map__threat" data-testid="area-map__threat">
            <svg viewBox="-6 -8 12 16" width="10" height="13" aria-hidden="true"><path d="M0 -7 L5 0 L0 7 L-5 0 Z" /></svg>
            視野內敵蹤 {{ hostileCount }}
          </span>
        </p>
        <div class="area-map__scale-row">
          <span class="area-map__north" aria-label="上方為北">
            <svg viewBox="0 0 14 18" width="14" height="18" aria-hidden="true"><path d="M7 0 L13 16 L7 12 L1 16 Z" /></svg>
            <span aria-hidden="true">北</span>
          </span>
          <template v-if="scale">
            <span class="area-map__scale-bar" data-testid="area-map__scale-bar" :style="{ width: `${scale.px}px` }" aria-hidden="true" />
            <span class="area-map__scale-text" data-testid="area-map__scale-text">{{ scale.text }}</span>
            <span v-if="dots" class="area-map__dot-caption" data-testid="area-map__dot-caption">{{ dots.caption }}</span>
          </template>
          <span v-else class="area-map__dot-caption" data-testid="area-map__schematic">示意圖 · 不依實際距離</span>
        </div>
      </div>
    </div>

    <div v-if="detailShown" class="area-map__detail" :style="{ width: `${DETAIL_DRAWER_WIDTH}px` }">
      <slot name="detail" :detail="detail" :move="onDetailMove" :centre="centreNode" :close="closeDetail" :busy="moveBusy">
        <AreaMapDetail :detail="detail" :busy="moveBusy" @move="onDetailMove" @centre="centreNode" @close="closeDetail" />
      </slot>
    </div>
    <p class="area-map__live" aria-live="polite" data-testid="area-map__live">{{ announcement }}</p>
    <ul v-if="isWild && (entityDraws.length || sightingDraws.length)" class="area-map__live" data-testid="area-map__sr-sight">
      <li v-for="mark in entityDraws" :key="`sr-${mark.id}`">{{ mark.hostile ? "敵對" : "人物" }}：{{ mark.label }}</li>
      <li v-for="mark in sightingDraws" :key="`sr-${mark.key}`">遠方：{{ mark.head }}，{{ mark.body }}</li>
    </ul>
  </div>
</template>

<style scoped src="./area-map-ink.css"></style>

<style scoped>
.area-map {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 0;
  overflow: hidden;
  color: var(--paper-200);
  font-family: var(--f-sans);
  /* Ink on aged vellum, in the obsidian palette: a warm umber wash lit from
     the upper left, settling into soot at the rim. */
  background:
    radial-gradient(85% 75% at 38% 32%, #2a2620 0%, #1c1a16 46%, #121110 100%);
  isolation: isolate;
}
/* Paper grain: a static tile, so panning never repaints a filter. */
.area-map::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  opacity: 0.5;
  background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' seed='7'/><feColorMatrix values='0 0 0 0 0.62 0 0 0 0 0.55 0 0 0 0 0.42 0 0 0 0.11 0'/></filter><rect width='180' height='180' filter='url(%23n)'/></svg>");
}
.area-map__surface {
  position: absolute;
  inset: 0;
  z-index: 1;
  touch-action: none;
  cursor: grab;
  user-select: none;
}
.area-map__surface:active { cursor: grabbing; }
.area-map__svg { position: absolute; inset: 0; display: block; overflow: hidden; }

/* scale-true dot field */
.area-map__dot { fill: var(--gold-400); fill-opacity: 0.26; }

/* roads: a soot casing under a paper-ink core (./area-map-ink.css, shared
   with the map legend) */

/* nodes */
.area-map__node { cursor: pointer; outline: none; }
.area-map__hit { fill: transparent; }
.area-map__selected-ring { fill: none; stroke: var(--gold-300); stroke-width: 2.6; }
/* node glyphs: MapNodeGlyph; the commission diamond: MapCommissionGlyph */
.area-map__node:focus-visible .area-map__hit,
.area-map__node:focus-visible .area-map__cell {
  stroke: var(--gold-300);
  stroke-width: 2;
  stroke-dasharray: none;
}

/* wilderness window: ink washes over vellum. Terrain hues are muted earth
   tones keyed to the obsidian palette; relief rides the fill opacity. */
.area-map {
  --terrain-open-ground: #7a6d4c;
  --terrain-hills: #8a7243;
  --terrain-mountain: #6d6862;
  --terrain-woodland: #45573f;
  --terrain-water: #3c5a6e;
  --terrain-sea: #263a49;
  --terrain-ridge: #4a443d;
  --terrain-settlement: #8e7d5a;
}
.area-map__fog-wash { fill: #0e0d0b; fill-opacity: 0.55; }
.area-map__fog-line { stroke: var(--paper-700); stroke-opacity: 0.3; stroke-width: 1; }
.area-map__window-frame { fill: none; stroke: var(--gold-600); stroke-opacity: 0.55; stroke-width: 1; }
.area-map__terrain { stroke: #0c0b09; stroke-opacity: 0.18; stroke-width: 0.6; }
.area-map__terrain.t-open_ground { fill: var(--terrain-open-ground); }
.area-map__terrain.t-hills { fill: var(--terrain-hills); }
.area-map__terrain.t-mountain { fill: var(--terrain-mountain); }
.area-map__terrain.t-woodland { fill: var(--terrain-woodland); }
.area-map__terrain.t-water { fill: var(--terrain-water); }
.area-map__terrain.t-sea { fill: var(--terrain-sea); }
.area-map__terrain.t-ridge { fill: var(--terrain-ridge); }
.area-map__terrain.t-settlement { fill: var(--terrain-settlement); }
.area-map__hatch { pointer-events: none; }
.area-map__hatch-line { stroke: #0c0b09; stroke-opacity: 0.55; stroke-width: 1.4; }
.area-map__relief { fill: none; stroke: var(--paper-100); stroke-opacity: 0.38; stroke-width: 1.2; stroke-linejoin: round; }
.area-map__relief.is-tier-3 { stroke-opacity: 0.6; }
.area-map__ford { stroke: var(--paper-200); stroke-opacity: 0.75; stroke-width: 1.6; stroke-dasharray: 2 2.5; }
.area-map__sight-ring { fill: var(--gold-400); fill-opacity: 0.05; stroke: var(--gold-400); stroke-opacity: 0.7; stroke-width: 1.4; stroke-dasharray: 5 4; pointer-events: none; }

/* wilderness node cells: the terrain is drawn below; a cell only states its
   node role (walked trail mark, travel, gate, selection) */
.area-map__cell { fill: transparent; stroke: none; }
.area-map__trail { fill: var(--gold-400); fill-opacity: 0.85; stroke: #14120e; stroke-width: 0.8; pointer-events: none; }
.area-map__node.is-current .area-map__cell { stroke: var(--seal-400); stroke-width: 1.5; }
.area-map__node.is-travel .area-map__cell { stroke: var(--gold-400); stroke-width: 1.4; stroke-dasharray: 4 3; }
.area-map__node.is-selected .area-map__cell { stroke: var(--gold-300); stroke-width: 2.4; stroke-dasharray: none; }

/* live-sight entities: a sealed diamond for a hostile, a paper token for
   a person (shape and colour both differ) */
.area-map__entity { pointer-events: none; }
.area-map__entity-mark { stroke: #14120e; stroke-width: 1.2; }
.area-map__entity.is-hostile .area-map__entity-mark { fill: var(--seal-500); }
.area-map__entity-core { fill: var(--paper-50); }
.area-map__entity.is-npc .area-map__entity-mark { fill: var(--paper-200); }
.area-map__entity.is-character .area-map__entity-mark { fill: var(--gold-400); }

/* distant sightings on the frame rim */
.area-map__sighting { pointer-events: none; }
.area-map__sighting-arrow { fill: var(--gold-400); stroke: #14120e; stroke-width: 1.2; stroke-linejoin: round; }
.area-map__sighting-text {
  fill: var(--paper-200);
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  paint-order: stroke;
  stroke: #14120e;
  stroke-width: 4.5px;
  stroke-linejoin: round;
}
.area-map__sighting-head { fill: var(--gold-400); font-family: var(--f-display); }

/* labels: 16 CSS px at ui-scale 1, never smaller; a soot halo keeps them
   legible over roads and dots */
.area-map__label {
  fill: var(--paper-100);
  font-family: var(--f-sans);
  font-size: var(--text-xs);
  letter-spacing: 0.04em;
  paint-order: stroke;
  stroke: #14120e;
  stroke-width: 4.5px;
  stroke-linejoin: round;
  pointer-events: none;
}
.area-map__label.is-current { fill: var(--paper-50); font-weight: 700; }
.area-map__label.is-seen { fill: var(--map-label-seen); }
.area-map__label-gate { fill: var(--gold-400); }

.area-map__vignette { pointer-events: none; }

/* legend: district, north mark, scale bar and the dot step */
.area-map__legend {
  position: absolute;
  left: calc(18px * var(--ui-scale));
  bottom: calc(16px * var(--ui-scale));
  display: grid;
  gap: calc(6px * var(--ui-scale));
  padding: calc(8px * var(--ui-scale)) calc(14px * var(--ui-scale));
  background: rgba(14, 13, 11, 0.62);
  border: 1px solid rgba(185, 154, 96, 0.22);
  border-radius: var(--radius-sm);
  pointer-events: none;
}
.area-map__district {
  margin: 0;
  color: var(--paper-100);
  font-family: var(--f-display);
  font-size: var(--text-md);
  letter-spacing: 0.16em;
}
.area-map__sight {
  display: flex;
  align-items: center;
  gap: calc(12px * var(--ui-scale));
  margin: 0;
  color: var(--paper-300);
  font-size: var(--text-xs);
  white-space: nowrap;
}
.area-map__threat { display: inline-flex; align-items: center; gap: calc(5px * var(--ui-scale)); color: var(--seal-400); }
.area-map__threat path { fill: var(--seal-500); stroke: #14120e; stroke-width: 1; }
.area-map__scale-row {
  display: flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  color: var(--paper-300);
  font-size: var(--text-xs);
  white-space: nowrap;
}
.area-map__north {
  display: inline-flex;
  align-items: center;
  gap: calc(3px * var(--ui-scale));
  color: var(--gold-400);
  font-family: var(--f-display);
}
.area-map__north path { fill: var(--gold-400); }
.area-map__scale-bar {
  display: inline-block;
  box-sizing: border-box;
  height: calc(7px * var(--ui-scale));
  border: 2px solid var(--paper-300);
  border-top: 0;
}
.area-map__dot-caption { color: var(--paper-500); }

/* selection reading (default card) */
.area-map__detail {
  position: absolute;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 2;
}

.area-map__live {
  position: absolute;
  width: 1px;
  height: 1px;
  margin: -1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}
</style>
