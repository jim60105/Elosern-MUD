import { h } from "vue";
import PresenceRail from "../../components/PresenceRail.vue";
import { ART_PANEL_SAMPLE } from "../fixtures.js";
import { AFFORDANCES, explorationPanelFixture, presenceArgs } from "../fixtures/scene_overview.js";

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
});

// Two hosts (the first with a committed portrait's face crop, the second
// with its initial), a bystander, the separator, and an object. The
// exploration panel's schema v3 still publishes `portrait_ref: null`, so the
// story supplies the ref the presenter will carry for the first host.
export const Default = {
  render,
  args: presenceArgs(HALL, { artPanel: ART_PANEL_SAMPLE, portraits: { 101: "101" } }),
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

// No portraits at all: every medallion shows its name's first character.
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
