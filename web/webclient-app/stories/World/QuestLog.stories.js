import { h } from "vue";
import QuestLog from "../../components/QuestLog.vue";
import {
  QUEST_LOG_PANEL_EMPTY_SAMPLE,
  QUEST_LOG_PANEL_SAMPLE,
  QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
} from "../fixtures.js";

// QuestLog (quest-issuer-model change 11): the player's own quest book — the
// host-free half of the split quest drawer. Props: questLog — the committed
// `quest_log` v1 payload; services — the committed `services` v4 payload read
// only for the guild section's quest rows (the counter-action merge by
// quest_id). The tracking / abandon / turnin controls emit the exact OOB
// action intents (the `action_id` and `payload` fields of the `ui_action`
// envelope). No invented quests.

const renderBook = (args) => ({
  render: () =>
    h("div", { style: "border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;" }, [
      h(QuestLog, args),
    ]),
});

export default {
  title: "World/QuestLog",
  component: QuestLog,
};

// The book in front of a clerk: every row gains its counter-side actions
// (q_1042: abandon enabled, turn-in disabled with the counter's reason).
export const BookPlusCounter = {
  render: renderBook,
  args: {
    questLog: QUEST_LOG_PANEL_SAMPLE,
    services: SERVICES_PANEL_SAMPLE,
  },
};

// The same book away from any clerk (no guild section): tracking only —
// the case that previously rendered 尚未取得公會資料.
export const BookNoCounter = {
  render: renderBook,
  args: {
    questLog: QUEST_LOG_PANEL_SAMPLE,
    services: SERVICES_PANEL_MINIMAL_SAMPLE,
  },
};

export const EmptyBook = {
  render: renderBook,
  args: {
    questLog: QUEST_LOG_PANEL_EMPTY_SAMPLE,
    services: SERVICES_PANEL_SAMPLE,
  },
};

export const PanelUnavailable = {
  render: renderBook,
  args: {
    questLog: QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE,
    services: SERVICES_PANEL_SAMPLE,
  },
};

// The private commission row (q_2077) offers tracking only even with a clerk
// present, because the guild section carries no row with that quest id.
export const PrivateCommissionRow = {
  render: renderBook,
  args: {
    questLog: QUEST_LOG_PANEL_SAMPLE,
    services: SERVICES_PANEL_SAMPLE,
  },
};

// A disabled counter-side descriptor renders its disabled state and reason,
// never an enabled control (q_1042's turn-in is quest_not_ready).
export const DisabledCounterAction = {
  render: renderBook,
  args: {
    questLog: QUEST_LOG_PANEL_SAMPLE,
    services: SERVICES_PANEL_SAMPLE,
  },
};
