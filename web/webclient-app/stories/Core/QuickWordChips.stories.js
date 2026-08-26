import { h } from "vue";
import QuickWordChips from "../../components/QuickWordChips.vue";

// QuickWordChips (H5, task 4.4): deterministic offline stories for the
// exploration chip set and the combat chip set. The mode gating CSS lives at
// the stage root, so each story wraps the chips in an `.elosern-stage` div
// carrying the matching `data-elosern-mode` attribute.

const renderChips = (args) => ({
  render: () =>
    h("div", { class: "elosern-stage", "data-elosern-mode": args.mode }, [
      h("div", { style: "padding: 8px; font-family: var(--f-mono); color: var(--paper-500); font-size: 13px;" }, "（上方為指令列快捷詞）"),
      h(QuickWordChips, args),
    ]),
});

export default {
  title: "Core/QuickWordChips",
  component: QuickWordChips,
};

export const ExplorationSet = {
  render: renderChips,
  args: { mode: "exploration" },
};

export const CombatSet = {
  render: renderChips,
  args: { mode: "combat" },
};

export const CreationSet = {
  render: renderChips,
  args: { mode: "creation" },
};
