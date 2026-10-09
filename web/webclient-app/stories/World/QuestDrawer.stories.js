import { h } from "vue";
import HudDrawer from "../../components/HudDrawer.vue";
import QuestDrawer from "../../components/QuestDrawer.vue";
import { useQuestDrawerMemory } from "../../components/quest-drawer-memory.js";
import {
  QUEST_LOG_PANEL_EMPTY_SAMPLE,
  QUEST_LOG_PANEL_SAMPLE,
  QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE,
  SERVICES_PANEL_GUILD_TURNIN_READY_SAMPLE,
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
// `{action_id, payload}`.

export default {
  title: "World/QuestDrawer",
  component: QuestDrawer,
};

// Each story seeds its own session memory scope, so it opens on its tab and
// state however the previous story left the shared memory.
const renderDrawer = ({ top = "book", bookState = "in_progress", ...args }, context) => ({
  setup() {
    const scope = `story:${context.id}`;
    const memory = useQuestDrawerMemory(scope);
    memory.top = top;
    memory.bookState = bookState;
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

// The counter tab hosting the current guild counter.
export const CounterTab = {
  render: renderDrawer,
  args: { questLog: QUEST_LOG_PANEL_SAMPLE, services: SERVICES_PANEL_SAMPLE, top: "counter" },
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
