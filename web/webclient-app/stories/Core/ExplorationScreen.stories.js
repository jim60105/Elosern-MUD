import { h } from "vue";
import HudFrame from "../../components/HudFrame.vue";
import ChoiceCard from "../../components/ChoiceCard.vue";
import ExitCompass from "../../components/ExitCompass.vue";
import ExplorationReadout from "../../components/ExplorationReadout.vue";
import LocalMap from "../../components/LocalMap.vue";
import PlaceCard from "../../components/PlaceCard.vue";
import PresenceRail from "../../components/PresenceRail.vue";
import SceneOverview from "../../components/SceneOverview.vue";
import StageActor from "../../components/StageActor.vue";
import { idleReadout } from "../../components/exploration-readout.js";
import { ART_PANEL_SAMPLE } from "../fixtures.js";
import { localMapAround, localMapModelFor } from "../fixtures/local_map.js";
import {
  AFFORDANCES,
  compassArgs,
  explorationPanelFixture,
  overviewArgs,
  presenceArgs,
  verbCardArgs,
} from "../fixtures/scene_overview.js";

// The exploration screen (exploration-presence-rail task 3.3; scene overview
// redesign §2): the stage with the presence rail on its floor, the place
// card and minimap in the right-hand island column, and the command panel
// holding the exit compass beside the shared readout and the footer chips.
// `PersonFocus` is the same room with the guild clerk in focus: the rail
// gone, the clerk's standee in `actor-right`, the verb card centred, the
// map column stepped away, and the command panel inert and dimmed. Every
// surface is bound to the real builders over one synthesized room.

const ROOM = explorationPanelFixture({
  exits: [
    { ref: "n", label: "北", destination: "town:gate:0:1" },
    { ref: "e", label: "東", destination: "town:gate:1:0" },
    { ref: "door", label: "酒館門", destination: "interior:tavern", enabled: false, reason: "酒館打烊了，門從裡面上了閂。" },
  ],
  targets: [
    { identity: 11, name: "葛里安‧衛登", affordances: [AFFORDANCES.talk, AFFORDANCES.guild] },
    { identity: 12, name: "霧狼", kind: "monster", affordances: [AFFORDANCES.engage] },
  ],
  entities: [{ identity: 21, name: "旅人艾拉" }],
  objects: [{ identity: 31, name: "任務板" }],
});

const LOCAL_MAP = localMapAround({
  layer: "grid",
  current: ["town:gate:0:0", "城門廣場", 0, 0],
  neighbours: [
    ["town:gate:0:1", "北岸大道", 0, 1],
    ["town:gate:1:0", "公會街", 1, 0],
  ],
});

const COMPASS = compassArgs(ROOM, LOCAL_MAP);

function renderScreen(args) {
  const focus = args.focus;
  const { localMapModel, ...compassProps } = COMPASS;
  const verb = verbCardArgs(ROOM, 11);
  return {
    render: () =>
      h(
        "div",
        { style: { position: "relative", width: "100vw", height: "100vh", background: "#0b0d10" } },
        [
          h(
            HudFrame,
            { mode: "exploration", cardOpen: focus, personFocus: focus },
            {
              "actor-right": () =>
                focus ? h(StageActor, { side: "right", portrait: null, name: "葛里安‧衛登" }) : null,
              presence: () => (focus ? null : h(PresenceRail, presenceArgs(ROOM, { artPanel: ART_PANEL_SAMPLE }))),
              choices: () => (focus ? h(ChoiceCard, { ...verb, testId: "presence-card", trapFocus: true }) : null),
              map: () => [
                h(PlaceCard, { locationLabel: "城門廣場", timeLabel: "第 3 天 ‧ 清晨" }),
                h(LocalMap, { localMap: localMapModel || localMapModelFor(LOCAL_MAP) }),
              ],
              "band-command": () =>
                h("div", { style: { display: "grid", gridTemplateColumns: "auto minmax(0, 1fr)", gap: "10px", height: "100%" } }, [
                  h("div", { style: { height: "100%", aspectRatio: "1 / 1" } }, [h(ExitCompass, { ...compassProps, active: !focus })]),
                  h("div", { style: { display: "flex", flexDirection: "column", gap: "8px", minWidth: 0 } }, [
                    h(ExplorationReadout, { ...idleReadout(COMPASS.targets.cycle.length, 3) }),
                    h(SceneOverview, overviewArgs(ROOM, { suggestions: { status: "generating" }, focusedKey: "look-room" })),
                  ]),
                ]),
            },
          ),
        ],
      ),
  };
}

export default {
  title: "Core/ExplorationScreen",
  component: HudFrame,
  parameters: { layout: "fullscreen" },
};

// The room at rest: the rail with the clerk, the wolf, the traveller, and
// the quest board; three exits on the compass (one locked).
export const Default = {
  render: renderScreen,
  args: { focus: false },
};

// The clerk in focus: the verb card over the stage.
export const PersonFocus = {
  render: renderScreen,
  args: { focus: true },
};
