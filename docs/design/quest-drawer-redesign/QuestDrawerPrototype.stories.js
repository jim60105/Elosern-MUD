// Approved visual prototype of the quest drawer redesign
// (docs/superpowers/specs/2026-10-09-quest-drawer-redesign-design.md).
// Reference only: self-contained mock data, not wired to any payload.
import { h } from "vue";
import QuestDrawerPrototype from "./QuestDrawerPrototype.vue";

const frame = (args) => ({
  render: () =>
    h(
      "div",
      {
        style: [
          "position: fixed; inset: 0;",
          "background: linear-gradient(rgba(5,6,8,.72), rgba(5,6,8,.82)), url(/art/showcase/sample-guild.webp) center/cover;",
          "padding: calc(60px * var(--ui-scale)) calc(16px * var(--ui-scale)) calc(16px * var(--ui-scale));",
          "box-sizing: border-box;",
        ].join(""),
      },
      [h(QuestDrawerPrototype, args)],
    ),
});

export default { title: "Design/QuestDrawerRedesign" };

export const QuestBook = { render: frame, args: { initialTab: "book", atCounter: true } };
export const GuildBoard = { render: frame, args: { initialTab: "counter", atCounter: true } };
export const AwayFromCounter = { render: frame, args: { initialTab: "book", atCounter: false } };
