import { h, ref } from "vue";
import QuestList from "../../components/QuestList.vue";
import { bookListRow, rowsByState } from "../../components/quest-drawer-model.js";
import { QUEST_LOG_PANEL_SAMPLE, QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE } from "../fixtures.js";

// QuestList (quest-drawer-book-tab): the quest drawer's list column. A
// heading with the row count, then a single-selection listbox: arrow keys
// move focus, Enter, Space, or a click selects. Rows show the category glyph,
// the name with the tracked flag, the grade gem, and either the in-progress
// bar or the issuer and deadline line. Non-list forms: the absent line
// before the first commit, the unavailable panel's own reason, and the
// shared empty guidance. Props are bookListRow view models
// (quest-drawer-model.js) built from the committed `quest_log` v2 panel.

const groups = rowsByState(QUEST_LOG_PANEL_SAMPLE);

// The list column's width and the list background, as in the drawer grid.
const renderList = (args) => ({
  setup() {
    const selected = ref(args.selectedId);
    return () =>
      h("div", { style: "width: calc(420px * var(--ui-scale)); height: calc(520px * var(--ui-scale)); margin: calc(24px * var(--ui-scale));" }, [
        h(QuestList, {
          ...args,
          selectedId: selected.value,
          onSelect: (id) => {
            selected.value = id;
          },
        }),
      ]);
  },
});

export default {
  title: "World/QuestList",
  component: QuestList,
};

// In progress: a tracked species hunt and a private commission.
export const InProgress = {
  render: renderList,
  args: {
    heading: "進行中",
    rows: groups.in_progress.map(bookListRow),
    selectedId: "q_1042",
  },
};

// Terminal rows show the issuer and the deadline line instead of progress.
export const Failed = {
  render: renderList,
  args: {
    heading: "失敗",
    rows: groups.failed.map(bookListRow),
    selectedId: "q_0099",
  },
};

export const EmptyState = {
  render: renderList,
  args: {
    heading: "已完成",
    rows: [],
    selectedId: null,
    emptyGuidance: "達成的委託會列在這裡。",
  },
};

// Before the first `quest_log` commit.
export const Absent = {
  render: renderList,
  args: {
    heading: "進行中",
    rows: [],
    selectedId: null,
    status: "absent",
  },
};

export const Unavailable = {
  render: renderList,
  args: {
    heading: "進行中",
    rows: [],
    selectedId: null,
    status: "unavailable",
    reason: QUEST_LOG_PANEL_UNAVAILABLE_SAMPLE.reason,
  },
};
