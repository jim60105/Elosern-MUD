import { h } from "vue";
import TimeChoiceCard from "../../components/TimeChoiceCard.vue";
// The card frame (`choice-card`) is ChoiceCard's stylesheet; importing the
// component loads it, so the tiles render in their real frame here.
import "../../components/ChoiceCard.vue";
import { timeChoiceArgs } from "../fixtures/scene_overview.js";

// TimeChoiceCard (redesign-rest-entry design D4): the rest entry's first
// layer, opened by the place card's 休息 — two choice tiles, 1 等待 and
// 2 睡眠, each with a hint and one context line the client already holds
// (`現在 HH:MM`, `精力 N%（stage label）`), and a corner ✕. Props: timeLabel,
// fatigue, locked (both tiles aria-disabled with the one reason), entrance,
// autofocus, initialTile. Events: pick("wait" | "sleep") and close (the ✕ or
// Escape). The frame below is the stage's `choices` anchor width; `Narrow`
// narrows it below 320px, which stacks the tiles.

const renderIn = (width) => (args) => ({
  render: () =>
    h(
      "div",
      { style: `box-sizing:border-box;width:${width};display:flex;flex-direction:column;justify-content:center;padding:24px;` },
      [h(TimeChoiceCard, args)],
    ),
});

export default {
  title: "Core/TimeChoiceCard",
  component: TimeChoiceCard,
  argTypes: {
    onPick: { action: "pick" },
    onClose: { action: "close" },
  },
};

export const Default = {
  render: renderIn("min(560px, 40vw)"),
  args: timeChoiceArgs(),
};

// A mutation in flight: both tiles stay focusable but aria-disabled, and the
// one reason reads under them.
export const Locked = {
  render: renderIn("min(560px, 40vw)"),
  args: timeChoiceArgs({ locked: true }),
};

// The status panel carries no fatigue row for the controlled body: the 睡眠
// tile omits only its context line.
export const NoFatigueRow = {
  render: renderIn("min(560px, 40vw)"),
  args: timeChoiceArgs({ fatigue: false }),
};

// A narrow anchor (300px): the tiles stack, icon left, badge right.
export const Narrow = {
  render: renderIn("300px"),
  args: timeChoiceArgs(),
};
