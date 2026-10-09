import { h } from "vue";
import HudDrawer from "../../components/HudDrawer.vue";
import QuestDrawer from "../../components/QuestDrawer.vue";
import { useQuestDrawerMemory } from "../../components/quest-drawer-memory.js";
import { boardBasis, holderRank } from "../../components/quest-drawer-model.js";
import {
  QUEST_LOG_PANEL_EMPTY_SAMPLE,
  QUEST_LOG_PANEL_SAMPLE,
  QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_GUILD_BOARD_SAMPLE,
  SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE,
  SERVICES_PANEL_GUILD_TURNIN_READY_SAMPLE,
  SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE,
  SERVICES_PANEL_MINIMAL_SAMPLE,
  SERVICES_PANEL_SAMPLE,
  SERVICES_PANEL_UNAVAILABLE_SAMPLE,
} from "../fixtures.js";

// QuestDrawer (quest-drawer-book-tab): the 任務 drawer's body inside the real
// HudDrawer chrome, as the live client mounts it (flush body). The first
// level switches between the quest book and the guild counter; the counter
// tab is disabled, yet focusable with its reason, while no usable guild
// section exists. The book shows one state at a time on a vertical rail with
// counts (the completed count turns hot while a turn-in waits), a listbox,
// and the selected quest's detail with the action bar. Props: questLog (the
// committed `quest_log` v2 panel or null), services (the committed `services`
// panel or null). Every intent is emitted as `action` with the exact
// `{action_id, payload}`. The counter tab (quest-drawer-guild-board-tab)
// shows the grade rail from the guild section's `rank_ladder`, the rank card
// above the grade's offers, and the selected offer with its accept action;
// an unregistered holder sees only the registration card.

export default {
  title: "World/QuestDrawer",
  component: QuestDrawer,
};

// Each story seeds its own session memory scope, so it opens on its tab and
// state however the previous story left the shared memory.
const renderDrawer = ({ top = "book", bookState = "in_progress", boardGrade = null, offerKey = null, ...args }, context) => ({
  setup() {
    const scope = `story:${context.id}`;
    const memory = useQuestDrawerMemory(scope);
    memory.top = top;
    memory.bookState = bookState;
    if (boardGrade) {
      memory.boardBasis = boardBasis(args.services?.guild?.rank_ladder, holderRank(args.services));
      memory.boardGrade = boardGrade;
      if (offerKey) memory.selectedByTab = { [`board:${boardGrade}`]: offerKey };
    }
    return () =>
      h(HudDrawer, { open: true, title: "任務", icon: "quests", drawerKey: "quest", bodyFlush: true }, () => [
        h(QuestDrawer, { ...args, memoryScope: scope }),
      ]);
  },
});

// In front of a clerk: in progress, the first row selected.
export const BookInProgress = {
  render: renderDrawer,
  args: { questLog: QUEST_LOG_PANEL_SAMPLE, services: SERVICES_PANEL_SAMPLE },
};

// A turn-in waits at the counter: the completed count is hot.
export const CompletedHotBadge = {
  render: renderDrawer,
  args: {
    questLog: QUEST_LOG_PANEL_SAMPLE,
    services: SERVICES_PANEL_GUILD_TURNIN_READY_SAMPLE,
    bookState: "completed",
  },
};

export const Failed = {
  render: renderDrawer,
  args: { questLog: QUEST_LOG_PANEL_SAMPLE, services: SERVICES_PANEL_SAMPLE, bookState: "failed" },
};

// An available, empty book: the shared empty guidance and an empty detail.
export const EmptyBook = {
  render: renderDrawer,
  args: { questLog: QUEST_LOG_PANEL_EMPTY_SAMPLE, services: SERVICES_PANEL_SAMPLE },
};

// Away from any clerk: tracking only, the counter tab disabled with the
// clerk reason (focus it to read the tooltip).
export const AwayFromCounter = {
  render: renderDrawer,
  args: { questLog: QUEST_LOG_PANEL_SAMPLE, services: SERVICES_PANEL_MINIMAL_SAMPLE },
};

// The counter tab for a C-rank holder: the default grade is the highest
// eligible grade with offers.
export const CounterTab = {
  render: renderDrawer,
  args: { questLog: QUEST_LOG_PANEL_SAMPLE, services: SERVICES_PANEL_SAMPLE, top: "counter" },
};

const BOARD_ROWS = SERVICES_PANEL_GUILD_BOARD_SAMPLE.guild.board;

// The approved GuildBoard layout: an E-rank holder on the E grade, an offer
// with prose selected (compare with Design/QuestDrawerRedesign GuildBoard).
export const GuildBoard = {
  render: renderDrawer,
  args: {
    questLog: QUEST_LOG_PANEL_SAMPLE,
    services: SERVICES_PANEL_GUILD_BOARD_SAMPLE,
    top: "counter",
    boardGrade: "E",
    offerKey: BOARD_ROWS.find((row) => row.rank === "E" && row.accept.enabled).definition_key,
  },
};

// A grade above the holder's rank: locked, no rows, no detail.
export const LockedGrade = {
  render: renderDrawer,
  args: { questLog: QUEST_LOG_PANEL_SAMPLE, services: SERVICES_PANEL_GUILD_BOARD_SAMPLE, top: "counter", boardGrade: "D" },
};

// An eligible grade with no offers posted: dimmed, with its empty line.
export const EmptyGrade = {
  render: renderDrawer,
  args: {
    questLog: QUEST_LOG_PANEL_SAMPLE,
    services: {
      ...SERVICES_PANEL_GUILD_BOARD_SAMPLE,
      guild: { ...SERVICES_PANEL_GUILD_BOARD_SAMPLE.guild, board: BOARD_ROWS.filter((row) => row.rank === "F") },
    },
    top: "counter",
    boardGrade: "E",
  },
};

// An offer already held: the accept is disabled beside the server's reason.
export const DisabledAccept = {
  render: renderDrawer,
  args: {
    questLog: QUEST_LOG_PANEL_SAMPLE,
    services: SERVICES_PANEL_GUILD_BOARD_SAMPLE,
    top: "counter",
    boardGrade: "E",
    offerKey: BOARD_ROWS.find((row) => !row.accept.enabled).definition_key,
  },
};

// An unregistered holder: only the registration card.
export const Unregistered = {
  render: renderDrawer,
  args: { questLog: QUEST_LOG_PANEL_EMPTY_SAMPLE, services: SERVICES_PANEL_GUILD_UNREGISTERED_SAMPLE, top: "counter" },
};

// The top rank: nothing is locked and the rank card reads 最高等級.
export const TopRank = {
  render: renderDrawer,
  args: {
    questLog: QUEST_LOG_PANEL_SAMPLE,
    services: {
      ...SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE,
      player: { ...SERVICES_PANEL_GUILD_TOP_RANK_SAMPLE.player, guild_rank: "S", next_rank: null, next_threshold: null },
    },
    top: "counter",
  },
};

// The services panel is unavailable: the book still works, and the counter
// tab carries the panel's own reason.
export const CounterUnavailable = {
  render: renderDrawer,
  args: { questLog: QUEST_LOG_PANEL_SAMPLE, services: SERVICES_PANEL_UNAVAILABLE_SAMPLE },
};

export const BookUnavailable = {
  render: renderDrawer,
  args: { questLog: QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE, services: SERVICES_PANEL_SAMPLE },
};

// Before the first `quest_log` commit.
export const BookBeforeCommit = {
  render: renderDrawer,
  args: { questLog: null, services: SERVICES_PANEL_SAMPLE },
};
