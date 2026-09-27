import { h, onBeforeUnmount, onMounted, ref } from "vue";
import DialogueChoices from "../../components/DialogueChoices.vue";
import { dialogueViewModel } from "../../stores/dialogue-view.js";
import { overviewExits } from "../../composables/use-dialogue-choices.js";
import { DIALOGUE_PANEL_SAMPLE } from "../fixtures.js";
import { explorationPanelFixture, localMapFixture, overviewArgs } from "../fixtures/scene_overview.js";

// DialogueChoices: the conversation's choice list, centred over the stage
// once the session line is fully read (AVG stage design §8.2;
// webclient-dialogue-choices-overlay). One menu composite and one tab stop:
// ArrowUp / ArrowDown wrap, Home / End jump, Enter / Space activate, digits
// 1–N pick directly, and `↦ 移動…` swaps in the committed overview's exits
// (Escape or the back row returns). Every story binds the same derived
// shapes the live wiring passes: the picks through `dialogueViewModel`, the
// exits through the real `overviewMenu` sliced by its `exits` section.

const PICKS = dialogueViewModel(DIALOGUE_PANEL_SAMPLE).picks;

const ROOM = explorationPanelFixture({
  exits: [
    { ref: "east", label: "東", destination: "room:43" },
    { ref: "north", label: "北", destination: "room:44", enabled: false, reason: "門被鎖住了" },
    { ref: "gate", label: "渡口木棧", destination: "room:45" },
  ],
});
const LOCAL_MAP = localMapFixture([
  ["room:43", "西風酒館"],
  ["room:44", "北岸大道"],
  ["room:45", "霧骨渡口"],
]);
const EXITS = overviewExits(overviewArgs(ROOM).menu);

// The list sits in a box the size of the `choices` anchor's span at
// 1920×1080 (560px wide), over a dim stage-like ground, and takes focus on
// mount the way the shell hands it focus.
const stageBox = (story) => ({
  render: () =>
    h(
      "div",
      {
        style: {
          width: "560px",
          height: "656px",
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

const renderList = (args) => ({
  setup() {
    const list = ref(null);
    onMounted(() => {
      list.value?.focus();
      if (args.openExits) {
        list.value?.$el?.querySelector('[data-testid="dialogue-move"]')?.click();
      }
    });
    return () => h(DialogueChoices, { ...args, ref: list });
  },
});

export default {
  title: "Core/DialogueChoices",
  component: DialogueChoices,
  decorators: [stageBox],
  parameters: {
    docs: {
      description: {
        component:
          "The dialogue choice list: one pick row per committed choice with " +
          "its digit badge, then `⌨ 自由對話`, `↦ 移動…`, and `✕ 結束對話`. " +
          "The active row carries the muted-gold fill and the leading `▸`. " +
          "`↦ 移動…` swaps in the committed overview's exits (direction glyph " +
          "and destination; a locked exit keeps its reason) and a back row. " +
          "Emits `pick(row)`, `freeform()`, `move(item)`, and `leave()` after " +
          "calling `beforeActivate`.",
      },
    },
  },
};

// Four picks and the three trailing rows.
export const Picks = {
  render: renderList,
  args: { picks: PICKS, exits: EXITS, localMap: LOCAL_MAP },
};

// A conversation with no scripted choices: only the trailing rows.
export const NoPicks = {
  render: renderList,
  args: { picks: [], exits: EXITS, localMap: LOCAL_MAP },
};

// `↦ 移動…` activated: the exits with their glyphs and destinations, the
// back row last.
export const MoveExits = {
  render: renderList,
  args: { picks: PICKS, exits: EXITS, localMap: LOCAL_MAP, openExits: true },
};

// The exits view with the locked exit active: its reason under the label,
// the dashed badge, and no gold fill.
export const DisabledExit = {
  render: (args) => ({
    setup() {
      const list = ref(null);
      onMounted(() => {
        const el = list.value?.$el;
        list.value?.focus();
        el?.querySelector('[data-testid="dialogue-move"]')?.click();
        el?.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: true }));
      });
      return () => h(DialogueChoices, { ...args, ref: list });
    },
  }),
  args: { picks: PICKS, exits: EXITS, localMap: LOCAL_MAP },
};

// More rows than the span holds (a short stage): the rows scroll inside the
// card while its frame stays put.
export const Overflowing = {
  render: renderList,
  args: {
    picks: dialogueViewModel({
      ...DIALOGUE_PANEL_SAMPLE,
      choices: [
        ...DIALOGUE_PANEL_SAMPLE.choices,
        { keyword_id: "river", label: "河上最近有沒有怪事？" },
        { keyword_id: "boat", label: "這條船還能撐幾趟？" },
        { keyword_id: "home", label: "妳在渡口待了多久？" },
        { keyword_id: "price", label: "五枚銅板是誰定的價？" },
        { keyword_id: "night", label: "夜裡也渡河嗎？" },
      ],
    }).picks,
    exits: EXITS,
    localMap: LOCAL_MAP,
  },
  decorators: [
    (story) => ({ render: () => h("div", { style: { height: "300px", display: "flex", flexDirection: "column" } }, [h(story())]) }),
  ],
};

// The entrance (webclient-mode-transitions): the card fades in and the rows
// fade and rise one stagger step apart. The list remounts every few seconds
// so the entrance replays; it takes focus and keys from its first frame.
export const Stagger = {
  render: (args) => ({
    setup() {
      const list = ref(null);
      const generation = ref(0);
      let timer = null;
      onMounted(() => {
        list.value?.focus();
        timer = setInterval(() => {
          generation.value += 1;
          requestAnimationFrame(() => list.value?.focus());
        }, 2600);
      });
      onBeforeUnmount(() => clearInterval(timer));
      return () => h(DialogueChoices, { ...args, key: generation.value, ref: list });
    },
  }),
  args: { picks: PICKS, exits: EXITS, localMap: LOCAL_MAP },
};
