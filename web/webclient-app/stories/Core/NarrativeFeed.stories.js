import { h } from "vue";
import NarrativeFeed from "../../components/NarrativeFeed.vue";
import { dialogueViewModel } from "../../stores/dialogue-view.js";
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

export const CombatMode = {
  render: renderFeed,
  args: {
    mode: "combat",
    lines: [
      { kind: "out", text: "你與蕾娜、幽 被三隻霧骨狼包圍。先攻 你 17 → 狼群 12。" },
      { kind: "out", text: "第一頭從側翼竄出——它的眼睛在霧裡燃著幽藍的火。" },
      { kind: "sys", text: "你有 2 個可用技能，背包 1 瓶煙霧彈。" },
    ],
  },
};

export const SemanticLines = {
  render: renderFeed,
  args: {
    mode: "exploration",
    lines: [
      { kind: "out", text: "晨霧貼著灰河的水面爬行，渡口的木棧浸在冷水裡。" },
      { kind: "sys", text: "渡口有 1 名可互動的人物，並察覺到 1 處可疑痕跡。" },
    ],
  },
};

// The dialogue variant (webclient-align-08-dialogue-surface): the `.dlg` box
// (avatar / gold speaker line with the bond stage / serif reply) over the
// numbered picks and the trailing free-dialogue row, with the head reading
// `對話` and no full-log capsule. The view model is the ONE derived shape over
// the committed panel — the story builds it from the panel form, exactly as
// AppClient does.
const DIALOGUE_PANEL = {
  schema_version: 1,
  available: true,
  kind: "dialogue",
  host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
  bond_stage: "親睦",
  line: "「渡河要五枚銅板，多一子我也不走。」她瞥了你一眼，「倒是你，身上聞起來有點……不對味。別是背著什麼臟東西吧？」",
  choices: [
    { keyword_id: "fare", label: "「就五枚，走嗎？」" },
    { keyword_id: "smell", label: "含糊帶過氣味" },
    { keyword_id: "chest", label: "直接問箱櫃下落" },
    { keyword_id: "silence", label: "保持沉默，觀察她下一步" },
  ],
};

export const DialogueMode = {
  render: renderFeed,
  args: {
    mode: "dialogue",
    dialogue: dialogueViewModel(DIALOGUE_PANEL),
    lines: [
      { kind: "out", text: "晨霧貼著灰河的水面爬行，渡口的木棧浸在冷水裡。" },
      { kind: "sys", text: "渡口有 1 名可互動的人物，並察覺到 1 處可疑痕跡。" },
    ],
  },
};
