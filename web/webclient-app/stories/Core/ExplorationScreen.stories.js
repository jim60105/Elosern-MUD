import { h } from "vue";
import HudFrame from "../../components/HudFrame.vue";
import ChoiceCard from "../../components/ChoiceCard.vue";
import ExitCompass from "../../components/ExitCompass.vue";
import ExplorationReadout from "../../components/ExplorationReadout.vue";
import LocalMap from "../../components/LocalMap.vue";
import PlaceCard from "../../components/PlaceCard.vue";
import PresenceRail from "../../components/PresenceRail.vue";
import QuestionCard from "../../components/QuestionCard.vue";
import StageActor from "../../components/StageActor.vue";
import { idleReadout } from "../../components/exploration-readout.js";
import { ART_PANEL_SAMPLE } from "../fixtures.js";
import { localMapAround, localMapModelFor } from "../fixtures/local_map.js";
import {
  AFFORDANCES,
  compassArgs,
  explorationPanelFixture,
  presenceArgs,
  suggestionsCardArgs,
  verbCardArgs,
  waitCardArgs,
} from "../fixtures/scene_overview.js";

// The exploration screen (exploration-presence-rail task 3.3; scene overview
// redesign §2): the stage with the presence rail on its floor, the place
// card with its 查看房間 and 等待 buttons and the minimap in the right-hand
// island column, and the command panel holding the exit compass beside the
// 建議 pill and the shared readout (exploration-room-actions). `PersonFocus`
// is the same room with the guild clerk in focus: the rail gone, the clerk's
// standee in `actor-right`, the verb card centred, the map column stepped
// away, and the command panel inert and dimmed. `WaitCard`, `DreamQuestion`,
// and `SuggestionsCard` open the room cards over the stage. Every surface is
// bound to the real builders over one synthesized room.

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

const SUGGESTIONS = {
  status: "ready",
  cards: [
    { kind: "known_action", label: "查看任務板", action_code: "explore.look", params: { target_id: 31 } },
    { kind: "known_action", label: "等到天亮再出發", action_code: "explore.wait", params: { daypart: "dawn" }, hint: "夜裡的北岸大道不太平。" },
    { kind: "freeform", label: "問問葛里安最近的委託", action_code: "explore.talk_freeform", params: { npc_id: 11 } },
    { kind: "known_action", label: "看看旅人艾拉", action_code: "explore.look", params: { target_id: 21 } },
  ],
};

function centredCard(card, focus) {
  if (focus) {
    return h(ChoiceCard, { ...verbCardArgs(ROOM, 11), testId: "presence-card", trapFocus: true });
  }
  if (card === "wait") {
    return h(ChoiceCard, { ...waitCardArgs(), trapFocus: true });
  }
  if (card === "dream") {
    return h(QuestionCard, { question: "進入夢境協作？", closeLabel: "取消睡眠", testId: "dream-question" });
  }
  if (card === "suggestions") {
    return h(ChoiceCard, { ...suggestionsCardArgs(SUGGESTIONS), trapFocus: true });
  }
  return null;
}

function renderScreen(args) {
  const focus = args.focus;
  const card = args.card || null;
  const cardOpen = focus || !!card;
  const { localMapModel, ...compassProps } = COMPASS;
  return {
    render: () =>
      h(
        "div",
        { style: { position: "relative", width: "100vw", height: "100vh", background: "#0b0d10" } },
        [
          h(
            HudFrame,
            { mode: "exploration", cardOpen, personFocus: focus },
            {
              "actor-right": () =>
                focus ? h(StageActor, { side: "right", portrait: null, name: "葛里安‧衛登" }) : null,
              presence: () => (cardOpen ? null : h(PresenceRail, presenceArgs(ROOM, { artPanel: ART_PANEL_SAMPLE }))),
              choices: () => centredCard(card, focus),
              map: () => [
                h(PlaceCard, { locationLabel: "城門廣場", timeLabel: "第 3 天 ‧ 清晨", actionsEnabled: true }),
                h(LocalMap, { localMap: localMapModel || localMapModelFor(LOCAL_MAP) }),
              ],
              "band-command": () =>
                h("div", { style: { display: "grid", gridTemplateColumns: "auto minmax(0, 1fr)", gap: "10px", height: "100%" } }, [
                  h("div", { style: { height: "100%", aspectRatio: "1 / 1" } }, [h(ExitCompass, { ...compassProps, active: !cardOpen })]),
                  h("div", { class: "exploration-root__side" }, [
                    h("button", { type: "button", class: "exploration-pill", "data-testid": "suggestions-pill" }, [
                      h("span", { class: "exploration-pill__label" }, "建議"),
                      h("b", { class: "exploration-pill__count" }, ` ${SUGGESTIONS.cards.length}`),
                    ]),
                    h(ExplorationReadout, { class: "exploration-root__readout", ...idleReadout(COMPASS.targets.cycle.length, 3) }),
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

// 等待 on the place card: the wait card over the stage.
export const WaitCard = {
  render: renderScreen,
  args: { focus: false, card: "wait" },
};

// 睡眠至完全恢復 on the wait card: the dream question.
export const DreamQuestion = {
  render: renderScreen,
  args: { focus: false, card: "dream" },
};

// The 建議 pill: the suggestions card over the stage.
export const SuggestionsCard = {
  render: renderScreen,
  args: { focus: false, card: "suggestions" },
};
