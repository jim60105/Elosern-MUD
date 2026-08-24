import { h } from "vue";
import NarrativeFeed from "../../components/NarrativeFeed.vue";
import {
  MARKUP_STRESS_SAMPLE,
  NARRATIVE_SAMPLE,
} from "../fixtures.js";

// NarrativeFeed: the bounded story centerpiece (H1, webclient-hud-01-shell-
// and-scene, design D4): the narrative is a bounded caption card
// (`width:min(880px,90vw)`, `max-height:30vh`) with the `#narrative-unread`
// indicator, its polite live region, the jump-to-latest behaviour, and a
// single labelled `完整日誌` control that opens the full-log surface. Server-
// transformed lines render through the preserved NarrativeMarkup allowlist
// pipeline; player input lines are literal text with a divider, never
// through the pipeline.
const renderFeed = (args) => ({ render: () => h(NarrativeFeed, args) });

// A bounded caption area so the card's bounded height and the full-log
// control are exercisable in the preview.
const renderBounded = (update) => {
  const inner = update();
  return {
    render: () =>
      h(
        "div",
        {
          style:
            "width: min(880px, 90vw); max-height: 30vh; overflow: hidden;",
        },
        [h(inner)],
      ),
  };
};

// A deterministic long narrative (40 lines) for the overflow and unread
// stories: the caption card scrolls internally within its bounded height.
const OVERFLOW_LINES = Array.from({ length: 40 }, (_, i) => ({
  kind: i % 7 === 0 ? "sys" : "out",
  text: i % 5 === 0 ? `（系統）第 ${i + 1} 段敘事。` : `河畔的霧氣逐漸散開，第 ${i + 1} 行。`,
}));

export default {
  title: "Core/NarrativeFeed",
  component: NarrativeFeed,
  decorators: [renderBounded],
  parameters: {
    docs: {
      description: {
        component:
          "The bounded narrative caption card: server lines through the " +
          "allowlist pipeline, `.inp` lines as literal text with a divider. " +
          "The card carries the `#narrative-unread` live region and a " +
          "`完整日誌` control that opens the full-log surface (one action).",
      },
    },
  },
};

export const WorldNarrative = {
  render: renderFeed,
  args: { lines: NARRATIVE_SAMPLE },
};

export const MarkupDegrade = {
  render: renderFeed,
  args: { lines: MARKUP_STRESS_SAMPLE },
};

export const EmptyFeed = {
  render: renderFeed,
  args: { lines: [] },
};

// The caption overflows its bounded height: the card scrolls internally and
// never grows to fill the stage (task 5.5).
export const Overflow = {
  render: renderFeed,
  args: { lines: OVERFLOW_LINES },
};

// With unread: the bounded card holds the unread indicator; scrolling away
// from the latest line counts new lines into the indicator (the live region
// announces them, exactly as before).
export const WithUnread = {
  render: renderFeed,
  args: { lines: OVERFLOW_LINES },
};
