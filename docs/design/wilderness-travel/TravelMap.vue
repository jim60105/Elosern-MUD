<script setup>
// The travel map (prototype): the full-bleed ink map of the 41 x 41 window.
// A canvas paints the terrain once per state — a cached per-pixel field
// (hillshade, contours, terrain wash, paper grain) masked by the revealed
// cells with a brushed edge, then inked strokes (river, road, woods, ford,
// hill hachures, district edge) clipped to the same mask, then the light
// phase (memory dimming outside live sight, the phase tint). An SVG layer
// on top draws what the player acts on: the party token with its eight
// neighbour nodes, the route preview, landmarks, hostiles in live sight and
// the distant-sighting bearings. Chips are HTML for crisp text.
//
// Keys (the map is one focus stop): arrows aim (two arrows aim a diagonal),
// Enter steps toward the aim or departs on the previewed route, holding an
// arrow 400 ms walks in that direction, Esc clears, + / - zoom.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from "vue";
import {
  CITY,
  DIRECTIONS,
  FORD,
  GRID,
  LANDMARKS,
  RIVER,
  ROAD,
  TERRAIN_LABEL,
  WINDOW,
  blockReason,
  canStep,
  cellAt,
  districtOf,
  elevationAt,
  inDisc,
} from "./travel-model.js";

const props = defineProps({
  party: { type: Object, required: true },
  mask: { type: Uint8Array, required: true },
  phase: { type: String, default: "day" },
  liveRadius: { type: Number, default: 4 },
  hostiles: { type: Array, default: () => [] },
  sightings: { type: Array, default: () => [] },
  plan: { type: Object, default: null },
  target: { type: Object, default: null },
  aim: { type: String, default: null },
  walking: { type: Boolean, default: false },
  litDistricts: { type: Object, default: () => new Set() },
  zoom: { type: Number, default: 30 },
  // A cell box to keep in view (the locked route), or null to follow the party.
  focus: { type: Object, default: null },
  motion: { type: String, default: "full" },
});
const emit = defineEmits(["aim", "hover", "pick", "step", "confirm", "cancel", "hold", "release", "zoom"]);

const SUB = 12; // field samples per cell
const FIELD = WINDOW * SUB;

const root = ref(null);
const canvas = ref(null);
const size = ref({ w: 1200, h: 700, top: 48, bottom: 220 });
const uiScale = ref(1);
const hoverCell = ref(null);

const openStage = computed(() => ({
  left: 240 * uiScale.value,
  right: size.value.w - 300 * uiScale.value,
  top: size.value.top + 24,
  bottom: size.value.h - size.value.bottom - 24,
}));
const cellPx = computed(() => {
  const base = props.zoom * uiScale.value;
  if (!props.focus) return base;
  const o = openStage.value;
  const fitW = (o.right - o.left) / (props.focus.maxX - props.focus.minX + 3);
  const fitH = (o.bottom - o.top) / (props.focus.maxY - props.focus.minY + 3);
  return Math.max(14, Math.min(base, fitW, fitH));
});
const span = computed(() => WINDOW * cellPx.value);
// The camera: the party's cell centre at the centre of the open stage
// between the header and the band.
const camera = computed(() => {
  const o = openStage.value;
  const cx = props.focus ? (o.left + o.right) / 2 : size.value.w / 2;
  const cy = size.value.top + (size.value.h - size.value.top - size.value.bottom) / 2;
  const fx = props.focus ? (props.focus.minX + props.focus.maxX + 1) / 2 : props.party.x + 0.5;
  const fy = props.focus ? (props.focus.minY + props.focus.maxY + 1) / 2 : props.party.y + 0.5;
  return { x: cx - fx * cellPx.value, y: cy - fy * cellPx.value };
});

// ------------------------------------------------------------ static field

let staticField = null;

function mix(a, b, t) {
  return a + (b - a) * t;
}

// A lamplit parchment wash under ink: warm umber ground, ochre hills,
// moss woods, slate water. Mid-tones, so the fog reads as the dark.
const TERRAIN_RGB = {
  open: [94, 84, 66],
  road: [98, 87, 68],
  ford: [84, 90, 88],
  hills: [108, 95, 72],
  woodland: [54, 70, 56],
  river: [44, 62, 74],
};

function hashGrain(i, j) {
  let v = Math.imul(i, 374761393) ^ Math.imul(j, 668265263);
  v = Math.imul(v ^ (v >>> 13), 1274126177);
  return ((v ^ (v >>> 16)) >>> 0) / 4294967295;
}

function buildStatic() {
  const elev = new Float32Array((FIELD + 2) * (FIELD + 2));
  for (let j = -1; j <= FIELD; j += 1) {
    for (let i = -1; i <= FIELD; i += 1) {
      elev[(j + 1) * (FIELD + 2) + (i + 1)] = elevationAt((i + 0.5) / SUB, (j + 0.5) / SUB);
    }
  }
  const E = (i, j) => elev[(j + 1) * (FIELD + 2) + (i + 1)];
  const rgb = new Uint8ClampedArray(FIELD * FIELD * 3);
  const jitter = new Float32Array(FIELD * FIELD);
  for (let j = 0; j < FIELD; j += 1) {
    for (let i = 0; i < FIELD; i += 1) {
      const e = E(i, j);
      const gx = E(i + 1, j) - E(i - 1, j);
      const gy = E(i, j + 1) - E(i, j - 1);
      // Light from the north-west.
      const shade = Math.max(-1, Math.min(1, (-gx - gy) * 22));
      // Terrain colour from a warped lookup, so region borders wander
      // instead of following the cell grid.
      const u = (i + 0.5) / SUB + (Math.sin(j * 0.21 + Math.sin(i * 0.13) * 2.1) * 0.5 + Math.sin(i * 0.47 + j * 0.11) * 0.25) * 0.55;
      const v = (j + 0.5) / SUB + (Math.sin(i * 0.19 + Math.sin(j * 0.17) * 2.3) * 0.5 + Math.sin(j * 0.43 - i * 0.09) * 0.25) * 0.55;
      const gx0 = Math.min(WINDOW - 1, Math.max(0, Math.floor(u)));
      const gy0 = Math.min(WINDOW - 1, Math.max(0, Math.floor(v)));
      const looked = GRID[gy0][gx0].terrain;
      const terrain = looked === "river" || looked === "ford" || looked === "road" ? "open" : looked;
      const base = TERRAIN_RGB[terrain];
      const band = Math.floor(e * 10);
      const contour =
        Math.floor(E(i + 1, j) * 10) !== band || Math.floor(E(i, j + 1) * 10) !== band;
      const index = contour && band % 3 === 0;
      const grain = (hashGrain(i, j) - 0.5) * 6;
      const lift = 0.6 + 0.55 * (shade * 0.5 + 0.5) + e * 0.12;
      const k = (i + j * FIELD) * 3;
      for (let c = 0; c < 3; c += 1) {
        let v = base[c] * lift + grain;
        if (contour) v = mix(v, [36, 30, 24][c], index ? 0.3 : 0.14);
        rgb[k + c] = v;
      }
      jitter[i + j * FIELD] =
        Math.sin(i * 0.71 + Math.sin(j * 0.37) * 3) * 0.5 + Math.sin(j * 0.53 + Math.sin(i * 0.29) * 3) * 0.5;
    }
  }
  return { rgb, jitter };
}

// ------------------------------------------------------------- painting

function maskAt(u, v) {
  // Bilinear revealed coverage at a cell-space point.
  const x = u - 0.5;
  const y = v - 0.5;
  const x0 = Math.floor(x);
  const y0 = Math.floor(y);
  const fx = x - x0;
  const fy = y - y0;
  const m = (xx, yy) =>
    xx < 0 || yy < 0 || xx >= WINDOW || yy >= WINDOW ? 0 : props.mask[yy * WINDOW + xx];
  return mix(mix(m(x0, y0), m(x0 + 1, y0), fx), mix(m(x0, y0 + 1), m(x0 + 1, y0 + 1), fx), fy);
}

function smoothstep(a, b, t) {
  const x = Math.max(0, Math.min(1, (t - a) / (b - a)));
  return x * x * (3 - 2 * x);
}

const PHASE_LOOK = {
  day: { tint: null, memory: 0.2, desat: 0.4 },
  dawn: { tint: "rgba(120, 110, 170, 0.16)", memory: 0.32, desat: 0.5 },
  dusk: { tint: "rgba(196, 112, 48, 0.18)", memory: 0.36, desat: 0.5 },
  night: { tint: "rgba(20, 34, 78, 0.36)", memory: 0.42, desat: 0.75 },
};

function paint() {
  const el = canvas.value;
  if (!el) return;
  staticField ??= buildStatic();
  const dpr = window.devicePixelRatio || 1;
  const px = span.value;
  el.width = Math.round(px * dpr);
  el.height = Math.round(px * dpr);
  el.style.width = `${px}px`;
  el.style.height = `${px}px`;
  const ctx = el.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  // 1. The terrain field, masked, into a FIELD-sized buffer.
  const field = document.createElement("canvas");
  field.width = FIELD;
  field.height = FIELD;
  const fctx = field.getContext("2d");
  const img = fctx.createImageData(FIELD, FIELD);
  const maskImg = fctx.createImageData(FIELD, FIELD);
  const { rgb, jitter } = staticField;
  const look = PHASE_LOOK[props.phase] ?? PHASE_LOOK.day;
  const pcx = props.party.x + 0.5;
  const pcy = props.party.y + 0.5;
  for (let j = 0; j < FIELD; j += 1) {
    for (let i = 0; i < FIELD; i += 1) {
      const n = i + j * FIELD;
      const cov = maskAt((i + 0.5) / SUB, (j + 0.5) / SUB) + jitter[n] * 0.16;
      const a = smoothstep(0.36, 0.64, cov);
      // The wash's edge pools darker, like ink drying at a brushed border.
      const rim = Math.min(1, a * (1 - a) * 4.5);
      // Outside live sight the wash loses colour: memory, not sight.
      const dist = Math.hypot((i + 0.5) / SUB - pcx, (j + 0.5) / SUB - pcy);
      const away = smoothstep(props.liveRadius + 0.1, props.liveRadius + 1.1, dist) * look.desat;
      const o = n * 4;
      let r0 = mix(rgb[n * 3], 30, rim * 0.6);
      let g0 = mix(rgb[n * 3 + 1], 24, rim * 0.6);
      let b0 = mix(rgb[n * 3 + 2], 18, rim * 0.6);
      const lum = r0 * 0.3 + g0 * 0.59 + b0 * 0.11;
      img.data[o] = mix(r0, lum, away);
      img.data[o + 1] = mix(g0, lum, away);
      img.data[o + 2] = mix(b0, lum, away);
      // Fog is transparent: the map root's hatched ink shows through, so
      // the fog inside and outside the window is one surface.
      img.data[o + 3] = Math.round(a * 255);
      maskImg.data[o + 3] = Math.round(a * 255);
    }
  }
  fctx.putImageData(img, 0, 0);
  const maskCanvas = document.createElement("canvas");
  maskCanvas.width = FIELD;
  maskCanvas.height = FIELD;
  maskCanvas.getContext("2d").putImageData(maskImg, 0, 0);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(field, 0, 0, px, px);

  // 2. Inked strokes on their own layer, clipped to the revealed mask.
  const ink = document.createElement("canvas");
  ink.width = el.width;
  ink.height = el.height;
  const ictx = ink.getContext("2d");
  ictx.setTransform(dpr, 0, 0, dpr, 0, 0);
  drawInk(ictx, cellPx.value);
  ictx.setTransform(1, 0, 0, 1, 0, 0);
  ictx.globalCompositeOperation = "destination-in";
  ictx.imageSmoothingEnabled = true;
  ictx.drawImage(maskCanvas, 0, 0, ink.width, ink.height);
  ctx.setTransform(1, 0, 0, 1, 0, 0);
  ctx.drawImage(ink, 0, 0);
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

  // 3. Light on everything painted (source-atop keeps the fog clear):
  // memory dimming outside live sight, the phase wash, a moonlit disc.
  const c = cellPx.value;
  const lx = (props.party.x + 0.5) * c;
  const ly = (props.party.y + 0.5) * c;
  const inner = Math.max(0.4, props.liveRadius + 0.1) * c;
  const outer = (props.liveRadius + 1.1) * c;
  ctx.globalCompositeOperation = "source-atop";
  const dim = ctx.createRadialGradient(lx, ly, inner, lx, ly, outer);
  dim.addColorStop(0, "rgba(8, 9, 12, 0)");
  dim.addColorStop(1, `rgba(8, 9, 12, ${look.memory})`);
  ctx.fillStyle = dim;
  ctx.fillRect(0, 0, px, px);
  if (look.tint) {
    ctx.fillStyle = look.tint;
    ctx.fillRect(0, 0, px, px);
  }
  if (props.phase === "night") {
    const moon = ctx.createRadialGradient(lx, ly, 0, lx, ly, outer);
    moon.addColorStop(0, "rgba(170, 190, 230, 0.16)");
    moon.addColorStop(1, "rgba(170, 190, 230, 0)");
    ctx.fillStyle = moon;
    ctx.fillRect(0, 0, px, px);
  }
  ctx.globalCompositeOperation = "source-over";
}

function isSummit(cell) {
  for (let dy = -1; dy <= 1; dy += 1) {
    for (let dx = -1; dx <= 1; dx += 1) {
      if (!dx && !dy) continue;
      const n = cellAt(cell.x + dx, cell.y + dy);
      if (!n) continue;
      if (n.prominence > cell.prominence) return false;
      if (n.prominence === cell.prominence && (n.y < cell.y || (n.y === cell.y && n.x < cell.x))) return false;
    }
  }
  return true;
}

function seeded(i, j, k) {
  const v = Math.sin(i * 127.1 + j * 311.7 + k * 74.7) * 43758.5453;
  return v - Math.floor(v);
}

function strokePolyline(ctx, line, c) {
  ctx.beginPath();
  line.forEach(([x, y], i) => {
    if (i === 0) ctx.moveTo(x * c, y * c);
    else {
      const [px0, py0] = line[i - 1];
      ctx.quadraticCurveTo(px0 * c, py0 * c, ((px0 + x) / 2) * c, ((py0 + y) / 2) * c);
    }
  });
  const last = line[line.length - 1];
  ctx.lineTo(last[0] * c, last[1] * c);
}

function drawInk(ctx, c) {
  ctx.lineCap = "round";
  ctx.lineJoin = "round";

  // Prominent cells: summit rings, one per prominence tier.
  for (const row of GRID) {
    for (const cell of row) {
      if (!cell.prominence || !isSummit(cell)) continue;
      const cx = (cell.x + 0.5) * c;
      const cy = (cell.y + 0.5) * c;
      ctx.lineWidth = Math.max(1, c * 0.035);
      for (let k = 0; k < cell.prominence; k += 1) {
        ctx.strokeStyle = `rgba(36, 28, 20, ${0.55 - k * 0.12})`;
        ctx.beginPath();
        ctx.ellipse(cx, cy, c * (0.12 + k * 0.1), c * (0.08 + k * 0.07), -0.3, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.fillStyle = "rgba(36, 28, 20, 0.7)";
      ctx.beginPath();
      ctx.arc(cx, cy, Math.max(1, c * 0.035), 0, Math.PI * 2);
      ctx.fill();
    }
  }

  // Woods: brush-dabbed conifers, three per cell, jittered.
  for (const row of GRID) {
    for (const cell of row) {
      if (cell.terrain !== "woodland") continue;
      for (let k = 0; k < 3; k += 1) {
        const tx = (cell.x + 0.2 + seeded(cell.x, cell.y, k) * 0.6) * c;
        const ty = (cell.y + 0.25 + seeded(cell.y, cell.x, k + 5) * 0.55) * c;
        const s = c * (0.14 + seeded(cell.x, k, cell.y) * 0.08);
        ctx.fillStyle = "rgba(24, 36, 27, 0.9)";
        ctx.beginPath();
        ctx.moveTo(tx, ty - s * 1.5);
        ctx.lineTo(tx + s, ty + s * 0.6);
        ctx.lineTo(tx - s, ty + s * 0.6);
        ctx.closePath();
        ctx.fill();
        ctx.strokeStyle = "rgba(150, 176, 140, 0.4)";
        ctx.lineWidth = Math.max(0.8, c * 0.03);
        ctx.beginPath();
        ctx.moveTo(tx - s * 0.7, ty + s * 0.2);
        ctx.lineTo(tx, ty - s * 1.4);
        ctx.stroke();
      }
    }
  }

  // The river: a dark bank wash, the water body, a light current line.
  strokePolyline(ctx, RIVER, c);
  ctx.strokeStyle = "rgba(30, 38, 40, 0.45)";
  ctx.lineWidth = c * 1.1;
  ctx.stroke();
  ctx.strokeStyle = "#4a6a7c";
  ctx.lineWidth = c * 0.62;
  ctx.stroke();
  ctx.strokeStyle = "rgba(150, 182, 200, 0.45)";
  ctx.lineWidth = Math.max(1, c * 0.07);
  ctx.setLineDash([c * 0.5, c * 0.35]);
  ctx.stroke();
  ctx.setLineDash([]);

  // The ford: stepping stones across the water.
  for (let k = 0; k < 4; k += 1) {
    const sx = (FORD.x + 0.12 + k * 0.26) * c;
    const sy = (FORD.y + 0.42 + (k % 2) * 0.16) * c;
    ctx.fillStyle = "#cfc6b2";
    ctx.beginPath();
    ctx.ellipse(sx, sy, c * 0.09, c * 0.06, 0.3, 0, Math.PI * 2);
    ctx.fill();
  }

  // The road: an ink underlay and a gold dash.
  strokePolyline(ctx, ROAD, c);
  ctx.strokeStyle = "rgba(28, 22, 16, 0.55)";
  ctx.lineWidth = Math.max(3, c * 0.16);
  ctx.stroke();
  ctx.strokeStyle = "rgba(208, 178, 118, 0.9)";
  ctx.lineWidth = Math.max(1.5, c * 0.07);
  ctx.setLineDash([c * 0.32, c * 0.2]);
  ctx.stroke();
  ctx.setLineDash([]);

  // The district edge: a dotted paper line along changing cells.
  ctx.fillStyle = "rgba(40, 32, 24, 0.55)";
  for (let y = 0; y < WINDOW; y += 1) {
    for (let x = 0; x < WINDOW - 1; x += 1) {
      if (districtOf(x, y) !== districtOf(x + 1, y)) {
        for (let k = 0; k < 3; k += 1) {
          ctx.beginPath();
          ctx.arc((x + 1) * c, (y + k / 3 + 0.16) * c, Math.max(1, c * 0.04), 0, Math.PI * 2);
          ctx.fill();
        }
      }
    }
  }

  // The city wall in the south-west corner.
  ctx.strokeStyle = "rgba(228, 200, 142, 0.85)";
  ctx.lineWidth = Math.max(1.5, c * 0.08);
  ctx.beginPath();
  ctx.moveTo(-1 * c, (CITY.y - 1.2) * c);
  ctx.lineTo((CITY.x + 0.6) * c, (CITY.y - 0.6) * c);
  ctx.lineTo((CITY.x + 1.1) * c, (CITY.y + 0.8) * c);
  ctx.lineTo((CITY.x + 0.5) * c, (WINDOW + 1) * c);
  ctx.stroke();
  ctx.fillStyle = "rgba(40, 36, 30, 0.9)";
  ctx.fill();

  // A faint cell grid, only near the party where cell precision matters.
  ctx.strokeStyle = "rgba(30, 24, 18, 0.16)";
  ctx.lineWidth = 1;
  const r = Math.max(2, props.liveRadius + 1);
  for (let k = -r; k <= r + 1; k += 1) {
    ctx.beginPath();
    ctx.moveTo((props.party.x + k) * c, (props.party.y - r) * c);
    ctx.lineTo((props.party.x + k) * c, (props.party.y + r + 1) * c);
    ctx.moveTo((props.party.x - r) * c, (props.party.y + k) * c);
    ctx.lineTo((props.party.x + r + 1) * c, (props.party.y + k) * c);
    ctx.stroke();
  }
}

// ---------------------------------------------------------- overlay model

function revealed(x, y) {
  return x >= 0 && y >= 0 && x < WINDOW && y < WINDOW && props.mask[y * WINDOW + x] === 1;
}

const neighbours = computed(() =>
  DIRECTIONS.map((d) => {
    const x = props.party.x + d.dx;
    const y = props.party.y + d.dy;
    return { ...d, x, y, open: canStep(props.party.x, props.party.y, d.dx, d.dy), reason: blockReason(props.party.x, props.party.y, d.dx, d.dy) };
  }),
);

const aimed = computed(() => neighbours.value.find((n) => n.key === props.aim) ?? null);

const routeDots = computed(() => {
  if (!props.plan) return [];
  return props.plan.steps.map((s, i) => ({
    ...s,
    i,
    beyond: i > props.plan.stopIndex,
    dim: props.plan.nightfallIndex !== null && i > props.plan.nightfallIndex,
  }));
});

const routePath = computed(() => {
  if (!props.plan || !props.plan.steps.length) return "";
  const c = cellPx.value;
  const pts = [props.party, ...props.plan.steps.slice(0, props.plan.stopIndex + 1)];
  return pts.map((p, i) => `${i ? "L" : "M"}${(p.x + 0.5) * c} ${(p.y + 0.5) * c}`).join(" ");
});

const landmarks = computed(() => LANDMARKS.filter((l) => revealed(l.x, l.y)));

const STAGE_CLASS = { normal: "is-normal", light: "is-light", moderate: "is-moderate", severe: "is-severe", asleep: "is-severe" };

const hoverLabel = computed(() => {
  const h = hoverCell.value;
  if (!h) return null;
  if (!revealed(h.x, h.y)) return { x: h.x, y: h.y, text: "未探明", muted: true };
  const cell = cellAt(h.x, h.y);
  const lm = LANDMARKS.find((l) => l.x === h.x && l.y === h.y);
  return { x: h.x, y: h.y, text: lm ? lm.name : TERRAIN_LABEL[cell.terrain], muted: false };
});

// The distant-sighting chips sit on the bearing ray, clamped inside the
// open stage so they never hide under the band or the place card.
function sightingStyle(s) {
  const c = cellPx.value;
  const len = Math.hypot(s.dx, s.dy);
  const ux = s.dx / len;
  const uy = s.dy / len;
  const o = openStage.value;
  const ox = (o.left + o.right) / 2;
  const oy = (o.top + o.bottom) / 2;
  const top = o.top + 60;
  const bottom = o.bottom - 30;
  const left = o.left + 40;
  const right = o.right - 40;
  let t = 99999;
  const limits = [
    ux > 0 ? (right - ox) / ux : ux < 0 ? (left - ox) / ux : Infinity,
    uy > 0 ? (bottom - oy) / uy : uy < 0 ? (top - oy) / uy : Infinity,
  ];
  t = Math.min(t, ...limits);
  return { left: `${ox + ux * t}px`, top: `${oy + uy * t}px` };
}

function sightingRay(s) {
  const c = cellPx.value;
  const len = Math.hypot(s.dx, s.dy);
  const ox = (props.party.x + 0.5) * c;
  const oy = (props.party.y + 0.5) * c;
  const reach = Math.min(len, props.liveRadius + 4) * c;
  return { x1: ox + (s.dx / len) * (props.liveRadius + 1) * c, y1: oy + (s.dy / len) * (props.liveRadius + 1) * c, x2: ox + (s.dx / len) * reach, y2: oy + (s.dy / len) * reach };
}

// --------------------------------------------------------------- input

function cellFromEvent(event) {
  const rect = root.value.getBoundingClientRect();
  const x = Math.floor((event.clientX - rect.left - camera.value.x) / cellPx.value);
  const y = Math.floor((event.clientY - rect.top - camera.value.y) / cellPx.value);
  if (x < 0 || y < 0 || x >= WINDOW || y >= WINDOW) return null;
  return { x, y };
}

function onPointerMove(event) {
  if (props.walking) return;
  const cell = cellFromEvent(event);
  hoverCell.value = cell;
  emit("hover", cell);
}

function onPointerLeave() {
  hoverCell.value = null;
  emit("hover", null);
}

function onClick(event) {
  root.value?.focus({ preventScroll: true });
  const cell = cellFromEvent(event);
  if (!cell) return;
  emit("pick", cell);
}

function onWheel(event) {
  event.preventDefault();
  emit("zoom", event.deltaY < 0 ? 1 : -1);
}

const pressed = new Set();
let holdTimer = null;

function aimFromKeys() {
  let dx = 0;
  let dy = 0;
  if (pressed.has("ArrowUp")) dy -= 1;
  if (pressed.has("ArrowDown")) dy += 1;
  if (pressed.has("ArrowLeft")) dx -= 1;
  if (pressed.has("ArrowRight")) dx += 1;
  return DIRECTIONS.find((d) => d.dx === dx && d.dy === dy)?.key ?? null;
}

function onKeyDown(event) {
  const key = event.key;
  if (key.startsWith("Arrow")) {
    event.preventDefault();
    if (event.repeat) return;
    pressed.add(key);
    emit("aim", aimFromKeys());
    clearTimeout(holdTimer);
    holdTimer = setTimeout(() => emit("hold", aimFromKeys()), 400);
    return;
  }
  if (key === "Enter" || key === " ") {
    event.preventDefault();
    if (props.aim) emit("step", props.aim);
    else emit("confirm");
    return;
  }
  if (key === "Escape") {
    event.preventDefault();
    emit("cancel");
    return;
  }
  if (key === "+" || key === "=") emit("zoom", 1);
  if (key === "-") emit("zoom", -1);
}

function onKeyUp(event) {
  if (!event.key.startsWith("Arrow")) return;
  pressed.delete(event.key);
  if (!pressed.size) {
    clearTimeout(holdTimer);
    emit("release");
  } else {
    emit("aim", aimFromKeys());
  }
}

function onBlur() {
  pressed.clear();
  clearTimeout(holdTimer);
  emit("release");
}

// --------------------------------------------------------------- sizing

let observer = null;

function measure() {
  const el = root.value;
  if (!el) return;
  const cs = getComputedStyle(el);
  const px = (name, fallback) => {
    const probe = document.createElement("div");
    probe.style.position = "absolute";
    probe.style.height = `var(${name})`;
    el.appendChild(probe);
    const v = probe.getBoundingClientRect().height || fallback;
    probe.remove();
    return v;
  };
  uiScale.value = Number.parseFloat(cs.getPropertyValue("--ui-scale")) || 1;
  size.value = { w: el.clientWidth, h: el.clientHeight, top: px("--header-h", 48), bottom: px("--band-h", 220) };
}

onMounted(() => {
  measure();
  observer = new ResizeObserver(() => measure());
  observer.observe(root.value);
  nextTick(paint);
});

onBeforeUnmount(() => {
  observer?.disconnect();
  clearTimeout(holdTimer);
});

watch(
  () => [props.mask, props.phase, props.liveRadius, props.party.x, props.party.y, cellPx.value],
  () => paint(),
);

defineExpose({ focus: () => root.value?.focus({ preventScroll: true }) });

const c = cellPx;
const center = (v) => (v + 0.5) * c.value;
</script>

<template>
  <div
    ref="root"
    class="travel-map"
    :class="[`travel-map--${phase}`, { 'travel-map--walking': walking, 'travel-map--still': motion === 'off' }]"
    tabindex="0"
    role="application"
    aria-roledescription="旅途地圖"
    aria-label="旅途地圖。方向鍵瞄準鄰格，Enter 前進一步；在已探明的格子上點一下預覽路線，再點一次出發。"
    data-testid="travel-map"
    @pointermove="onPointerMove"
    @pointerleave="onPointerLeave"
    @click="onClick"
    @wheel="onWheel"
    @keydown="onKeyDown"
    @keyup="onKeyUp"
    @blur="onBlur"
  >
    <div class="travel-map__world" :style="{ transform: `translate(${camera.x}px, ${camera.y}px)` }">
      <canvas ref="canvas" class="travel-map__canvas" aria-hidden="true"></canvas>
      <svg class="travel-map__overlay" :width="span" :height="span" aria-hidden="true">
        <defs>
          <filter id="tm-glow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" />
          </filter>
        </defs>
        <!-- Live sight: a quiet dashed ring. -->
        <circle
          class="travel-map__sight"
          :cx="center(party.x)"
          :cy="center(party.y)"
          :r="(liveRadius + 0.5) * c"
        />
        <!-- Distant-sighting bearings. -->
        <line
          v-for="s in sightings"
          :key="`ray-${s.id}`"
          class="travel-map__ray"
          v-bind="sightingRay(s)"
        />
        <!-- The route preview. -->
        <g v-if="plan" class="travel-map__route">
          <path class="travel-map__route-line" :d="routePath" />
          <g v-for="dot in routeDots" :key="`d-${dot.i}`" :class="[STAGE_CLASS[dot.stage], { 'is-beyond': dot.beyond, 'is-dim': dot.dim }]">
            <circle v-if="dot.stage === 'normal'" :cx="center(dot.x)" :cy="center(dot.y)" :r="c * 0.11" />
            <rect
              v-else-if="dot.stage === 'light'"
              :x="center(dot.x) - c * 0.1"
              :y="center(dot.y) - c * 0.1"
              :width="c * 0.2"
              :height="c * 0.2"
              :transform="`rotate(45 ${center(dot.x)} ${center(dot.y)})`"
            />
            <circle v-else :cx="center(dot.x)" :cy="center(dot.y)" :r="c * 0.1" class="is-ring" />
          </g>
          <!-- Nightfall: a crescent on the step where night begins. -->
          <g
            v-if="plan.nightfallIndex !== null && plan.steps[plan.nightfallIndex]"
            class="travel-map__moon"
            :transform="`translate(${center(plan.steps[plan.nightfallIndex].x)} ${center(plan.steps[plan.nightfallIndex].y) - c * 0.55})`"
          >
            <circle :r="c * 0.24" class="travel-map__moon-disc" />
            <path :d="`M ${c * 0.06} ${-c * 0.15} a ${c * 0.15} ${c * 0.15} 0 1 0 0 ${c * 0.3} a ${c * 0.11} ${c * 0.11} 0 1 1 0 ${-c * 0.3} z`" class="travel-map__moon-glyph" />
          </g>
          <!-- The stop: a camp mark. -->
          <g
            v-if="plan.steps[plan.stopIndex] && plan.stopReason !== 'arrival'"
            class="travel-map__camp"
            :transform="`translate(${center(plan.steps[plan.stopIndex].x)} ${center(plan.steps[plan.stopIndex].y)})`"
          >
            <circle :r="c * 0.36" />
            <path :d="`M ${-c * 0.2} ${c * 0.16} L 0 ${-c * 0.2} L ${c * 0.2} ${c * 0.16} Z M ${-c * 0.06} ${c * 0.16} L 0 ${c * 0.04} L ${c * 0.06} ${c * 0.16}`" />
          </g>
          <!-- The destination. -->
          <rect
            v-if="target"
            class="travel-map__target"
            :x="target.x * c + 2"
            :y="target.y * c + 2"
            :width="c - 4"
            :height="c - 4"
            rx="3"
          />
        </g>
        <!-- Hover. -->
        <rect
          v-if="hoverCell && !walking"
          class="travel-map__hover"
          :class="{ 'is-fog': !revealed(hoverCell.x, hoverCell.y) }"
          :x="hoverCell.x * c + 1"
          :y="hoverCell.y * c + 1"
          :width="c - 2"
          :height="c - 2"
          rx="2"
        />
        <!-- Landmarks: the band ornament's diamond. -->
        <g v-for="l in landmarks" :key="l.id" class="travel-map__landmark" :transform="`translate(${center(l.x)} ${center(l.y)})`">
          <path :d="`M 0 ${-c * 0.42} L ${c * 0.3} 0 L 0 ${c * 0.42} L ${-c * 0.3} 0 Z`" />
          <circle :r="c * 0.07" />
        </g>
        <!-- Hostiles in live sight. -->
        <g v-for="h in hostiles" :key="h.id" class="travel-map__hostile" :transform="`translate(${center(h.x)} ${center(h.y)})`">
          <circle :r="c * 0.34" class="travel-map__hostile-halo" filter="url(#tm-glow)" />
          <circle :r="c * 0.28" />
          <path :d="`M ${-c * 0.13} ${c * 0.1} L 0 ${-c * 0.13} L ${c * 0.13} ${c * 0.1}`" />
        </g>
        <!-- Neighbour nodes around the token. -->
        <g v-if="!walking" class="travel-map__ring">
          <rect
            v-if="aimed && aimed.open"
            class="travel-map__aim-cell"
            :x="aimed.x * c + 1"
            :y="aimed.y * c + 1"
            :width="c - 2"
            :height="c - 2"
            rx="3"
          />
          <circle
            v-for="n in neighbours"
            :key="n.key"
            :cx="center(n.x)"
            :cy="center(n.y)"
            :r="Math.max(3.5, c * (n.key === aim ? 0.15 : 0.1))"
            :class="{ 'is-blocked': !n.open, 'is-aimed': n.key === aim }"
          />
        </g>
        <!-- The party token. -->
        <g class="travel-map__token" :transform="`translate(${center(party.x)} ${center(party.y)})`">
          <circle :r="Math.max(14, c * 0.55)" class="travel-map__token-halo" />
          <circle :r="Math.max(9, c * 0.36)" class="travel-map__token-body" />
          <circle :r="Math.max(3, c * 0.12)" class="travel-map__token-core" />
        </g>
      </svg>
      <!-- HTML chips in world space. -->
      <div
        v-for="l in landmarks"
        :key="`chip-${l.id}`"
        class="tm-chip tm-chip--gold"
        data-side="above"
        :style="{ left: `${center(l.x)}px`, top: `${(l.y + 0.5) * c - Math.max(14, c * 0.5)}px` }"
      >{{ l.name }}</div>
      <div
        v-for="h in hostiles"
        :key="`chip-${h.id}`"
        class="tm-chip tm-chip--seal"
        :style="{ left: `${center(h.x)}px`, top: `${(h.y + 0.95) * c}px` }"
      >{{ h.name }} ×{{ h.count }}・<b>{{ h.threat }}</b></div>
      <div
        v-if="FORD && revealed(FORD.x, FORD.y)"
        class="tm-chip tm-chip--quiet"
        :style="{ left: `${center(FORD.x)}px`, top: `${(FORD.y + 1) * c}px` }"
      >主渡口</div>
      <div
        v-if="revealed(CITY.x, CITY.y)"
        class="tm-chip tm-chip--gold"
        :style="{ left: `${(CITY.x + 2.2) * c}px`, top: `${(CITY.y - 0.4) * c}px` }"
      >{{ CITY.name }}</div>
      <div
        v-if="aimed && !walking"
        class="tm-chip tm-chip--aim"
        :class="{ 'is-blocked': !aimed.open }"
        :style="{ left: `${center(aimed.x) + (aimed.dx >= 0 ? c * 0.7 : -c * 0.7)}px`, top: `${center(aimed.y)}px` }"
        :data-side="aimed.dx >= 0 ? 'right' : 'left'"
      >
        {{ aimed.label }}・{{ aimed.open ? TERRAIN_LABEL[cellAt(aimed.x, aimed.y).terrain] : aimed.reason }}
      </div>
      <div
        v-else-if="hoverLabel && !plan && !walking"
        class="tm-chip"
        :class="hoverLabel.muted ? 'tm-chip--quiet' : 'tm-chip--paper'"
        :style="{ left: `${center(hoverLabel.x)}px`, top: `${(hoverLabel.y - 0.25) * c}px` }"
        data-side="above"
      >{{ hoverLabel.text }}</div>
    </div>
    <!-- Orientation: a north mark and a five-kilometre scale bar. -->
    <div class="tm-legend" aria-hidden="true">
      <svg class="tm-legend__rose" viewBox="-20 -20 40 40">
        <circle r="15" class="tm-legend__ring" />
        <path d="M0 -17 L4 0 L0 4 L-4 0 Z" class="tm-legend__north" />
        <path d="M0 17 L4 0 L0 -4 L-4 0 Z" class="tm-legend__south" />
        <path d="M-17 0 L0 -2.5 L17 0 L0 2.5 Z" class="tm-legend__south" />
      </svg>
      <span class="tm-legend__n">北</span>
      <span class="tm-legend__scale">
        <span class="tm-legend__bar" :style="{ width: `${5 * c}px` }"></span>
        5 公里
      </span>
    </div>
    <!-- Distant sightings sit in screen space at the stage edge. -->
    <div
      v-for="s in sightings"
      :key="`s-${s.id}`"
      class="tm-sighting"
      :style="sightingStyle(s)"
    >
      <span class="tm-sighting__bearing">{{ s.bearing }}・約 {{ s.km }} 公里</span>
      <span class="tm-sighting__what">{{ s.label }}</span>
    </div>
  </div>
</template>

<style>
.travel-map {
  position: absolute;
  inset: 0;
  overflow: hidden;
  outline: none;
  cursor: crosshair;
  background:
    repeating-linear-gradient(-45deg, rgba(30, 31, 36, 0.85) 0 1px, transparent 1px 8px),
    radial-gradient(120% 90% at 50% 40%, #121418, #0a0b0d);
}
.travel-map:focus-visible::after {
  content: "";
  position: absolute;
  inset: calc(var(--header-h) + 6px) 6px calc(var(--band-h) + 6px) 6px;
  border: 1px solid rgba(228, 200, 142, 0.28);
  border-radius: var(--radius);
  pointer-events: none;
}
.travel-map__world {
  position: absolute;
  left: 0;
  top: 0;
  transition: transform calc(380ms * var(--motion-travel)) var(--ease-standard);
  will-change: transform;
}
.travel-map--still .travel-map__world {
  transition: none;
}
.travel-map__canvas,
.travel-map__overlay {
  position: absolute;
  left: 0;
  top: 0;
}
.travel-map__overlay {
  overflow: visible;
  pointer-events: none;
}

.travel-map__sight {
  fill: none;
  stroke: rgba(242, 236, 223, 0.22);
  stroke-width: 1;
  stroke-dasharray: 2 6;
}
.travel-map--night .travel-map__sight {
  stroke: rgba(170, 190, 230, 0.32);
}
.travel-map__ray {
  stroke: rgba(228, 200, 142, 0.5);
  stroke-width: 1.2;
  stroke-dasharray: 1 6;
  stroke-linecap: round;
}

.travel-map__route-line {
  fill: none;
  stroke: rgba(228, 200, 142, 0.28);
  stroke-width: 2;
}
.travel-map__route .is-normal circle,
.travel-map__route .is-normal rect {
  fill: var(--gold-400);
}
.travel-map__route .is-light rect {
  fill: var(--warn);
}
.travel-map__route .is-ring {
  fill: none;
  stroke: #d0705a;
  stroke-width: 2;
}
.travel-map__route .is-dim {
  opacity: 0.55;
}
.travel-map__route .is-beyond {
  opacity: 0.28;
}
.travel-map__route .is-beyond circle:not(.is-ring),
.travel-map__route .is-beyond rect {
  fill: none;
  stroke: var(--paper-400);
  stroke-width: 1.5;
}
.travel-map__moon-disc {
  fill: rgba(13, 16, 28, 0.92);
  stroke: rgba(170, 190, 230, 0.7);
  stroke-width: 1;
}
.travel-map__moon-glyph {
  fill: #c8d4ee;
}
.travel-map__camp circle {
  fill: rgba(15, 12, 18, 0.92);
  stroke: var(--gold-400);
  stroke-width: 1.6;
}
.travel-map__camp path {
  fill: none;
  stroke: var(--gold-300);
  stroke-width: 1.6;
  stroke-linejoin: round;
}
.travel-map__target {
  fill: rgba(228, 200, 142, 0.1);
  stroke: var(--gold-400);
  stroke-width: 1.5;
}
.travel-map__hover {
  fill: rgba(242, 236, 223, 0.06);
  stroke: rgba(242, 236, 223, 0.45);
  stroke-width: 1;
}
.travel-map__hover.is-fog {
  stroke: rgba(242, 236, 223, 0.18);
  stroke-dasharray: 3 3;
}

.travel-map__landmark path {
  fill: #0f0c12;
  stroke: var(--gold-400);
  stroke-width: 1.8;
}
.travel-map__landmark circle {
  fill: var(--gold-400);
}

.travel-map__hostile circle {
  fill: #2a1416;
  stroke: var(--seal-500);
  stroke-width: 1.8;
}
.travel-map__hostile .travel-map__hostile-halo {
  fill: rgba(207, 68, 68, 0.35);
  stroke: none;
}
.travel-map__hostile path {
  fill: none;
  stroke: var(--seal-light);
  stroke-width: 1.8;
  stroke-linejoin: round;
}

.travel-map__ring circle {
  fill: #0f0c12;
  stroke: var(--gold-400);
  stroke-width: 1.2;
}
.travel-map__ring circle.is-aimed {
  fill: var(--gold-400);
  stroke: var(--gold-300);
}
.travel-map__ring circle.is-blocked {
  fill: none;
  stroke: var(--paper-500);
  stroke-dasharray: 2 2;
}
.travel-map__aim-cell {
  fill: rgba(228, 200, 142, 0.14);
  stroke: var(--gold-400);
  stroke-width: 1.2;
}

.travel-map__token-halo {
  transform-box: fill-box;
  fill: none;
  stroke: rgba(207, 68, 68, 0.35);
  stroke-width: 5;
  transform-origin: center;
  animation: tm-breathe 3.2s ease-in-out infinite;
}
.travel-map__token-body {
  fill: var(--seal-500);
  stroke: var(--gold-300);
  stroke-width: 2;
}
.travel-map__token-core {
  fill: var(--gold-300);
}
.travel-map--still .travel-map__token-halo {
  animation: none;
}
@keyframes tm-breathe {
  50% {
    stroke-opacity: 0.12;
    transform: scale(1.12);
  }
}

.tm-chip {
  position: absolute;
  transform: translate(-50%, 0);
  white-space: nowrap;
  padding: calc(2px * var(--ui-scale)) calc(8px * var(--ui-scale));
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
.tm-chip--quiet {
  color: var(--paper-400);
  background: rgba(15, 17, 21, 0.7);
}
.tm-chip--paper {
  color: var(--paper-50);
  background: rgba(15, 17, 21, 0.85);
  border: 1px solid rgba(242, 236, 223, 0.25);
}
.tm-chip--aim {
  color: var(--gold-300);
  background: rgba(15, 17, 21, 0.9);
  border: 1px solid var(--gold-600);
}
.tm-chip--aim.is-blocked {
  color: var(--paper-400);
  border-style: dashed;
  border-color: var(--paper-700);
}

.tm-legend {
  position: absolute;
  left: calc(22px * var(--ui-scale));
  top: calc(var(--header-h) + 18px * var(--ui-scale));
  display: grid;
  grid-template-columns: auto auto;
  align-items: center;
  column-gap: calc(10px * var(--ui-scale));
  pointer-events: none;
}
.tm-legend__rose {
  width: calc(44px * var(--ui-scale));
  height: calc(44px * var(--ui-scale));
  grid-row: span 2;
}
.tm-legend__ring {
  fill: rgba(11, 13, 16, 0.7);
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
}
.tm-legend__scale {
  display: grid;
  gap: calc(3px * var(--ui-scale));
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--paper-400);
}
.tm-legend__bar {
  display: block;
  height: calc(5px * var(--ui-scale));
  border: 1px solid rgba(201, 196, 185, 0.6);
  border-top: 0;
  transition: width var(--motion-base) var(--ease-standard);
}
.tm-sighting {
  position: absolute;
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
.travel-map--night .tm-sighting {
  border-color: rgba(170, 190, 230, 0.5);
}
.travel-map--night .tm-sighting__bearing {
  color: #c8d4ee;
}
</style>
