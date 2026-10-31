import { h, onBeforeUnmount, onMounted } from "vue";
import HudFrame from "../../components/HudFrame.vue";
import PlaceCard from "../../components/PlaceCard.vue";
import StatusPanel from "../../components/StatusPanel.vue";
import TravelMap from "../../components/travel/TravelMap.vue";
import PartyMedallions from "../../components/travel/PartyMedallions.vue";
import { medallionMembers } from "../../components/travel/travel-model.js";
import { companionFigures } from "../../components/companion-lineup.js";
import { portraitFor } from "../../components/party-helpers.js";
import { artworkDescriptor, artworkEntry, artworkResource, fixtureDigest } from "../fixtures/art_panels.js";
import { wildernessArea } from "../fixtures/area_map.js";
import { DUSK_GRID, MORNING_GRID, NIGHT_GRID, WOODLAND_GRID } from "../fixtures/travel_grid.js";
import { decodeTravelGrid } from "../../lib/travel-grid.js";
import { STATUS_PANEL_SAMPLE } from "../fixtures/status_panels.js";

// The wilderness travel stage (OpenSpec change wilderness-travel-interface;
// design docs/superpowers/specs/2026-10-30-wilderness-travel-interface-design.md
// §3/§8; approved prototype Design/WildernessTravel): the real HudFrame with
// its travel hook, TravelMap painting a decoded travel grid (the full-fact
// synthetic grids of stories/fixtures/travel_grid.js for the painted states,
// the real adapter over a schema-valid area_map window for the refresh ones),
// the vitals dock above the party medallions, and the place card alone in the
// map column. Every body is a synthetic protocol fixture; the medallions join
// each member to its own status v5 fatigue row. The band keeps the ordinary
// message and command regions (later travel slices replace them), shown here
// as quiet samples.

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

const quiet = (label) =>
  h(
    "div",
    {
      style:
        "box-sizing:border-box;height:100%;display:grid;place-items:center;" +
        "color:#8f8a7e;font:var(--text-xs) var(--f-sans);letter-spacing:.08em;",
    },
    label,
  );

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
        "band-message": () => quiet("訊息視窗（旅行紀錄由後續變更取代）"),
        "band-command": () => quiet("移動控制（行程面板由後續變更取代）"),
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

// The real adapter's output over a schema-2 window: terrain and reveal only,
// so it paints flat, with no relief, flags or light.
const ADAPTED = decodeTravelGrid(wildernessArea());

const MORNING = {
  grid: MORNING_GRID,
  aim: "east",
  status: "ready",
  fatigue: FATIGUE.morning,
  vitalsVisible: false,
  place: "灰鬃荒原東麓・曠野",
  time: "春 3 日 ‧ 07:20・白晝",
  motionLevel: "full",
};

// Morning on the road: the painted window at full strength with relief,
// river, road and ford, a wolf pack in live sight, three distant sightings
// and the eastern neighbour aimed; the whole party fresh.
export const Morning = { args: MORNING };

// The day wears on: stages lower each face's colour and carry their label,
// the sleeper wears the crescent, and the dock shows the damaged gauges.
export const WearyParty = {
  name: "Weary Party",
  args: { ...MORNING, fatigue: FATIGUE.weary, vitalsVisible: true, time: "春 3 日 ‧ 14:20・白晝" },
};

// A committed step: the last map stays, dimmed, while the next one settles.
export const Refreshing = { args: { ...MORNING, grid: ADAPTED, aim: null, status: "refreshing" } };

// The first entry: no map adopted yet, only the hatched fog.
export const FirstLoad = { name: "First Load", args: { ...MORNING, grid: null, aim: null, status: "refreshing" } };

// A failed read: the last map dimmed, one status line and the explicit retry.
export const Unavailable = { args: { ...MORNING, grid: ADAPTED, aim: null, status: "unavailable" } };

// Dusk: the amber wash and a narrower live sight.
export const Dusk = {
  args: { ...MORNING, grid: DUSK_GRID, aim: null, fatigue: FATIGUE.weary, vitalsVisible: true, time: "春 3 日 ‧ 17:40・黃昏" },
};

// Night: the deep blue wash, the moonlit disc and only the lights that carry.
export const Night = {
  args: { ...MORNING, grid: NIGHT_GRID, aim: null, fatigue: FATIGUE.weary, vitalsVisible: true, time: "春 3 日 ‧ 22:10・夜晚" },
};

// Woodland: under the canopy, one cell of sight and no horizon.
export const Woodland = {
  args: { ...MORNING, grid: WOODLAND_GRID, aim: "north", place: "合成東麓・林地", time: "春 3 日 ‧ 11:05・白晝" },
};

// Motion off: every state lands at once, with no glide, crossfade or breath.
export const MotionOff = { name: "Motion Off", args: { ...MORNING, motionLevel: "off" } };
