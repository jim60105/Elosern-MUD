import { h, ref } from "vue";
import GradeGem from "../../components/GradeGem.vue";
import IconTabs from "../../components/IconTabs.vue";

// IconTabs (quest-drawer-ui-primitives): the icon-only tablist the quest
// drawer uses for its horizontal first level and its vertical rails. Arrow
// keys, Home, and End move focus; Enter, Space, or a click selects. Hover or
// focus shows the tooltip (right of a vertical tab, below a horizontal one).
// Disabled tabs stay focusable and describe their reason; count badges hide
// at zero, and `hot` marks the one actionable state.

const TOP_TABS = [
  { key: "book", label: "任務簿", glyph: "quest_book" },
  { key: "counter", label: "公會櫃檯", glyph: "guild_counter", disabled: true, reason: "需在公會職員面前" },
];

const STATE_TABS = [
  { key: "in_progress", label: "進行中", glyph: "quest_in_progress", count: 3 },
  { key: "completed", label: "已完成", glyph: "quest_completed", count: 2, hot: true },
  { key: "failed", label: "失敗", glyph: "quest_failed", count: 1 },
];

// The guild board's F→S rail for a holder at rank E: the own grade marked,
// empty grades dimmed, grades above the rank locked.
const GRADE_COUNTS = { F: 0, E: 2 };
const GRADE_TABS = ["F", "E", "D", "C", "B", "A", "S"].map((grade, index) => ({
  key: grade,
  label: `${grade} 級`,
  count: GRADE_COUNTS[grade] ?? 0,
  mark: grade === "E",
  dim: !GRADE_COUNTS[grade],
  locked: index > 1,
  reason: grade === "E" ? "你的等級" : index > 1 ? "尚未開放" : undefined,
}));

// A stateful host so the story behaves like the drawer's v-model.
const renderTabs = (frameStyle, slots) => (args) => ({
  setup() {
    const selected = ref(args.modelValue);
    return () =>
      h("div", { style: frameStyle }, [
        h(
          IconTabs,
          {
            ...args,
            modelValue: selected.value,
            "onUpdate:modelValue": (value) => {
              selected.value = value;
            },
          },
          slots,
        ),
      ]);
  },
});

// The horizontal tabs sit on a header rule, as in the drawer header. The
// bottom margin leaves room for the tooltip below the tabs.
const HEADER_FRAME = [
  "display: flex; justify-content: flex-start;",
  "margin: calc(24px * var(--ui-scale)) calc(24px * var(--ui-scale)) calc(96px * var(--ui-scale));",
  "padding: calc(12px * var(--ui-scale)) calc(20px * var(--ui-scale)) 0;",
  "border-bottom: 1px solid rgba(185, 154, 96, 0.28);",
  "background: linear-gradient(180deg, #16181dfa, #0e1014fa);",
].join("");

// The vertical rail sits beside the list column it opens into.
const RAIL_FRAME = [
  "display: grid; grid-template-columns: calc(68px * var(--ui-scale)) calc(320px * var(--ui-scale));",
  "height: calc(560px * var(--ui-scale));",
  "margin: calc(24px * var(--ui-scale));",
  "background: #15171c;",
  "border: 1px solid rgba(185, 154, 96, 0.45);",
].join("");

export default {
  title: "Core/IconTabs",
  component: IconTabs,
  argTypes: {
    orientation: { control: "inline-radio", options: ["horizontal", "vertical"] },
  },
};

// First level: the book and the guild counter, the counter disabled away
// from a clerk (focus it to read the reason).
export const HorizontalTopTabs = {
  render: renderTabs(HEADER_FRAME),
  args: {
    tabs: TOP_TABS,
    modelValue: "book",
    orientation: "horizontal",
    ariaLabel: "任務分類",
  },
};

// The quest book's state rail: ink-and-gold counts, the completed count hot.
export const VerticalQuestStates = {
  render: renderTabs(RAIL_FRAME),
  args: {
    tabs: STATE_TABS,
    modelValue: "in_progress",
    orientation: "vertical",
    ariaLabel: "任務狀態",
  },
};

// The guild board's grade rail: GradeGem in the icon slot, the own grade
// marked, empty grades dimmed, grades above the rank locked.
export const VerticalGrades = {
  render: renderTabs(`${RAIL_FRAME}--icon-tabs-tab-h: calc(52px * var(--ui-scale));`, {
    icon: ({ tab }) => h(GradeGem, { grade: tab.key }),
  }),
  args: {
    tabs: GRADE_TABS,
    modelValue: "E",
    orientation: "vertical",
    ariaLabel: "委託難度",
  },
};
