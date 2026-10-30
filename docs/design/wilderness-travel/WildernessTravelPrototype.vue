<script setup>
// Wilderness travel-mode prototype (reference only, mock data; not imported
// by the app). Layout A of the travel-mode blueprint on the real HudFrame:
// the full-bleed ink map as the backdrop, the party as medallions in the
// lower-left dock, the place card top-right, the travel log in the band's
// message region and the leg panel in its command region; event cards
// (landmark, camp, campfire) use the stage's `choices` anchor.
//
// Nothing dispatches. The rules the server owns (sight, reveal, routing,
// reserve prediction, interrupt flags) are imitated by travel-model.js; the
// intents the real client would send are written to the strip above the
// stage. Try it: hover a revealed cell for a route, click to lock it, click
// again or Enter to depart; arrows aim a neighbour, Enter steps, holding an
// arrow walks; any key stops a walk. 紮營 opens the camp card.
import { computed, nextTick, onBeforeUnmount, onMounted, ref, shallowRef } from "vue";
import HudFrame from "../../../web/webclient-app/components/HudFrame.vue";
import PlaceCard from "../../../web/webclient-app/components/PlaceCard.vue";
// The card frame (`choice-card`) is ChoiceCard's global stylesheet.
import "../../../web/webclient-app/components/ChoiceCard.vue";
import CampCard from "./CampCard.vue";
import CampfireCard from "./CampfireCard.vue";
import LandmarkCard from "./LandmarkCard.vue";
import LegPanel from "./LegPanel.vue";
import PartyMedallions from "./PartyMedallions.vue";
import TravelLog from "./TravelLog.vue";
import TravelMap from "./TravelMap.vue";
import {
  DIRECTIONS,
  DISTANT_SOURCES,
  HOME,
  HOSTILES,
  LANDMARKS,
  PACES,
  PHASE_LABEL,
  RESERVE_FULL,
  SLEEP_RESTORE_PER_SECOND,
  STAGE_INDEX,
  TERRAIN_LABEL,
  WALK_COST_PER_SECOND,
  WINDOW,
  canStep,
  capacityByStage,
  cellAt,
  compassBearing,
  districtOf,
  findRoute,
  formatClock,
  inDisc,
  initialVisits,
  lightPhase,
  planRoute,
  revealedMask,
  sightRadius,
  stageOf,
  stepSeconds,
} from "./travel-model.js";

const props = defineProps({
  // "free" | "route" | "dusk" | "night" | "woodland" | "camp" | "campfire" | "landmark"
  scenario: { type: String, default: "free" },
  // The effective motion level: "full" or "off".
  motion: { type: String, default: "full" },
  zoom: { type: Number, default: 30 },
});

const DAY_START = 11 * 1440;
const at = (h, m = 0) => DAY_START + h * 60 + m;

const party = ref({ ...HOME });
const minutes = ref(at(6, 10));
const members = ref([]);
const visits = shallowRef([]);
const lit = shallowRef(new Set());
const pace = ref("standard");
const stopAtNight = ref(true);
const aim = ref(null);
const hover = ref(null);
const target = ref(null);
const walking = ref(false);
const walkKind = ref(null);
// The route being walked and how many of its steps are done.
const walkPlan = shallowRef(null);
const progress = ref(0);
const card = ref(null);
const cardData = ref(null);
const rememberDream = ref(false);
const zoomLevel = ref(props.zoom);
const log = ref([]);
const intents = ref([]);
const mapRef = ref(null);

const phase = computed(() => lightPhase(minutes.value));
const liveRadius = computed(() => sightRadius(party.value.x, party.value.y, phase.value));
const mask = computed(() => revealedMask(visits.value, lit.value));
const awake = computed(() => members.value.filter((m) => !m.asleep));
const slowest = computed(() => Math.min(...awake.value.map((m) => m.reserve)));
const clock = computed(() => formatClock(minutes.value));
const here = computed(() => cellAt(party.value.x, party.value.y));

function isRevealed(x, y) {
  return x >= 0 && y >= 0 && x < WINDOW && y < WINDOW && mask.value[y * WINDOW + x] === 1;
}

// ------------------------------------------------------------ derived

const hostiles = computed(() =>
  HOSTILES.filter((h) => inDisc(h.x, h.y, party.value.x, party.value.y, liveRadius.value)),
);

const sightings = computed(() => {
  const out = [];
  // Under the canopy nothing far is in view.
  if (here.value?.terrain === "woodland") return out;
  for (const s of DISTANT_SOURCES) {
    const { dx, dy } = s.bearingFrom(party.value);
    const dist = Math.hypot(dx, dy);
    const reach = phase.value === "night" ? s.nightKm : phase.value === "day" ? s.dayKm : s.dayKm * 0.6;
    if (!reach || dist > reach) continue;
    const sx = party.value.x + dx;
    const sy = party.value.y + dy;
    if (inDisc(sx, sy, party.value.x, party.value.y, liveRadius.value)) continue;
    if (isRevealed(sx, sy)) continue;
    const lm = LANDMARKS.find((l) => l.id === s.id);
    const named = lm && lit.value.has(lm.district);
    const label = named ? lm.name : phase.value === "night" && s.nightSilhouette ? s.nightSilhouette : s.silhouette;
    out.push({ id: s.id, dx, dy, bearing: compassBearing(dx, dy), km: Math.max(5, Math.round(dist / 5) * 5), label });
  }
  return out;
});

const capacity = computed(() => {
  const per = here.value?.terrain === "woodland" ? 1800 : 1200;
  return capacityByStage(slowest.value, per);
});

const routeTo = computed(() => target.value ?? (walking.value ? null : hoverRouteCell.value));
const hoverRouteCell = computed(() => {
  const h = hover.value;
  if (!h || aim.value) return null;
  if (Math.max(Math.abs(h.x - party.value.x), Math.abs(h.y - party.value.y)) <= 1) return null;
  return isRevealed(h.x, h.y) ? h : null;
});

const plan = computed(() => {
  const to = routeTo.value;
  if (!to) return null;
  const steps = findRoute(party.value, to, mask.value);
  if (!steps || !steps.length) return null;
  return planRoute({ from: party.value, steps, reserve: slowest.value, minutes: minutes.value, pace: pace.value, stopAtNight: stopAtNight.value });
});

// A locked route keeps the whole leg and its destination in view.
const routeFocus = computed(() => {
  if (walking.value || !target.value || !plan.value) return null;
  const pts = [party.value, target.value, ...plan.value.steps];
  return {
    minX: Math.min(...pts.map((p) => p.x)),
    maxX: Math.max(...pts.map((p) => p.x)),
    minY: Math.min(...pts.map((p) => p.y)),
    maxY: Math.max(...pts.map((p) => p.y)),
  };
});

// While walking, the map and the gauge keep the rest of the departed route.
const remainingPlan = computed(() => {
  const p = walkPlan.value;
  if (!p) return null;
  const k = progress.value;
  return {
    ...p,
    steps: p.steps.slice(k),
    stopIndex: p.stopIndex - k,
    nightfallIndex: p.nightfallIndex === null || p.nightfallIndex < k ? null : p.nightfallIndex - k,
  };
});

function nameOf(cell) {
  const lm = LANDMARKS.find((l) => l.x === cell.x && l.y === cell.y);
  if (lm) return lm.name;
  const c = cellAt(cell.x, cell.y);
  return c.terrain === "ford" ? "主渡口" : `${compassBearing(cell.x - party.value.x, cell.y - party.value.y)}方的${TERRAIN_LABEL[c.terrain]}`;
}

const intent = computed(() => {
  if (walking.value) {
    return walkKind.value === "route"
      ? { kind: "walking", title: `前往${nameOf(target.value)}`, detail: "行進中・任意鍵停步" }
      : { kind: "walking", title: `朝${DIRECTIONS.find((d) => d.key === walkKind.value)?.label ?? ""}連續前進`, detail: "放開方向鍵停步" };
  }
  if (aim.value) {
    const d = DIRECTIONS.find((x) => x.key === aim.value);
    const ok = canStep(party.value.x, party.value.y, d.dx, d.dy);
    const sec = ok ? stepSeconds(party.value.x, party.value.y, party.value.x + d.dx, party.value.y + d.dy, slowest.value) : 0;
    return { kind: "aim", title: `瞄準${d.label}・一步`, detail: ok ? `${Math.round(sec / 60)} 分・Enter 前進` : "無法通行" };
  }
  if (plan.value && routeTo.value) {
    return { kind: "route", title: `前往${nameOf(routeTo.value)}`, detail: null };
  }
  const stopStage = PACES.find((p) => p.key === pace.value)?.stopStage;
  if (stopStage && STAGE_INDEX[stageOf(slowest.value).key] >= STAGE_INDEX[stopStage]) {
    return { kind: "none", title: "已到今天的節制門檻", detail: "建議紮營" };
  }
  if (phase.value === "night" && stopAtNight.value) {
    return { kind: "none", title: "夜裡只看得見身邊", detail: "建議紮營到天亮" };
  }
  return { kind: "none", title: "點選已探明的格子規劃路線", detail: null };
});

const placeLabel = computed(() => {
  const t = here.value?.terrain;
  return `${districtOf(party.value.x, party.value.y)}・${TERRAIN_LABEL[t] ?? ""}`;
});

// ------------------------------------------------------------- logging

function addLog(tone, html) {
  log.value = [...log.value, { day: clock.value.day, time: clock.value.text, tone, html }];
}

function intentLog(text) {
  intents.value = [text, ...intents.value].slice(0, 3);
}

// ---------------------------------------------------------------- steps

function recordSight(x, y) {
  const r = sightRadius(x, y, lightPhase(minutes.value));
  const prev = visits.value.find((v) => v.x === x && v.y === y);
  if (prev && prev.sight >= r) return;
  visits.value = [...visits.value.filter((v) => !(v.x === x && v.y === y)), { x, y, sight: Math.max(r, prev?.sight ?? 0) }];
}

function doStep(x, y, walkContext) {
  const before = {
    phase: phase.value,
    stages: Object.fromEntries(members.value.map((m) => [m.id, stageOf(m.reserve).key])),
    hostiles: new Set(hostiles.value.map((h) => h.id)),
    sightings: new Set(sightings.value.map((s) => s.id)),
    terrain: here.value.terrain,
  };
  const sec = stepSeconds(party.value.x, party.value.y, x, y, slowest.value);
  members.value = members.value.map((m) => {
    if (m.asleep) return m;
    const reserve = Math.max(0, m.reserve - sec * WALK_COST_PER_SECOND);
    return { ...m, reserve, asleep: reserve === 0 };
  });
  minutes.value += sec / 60;
  party.value = { x, y };
  recordSight(x, y);

  const flags = [];
  const cell = here.value;
  if (cell.terrain === "ford") addLog("ford", "涉過<b>界河主渡口</b>，卵石淺灘上的水只到膝蓋。");
  else if (cell.terrain === "woodland" && before.terrain !== "woodland") addLog("plain", "走進林地，樹冠把視野壓到身邊。");
  for (const h of hostiles.value) {
    if (before.hostiles.has(h.id)) continue;
    flags.push("hostile_in_sight");
    addLog("hostile", `<em>${compassBearing(h.x - x, h.y - y)}方</em>出現<b>${h.name}</b>的身影（${h.threat}）。`);
  }
  for (const s of sightings.value) {
    if (before.sightings.has(s.id)) continue;
    flags.push("landmark_sighted");
    addLog("landmark", `望見${s.bearing}方約 ${s.km} 公里處有<em>${s.label}</em>。`);
  }
  const stopStage = PACES.find((p) => p.key === pace.value)?.stopStage;
  for (const m of members.value) {
    const now = stageOf(m.reserve).key;
    if (now === before.stages[m.id]) continue;
    if (m.asleep) {
      flags.push("member_asleep");
      addLog("fatigue", `<b>${m.name}</b>撐不住了，倒地<em>沉睡</em>。`);
      continue;
    }
    addLog("fatigue", `<b>${m.name}</b>進入<em>${stageOf(m.reserve).label}</em>。`);
    if (walkContext && stopStage && STAGE_INDEX[now] >= STAGE_INDEX[stopStage]) flags.push("pace_threshold");
  }
  if (phase.value !== before.phase) {
    if (phase.value === "night") {
      addLog("night", "<em>夜幕降臨</em>，視野縮到身邊一小圈。");
      if (walkContext?.stopAtNight) flags.push("nightfall");
    } else if (phase.value === "dusk") {
      addLog("plain", "太陽西沉，影子拉得很長。");
    }
  }
  const lm = LANDMARKS.find((l) => l.x === x && l.y === y);
  if (lm) {
    flags.push("landmark_reached");
    const fresh = !lit.value.has(lm.district);
    if (fresh) lit.value = new Set([...lit.value, lm.district]);
    addLog("landmark", `抵達<em>${lm.name}</em>${fresh ? `，${lm.district}已探明` : ""}。`);
    cardData.value = { landmark: lm, litDistrict: fresh ? lm.district : null };
    card.value = "landmark";
  }
  return flags;
}

// ------------------------------------------------------------- walking

let walkTimer = null;
const STEP_MS = computed(() => (props.motion === "off" ? 60 : 420));

function stopWalk(reason) {
  clearTimeout(walkTimer);
  walkTimer = null;
  if (!walking.value) return;
  walking.value = false;
  walkKind.value = null;
  walkPlan.value = null;
  progress.value = 0;
  if (reason === "user") addLog("plain", "停下腳步。");
  if (reason === "arrival") target.value = null;
  nextTick(() => {
    if (!card.value) mapRef.value?.focus();
  });
}

const FLAG_REASON = {
  hostile_in_sight: "hostile",
  landmark_sighted: "sighted",
  pace_threshold: "pace",
  nightfall: "night",
  member_asleep: "asleep",
  landmark_reached: "arrival",
};

function walkContext() {
  return { pace: pace.value, stopAtNight: stopAtNight.value };
}

function departRoute() {
  if (!plan.value || walking.value) return;
  const queue = plan.value.steps.slice(0, plan.value.stopIndex + 1).map((s) => ({ x: s.x, y: s.y }));
  if (!queue.length) return;
  target.value = target.value ?? routeTo.value;
  walkPlan.value = plan.value;
  progress.value = 0;
  walking.value = true;
  walkKind.value = "route";
  aim.value = null;
  intentLog(`travel.plan → ${queue.length} 步；逐步送出 explore.move {walk: {pace: "${pace.value}", stop_at_night: ${stopAtNight.value}}}`);
  const next = () => {
    const cell = queue.shift();
    if (!cell) return stopWalk("arrival");
    const flags = doStep(cell.x, cell.y, walkContext());
    progress.value += 1;
    if (flags.length) {
      if (!queue.length && flags.every((f) => f === "landmark_reached")) target.value = null;
      return stopWalk(FLAG_REASON[flags[0]]);
    }
    if (!queue.length) {
      const reached = party.value.x === target.value?.x && party.value.y === target.value?.y;
      if (!reached && plan.value === null) addLog("camp", "今天的行程到此，該找地方紮營了。");
      return stopWalk(reached ? "arrival" : "pace");
    }
    walkTimer = setTimeout(next, STEP_MS.value);
  };
  walkTimer = setTimeout(next, props.motion === "off" ? 0 : 120);
}

function stepDir(key, context = null) {
  const d = DIRECTIONS.find((x) => x.key === key);
  if (!d) return ["blocked"];
  if (!canStep(party.value.x, party.value.y, d.dx, d.dy)) return ["blocked"];
  intentLog(`explore.move {direction: "${key}"${context ? `, walk: {pace: "${context.pace}"}` : ""}}`);
  target.value = null;
  return doStep(party.value.x + d.dx, party.value.y + d.dy, context);
}

function holdWalk(key) {
  if (!key || walking.value || card.value) return;
  walking.value = true;
  walkKind.value = key;
  const next = () => {
    if (!walking.value || walkKind.value !== key) return;
    const flags = stepDir(key, walkContext());
    if (flags.length) return stopWalk(flags[0] === "blocked" ? "blocked" : FLAG_REASON[flags[0]]);
    walkTimer = setTimeout(next, STEP_MS.value);
  };
  next();
}

// ---------------------------------------------------------------- map IO

function onAim(key) {
  if (walking.value) return;
  aim.value = key;
  if (key) target.value = null;
}

function onPick(cell) {
  if (walking.value || card.value) return;
  const dx = cell.x - party.value.x;
  const dy = cell.y - party.value.y;
  if (!dx && !dy) return;
  if (Math.max(Math.abs(dx), Math.abs(dy)) === 1) {
    const d = DIRECTIONS.find((x) => x.dx === dx && x.dy === dy);
    aim.value = null;
    stepDir(d.key);
    return;
  }
  if (!isRevealed(cell.x, cell.y)) return;
  if (target.value && target.value.x === cell.x && target.value.y === cell.y) {
    departRoute();
    return;
  }
  target.value = cell;
  intentLog(`travel.plan {destination: [${cell.x}, ${cell.y}], pace: "${pace.value}", stop_at_night: ${stopAtNight.value}}`);
}

function onStep(key) {
  if (walking.value || card.value) return;
  stepDir(key);
}

function onConfirm() {
  if (target.value) departRoute();
}

function onCancel() {
  if (walking.value) return stopWalk("user");
  aim.value = null;
  target.value = null;
}

// Releasing the arrows ends a held walk; a tapped aim stays for Enter.
function onRelease() {
  if (walking.value && walkKind.value !== "route") stopWalk("released");
}

function onZoom(dir) {
  zoomLevel.value = Math.max(18, Math.min(46, zoomLevel.value + dir * 4));
}

// Any key stops a route walk (spec: the player can always interrupt).
function onWindowKey(event) {
  if (walking.value && walkKind.value === "route") {
    event.preventDefault();
    event.stopPropagation();
    stopWalk("user");
  }
}

// ------------------------------------------------------------- camping

function nextSixAm() {
  const dayStart = Math.floor(minutes.value / 1440) * 1440;
  const six = dayStart + 360;
  return minutes.value < six ? six : six + 1440;
}

function sleepOutcome(wake) {
  const secs = (wake - minutes.value) * 60;
  return members.value.map((m) => ({
    id: m.id,
    name: m.name,
    portrait: m.portrait,
    from: m.reserve,
    to: Math.min(RESERVE_FULL, m.reserve + secs * SLEEP_RESTORE_PER_SECOND),
  }));
}

function openCamp() {
  if (walking.value) return;
  const dawn = nextSixAm();
  const fullSecs = Math.max(...members.value.map((m) => (RESERVE_FULL - m.reserve) / SLEEP_RESTORE_PER_SECOND));
  const full = minutes.value + Math.ceil(fullSecs / 60);
  const dawnOutcome = sleepOutcome(dawn);
  const low = Math.min(...dawnOutcome.map((m) => Math.round((m.to / RESERVE_FULL) * 100)));
  const opts = [
    { key: "dawn", label: "睡到天亮", wake: dawn, note: low >= 100 ? "天亮時全員精力全滿" : `天亮時最低精力 ${low}%`, members: dawnOutcome },
    { key: "full", label: "睡到精力全滿", wake: full, note: "最慢恢復的成員睡滿為止", members: sleepOutcome(full) },
  ];
  const night = phase.value === "night" || phase.value === "dusk";
  cardData.value = { options: night ? opts : opts.reverse() };
  card.value = "camp";
  aim.value = null;
  target.value = null;
}

function confirmCamp({ choice, dream }) {
  rememberDream.value = dream;
  const opt = cardData.value.options.find((o) => o.key === choice);
  intentLog(`explore.camp {until: "${choice}", dream: ${dream}}`);
  const low = Math.min(...opt.members.map((m) => Math.round((m.to / RESERVE_FULL) * 100)));
  const wake = formatClock(opt.wake);
  cardData.value = {
    option: opt,
    members: opt.members,
    result: `夜裡無事。${low >= 100 ? "全隊精力恢復至 100%" : `全隊精力至少恢復至 ${low}%`}，第 ${wake.day} 日 ${wake.text} 醒來。`,
  };
  card.value = "campfire";
}

function finishCamp() {
  const opt = cardData.value.option;
  members.value = members.value.map((m) => {
    const to = opt.members.find((x) => x.id === m.id).to;
    return { ...m, reserve: to, asleep: false };
  });
  minutes.value = opt.wake;
  recordSight(party.value.x, party.value.y);
  addLog("camp", `在此紮營過夜；${formatClock(opt.wake).text} 醒來，${cardData.value.result.replace(/^夜裡無事。/, "").replace(/，第.*$/, "")}。`);
  card.value = null;
  cardData.value = null;
  nextTick(() => mapRef.value?.focus());
}

function cancelCard() {
  card.value = null;
  cardData.value = null;
  nextTick(() => mapRef.value?.focus());
}

function look() {
  const t = here.value.terrain;
  const lines = {
    open: "環顧四周：低矮的石楠與野草在風裡起伏，遠處的丘陵像一層層摺起的布。",
    road: "環顧四周：官道的車轍被雨水沖得很深，路旁立著半截里程碑。",
    hills: "環顧四周：站在坡上，風比坡下更冷，眼前的河谷一覽無遺。",
    woodland: "環顧四周：杉木的樹幹又直又密，林間只有自己的腳步聲。",
    ford: "環顧四周：界河在腳邊嘩嘩作響，對岸的蘆葦後面有一條踩出來的小徑。",
  };
  addLog("plain", lines[t] ?? lines.open);
}

// -------------------------------------------------------------- setup

const PORTRAIT = { man: "/art/defaults/man.webp", woman: "/art/defaults/woman.webp", girl: "/art/defaults/girl.webp" };
const pctR = (p) => Math.round((p / 100) * RESERVE_FULL);

function corridorVisits() {
  const extra = [];
  const pts = [[21, 23], [22, 23], [23, 23], [24, 23], [25, 23], [26, 23], [27, 23], [27, 22], [28, 21], [28, 20], [29, 19], [29, 18], [30, 17], [31, 16], [32, 15], [32, 14], [33, 13], [33, 12], [33, 11], [33, 10]];
  for (const [x, y] of pts) extra.push({ x, y, sight: sightRadius(x, y, "day") });
  return extra;
}

function nearestWoodland() {
  let best = null;
  for (let y = 0; y < WINDOW; y += 1) {
    for (let x = 0; x < WINDOW; x += 1) {
      if (cellAt(x, y).terrain !== "woodland") continue;
      const d = Math.hypot(x - HOME.x, y - HOME.y);
      const ring = [-1, 0, 1].every((dy) => [-1, 0, 1].every((dx) => cellAt(x + dx, y + dy)?.terrain === "woodland"));
      if (ring && (!best || d < best.d)) best = { x, y, d };
    }
  }
  return best ?? { x: 12, y: 18 };
}

function reset() {
  stopWalk("reset");
  party.value = { ...HOME };
  minutes.value = at(7, 40);
  members.value = [
    { id: "allen", name: "艾倫", portrait: PORTRAIT.man, reserve: pctR(100), asleep: false },
    { id: "elaine", name: "伊蓮", portrait: PORTRAIT.woman, reserve: pctR(96), asleep: false },
    { id: "lia", name: "莉亞", portrait: PORTRAIT.girl, reserve: pctR(100), asleep: false },
  ];
  visits.value = initialVisits();
  lit.value = new Set();
  aim.value = null;
  target.value = null;
  card.value = null;
  cardData.value = null;
  log.value = [
    { day: 11, time: "17:50", tone: "camp", html: "出王都東門走了半天，在官道旁的石楠坡紮營。" },
    { day: 12, time: "06:00", tone: "plain", html: "天亮了。全隊醒來，精力恢復；露水還掛在草尖上。" },
  ];
  const s = props.scenario;
  if (s === "route") {
    visits.value = [...visits.value, ...corridorVisits()];
    target.value = { x: 34, y: 6 };
    log.value.push({ day: 12, time: "07:40", tone: "landmark", html: "上回走過的路還記得：沿官道過主渡口，北東方就是<em>古哨塔</em>。" });
  }
  if (s === "dusk") minutes.value = at(17, 40);
  if (s === "night") {
    minutes.value = at(21, 30);
    members.value = members.value.map((m, i) => ({ ...m, reserve: pctR([46, 39, 52][i]) }));
  }
  if (s === "woodland") {
    // Walked in from the trail: the open approach, then the woods.
    const w = nearestWoodland();
    const walked = [];
    const n = Math.max(Math.abs(w.x - HOME.x), Math.abs(w.y - HOME.y));
    for (let k = 1; k <= n; k += 1) {
      const x = Math.round(HOME.x + ((w.x - HOME.x) * k) / n);
      const y = Math.round(HOME.y + ((w.y - HOME.y) * k) / n);
      walked.push({ x, y, sight: sightRadius(x, y, "day") });
    }
    party.value = { x: w.x, y: w.y };
    visits.value = [...visits.value, ...walked];
    minutes.value = at(10, 20);
  }
  if (s === "camp" || s === "campfire") {
    minutes.value = at(18, 20);
    members.value = members.value.map((m, i) => ({ ...m, reserve: pctR([41, 37, 45][i]) }));
  }
  if (s === "landmark") {
    visits.value = [...visits.value, ...corridorVisits()];
    party.value = { x: 33, y: 10 };
    minutes.value = at(13, 40);
  }
  nextTick(() => {
    if (s === "camp") openCamp();
    if (s === "campfire") {
      openCamp();
      confirmCamp({ choice: cardData.value.options[0].key, dream: false });
    }
    if (s === "landmark") {
      for (const [x, y] of [[33, 9], [34, 8], [34, 7], [34, 6]]) doStep(x, y, null);
    }
    mapRef.value?.focus();
  });
}

function jumpTo(h, m) {
  minutes.value = Math.floor(minutes.value / 1440) * 1440 + h * 60 + m;
  recordSight(party.value.x, party.value.y);
}

onMounted(() => {
  reset();
  window.addEventListener("keydown", onWindowKey, true);
});
onBeforeUnmount(() => {
  clearTimeout(walkTimer);
  window.removeEventListener("keydown", onWindowKey, true);
});
</script>

<template>
  <div class="wt-proto" :data-card="card" data-testid="wilderness-travel-prototype">
    <section class="wt-proto__controls" aria-label="原型模擬控制（非遊戲內容）">
      <span class="wt-proto__tag">原型模擬</span>
      <button type="button" class="wt-proto__btn" @click="jumpTo(5, 30)">黎明</button>
      <button type="button" class="wt-proto__btn" @click="jumpTo(9, 0)">白晝</button>
      <button type="button" class="wt-proto__btn" @click="jumpTo(17, 40)">黃昏</button>
      <button type="button" class="wt-proto__btn" @click="jumpTo(21, 30)">夜晚</button>
      <button type="button" class="wt-proto__btn" @click="onZoom(-1)">縮小</button>
      <button type="button" class="wt-proto__btn" @click="onZoom(1)">放大</button>
      <button type="button" class="wt-proto__btn" @click="reset">重設</button>
      <p class="wt-proto__log" aria-live="polite" :title="intents[0]">{{ intents[0] ?? "送出的意圖會顯示在這裡" }}</p>
    </section>

    <div class="wt-proto__stage">
      <HudFrame mode="exploration" :card-open="!!card">
        <template #backdrop>
          <TravelMap
            ref="mapRef"
            :party="party"
            :mask="mask"
            :phase="phase"
            :live-radius="liveRadius"
            :hostiles="hostiles"
            :sightings="sightings"
            :plan="walking ? remainingPlan : plan"
            :target="target"
            :aim="aim"
            :walking="walking"
            :lit-districts="lit"
            :zoom="zoomLevel"
            :focus="routeFocus"
            :motion="motion"
            @aim="onAim"
            @hover="hover = $event"
            @pick="onPick"
            @step="onStep"
            @confirm="onConfirm"
            @cancel="onCancel"
            @hold="holdWalk"
            @release="onRelease"
            @zoom="onZoom"
          />
        </template>
        <template #vitals>
          <PartyMedallions :members="members" controlled="allen" />
        </template>
        <template #map>
          <PlaceCard :location-label="placeLabel" :time-label="`${clock.label}・${PHASE_LABEL[phase]}`" :motion-level="motion" />
        </template>
        <template #choices>
          <LandmarkCard
            v-if="card === 'landmark'"
            :landmark="cardData.landmark"
            :lit-district="cardData.litDistrict"
            @done="cancelCard"
          />
          <CampCard
            v-else-if="card === 'camp'"
            :place="placeLabel.split('・')[0]"
            :minutes="minutes"
            :phase="phase"
            :options="cardData.options"
            :dream="rememberDream"
            @confirm="confirmCamp"
            @cancel="cancelCard"
          />
          <CampfireCard
            v-else-if="card === 'campfire'"
            :members="cardData.members"
            :result="cardData.result"
            :motion="motion"
            @done="finishCamp"
          />
        </template>
        <template #band-message>
          <TravelLog :entries="log" />
        </template>
        <template #band-command>
          <LegPanel
            :intent="intent"
            :plan="walking ? walkPlan : plan"
            :progress="walking ? progress : 0"
            :capacity="capacity"
            :pace="pace"
            :stop-at-night="stopAtNight"
            :walking="walking"
            :locked="!!card"
            @pace="pace = $event"
            @night="stopAtNight = $event"
            @depart="departRoute"
            @stop="stopWalk('user')"
            @camp="openCamp"
            @look="look"
          />
        </template>
      </HudFrame>
    </div>
  </div>
</template>

<style>
.wt-proto {
  position: relative;
  width: 100%;
  height: calc(100vh - var(--header-h));
}
.wt-proto__stage {
  position: absolute;
  inset: 0;
}
/* Travel mode replaces the AVG stage's standing portraits; the HudFrame's
   heavy vignette is lightened so the map edges stay legible. */
.wt-proto .stage-vignette {
  box-shadow: inset 0 0 160px 20px rgba(0, 0, 0, 0.55);
}
.wt-proto .elosern-stage [data-anchor="vitals"] {
  width: auto;
}
/* Travel cards may use the whole open stage height above the band. */
.wt-proto[data-card] .elosern-stage [data-anchor="choices"] {
  bottom: calc(var(--band-h) + 16px * var(--ui-scale));
}
/* The campfire beat is wider than a choice list. */
.wt-proto[data-card="campfire"] .elosern-stage [data-anchor="choices"],
.wt-proto[data-card="landmark"] .elosern-stage [data-anchor="choices"] {
  left: calc(50% - min(380px * var(--ui-scale), 30%));
  width: min(760px * var(--ui-scale), 60%);
}
.wt-proto__controls {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: calc(var(--z-surface-modal) + 1);
  box-sizing: border-box;
  height: var(--header-h);
  display: flex;
  align-items: center;
  gap: calc(8px * var(--ui-scale));
  padding: 0 calc(16px * var(--ui-scale));
  background: repeating-linear-gradient(135deg, rgba(185, 154, 96, 0.08) 0 calc(8px * var(--ui-scale)), transparent 0 calc(16px * var(--ui-scale))), var(--ink-950);
  border-bottom: 1px dashed rgba(185, 154, 96, 0.55);
  font: var(--text-sm)/1.3 var(--f-sans);
  color: var(--paper-300);
}
.wt-proto__tag {
  flex: none;
  padding: calc(2px * var(--ui-scale)) calc(8px * var(--ui-scale));
  border: 1px solid var(--gold-600);
  border-radius: 3px;
  color: var(--gold-400);
  font-size: var(--text-xs);
}
.wt-proto__btn {
  flex: none;
  border: 1px solid rgba(143, 113, 60, 0.6);
  background: rgba(43, 42, 39, 0.5);
  color: var(--paper-200);
  font: var(--text-xs)/1 var(--f-sans);
  padding: calc(6px * var(--ui-scale)) calc(10px * var(--ui-scale));
  border-radius: 4px;
  cursor: pointer;
}
.wt-proto__log {
  margin: 0 0 0 auto;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font: var(--text-xs)/1.2 var(--f-mono);
  color: var(--paper-500);
}
</style>
