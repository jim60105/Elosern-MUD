import { h } from "vue";
import UnreadIndicator from "../../components/UnreadIndicator.vue";

// UnreadIndicator: the narrative feed's unread marker. Props: count.
// Events: jump — the owning feed scrolls to the latest line, moves focus to
// the narrative pane first, and clears the count. The `#narrative-unread`
// live region (role=status, polite, atomic) and the `.narrative-unread-button`
// control with `data-count` are preserved DOM contract; the wrapper hides
// entirely at count 0 (no empty pill).

const renderIndicator = (args) => ({ render: () => h(UnreadIndicator, args) });

export default {
  title: "Core/UnreadIndicator",
  component: UnreadIndicator,
  decorators: [
    (Story) => ({
      render: () =>
        h(
          "div",
          {
            style:
              "height: 320px; overflow-y: auto; border: 1px solid var(--ink-700); border-radius: 12px; padding: 12px;",
          },
          [
            h(Story),
            ...Array.from({ length: 24 }, (_, i) =>
              h("p", { style: "font-family: var(--f-serif); color: var(--paper-300);" }, `敘事行 ${i + 1} — 夜霧在石板路上流動。`),
            ),
          ],
        ),
    }),
  ],
};

export const UnreadLines = {
  render: renderIndicator,
  args: { count: 3 },
};

export const NoUnreadHidden = {
  render: renderIndicator,
  args: { count: 0 },
};
