import { h } from "vue";
import QuestBoard from "../../components/QuestBoard.vue";
import {
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// QuestBoard (B4 services family): the guild quest surface. Prop: services —
// the committed `services` v2 payload (host, player, guild registration /
// board / quests / rank, shop, inventory). The accept / abandon / turnin /
// exam controls emit the exact OOB action intents (the `action_id` and
// `payload` fields of the `ui_action` envelope — the `guild.*` action ids
// come from the payload; transport-level fields are owned by the C1 store).
// No invented quests.

const renderBoard = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(QuestBoard, args),
    ]),
});

export default {
  title: "World/QuestBoard",
  component: QuestBoard,
};

export const FullGuild = {
  render: renderBoard,
  args: {
    services: SERVICES_PANEL_SAMPLE,
  },
};

export const NoGuild = {
  render: renderBoard,
  args: {
    services: SERVICES_PANEL_MINIMAL_SAMPLE,
  },
};

export const SectionUnavailable = {
  render: renderBoard,
  args: {
    services: SERVICES_PANEL_UNAVAILABLE_SAMPLE,
  },
};
