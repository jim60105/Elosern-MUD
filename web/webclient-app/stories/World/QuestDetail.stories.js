import { h } from "vue";
import QuestDetail from "../../components/QuestDetail.vue";
import { bookActions, bookDetail } from "../../components/quest-drawer-model.js";
import { QUEST_LOG_PANEL_SAMPLE, SERVICES_PANEL_GUILD_TURNIN_READY_SAMPLE, SERVICES_PANEL_SAMPLE } from "../fixtures.js";

// QuestDetail (quest-drawer-book-tab): the quest drawer's detail column. It
// renders a bookDetail view model and a bookActions set
// (quest-drawer-model.js): the hero (ribbon, title, objective and note,
// grade gem, completed or failed stamp), one-based progress (pips up to
// twelve, a bar above), the rationale and deadline pair, the issuer letter,
// and the reward cells with their settlement note. The action bar is pinned
// to the bottom and emits the exact `{action_id, payload}`; abandon asks for
// a second confirmation.

const rowById = (id) => QUEST_LOG_PANEL_SAMPLE.rows.find((row) => row.quest_id === id);
const counterRow = (services, id) => services.guild.quests.find((row) => row.quest_id === id) ?? null;

// The detail column's width and height, as in the drawer grid.
const renderDetail = (args) => ({
  render: () =>
    h("div", { style: "width: calc(760px * var(--ui-scale)); height: calc(640px * var(--ui-scale)); margin: calc(24px * var(--ui-scale));" }, [
      h(QuestDetail, args),
    ]),
});

const view = (row, counter = null) => ({ detail: bookDetail(row), actions: bookActions(row, counter) });

export default {
  title: "World/QuestDetail",
  component: QuestDetail,
};

// In progress in front of a clerk: pips, the mirrored abandon, tracking on.
export const InProgressPips = {
  render: renderDetail,
  args: view(rowById("q_1042"), counterRow(SERVICES_PANEL_SAMPLE, "q_1042")),
};

// A target above twelve renders a bar instead of pips.
export const LongBarTarget = {
  render: renderDetail,
  args: view({ ...rowById("q_1042"), stage_progress: 17, objective_quantity: 40 }),
};

// Completed with an enabled counter turn-in: the primary button.
export const CompletedTurnIn = {
  render: renderDetail,
  args: view(rowById("q_0301"), counterRow(SERVICES_PANEL_GUILD_TURNIN_READY_SAMPLE, "q_0301")),
};

// Completed and already claimed, away from the counter.
export const CompletedClaimed = {
  render: renderDetail,
  args: view({ ...rowById("q_0301"), reward_claimed: true }),
};

// Failed: the grey stamp and the no-reward line.
export const Failed = {
  render: renderDetail,
  args: view(rowById("q_0099")),
};

// Null rationale and flavor: no 評價 cell, the fixed no-message letter.
export const NullProse = {
  render: renderDetail,
  args: view({ ...rowById("q_1042"), rationale: null, flavor: null, deadline_line: null }),
};

// A null reward (unresolvable issuance): no reward section, no settlement.
export const NullReward = {
  render: renderDetail,
  args: view({ ...rowById("q_2077"), reward: null, settlement: null }),
};
