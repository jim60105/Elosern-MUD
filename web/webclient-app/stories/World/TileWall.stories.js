import { h, ref } from "vue";
import TileWall from "../../components/handbook/TileWall.vue";
import CodexEmblem from "../../components/handbook/CodexEmblem.vue";

// TileWall (handbook-primitives): the handbook's grouped tile wall. One
// listbox with one roving tab stop; the arrow keys walk the tiles in reading
// order across groups, Home and End go to the ends, and Enter, Space or a
// click selects. A non-selectable tile stays focusable and never selects.
// The tile face is slot content; these synthetic tiles draw an emblem and a
// caption.

const tileFace = ({ item, selected }) =>
  h(
    "div",
    {
      style: `display: grid; gap: var(--sp-1); place-items: center; padding: var(--sp-3); color: ${selected ? "var(--gold-300)" : "var(--paper-300)"}; border: 1px solid ${selected ? "var(--gold-500)" : "var(--ink-600)"}; border-radius: var(--radius-sm); opacity: ${item.selectable ? 1 : 0.45};`,
    },
    [
      h("span", { style: "width: calc(40px * var(--ui-scale)); height: calc(40px * var(--ui-scale));" }, [
        h(CodexEmblem, { name: item.selectable ? item.emblem : "unknown" }),
      ]),
      h("span", { style: "font-size: var(--text-xs);" }, item.label),
    ],
  );

const renderWall = (args) => ({
  setup() {
    const selectedId = ref(args.selectedId ?? null);
    return () =>
      h("div", { style: "width: calc(560px * var(--ui-scale)); margin: calc(24px * var(--ui-scale));" }, [
        h(
          TileWall,
          { ...args, selectedId: selectedId.value, onSelect: (id) => (selectedId.value = id) },
          { tile: tileFace },
        ),
      ]);
  },
});

export default {
  title: "World/TileWall",
  component: TileWall,
};

// Two groups, with a non-selectable placeholder in the first.
export const TwoGroups = {
  render: renderWall,
  args: {
    ariaLabel: "示範圖鑑",
    selectedId: "tile-2",
    groups: [
      {
        key: "first",
        label: "第一組",
        items: [
          { id: "tile-1", selectable: true, label: "甲", emblem: "combat" },
          { id: "tile-2", selectable: true, label: "乙", emblem: "spell" },
          { id: "tile-3", selectable: false, label: "未記錄", emblem: null },
        ],
      },
      {
        key: "second",
        label: "第二組",
        items: [
          { id: "tile-4", selectable: true, label: "丙", emblem: "explore" },
          { id: "tile-5", selectable: true, label: "丁", emblem: "guild" },
        ],
      },
    ],
  },
};
