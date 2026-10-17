import { h } from "vue";
import QuestionCard from "../../components/QuestionCard.vue";
// The card frame (`choice-card`) is ChoiceCard's stylesheet; importing the
// component loads it, so the question renders in its real frame here.
import "../../components/ChoiceCard.vue";

// QuestionCard (exploration-room-actions design D5): the small modal yes/no
// question in the centred card frame — the wait card's 進入夢境協作？ before
// a sleep is sent. Props: question, yesLabel / noLabel, closeLabel (the ✕ at
// its top right), locked (a mutation in flight or awaiting its revision:
// 是 and 否 disabled, with `reason`), and entrance. Events: yes, no, close
// (the ✕ or Escape). Focus is trapped inside it and starts on `initialFocus`
// (是 by default). `tone="caution"` (with an optional `caption`) marks a
// think-twice question, and `noWhileLocked` keeps 否 answering under a lock. The frame
// below is the stage's `choices` anchor width.

const render = (args) => ({
  render: () =>
    h(
      "div",
      { style: "width:min(560px, 40vw);display:flex;flex-direction:column;justify-content:center;padding:24px;" },
      [h(QuestionCard, args)],
    ),
});

export default {
  title: "Core/QuestionCard",
  component: QuestionCard,
};

// The dream question as the wait card opens it.
export const DreamQuestion = {
  render,
  args: { question: "進入夢境協作？", closeLabel: "取消睡眠", testId: "dream-question" },
};

// Another action is still in flight: 是 and 否 wait, with the wait rows' reason.
export const Locked = {
  render,
  args: {
    question: "進入夢境協作？",
    closeLabel: "取消睡眠",
    locked: true,
    reason: "上一個行動尚未完成，請稍候。",
    testId: "dream-question",
  },
};

// A cast across sides (webclient-combat-cross-side-confirm): the caution
// tone, focus starting on the safe answer 否, which carries the primary fill.
export const SafeDefault = {
  render,
  args: {
    question: "確定要對友方使用〈基本攻擊〉？",
    caption: "跨陣營施展",
    tone: "caution",
    initialFocus: "no",
    noWhileLocked: true,
    closeLabel: "返回選擇目標",
    testId: "cross-side-question",
  },
};

// The same question while the previous action is still in flight: 是 waits
// with the reason, 否 and ✕ still answer.
export const SafeDefaultLocked = {
  render,
  args: { ...SafeDefault.args, question: "確定要對友方與敵方使用〈潮汐逆轉〉？", locked: true, reason: "上一個行動尚未完成，請稍候。" },
};
