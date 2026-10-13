import { h } from "vue";
import ChoiceCard from "../../components/ChoiceCard.vue";
import {
  AFFORDANCES,
  explorationPanelFixture,
  overflowCardArgs,
  suggestionsCardArgs,
  verbCardArgs,
  waitCardArgs,
} from "../fixtures/scene_overview.js";

// ChoiceCard: the one centred card shell (exploration-presence-rail design
// D1; scene overview redesign §4.2), extracted from the dialogue choice
// list. The frame, crest, and corner brackets; digit-badged rows and the
// hairline rule before the trailing `✕ 返回`; the active row's fill and
// caret; one tab stop (ArrowUp / ArrowDown wrap, Home / End, digits 1–N,
// Enter / Space, Escape emits back); the staggered entrance. Props: rows
// (each with an optional second `hint` line, and an optional `icon`: close,
// keyboard, or trash), notes (muted lines above the rows, never selectable),
// viewKey, trailingIndex, caption, ariaLabel, testId, entrance, escapeBack,
// digitRows, claimDigits, trapFocus, autofocus, block. Events: pick(key),
// back. Every story's rows come from the real exploration-menu builders
// through the shared derived-shape helpers.

const stageBox = (story) => ({
  render: () =>
    h(
      "div",
      {
        style: {
          width: "560px",
          height: "560px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          padding: "24px",
          background: "radial-gradient(80% 70% at 50% 40%, #2a2a33, #0b0d10)",
        },
      },
      [h(story())],
    ),
});

const render = (args) => ({ render: () => h(ChoiceCard, args) });

export default {
  title: "Core/ChoiceCard",
  component: ChoiceCard,
  decorators: [stageBox],
};

const GUILD_HALL = explorationPanelFixture({
  targets: [
    {
      identity: 11,
      name: "葛里安‧衛登",
      affordances: [
        AFFORDANCES.talk,
        AFFORDANCES.guild,
        AFFORDANCES.trade,
        { ...AFFORDANCES.engage, enabled: false, disabled_reason: { code: "safe_zone", message: "公會大廳裡不能動手。" } },
      ],
    },
  ],
  entities: [21, 22, 23, 24].map((identity, i) => ({ identity, name: ["旅人艾拉", "吟遊詩人", "鐵匠學徒", "信差"][i] })),
  objects: [
    { identity: 31, name: "任務板" },
    { identity: 32, name: "壁爐" },
  ],
});

// A guild clerk's verb card: 交談, 公會服務, 交易, a disabled 戰鬥 with its
// server-authored reason, 查看, then `✕ 返回`.
export const Verbs = {
  render,
  args: { ...verbCardArgs(GUILD_HALL, 11), autofocus: true, trapFocus: true },
};

// The wait menu on the card: 等待直到黎明, 睡眠至完全恢復, 休息 N 小時.
export const Wait = {
  render,
  args: { ...waitCardArgs(), autofocus: true, trapFocus: true },
};

// The wait card while another action is in flight: every row disabled with
// one reason.
export const WaitLocked = {
  render,
  args: { ...waitCardArgs({ locked: true }), autofocus: true, trapFocus: true },
};

// The suggestions card: the ready cards (one with its hint), 清除建議 with its
// trash-can badge, then `✕ 返回`.
export const Suggestions = {
  render,
  args: {
    ...suggestionsCardArgs({
      status: "ready",
      cards: [
        { kind: "known_action", label: "查看任務板", action_code: "explore.look", params: { target_id: 31 } },
        {
          kind: "known_action",
          label: "等到天亮再出發",
          action_code: "explore.wait",
          params: { daypart: "dawn" },
          hint: "夜裡的北岸大道不太平。",
        },
        { kind: "freeform", label: "問問葛里安最近的委託", action_code: "explore.talk_freeform", params: { npc_id: 11 } },
      ],
    }),
    autofocus: true,
    trapFocus: true,
  },
};

// The suggestions card while the AI composes: the muted note, no card row.
export const SuggestionsGenerating = {
  render,
  args: { ...suggestionsCardArgs({ status: "generating" }), autofocus: true, trapFocus: true },
};

// The AI offline with no rule card: the unavailable note and the empty line.
export const SuggestionsDegradedEmpty = {
  render,
  args: { ...suggestionsCardArgs({ status: "degraded", cards: [] }), autofocus: true, trapFocus: true },
};

// The presence overflow card: the entries the rail folded into `＋2`, the
// objects marked ◇.
export const Overflow = {
  render,
  args: { ...overflowCardArgs(GUILD_HALL), autofocus: true, trapFocus: true },
};
