import { h } from "vue";
import NarrativeFeed from "../../components/NarrativeFeed.vue";
import {
  MARKUP_STRESS_SAMPLE,
  NARRATIVE_SAMPLE,
} from "../fixtures.js";

// NarrativeFeed: the story centerpiece. Props: lines — the narrative log
// slice, [{ kind: "out" | "in" | "sys" | "err", text }]. No emitted events:
// scroll-keep and the unread marker are owned here (the marker's `jump`
// restores focus to the feed and clears the count). Server-transformed lines
// render through the preserved NarrativeMarkup allowlist pipeline (see the
// MarkupDegrade story); player input lines are literal text with a divider,
// never through the pipeline. No events emitted.

const renderFeed = (args) => ({ render: () => h(NarrativeFeed, args) });

// A bounded scroll area so the feed's scroll-keep/unread behavior is
// exercisable in the preview. Storybook 8 vue3 decorators are
// `(update, context) => story`: `update()` renders the inner story, which is
// then wrapped.
const renderBounded = (update) => {
  const inner = update();
  return {
    render: () =>
      h(
        "div",
        {
          style:
            "height: 420px; border: 1px solid var(--ink-700); border-radius: 12px; overflow: hidden;",
        },
        [h(inner)],
      ),
  };
};

export default {
  title: "Core/NarrativeFeed",
  component: NarrativeFeed,
  decorators: [renderBounded],
  parameters: {
    docs: {
      description: {
        component:
          "Server lines go through the allowlist markup pipeline; the " +
          "`in` kind renders a literal `.inp` line plus divider. Lines " +
          "landing while the reader is not at the bottom count into the " +
          "UnreadIndicator instead of auto-scrolling.",
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
