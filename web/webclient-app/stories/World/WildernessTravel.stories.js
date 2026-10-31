import { h, onBeforeUnmount, onMounted } from "vue";
import { createPinia, disposePinia } from "pinia";
import HudFrame from "../../components/HudFrame.vue";
import PlaceCard from "../../components/PlaceCard.vue";
import StatusPanel from "../../components/StatusPanel.vue";
import TravelMap from "../../components/travel/TravelMap.vue";
import PartyMedallions from "../../components/travel/PartyMedallions.vue";
import LegPanel from "../../components/travel/LegPanel.vue";
import { legView } from "../../components/travel/leg-model.js";
import TravelLog from "../../components/travel/TravelLog.vue";
import { travelJourney, travelLogPanel } from "../fixtures/travel_log.js";
import { useElosernStore } from "../../stores/elosern.js";
import * as fx from "../../tests/store/protocol_fixtures.js";
import { walkArea, walkCapacity, walkPanels } from "../fixtures/travel_walk.js";
import { medallionMembers, travelPlace } from "../../components/travel/travel-model.js";
import { companionFigures } from "../../components/companion-lineup.js";
import { portraitFor } from "../../components/party-helpers.js";
import { artworkDescriptor, artworkEntry, artworkResource, fixtureDigest } from "../fixtures/art_panels.js";
import { wildernessArea } from "../fixtures/area_map.js";
import { DUSK_GRID, MORNING_AREA, MORNING_GRID, NIGHT_GRID, WOODLAND_GRID } from "../fixtures/travel_grid.js";
import { decodeTravelGrid } from "../../lib/travel-grid.js";
import { STATUS_PANEL_SAMPLE } from "../fixtures/status_panels.js";

// The wilderness travel stage (OpenSpec change wilderness-travel-interface;
// design docs/superpowers/specs/2026-10-30-wilderness-travel-interface-design.md
// §3/§8; approved prototype Design/WildernessTravel): the real HudFrame with
// its travel hook, TravelMap painting a decoded travel grid (exact schema-3
// area_map bodies of stories/fixtures/travel_grid.js, validated by the real
// wire validator and decoded by the real lib/travel-grid.js decoder; the
// drawer's own fixture window for the refresh ones), the vitals dock above
// the party medallions, and the place card alone in the map column, its
// lines projected by the real `travelPlace`. Every body is a synthetic protocol fixture; the medallions join
// each member to its own status fatigue row. The band's message region is
// the travel log and its command region the leg panel (wilderness-travel-
// leg-ui), projected by the real `legView` from a status v6 travel capacity
// fixture, an aimed committed row and a supplied light phase. The route
// preview stories (wilderness-travel-planning-ui) drive the real store: a
// destination locked (or hovered) through its own actions, the window adopted
// through `setTravelMap`, and the `travel.plan` answer delivered through the
// real result validator.

// The committed portrait catalog: the bundled default figures as each
// member's own descriptor (no URL is built by the components).
function portraitEntry(key, file, face) {
  return artworkEntry(
    { context: { name: key, role: "同伴" } },
    artworkDescriptor({
      subject_id: `story_${key}`,
      generation_subject: `story_${key}`,
      attempts: [
        {
          type: "image",
          source_id: `portrait.default:${key}`,
          rank: 30,
          resource: artworkResource({
            resource_id: `defaults/${file}.webp`,
            version: fixtureDigest(`story-${key}`),
            url: `/art/defaults/${file}.webp`,
            origin: "bundled_official",
            geometry: { image_size: null, face_rect: face, stage: null, aspect_ratio: "3:4" },
          }),
        },
      ],
      terminal: null,
    }),
  );
}

const ART = {
  schema_version: 4,
  available: true,
  kind: "scene",
  portrait_catalog: {
    "301": portraitEntry("allen", "man", { x: 0.35, y: 0.03, w: 0.29, h: 0.16 }),
    "302": portraitEntry("elaine", "woman", { x: 0.36, y: 0.04, w: 0.28, h: 0.16 }),
    "303": portraitEntry("lia", "girl", { x: 0.36, y: 0.06, w: 0.28, h: 0.16 }),
    "304": portraitEntry("bran", "elder", { x: 0.36, y: 0.04, w: 0.28, h: 0.16 }),
  },
};

const row = (identity, name, reserve, stage = "normal", label = "精神充沛", asleep = false) => ({
  identity, name, reserve_percent: reserve, stage, label,
  severity: stage === "normal" || stage === "sleeping" ? "informational" : "harmful",
  restriction: asleep ? "沉睡中，無法行動" : null, asleep,
});

const PARTY = [
  { identity: 7, display_name: "伊蓮", portrait_ref: "302", role: "companion" },
  { identity: 8, display_name: "莉亞", portrait_ref: "303", role: "companion" },
  { identity: 9, display_name: "布蘭", portrait_ref: "304", role: "companion" },
];

const FATIGUE = {
  morning: [row("42", "艾倫", 96), row("7", "伊蓮", 88), row("8", "莉亞", 100), row("9", "布蘭", 91)],
  weary: [
    row("42", "艾倫", 61, "light", "輕度疲勞"),
    row("7", "伊蓮", 37, "moderate", "中度疲勞"),
    row("8", "莉亞", 54, "sleeping", "沉睡", true),
    row("9", "布蘭", 14, "severe", "精疲力竭"),
  ],
};

function members(fatigue) {
  const figures = companionFigures({
    player: { identity: "42", artwork: portraitFor(ART, "301"), panel: ART, hasReference: true, displayName: "艾倫" },
    companions: PARTY,
    actorIdentity: "42",
    possessing: false,
    artPanel: ART,
    portraitFor,
  });
  return medallionMembers(figures, { ...STATUS_PANEL_SAMPLE, fatigue }, "42");
}

// The band's command pane as AppClient frames it (the dock pane's padding).
const commandPane = (child) =>
  h("div", { style: "box-sizing:border-box;height:100%;display:flex;padding:calc(12px * var(--ui-scale));" }, child);

// The static stories' committed noon and the aimed east row.
const NOON = { year: 1, season_index: 0, season_label: "春", day_in_season: 3, hour: 12, minute: 0, second: 0 };
const EAST = { direction: "east", word: "東方", exists: true, enabled: true, reason: null, exitRef: "e_wild_e" };

function staticLeg(args) {
  return legView({
    aim: args.legAim === undefined ? (args.aim === "east" ? EAST : null) : args.legAim,
    progress: args.progress ?? 0,
    walking: args.legWalking ?? null,
    capacity: args.capacity,
    preferences: args.preferences,
    phase: args.phase ?? null,
    error: args.notice ?? null,
    serverTime: args.serverTime ?? NOON,
    mapStatus: args.status,
  });
}

function withMotion(level, render) {
  return {
    setup() {
      let previous = null;
      onMounted(() => {
        previous = document.documentElement.getAttribute("data-motion");
        document.documentElement.setAttribute("data-motion", level);
      });
      onBeforeUnmount(() => {
        if (previous === null) document.documentElement.removeAttribute("data-motion");
        else document.documentElement.setAttribute("data-motion", previous);
      });
      return render;
    },
  };
}

const renderStage = (args) =>
  withMotion(args.motionLevel, () =>
    h(
      "div",
      { style: "position:relative;height:calc(100vh - var(--header-h));" },
      h(HudFrame, { mode: "exploration", travel: true }, {
        backdrop: () =>
          h(TravelMap, { grid: args.grid, status: args.status, aim: args.aim, motionLevel: args.motionLevel }),
        vitals: () => [
          h(StatusPanel, {
            status: { ...STATUS_PANEL_SAMPLE, fatigue: args.fatigue },
            visible: args.vitalsVisible,
            motionLevel: args.motionLevel,
            showFatigue: false,
          }),
          h(PartyMedallions, { members: members(args.fatigue) }),
        ],
        map: () => h(PlaceCard, { locationLabel: args.place, timeLabel: args.time, motionLevel: args.motionLevel }),
        "band-message": () => h(TravelLog, { entries: args.log ?? [] }),
        "band-command": () => commandPane(h(LegPanel, { view: staticLeg(args), motionLevel: args.motionLevel })),
      }),
    ),
  );

export default {
  title: "World/WildernessTravel",
  component: TravelMap,
  render: renderStage,
  argTypes: {
    status: { control: "select", options: ["ready", "refreshing", "unavailable", "invalid", "retired"] },
    motionLevel: { control: "inline-radio", options: ["full", "reduced", "off"] },
  },
};

// The drawer's own schema-3 fixture window through the real decoder.
const ADAPTED = decodeTravelGrid(wildernessArea());

// The place card's lines for one grid at one server time line.
const placeOf = (grid, time) => {
  const labels = travelPlace(grid, time);
  return { place: labels.location, time: labels.time };
};

// The travel band log (wilderness-travel-log-ui): one leg's committed
// notices under their day headings — region, woodland, ford, hostiles, a
// look with its full prose behind 全文, fatigue, a landmark arrival, dusk,
// night and the next morning's camp result.
const JOURNEY = travelJourney();

const MORNING = {
  capacity: walkCapacity({ quotes: { east: 1260 } }),
  preferences: { pace: "standard", stopAtNight: true },
  grid: MORNING_GRID,
  aim: "east",
  status: "ready",
  fatigue: FATIGUE.morning,
  vitalsVisible: false,
  ...placeOf(MORNING_GRID, "春 3 日 ‧ 07:20"),
  motionLevel: "full",
  log: JOURNEY.slice(0, 4),
};

// Morning on the road: the painted window at full strength with relief,
// river, road and ford, a wolf pack in live sight, three distant sightings
// and the eastern neighbour aimed; the whole party fresh.
export const Morning = { args: MORNING };

// The day wears on: stages lower each face's colour and carry their label,
// the sleeper wears the crescent, and the dock shows the damaged gauges.
export const WearyParty = {
  name: "Weary Party",
  args: {
    ...MORNING,
    aim: null,
    fatigue: FATIGUE.weary,
    vitalsVisible: true,
    time: "春 3 日 ‧ 14:20・白晝",
    // The worst member already meets the standard threshold: the intent
    // advises camping and the gauge is short.
    capacity: walkCapacity({ normal: 0, light: 0, moderate: 2, severe: 3, cautious: true, standard: true }),
  },
};

// A committed step: the last map stays, dimmed, while the next one settles.
export const Refreshing = { args: { ...MORNING, grid: ADAPTED, aim: null, status: "refreshing" } };

// The first entry: no map adopted yet, only the hatched fog.
export const FirstLoad = { name: "First Load", args: { ...MORNING, grid: null, aim: null, status: "refreshing" } };

// A failed read: the last map dimmed, one status line and the explicit retry.
export const Unavailable = { args: { ...MORNING, grid: ADAPTED, aim: null, status: "unavailable" } };

// Dusk: the amber wash and a narrower live sight.
export const Dusk = {
  args: { ...MORNING, grid: DUSK_GRID, aim: null, fatigue: FATIGUE.weary, vitalsVisible: true, ...placeOf(DUSK_GRID, "春 3 日 ‧ 17:40") },
};

// Night: the deep blue wash, the moonlit disc and only the lights that carry.
export const Night = {
  args: {
    ...MORNING, grid: NIGHT_GRID, aim: null, fatigue: FATIGUE.weary, vitalsVisible: true, ...placeOf(NIGHT_GRID, "春 3 日 ‧ 22:10"),
    phase: "night", capacity: walkCapacity({ normal: 0, light: 7, moderate: 6, severe: 3 }),
  },
};

// The capacity read failed (or the party has no physiology): the gauge says
// so and 出發 stays disabled; 環顧 and 紮營 still work.
export const CapacityUnavailable = {
  name: "Capacity Unavailable",
  args: { ...MORNING, aim: null, capacity: null },
};

// Woodland: under the canopy, one cell of sight and no horizon.
export const Woodland = {
  args: { ...MORNING, grid: WOODLAND_GRID, aim: "north", ...placeOf(WOODLAND_GRID, "春 3 日 ‧ 11:05") },
};

// Motion off: every state lands at once, with no glide, crossfade or breath.
export const MotionOff = { name: "Motion Off", args: { ...MORNING, motionLevel: "off" } };

// ── walking (wilderness-travel-walking-ui) ──────────────────────────────

// The aimed and held states come from the real composed store, never from a
// second movement model: each story establishes a synthetic wilderness cell
// through the store's own `receive`, adopts that cell's window through
// `setTravelMap` exactly as the refresh owner does, then calls the store's
// walking actions. A recording sender keeps every step on the page. The
// painted map is the full-fact morning grid; the band's command region is
// the leg panel over `view.travel`, exactly as AppClient projects it.
function walkingStage(args) {
  return {
    setup() {
      const pinia = createPinia();
      const store = useElosernStore(pinia);
      const sender = fx.createFakeSender();
      store.setSender(sender);
      store.beginTransport(1);
      store.setConnected(true);
      const { x, y } = MORNING_GRID.party;
      const panels = walkPanels(x, y, { capacity: args.capacity, ...(args.walk?.panels ?? {}) });
      store.receive(store.view.generation, "ui_snapshot", [fx.snapshot({ panels })], {});
      // The travel band log through the store's own adoption (and the real
      // travel_log validator), exactly as a committed batch arrives.
      if (args.log?.length) {
        const v = store.view;
        store.receive(v.generation, "ui_update", [fx.update({ revision: v.revision + 1, panels: { travel_log: travelLogPanel(args.log), status: panels.status } })], {});
      }
      store.setTravelMap({ status: "ready", area: walkArea(x, y) });
      onMounted(() => {
        if (args.walk?.aim) store.aimTravel(args.walk.aim);
        // The store's own 400 ms hold timer sends the first step.
        if (args.walk?.hold) store.holdTravel(args.walk.hold);
        if (args.walk?.step) {
          const sent = store.stepTravel(args.walk.step);
          if (sent.sent && args.walk.refuse) {
            const v = store.view;
            store.receive(v.generation, "ui_action_result", [fx.actionResult({
              request_id: sent.requestId, presentation_revision: v.revision, outcome: "rejected",
              code: "blocked", message: args.walk.refuse,
            })], {});
          }
        }
      });
      onBeforeUnmount(() => {
        store.stopTravel("story");
        disposePinia(pinia);
      });
      const render = () => {
        const travel = store.view.travel;
        return h(
          "div",
          { style: "position:relative;height:calc(100vh - var(--header-h));" },
          h(HudFrame, { mode: "exploration", travel: true }, {
            backdrop: () =>
              h(TravelMap, { grid: args.grid, status: args.status, aim: travel.aim, aimBlocked: !!travel.aimTarget && !travel.aimTarget.enabled, aimReason: travel.aimTarget?.reason ?? null, walking: travel.walking, motionLevel: args.motionLevel }),
            vitals: () => [
              h(StatusPanel, {
                status: { ...STATUS_PANEL_SAMPLE, fatigue: args.fatigue },
                visible: args.vitalsVisible,
                motionLevel: args.motionLevel,
                showFatigue: false,
              }),
              h(PartyMedallions, { members: members(args.fatigue) }),
            ],
            map: () => h(PlaceCard, { locationLabel: args.place, timeLabel: args.time, motionLevel: args.motionLevel }),
            "band-message": () => h(TravelLog, { entries: travel.entries }),
            "band-command": () =>
              commandPane(h(LegPanel, {
                view: legView({
                  aim: travel.aimTarget,
                  walking: travel.walking,
                  holding: travel.holding,
                  progress: travel.walking?.progress ?? 0,
                  capacity: travel.capacity,
                  preferences: travel.preferences,
                  phase: args.phase ?? null,
                  error: travel.notice,
                  serverTime: store.view.serverTime,
                  mapStatus: travel.mapStatus,
                  busy: store.view.dispatch.inFlight !== null,
                }),
                motionLevel: args.motionLevel,
                onPace: (value) => store.setTravelPace(value),
                onNight: (value) => store.setTravelStopAtNight(value),
                onStop: () => store.stopTravel("stop"),
                onLook: () => store.activateRoomLook(),
              })),
          }),
        );
      };
      return withMotion(args.motionLevel, render).setup();
    },
  };
}

// Aimed: the eastern neighbour aimed by the store; the intent line names it
// and offers the step.
export const Aimed = { args: { ...MORNING, aim: null, walk: { aim: "east" } }, render: walkingStage };

// A blocked aim: the northern row is committed disabled with its reason, which
// the intent line states instead of offering a step.
export const AimBlocked = {
  name: "Aim Blocked",
  args: { ...MORNING, aim: null, walk: { aim: "north", panels: { disabled: { north: "斷崖擋住了去路。" } } } },
  render: walkingStage,
};

// Held walk: the store's 400 ms hold fired and its first step waits for the
// commit; neighbours and hover are hidden and 停步 is live.
export const HeldWalk = { name: "Held Walk", args: { ...MORNING, aim: null, walk: { hold: "east" } }, render: walkingStage };

// A refused step: the server's message stands in the intent line.
export const StepRefused = {
  name: "Step Refused",
  args: { ...MORNING, aim: null, walk: { step: "east", refuse: "前方的河水太深，無法涉過。" } },
  render: walkingStage,
};

// The travel band log across one whole leg: every notice kind the server
// emits, newest at the bottom, the full log one control away.
export const TravelLogLeg = {
  name: "Travel Log",
  args: { ...MORNING, aim: null, grid: DUSK_GRID, log: JOURNEY, time: "春 4 日 ‧ 06:00・黎明" },
};

// An empty band on first entry: the log's one quiet line.
export const TravelLogEmpty = { name: "Travel Log Empty", args: { ...MORNING, log: [] } };

// ── route preview (wilderness-travel-planning-ui) ──────────────────────

// The morning party's road east to the lit stone marker: three fresh steps,
// two light, two moderate (the standard pace camps on the first) and one
// severe; nightfall would fall on the step after the camp.
const ORIGIN = { x: 100, y: 200 };
const MARKER = { x: 108, y: 207 };
const ROAD = [[101, 201], [102, 201], [103, 202], [104, 203], [105, 204], [106, 205], [107, 206], [108, 207]];
const routeSteps = (stages, seconds) => ROAD.slice(0, stages.length).map(([x, y], i) => ({ cell: { x, y }, seconds: seconds[i], fatigue_stage: stages[i] }));
const ROUTE_STEPS = routeSteps(
  ["normal", "normal", "normal", "light", "light", "moderate", "moderate", "severe"],
  [1260, 1200, 1320, 1400, 1460, 1580, 1640, 1720],
);
const ROUTE_PLAN = {
  origin: ORIGIN,
  destination: MARKER,
  steps: ROUTE_STEPS,
  total_seconds: ROUTE_STEPS.slice(0, 6).reduce((sum, step) => sum + step.seconds, 0),
  nightfall_index: 6,
  stop_index: 5,
  stop_reason: "pace_threshold",
};
// A forced march that ends in an admitted exact-zero arrival.
const SLEEP_STEPS = routeSteps(["light", "moderate", "severe", "severe", "forced_sleep"], [1400, 1580, 1720, 1760, 1810]);
const SLEEP_PLAN = {
  origin: ORIGIN,
  destination: { x: 105, y: 204 },
  steps: SLEEP_STEPS,
  total_seconds: SLEEP_STEPS.reduce((sum, step) => sum + step.seconds, 0),
  nightfall_index: null,
  stop_index: 4,
  stop_reason: "member_asleep",
};

function planningStage(args) {
  return {
    setup() {
      const pinia = createPinia();
      const store = useElosernStore(pinia);
      const sender = fx.createFakeSender();
      store.setSender(sender);
      store.beginTransport(1);
      store.setConnected(true);
      const panels = walkPanels(ORIGIN.x, ORIGIN.y, { capacity: args.capacity });
      store.receive(store.view.generation, "ui_snapshot", [fx.snapshot({ panels })], {});
      store.setTravelMap({ status: "ready", area: MORNING_AREA });
      onMounted(() => {
        const { lock, hover, answer } = args.route;
        if (lock) store.lockTravelDestination(lock);
        if (hover) store.hoverTravelCell(hover);
        const request = () => sender.sent.actions.filter((a) => a.action_id === "travel.plan").at(-1);
        const reply = () => {
          const env = request();
          if (!env || !answer) return;
          const v = store.view;
          const body = answer.refuse
            ? { outcome: "rejected", code: answer.refuse, message: "目前無法找到通往該處的路線。" }
            : { outcome: "success", code: "travel.plan", message: "已規劃行程。", data: answer.plan };
          store.receive(v.generation, "ui_action_result", [fx.actionResult({ request_id: env.request_id, presentation_revision: v.revision, ...body })], {});
        };
        // A hovered cell is asked for after its debounce.
        if (hover) setTimeout(reply, 200);
        else reply();
      });
      onBeforeUnmount(() => {
        store.clearTravelTarget();
        disposePinia(pinia);
      });
      const render = () => {
        const travel = store.view.travel;
        const plan = travel.plan ? { ...travel.plan, label: travel.planTarget?.label ?? null } : null;
        return h(
          "div",
          { style: "position:relative;height:calc(100vh - var(--header-h));" },
          h(HudFrame, { mode: "exploration", travel: true }, {
            backdrop: () =>
              h(TravelMap, {
                grid: travel.map,
                status: travel.mapStatus,
                aim: travel.aim,
                walking: travel.walking,
                plan: travel.plan,
                locked: !!travel.lockedDestination,
                target: travel.planTarget,
                motionLevel: args.motionLevel,
              }),
            vitals: () => [
              h(StatusPanel, { status: { ...STATUS_PANEL_SAMPLE, fatigue: args.fatigue }, visible: args.vitalsVisible, motionLevel: args.motionLevel, showFatigue: false }),
              h(PartyMedallions, { members: members(args.fatigue) }),
            ],
            map: () => h(PlaceCard, { locationLabel: args.place, timeLabel: args.time, motionLevel: args.motionLevel }),
            "band-message": () => h(TravelLog, { entries: travel.entries }),
            "band-command": () =>
              commandPane(h(LegPanel, {
                view: legView({
                  aim: travel.aimTarget,
                  plan,
                  locked: !!travel.lockedDestination && !!travel.planTarget?.locked,
                  pending: travel.planPending,
                  planError: travel.planError,
                  target: travel.planTarget,
                  routeReady: false,
                  capacity: travel.capacity,
                  preferences: travel.preferences,
                  phase: args.phase ?? null,
                  serverTime: { ...NOON, hour: 9, minute: 40 },
                  mapStatus: travel.mapStatus,
                  busy: store.view.dispatch.inFlight !== null,
                }),
                motionLevel: args.motionLevel,
              })),
          }),
        );
      };
      return withMotion(args.motionLevel, render).setup();
    },
  };
}

const ROUTE_ARGS = { ...MORNING, aim: null, time: "春 3 日 ‧ 09:40・白晝" };

// Route Preview: the stone marker locked; the server's plan draws one stage
// mark per step, the camp at the pace stop, the moon on the nightfall step
// beyond it and the faint planned steps past the camp, and the camera frames
// the whole leg. 出發 waits for the route walk.
export const RoutePreview = {
  name: "Route Preview",
  args: { ...ROUTE_ARGS, route: { lock: MARKER, answer: { plan: ROUTE_PLAN } } },
  render: planningStage,
};

// Hovering the marker: the same plan as an unlocked preview (dashed frame);
// the camera keeps following the party.
export const RouteHover = {
  name: "Route Hover",
  args: { ...ROUTE_ARGS, route: { hover: MARKER, answer: { plan: ROUTE_PLAN } } },
  render: planningStage,
};

// A locked destination whose answer has not arrived: the intent line waits.
export const RoutePending = {
  name: "Route Pending",
  args: { ...ROUTE_ARGS, route: { lock: MARKER, answer: null } },
  render: planningStage,
};

// The planner refuses: its stable reason stands in the intent line and no
// route is drawn.
export const RouteRefused = {
  name: "Route Refused",
  args: { ...ROUTE_ARGS, route: { lock: MARKER, answer: { refuse: "plan_unreachable" } } },
  render: planningStage,
};

// A forced march to collapse: the terminal forced_sleep step keeps its stage
// and is drawn as the severe ring with the sleep crescent, on the map and in
// the gauge.
export const RouteTerminalSleep = {
  name: "Route Terminal Sleep",
  args: { ...ROUTE_ARGS, fatigue: FATIGUE.weary, vitalsVisible: true, route: { lock: { x: 105, y: 204 }, answer: { plan: SLEEP_PLAN } } },
  render: planningStage,
};
