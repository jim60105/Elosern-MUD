import { h, onMounted, ref } from "vue";
import MessageWindow from "../../components/MessageWindow.vue";
import FullLogOverlay from "../../components/FullLogOverlay.vue";
import { dialogueViewModel } from "../../stores/dialogue-view.js";
import { DIALOGUE_PANEL_SAMPLE } from "../fixtures.js";

// MessageWindow: the AVG message window (AVG stage design §6;
// webclient-message-window-component). The stories render inside a box the
// size of the band's message region at 1920×1080 (1280×300, the band's
// gradient and the region's padding), with the real DOM measurer, so every
// page shown here is cut by real layout. A decorative ⌨ in the corner marks
// where the shell's controls sit beside the marker.

// Narrative lines as the store keeps them: kind, text, and a monotonic seq.
function seqLines(start, entries) {
  return entries.map(([kind, text], index) => ({ kind, text, seq: start + index }));
}

const ARRIVAL = seqLines(1, [
  ["out", "晨霧貼著灰河的水面爬行，渡口的木棧浸在冷水裡。"],
  ["sys", "渡口有 1 名可互動的人物。"],
]);

const LOOK_ECHO = [["in", "look"]];

const LONG_LOOK = [
  [
    "out",
    "你環顧冒險者公會的大廳。橡木長桌上刻滿了歷代冒險者留下的名字與刀痕，壁爐裡的柴火劈啪作響，" +
      "把牆上那幅褪色的王國地圖映得忽明忽暗。櫃檯後方，一位戴著單片眼鏡的書記正低頭抄寫委託，" +
      "筆尖在羊皮紙上沙沙作響。<span class=\"color-011\">任務板</span>上釘著三張新貼的告示，其中一張蓋著鮮紅的封蠟，" +
      "邊角已經被好奇的手指摸得起毛。靠窗的角落，幾名傭兵壓低聲音交談，偶爾朝門口投去警覺的目光。" +
      "空氣裡混著麥酒、皮革與松脂的氣味，遠處的鐵匠鋪傳來規律的敲打聲，像是整座城市緩慢的心跳。" +
      "你注意到地板上有一道新鮮的泥痕，從後門一路延伸到樓梯底下，然後突兀地消失。",
  ],
  ["sys", "大廳裡有 3 名可互動的人物，並察覺到 1 處可疑痕跡。"],
];

const MAP_LINES = [
  "┌───┬───┬───┬───┬───┐",
  "│ ‧ │ ‧ │ ‧ │ ‧ │ ‧ │",
  "├───┼───┼───┼───┼───┤",
  "│ ‧ │ @ │ ‧ │ # │ ‧ │",
  "├───┼───┼───┼───┼───┤",
  "│ ‧ │ ‧ │ ‧ │ ‧ │ ‧ │",
  "├───┼───┼───┼───┼───┤",
  "│ # │ ‧ │ ‧ │ ‧ │ ‧ │",
  "├───┼───┼───┼───┼───┤",
  "│ ‧ │ ‧ │ ~ │ ~ │ ‧ │",
  "├───┼───┼───┼───┼───┤",
  "│ ‧ │ ‧ │ ~ │ ~ │ ‧ │",
  "├───┼───┼───┼───┼───┤",
  "│ ‧ │ ‧ │ ‧ │ ‧ │ ‧ │",
  "├───┼───┼───┼───┼───┤",
  "│ ‧ │ # │ ‧ │ ‧ │ ‧ │",
  "└───┴───┴───┴───┴───┘",
].join("<br>");

// The band message region at the reference size: the left two thirds of a
// 1920px band, or the whole band in dialogue mode, where the command region
// collapses (webclient-dialogue-stage-actors).
const bandRegion = (story, context) => ({
  render: () =>
    h(
      "div",
      {
        style: {
          position: "relative",
          width: context?.args?.mode === "dialogue" ? "1920px" : "1280px",
          maxWidth: "100vw",
          height: "300px",
          boxSizing: "border-box",
          padding: "10px 12px 12px 18px",
          background: "linear-gradient(0deg, #0c0a0e, #141019 70%, var(--panel))",
          borderTop: "var(--line)",
          boxShadow: "0 -14px 34px -24px #000",
        },
      },
      [
        h(story()),
        h(
          "span",
          {
            "aria-hidden": "true",
            style: {
              position: "absolute",
              right: "22px",
              bottom: "18px",
              width: "30px",
              height: "30px",
              boxSizing: "border-box",
              display: "grid",
              placeItems: "center",
              border: "var(--line)",
              borderRadius: "var(--radius-sm)",
              background: "var(--panel-solid)",
              color: "var(--paper-300)",
              font: "14px/1 var(--f-mono)",
            },
          },
          "⌨",
        ),
      ],
    ),
});

const renderWindow = (args) => ({ render: () => h(MessageWindow, args) });

export default {
  title: "Core/MessageWindow",
  component: MessageWindow,
  decorators: [bandRegion],
  argTypes: {
    textSpeed: { control: "inline-radio", options: ["slow", "normal", "fast", "instant"] },
    autoAdvance: { control: "boolean" },
    motionLevel: { control: "inline-radio", options: ["full", "reduced", "off"] },
    held: { control: "boolean" },
  },
  parameters: {
    docs: {
      description: {
        component:
          "The AVG message window: the current response one page at a time " +
          "(28px serif at 1080, at most 42 CJK characters per line), a blinking " +
          "`▼` while pages follow and `■` on the last page. A click advances " +
          "(not on a control, not with a text selection); Enter / Space advance " +
          "only while the page surface has focus and never reach the dock. " +
          "Scrolling up over the page emits `open-full-log`. A polite live " +
          "region announces each page once. In dialogue mode the window spans " +
          "the band and pages the session line like any response, under the " +
          "host's name plate, in a column starting under the player portrait; " +
          "it holds no choice row and emits `reading-change` (true once the " +
          "last page is fully shown). Pages type in at the " +
          "reader's `textSpeed` (the unrevealed tail keeps its place " +
          "invisibly); a click or Enter while typing shows the page in full. " +
          "Opt-in `autoAdvance` turns a fully shown page after 1.2s + 60ms per " +
          "character, never past the last page; `held` pauses the wait; " +
          "a motion level other than `full` shows pages at once.",
      },
    },
  },
};

// A short response: one page, already read (■).
export const SinglePage = {
  render: renderWindow,
  args: { lines: ARRIVAL, marks: [], textSpeed: "instant" },
};

// The same server-shaped markup through the real message and full-log
// renderers. No local palette or renderer duplicates the generated CSS.
const ANSI_PROSE = seqLines(1, [
  ["out", '<span class="color-001">紅封蠟</span>　<span class="color-009">爐火微光</span>　' +
    '<span class="color-002">苔蘚</span>　<span class="color-010">林間新葉</span><br>' +
    '<span class="color-003">舊羊皮紙</span>　<span class="color-011">金色徽記</span>　' +
    '<span class="color-004">暮色</span>　<span class="color-012">遠山</span><br>' +
    '<span class="color-005">紫布</span>　<span class="color-013">晚霞</span>　' +
    '<span class="color-006">河影</span>　<span class="color-014">晨霧</span><br>' +
    '<span class="color-232">石階陰影</span>　<span class="color-244">灰色路標</span>　' +
    '<span class="color-255">銀白月光</span>　<span class="color-011 blink">燈火</span>'],
]);

export const NarrativeTones = {
  render: (args) => ({
    setup() {
      const open = ref(false);
      const fullLog = ref(null);
      return () => [
        h(MessageWindow, { ...args, onOpenFullLog: () => { open.value = true; } }),
        h("button", {
          type: "button",
          style: "position: absolute; right: 60px; bottom: 18px;",
          onClick: () => { open.value = true; },
        }, "完整日誌"),
        open.value ? h(FullLogOverlay, {
          ref: fullLog,
          onVnodeMounted: () => fullLog.value?.focusSelf(),
          lines: args.lines,
          onClose: () => { open.value = false; },
        }) : null,
      ];
    },
  }),
  args: { lines: ANSI_PROSE, marks: [], textSpeed: "instant" },
  parameters: {
    docs: {
      description: {
        story: "Authored normal/bright ANSI pairs, grayscale and blink on the actual band gradient. " +
          "Open the full log to compare the same markup at normal text size. The 3:1 palette " +
          "floor is not a claim of 4.5:1 normal-text WCAG AA for every grayscale/cube entry.",
      },
    },
  },
};

// A long response that has just arrived: page 1 of several (▼). The window
// mounts on the last page of the earlier response; the new response then
// lands and opens on page 1, exactly as a live reply does.
export const MorePages = {
  render: (args) => ({
    setup() {
      const lines = ref(args.lines);
      const marks = ref(args.marks);
      onMounted(() => {
        setTimeout(() => {
          const echo = seqLines(lines.value.length + 1, LOOK_ECHO);
          const reply = seqLines(lines.value.length + 2, LONG_LOOK);
          lines.value = [...lines.value, ...echo, ...reply];
        }, 60);
      });
      return () => h(MessageWindow, { ...args, lines: lines.value, marks: marks.value });
    },
  }),
  args: { lines: ARRIVAL, marks: [], textSpeed: "instant" },
};

// A long reply arriving as a live one does and typing in at the normal
// speed: no marker until a page is fully shown; click to complete, click
// again to advance.
export const Typing = {
  render: MorePages.render,
  args: { lines: ARRIVAL, marks: [], textSpeed: "normal" },
};

// The same reply with auto-advance on at the fast speed: each fully shown
// page turns on its own and the window stops on the last page (■).
export const AutoAdvance = {
  render: MorePages.render,
  args: { lines: ARRIVAL, marks: [], textSpeed: "fast", autoAdvance: true },
};

// The same long response opened by a mount: the last page, fully read (■).
export const LastPage = {
  render: renderWindow,
  args: {
    lines: [...ARRIVAL, ...seqLines(3, LOOK_ECHO), ...seqLines(4, LONG_LOOK)],
    marks: [],
    textSpeed: "instant",
  },
};

// A refused action: the err line starts its own page in the seal colour.
export const ErrorPage = {
  render: renderWindow,
  args: {
    lines: [
      ...ARRIVAL,
      ...seqLines(3, [["in", "north"]]),
      ...seqLines(4, [["err", "北邊的門鎖著，你推不開。"]]),
    ],
    marks: [],
    textSpeed: "instant",
  },
};

// A box-drawing map taller than a page: its own oversize page that scrolls
// inside the surface; wheel-up at its top opens the full log.
export const OversizeMap = {
  render: renderWindow,
  args: {
    lines: [...seqLines(1, [["in", "map"]]), ...seqLines(2, [["out", MAP_LINES]])],
    marks: [],
    textSpeed: "instant",
  },
};

// CJK prose typesetting (webclient-message-typesetting): mixed scripts get
// a small CJK–Latin gap from `text-autospace` (spacing only, the text is
// unchanged), punctuation keeps strict line-break rules, and a box-drawing
// map between two prose lines keeps its grid — no inserted spacing. At full
// motion the `▼` bobs slowly; reduced and off keep it still.
const SMALL_MAP = ["┌───┬───┬───┐", "│ ‧ │ @ │ # │", "├───┼───┼───┤", "│ ~ │ ‧ │ ‧ │", "└───┴───┴───┘"].join("<br>");

const MIXED_REPLY = [
  [
    "out",
    "告示寫著：「徵求3名冒險者護送商隊前往Rivermouth，酬勞120枚銀幣，限E級以上。」" +
      "下方有人用炭筆補了一行小字：「小心North Gate附近的狼群（已有2人受傷）。」",
  ],
  ["out", SMALL_MAP],
  ["sys", "你記下了委託編號Q-042。"],
  ["out", "書記抬頭看了你一眼，推了推單片眼鏡：「要接的話，先到櫃檯登記。」"],
];

// The reply arrives live, as in MorePages, so the window opens on page 1.
export const MixedScripts = {
  render: (args) => ({
    setup() {
      const lines = ref(args.lines);
      onMounted(() => {
        setTimeout(() => {
          const echo = seqLines(lines.value.length + 1, [["in", "look board"]]);
          const reply = seqLines(lines.value.length + 2, MIXED_REPLY);
          lines.value = [...lines.value, ...echo, ...reply];
        }, 60);
      });
      return () => h(MessageWindow, { ...args, lines: lines.value });
    },
  }),
  args: { lines: ARRIVAL, marks: [], textSpeed: "instant" },
};

// A silent action is out and its reply has not arrived (the last mark is
// newer than the last line): the previous response stays, flushed to its
// last page.
export const PendingAction = {
  render: renderWindow,
  args: {
    lines: [...ARRIVAL, ...seqLines(3, LOOK_ECHO), ...seqLines(4, LONG_LOOK)],
    marks: [7],
    textSpeed: "instant",
  },
};

// Dialogue across the whole band (webclient-dialogue-choices-overlay D1):
// the host's name plate over the session line, paged and typed like any
// response, verbatim as the narrative delivered it. No row renders here:
// the choices are the centred list over the stage. The view model is built
// from the shared panel fixture exactly as AppClient does.
const DIALOGUE_PANEL = DIALOGUE_PANEL_SAMPLE;

export const Dialogue = {
  render: renderWindow,
  args: {
    mode: "dialogue",
    dialogue: dialogueViewModel(DIALOGUE_PANEL),
    lines: [
      ...ARRIVAL,
      ...seqLines(3, [["in", "talk 灰婆婆"]]),
      ...seqLines(4, [["out", `灰婆婆說：${DIALOGUE_PANEL.line}`]]),
    ],
    marks: [],
    textSpeed: "instant",
  },
};

// A combat round playing beat by beat (webclient-combat-beat-queue design D6):
// the window's pages are the round's beat pages — each beat paginated alone —
// followed by the response's own closing line. The round's event lines are
// replaced by the beats, never paged twice. The published slice paces them;
// the story stands in for the store by advancing `index` on each
// `beat-shown` and ending the round on `beat-skip`.
const COMBAT_ROUND = {
  round: "s-1/1",
  startSeq: 2,
  auto: true,
  index: 1,
  count: 3,
  phase: "text",
  texts: [
    "你擲出了骰子，命中判定為 14。",
    "你擊中了哥布林的肩膀，牠踉蹌後退。",
    "哥布林發出短促的嘶吼，舉起木棒。",
  ],
  coveredLines: 3,
  terminal: false,
};

const COMBAT_ROUND_LINES = seqLines(2, [
  ["in", "attack 哥布林"],
  ["out", "你擲出了骰子，命中判定為 14。"],
  ["out", "你擊中了哥布林的肩膀，牠踉蹌後退。"],
  ["out", "哥布林發出短促的嘶吼，舉起木棒。"],
  ["out", "行動完成，繼續戰鬥。"],
]);

// The story's stand-in for the store's playback: the next beat follows the
// beat pause, and a click on the window ends the round at once.
const renderCombatRound = (args) => ({
  setup() {
    const bound = ref({ ...COMBAT_ROUND });
    const show = (index) => {
      bound.value = {
        ...bound.value,
        index,
        phase: index < bound.value.count ? "text" : "done",
      };
    };
    return () =>
      h(MessageWindow, {
        ...args,
        beatPlayback: bound.value,
        onBeatShown: (index) => globalThis.setTimeout(() => show(index + 1), 400),
        onBeatSkip: () => show(bound.value.count),
      });
  },
});

export const CombatRound = {
  render: renderCombatRound,
  args: { lines: COMBAT_ROUND_LINES, marks: [], textSpeed: "instant" },
};

// The same round at `off`: presentation ends at once, the command panel is
// never held, and the beat pages are ordinary pages the reader turns.
export const CombatRoundOff = {
  render: renderCombatRound,
  args: {
    lines: COMBAT_ROUND_LINES,
    marks: [],
    textSpeed: "instant",
  },
  parameters: {
    docs: {
      description:
        "At the `off` motion level `--motion-beat` is 0ms and the published " +
        "round is already done, so the beat pages and the closing line are " +
        "ordinary pages: the marker renders, a click turns a page, and the " +
        "command panel is never held.",
    },
  },
};
