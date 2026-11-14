<script setup>
// Prototype of the landmark rite flow. Reference only: mock data, nothing
// dispatches; the intent the real client would send shows in the strip.
//
// arrival  the new arrival card over the map (or the city room)
// menu     the AVG stage: the archetype art full-bleed, the party standing
//          on the stage, the new rite panel in the centre
// playing  the panel leaves; the shared authored-scene player runs the
//          delivery in the message window
// map      stepped back; the place column keeps a 儀式 entry to return
import { computed, h, ref } from "vue";
import HudFrame from "../../../web/webclient-app/components/HudFrame.vue";
import PlaceCard from "../../../web/webclient-app/components/PlaceCard.vue";
import CompanionLineup from "../../../web/webclient-app/components/CompanionLineup.vue";
import MessageWindow from "../../../web/webclient-app/components/MessageWindow.vue";
import TravelMap from "../../../web/webclient-app/components/travel/TravelMap.vue";
import TravelLog from "../../../web/webclient-app/components/travel/TravelLog.vue";
import LegPanel from "../../../web/webclient-app/components/travel/LegPanel.vue";
import { legView } from "../../../web/webclient-app/components/travel/leg-model.js";
import { companionFigures } from "../../../web/webclient-app/components/companion-lineup.js";
import { portraitFor } from "../../../web/webclient-app/components/party-helpers.js";
import { useAuthoredScene } from "../../../web/webclient-app/composables/use-authored-scene.js";
import { artworkDescriptor, artworkEntry, artworkResource, fixtureDigest } from "../../../web/webclient-app/stories/fixtures/art_panels.js";
import { MORNING_GRID } from "../../../web/webclient-app/stories/fixtures/travel_grid.js";
import { travelJourney } from "../../../web/webclient-app/stories/fixtures/travel_log.js";
import { walkCapacity } from "../../../web/webclient-app/stories/fixtures/travel_walk.js";
import RiteArrivalCard from "./RiteArrivalCard.vue";
import RitePanel from "./RitePanel.vue";
import { ART, CITY_ART, CITY_DISTRICT, CITY_GUARDIAN, DISTRICT, GUARDIAN, riteOptions } from "./prototype-data.js";

const props = defineProps({
  initialPhase: { type: String, default: "arrival" },
  city: { type: Boolean, default: false },
  art: { type: Boolean, default: true },
  companions: { type: Number, default: 2 },
  watchScenes: { type: Boolean, default: true },
  third: { type: Boolean, default: false },
  initialSeen: { type: Array, default: () => [] },
  initialPerformer: { type: Number, default: 42 },
  motion: { type: String, default: "full" },
});

const district = props.city ? CITY_DISTRICT : DISTRICT;
const guardian = props.city ? CITY_GUARDIAN : GUARDIAN;
const artUrl = props.art ? (props.city ? CITY_ART : ART) : null;
const options = riteOptions({ watchScenes: props.watchScenes, third: props.third });

const phase = ref(props.initialPhase);
const revisit = ref(false);
const seen = ref([...props.initialSeen]);
const lit = computed(() => seen.value.length > 0);
const intent = ref("—");
const justLit = ref(false);

// ── the party on the stage ──────────────────────────────────────────────
const portraitEntry = (key, file, face) =>
  artworkEntry(
    { context: { name: key, role: "同伴" } },
    artworkDescriptor({
      subject_id: `rite_proto_${key}`,
      generation_subject: `rite_proto_${key}`,
      attempts: [
        {
          type: "image",
          source_id: `portrait.default:${key}`,
          rank: 30,
          resource: artworkResource({
            resource_id: `defaults/${file}.webp`,
            version: fixtureDigest(`rite-proto-${key}`),
            url: `/art/defaults/${file}.webp`,
            origin: "bundled_official",
            geometry: { image_size: null, face_rect: face, stage: null, aspect_ratio: "3:4" },
          }),
        },
      ],
      terminal: null,
    }),
  );
const ART_PANEL = {
  schema_version: 4, available: true, kind: "scene",
  portrait_catalog: {
    "301": portraitEntry("elaine", "woman", { x: 0.36, y: 0.04, w: 0.28, h: 0.16 }),
    "302": portraitEntry("allen", "man", { x: 0.35, y: 0.03, w: 0.29, h: 0.16 }),
    "303": portraitEntry("lia", "girl", { x: 0.36, y: 0.06, w: 0.28, h: 0.16 }),
    "304": portraitEntry("bran", "elder", { x: 0.36, y: 0.04, w: 0.28, h: 0.16 }),
  },
};
const PLAYER = { identity: "42", displayName: "伊蓮", artwork: portraitFor(ART_PANEL, "301"), panel: ART_PANEL, hasReference: true };
const companionRows = [
  { identity: 7, display_name: "艾倫", portrait_ref: "302", role: "companion" },
  { identity: 8, display_name: "莉亞", portrait_ref: "303", role: "companion" },
  { identity: 9, display_name: "布蘭", portrait_ref: "304", role: "companion" },
].slice(0, props.companions);
const slots = companionFigures({
  player: PLAYER, companions: companionRows, actorIdentity: "42", possessing: false, artPanel: ART_PANEL, portraitFor,
});
const performers = [
  { id: 42, name: PLAYER.displayName, self: true },
  ...companionRows.map((row) => ({ id: row.identity, name: row.display_name, self: false })),
];
const anyWatch = options.some((option) => !!option.watch);
const canSwitch = anyWatch && performers.length > 1;
const performerId = ref(canSwitch ? props.initialPerformer : 42);
const performer = computed(() => performers.find((p) => p.id === performerId.value) ?? performers[0]);
const hovered = ref(null);
const targeting = computed(() => {
  if (phase.value === "playing") return { lit: new Set([String(performerId.value)]), selectable: new Set(), selected: new Set() };
  if (phase.value !== "menu" || !canSwitch) return null;
  return {
    lit: new Set([String(performerId.value), ...(hovered.value ? [String(hovered.value)] : [])]),
    selectable: new Set(performers.map((p) => String(p.id))),
    selected: new Set([String(performerId.value)]),
  };
});
function onTargetPointer(identity, kind) {
  if (kind === "hover") hovered.value = Number(identity);
  else {
    performerId.value = Number(identity);
    hovered.value = null;
  }
}
function stepPerformer(delta) {
  const index = performers.findIndex((p) => p.id === performerId.value);
  performerId.value = performers[(index + delta + performers.length) % performers.length].id;
}

// ── the delivery and the shared scene player ────────────────────────────
const delivery = ref(null);
let serial = 0;
const source = computed(() => ({
  playable: phase.value === "playing",
  generation: 1,
  contextId: `rite:${district.key}`,
  delivery: delivery.value,
  actorName: performer.value.self ? "你" : performer.value.name,
  hostName: guardian.name,
  bondStage: null,
}));
const scene = useAuthoredScene(source);
scene.onSceneFinished(() => {
  const key = delivery.value.option;
  justLit.value = !lit.value;
  if (!seen.value.includes(key)) seen.value = [...seen.value, key];
  phase.value = "menu";
});

function perform(key) {
  const option = options.find((entry) => entry.key === key);
  const body = performer.value.self ? option.self : option.watch(performer.value.name);
  serial += 1;
  intent.value = `explore.landmark_rite { option: "${key}", member_id: ${performer.value.self ? "null" : performer.value.id} }`;
  delivery.value = {
    kind: "formal", option: key,
    delivery_id: `rite:${district.key}:${key}:${8123 + serial}`,
    context_id: `rite:${district.key}`, topic_id: null,
    scene_id: body.scene_id, scene_revision: body.revision, phase_revision: null,
    lines: body.lines,
  };
  phase.value = "playing";
}
function approach() {
  intent.value = "（本地）進入儀式舞台，不送出任何請求";
  justLit.value = false;
  phase.value = "menu";
}
function leave() {
  intent.value = "（本地）退開，不寫入任何狀態";
  phase.value = "map";
}
function reopen() {
  revisit.value = true;
  phase.value = "arrival";
}

// ── the band's idle lines ───────────────────────────────────────────────
const stageLines = computed(() => {
  const lines = [{ kind: "out", text: guardian.form, seq: 1 }];
  if (justLit.value) lines.push({ kind: "out", text: `◆ ${district.name}的地圖亮了起來。`, seq: 2 });
  return lines;
});
const cityLines = [{ kind: "out", text: "石磚廣場向四面敞開，噴泉的水聲蓋過了市集的叫賣。", seq: 1 }];
const dialogueModel = { host: { displayName: guardian.name }, bondStage: null };

const NOON = { year: 1, season_index: 0, season_label: "春", day_in_season: 3, hour: 9, minute: 40, second: 0 };
const leg = legView({
  aim: null, progress: 0, walking: null, capacity: walkCapacity({ quotes: { east: 1260 } }),
  preferences: { pace: "standard", stopAtNight: true }, phase: null, error: null, serverTime: NOON, mapStatus: "ready",
});
const journey = travelJourney().slice(0, 4);

const onStage = computed(() => phase.value === "menu" || phase.value === "playing");
const still = props.motion === "off";

function backdrop() {
  if (onStage.value || props.city) {
    const url = onStage.value ? artUrl : CITY_ART;
    return h("div", { class: ["rite-proto__art", { "is-empty": !url }], key: `art-${onStage.value}` }, [
      url ? h("img", { src: url, alt: "" }) : null,
      onStage.value
        ? h("p", { class: "rite-proto__place" }, [h("span", { "aria-hidden": "true" }, "◆ "), `${district.landmark}・${guardian.name}`])
        : null,
    ]);
  }
  return h(TravelMap, { grid: MORNING_GRID, status: "ready", aim: null, motionLevel: props.motion });
}
function lineup() {
  return h(CompanionLineup, {
    slots, motionLevel: props.motion, targeting: targeting.value,
    onTargetPointer,
    onPointerleave: () => { hovered.value = null; },
  });
}
function messageBand() {
  if (onStage.value) {
    return h(MessageWindow, {
      mode: "dialogue", dialogue: dialogueModel, lines: stageLines.value, marks: [], textSpeed: still ? "instant" : "normal",
      motionLevel: props.motion, scene: scene.presentation.value, onSceneAdvance: () => scene.advance(),
    });
  }
  if (props.city) return h(MessageWindow, { lines: cityLines, marks: [], textSpeed: "instant", motionLevel: props.motion });
  return h(TravelLog, { entries: journey });
}
function placeColumn() {
  const label = props.city ? district.landmark : "界源高地・丘陵";
  const children = [h(PlaceCard, { locationLabel: label, timeLabel: "春 3 日 ‧ 09:40・白晝", motionLevel: props.motion })];
  if (phase.value === "map") {
    children.push(
      h("button", { type: "button", class: "rite-proto__entry", onClick: reopen }, [
        h("span", { class: "rite-proto__entry-gem", "aria-hidden": "true" }),
        h("span", { class: "rite-proto__entry-text" }, [h("b", null, guardian.name), ` 儀式`]),
        h("kbd", { "aria-hidden": "true" }, "R"),
      ]),
    );
  }
  return children;
}
function choices() {
  if (phase.value === "arrival") {
    return h(RiteArrivalCard, {
      district, guardian, art: artUrl, lit: lit.value, seen: seen.value.length, total: options.length, revisit: revisit.value,
      onApproach: approach, onLeave: leave,
    });
  }
  if (phase.value === "menu") {
    return h(RitePanel, {
      key: `panel-${serial}`, options, seen: seen.value, performer: performer.value, canSwitch, entrance: !still,
      onPerform: perform, onLeave: leave, onStepPerformer: stepPerformer,
    });
  }
  return null;
}

const render = () =>
  h("div", { class: "rite-proto" }, [
    h("p", { class: "rite-proto__intent" }, [h("b", null, "intent "), intent.value]),
    h(
      HudFrame,
      {
        mode: onStage.value ? "dialogue" : "exploration",
        travel: !onStage.value && !props.city,
        cardOpen: phase.value === "arrival",
        motionLevel: props.motion,
      },
      {
        backdrop,
        "actor-left": () => (onStage.value || props.city ? lineup() : null),
        map: placeColumn,
        choices,
        "band-message": messageBand,
        "band-command": () =>
          props.city
            ? h("div", { class: "rite-proto__dock" }, "指令面板（探索）")
            : h("div", { class: "rite-proto__leg" }, h(LegPanel, { view: leg, motionLevel: props.motion })),
      },
    ),
  ]);
</script>

<template>
  <render />
</template>

<style>
.rite-proto {
  position: relative;
  height: calc(100vh - var(--header-h));
}
.rite-proto__intent {
  position: fixed;
  z-index: 50;
  top: 0;
  left: 0;
  right: 0;
  box-sizing: border-box;
  height: var(--header-h);
  margin: 0;
  padding: 0 calc(20px * var(--ui-scale));
  display: flex;
  align-items: center;
  gap: 0.6em;
  background: var(--ink-900);
  border-bottom: var(--line);
  font: var(--text-sm)/1 var(--f-mono);
  color: var(--paper-300);
}
.rite-proto__intent b {
  color: var(--gold-300);
  font-weight: 400;
  letter-spacing: 0.2em;
}
/* The stage ground: the archetype art full-bleed under an ink wash that
   keeps the figures and the panel readable. No art: quiet ink, never
   substitute art. */
.rite-proto__art {
  position: absolute;
  inset: 0;
  overflow: hidden;
  background:
    radial-gradient(70% 60% at 50% 45%, rgba(185, 154, 96, 0.1), transparent 70%),
    linear-gradient(180deg, #1b1a20, #0c0d11);
}
.rite-proto__art img {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
  object-position: center 40%;
}
.rite-proto__art::after {
  content: "";
  position: absolute;
  inset: 0;
  background:
    linear-gradient(90deg, rgba(8, 9, 12, 0.5), rgba(8, 9, 12, 0.08) 45%, rgba(8, 9, 12, 0.3)),
    linear-gradient(180deg, rgba(8, 9, 12, 0.2), rgba(8, 9, 12, 0) 30%, rgba(8, 9, 12, 0.7));
}
.rite-proto__art.is-empty::before {
  content: "";
  position: absolute;
  left: 18%;
  right: 18%;
  top: 46%;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(228, 200, 142, 0.3), transparent);
}
.rite-proto__place {
  position: absolute;
  z-index: 1;
  right: calc(24px * var(--ui-scale));
  top: calc(20px * var(--ui-scale));
  margin: 0;
  padding: calc(6px * var(--ui-scale)) calc(14px * var(--ui-scale));
  border: 1px solid rgba(228, 200, 142, 0.35);
  border-radius: var(--radius-sm);
  background: rgba(12, 13, 17, 0.62);
  font: var(--text-md)/1.3 var(--f-display);
  letter-spacing: 0.14em;
  color: var(--paper-50);
}
.rite-proto__place span {
  color: var(--gold-400);
}
.rite-proto__leg,
.rite-proto__dock {
  box-sizing: border-box;
  height: 100%;
  display: flex;
  padding: calc(12px * var(--ui-scale));
}
.rite-proto__dock {
  align-items: center;
  justify-content: center;
  color: var(--paper-500);
  font: var(--text-sm) var(--f-sans);
}
/* The return entry under the place card while standing on a rite landmark. */
.rite-proto__entry {
  align-self: flex-end;
  display: inline-flex;
  align-items: center;
  gap: calc(10px * var(--ui-scale));
  min-height: calc(40px * var(--ui-scale));
  padding: 0 calc(14px * var(--ui-scale));
  border: 1px solid rgba(185, 154, 96, 0.5);
  border-radius: var(--radius-sm);
  background: rgba(12, 13, 17, 0.86);
  color: var(--paper-200);
  font: var(--text-md)/1 var(--f-sans);
  letter-spacing: 0.08em;
  cursor: pointer;
  pointer-events: auto;
}
.rite-proto__entry b {
  color: var(--gold-300);
  font-weight: 400;
}
.rite-proto__entry-gem {
  width: calc(7px * var(--ui-scale));
  height: calc(7px * var(--ui-scale));
  background: var(--gold-400);
  transform: rotate(45deg);
}
.rite-proto__entry kbd {
  font: var(--text-xs)/1 var(--f-sans);
  color: var(--gold-300);
  padding: calc(3px * var(--ui-scale)) calc(6px * var(--ui-scale));
  border: 1px solid rgba(228, 200, 142, 0.35);
  border-radius: calc(3px * var(--ui-scale));
}
.rite-proto__entry:hover,
.rite-proto__entry:focus-visible {
  border-color: var(--gold-400);
  background: var(--gold-glow);
  outline: none;
}
</style>
