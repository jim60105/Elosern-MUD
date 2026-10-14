import { h } from "vue";
import PresenceRail from "../../components/PresenceRail.vue";
import { ART_PANEL_SAMPLE } from "../fixtures.js";
import { AFFORDANCES, explorationPanelFixture, presenceArgs } from "../fixtures/scene_overview.js";

// The story's face-crop entry. Storybook serves `web/static` only (the built-in
// fallbacks under `/art/defaults/`), so the SHARED sample's portrait-store URL
// would 404 in the showcase and the medallion would silently fall back to the
// initial. The story therefore re-points the entry at a served committed
// bitmap: it pins the medallion's RENDERING, never the producer's URL.
// The catalog value is exactly `{artwork, context}`: the story re-points the
// descriptor's own candidate at a served committed bitmap.
const STORY_FACE = {
  ...ART_PANEL_SAMPLE.portrait_catalog["101"],
  artwork: {
    ...ART_PANEL_SAMPLE.portrait_catalog["101"].artwork,
    attempts: [
      {
        ...ART_PANEL_SAMPLE.portrait_catalog["101"].artwork.attempts[0],
        resource: {
          ...ART_PANEL_SAMPLE.portrait_catalog["101"].artwork.attempts[0].resource,
          resource_id: "defaults/man.webp",
          version: "m".repeat(64),
          url: "/art/defaults/man.webp",
        },
      },
    ],
  },
};

const STORY_ART = {
  ...ART_PANEL_SAMPLE,
  portrait_catalog: { ...ART_PANEL_SAMPLE.portrait_catalog, 101: STORY_FACE },
};

// PresenceRail: who and what is in the room, on the stage floor
// (exploration-presence-rail; scene overview redesign §4.1). Gold medallions
// for interact targets (the face crop, else the first character), dashed
// muted medallions for present entities with no interact descriptor, a
// separator, then steel lozenges for objects, each with a name plate; at
// most six slots, the sixth `＋N` beyond that. One tab stop: ←/→ move, Enter
// activates; hovering or focusing lifts an entry and feeds the readout.
// Props: entries, artPanel, motionLevel. Events: activate(key),
// hover(content|null), tab({event, backward}). The entries are the real
// `presenceEntries` rows through the shared derived-shape helper.

const stageFloor = (story) => ({
  render: () =>
    h(
      "div",
      {
        style: {
          width: "900px",
          height: "200px",
          display: "flex",
          alignItems: "flex-end",
          justifyContent: "flex-end",
          padding: "16px",
          background: "linear-gradient(180deg, #2a2a33, #15161b 70%, #0b090d)",
        },
      },
      [h(story())],
    ),
});

const render = (args) => ({ render: () => h(PresenceRail, args) });

export default {
  title: "Core/PresenceRail",
  component: PresenceRail,
  decorators: [stageFloor],
};

const HALL = explorationPanelFixture({
  targets: [
    { identity: 101, name: "碼頭船長", affordances: [AFFORDANCES.talk, AFFORDANCES.trade] },
    { identity: 12, name: "葛里安‧衛登", affordances: [AFFORDANCES.talk, AFFORDANCES.guild] },
  ],
  entities: [{ identity: 21, name: "旅人艾拉" }],
  objects: [{ identity: 31, name: "任務板" }],
  // The wire-valid decimal references the presenter supplies for a catalogued
  // character (schema v4) — the shared art sample's own `"101"` entry; every
  // other identity deliberately carries none, so the real image and the
  // truthful fallback sit side by side.
  portraits: { 101: "101" },
});

// Two hosts (the first with the catalog's face crop, the second with its
// initial), a bystander, the separator, and an object. The reference is a
// hand-authored fixture value matched to the shared art sample, so this story
// pins the RENDERING of a supplied face crop — it is not production protocol
// evidence: only the live server packet proves that a reference names an
// admitted catalog image. A newer committed URL for the same reference
// replaces the crop in place (no rail reopen); that stateful refresh is
// asserted in the component tests, not by a static story.
export const Default = {
  render,
  args: presenceArgs(HALL, { artPanel: STORY_ART }),
};

// Seven entries: five slots and `＋2`, which opens the overflow card.
export const Overflow = {
  render,
  args: presenceArgs(
    explorationPanelFixture({
      targets: ["哨兵", "攤販", "吟遊詩人", "巡邏隊長", "藥師"].map((name, i) => ({
        identity: 40 + i,
        name,
        affordances: i === 0 ? [AFFORDANCES.engage] : [AFFORDANCES.talk],
      })),
      objects: [
        { identity: 31, name: "告示板" },
        { identity: 32, name: "水井" },
      ],
    }),
  ),
};

// Every reference null (`portrait_ref: null` on the wire): the truthful
// fallback, the name's first character, on every medallion and lozenge.
export const NoPortraits = {
  render,
  args: presenceArgs(HALL),
};

// Only things, no one: the lozenges alone, with no separator.
export const ObjectsOnly = {
  render,
  args: presenceArgs(
    explorationPanelFixture({
      objects: [
        { identity: 31, name: "任務板" },
        { identity: 32, name: "壁爐" },
        { identity: 33, name: "舊木箱" },
      ],
    }),
  ),
};
