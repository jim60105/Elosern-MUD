// Approved-direction prototype of the place card's 等待 entry redesign: the
// first layer chooses 等待 or 睡眠 on two tiles, then the wait form (等待直到
// 黎明 or a duration) or the existing SleepForm opens under one header with
// ‹ 返回上一層 and ✕ 關閉. Reference only: mock data, not wired to any payload;
// the intents the real client would send are written to the log.
//
// Try it: 1 / 2 or the arrows on the tiles, Enter to open a form, Esc or ‹
// to step back, ✕ to close; the place card button reopens the tiles.
// Controls: `placeLabel` and `reserveTerm` try other wordings.
import { h } from "vue";
import TimeChoicePrototype from "./TimeChoicePrototype.vue";

const render = (args) => ({ render: () => h(TimeChoicePrototype, { ...args, key: JSON.stringify(args) }) });

export default { title: "Design/TimeChoiceRedesign", component: TimeChoicePrototype, render };

// The first layer as the place card button opens it.
export const Choice = { args: { initialStep: "choice" } };
// 等待 picked: the new wait form.
export const WaitForm = { args: { initialStep: "wait" } };
// 睡眠 picked: the existing SleepForm under the shared header.
export const SleepFormStep = { name: "Sleep Form", args: { initialStep: "sleep" } };
// A mutation in flight: both tiles disabled with the one reason.
export const Locked = { args: { initialStep: "choice", locked: true } };
// No fatigue row in the status panel: the sleep tile drops its context line.
export const NoFatigueData = { args: { initialStep: "choice", fatigue: null } };
// A narrow anchor: the tiles stack, still as tiles.
export const Narrow = { args: { initialStep: "choice", cardWidth: 300 } };
// Closed: start from the place card.
export const Closed = { args: { initialStep: "closed" } };
// The widest context line: a full reserve with its four-character stage.
export const FullReserve = { args: { initialStep: "choice", fatigue: { reserve_percent: 100, label: "精神充沛" } } };
