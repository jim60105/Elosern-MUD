import { h, onMounted, ref } from "vue";
import MessageWindow from "../../components/MessageWindow.vue";
import { dialogueViewModel } from "../../stores/dialogue-view.js";

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
  "│ · │ · │ · │ · │ · │",
  "├───┼───┼───┼───┼───┤",
  "│ · │ @ │ · │ # │ · │",
  "├───┼───┼───┼───┼───┤",
  "│ · │ · │ · │ · │ · │",
  "├───┼───┼───┼───┼───┤",
  "│ # │ · │ · │ · │ · │",
  "├───┼───┼───┼───┼───┤",
  "│ · │ · │ ~ │ ~ │ · │",
  "├───┼───┼───┼───┼───┤",
  "│ · │ · │ ~ │ ~ │ · │",
  "├───┼───┼───┼───┼───┤",
  "│ · │ · │ · │ · │ · │",
  "├───┼───┼───┼───┼───┤",
  "│ · │ # │ · │ · │ · │",
  "└───┴───┴───┴───┴───┘",
].join("<br>");

// The band message region at the reference size.
const bandRegion = (story) => ({
  render: () =>
    h(
      "div",
      {
        style: {
          position: "relative",
          width: "1280px",
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
    reducedMotion: { control: "inline-radio", options: [null, "on", "off"] },
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
          "region announces each page once. In dialogue mode the window shows " +
          "the dialogue box and its pick rows, unpaged. Pages type in at the " +
          "reader's `textSpeed` (the unrevealed tail keeps its place " +
          "invisibly); a click or Enter while typing shows the page in full. " +
          "Opt-in `autoAdvance` turns a fully shown page after 1.2s + 60ms per " +
          "character, never past the last page; `held` pauses the wait; " +
          "reduced motion shows pages at once.",
      },
    },
  },
};

// A short response: one page, already read (■).
export const SinglePage = {
  render: renderWindow,
  args: { lines: ARRIVAL, marks: [], textSpeed: "instant" },
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

// The dialogue variant: the dialogue box, the numbered picks, the free
// dialogue and exit rows, unpaged. The view model is built from the panel
// form exactly as AppClient does.
const DIALOGUE_PANEL = {
  schema_version: 1,
  available: true,
  kind: "dialogue",
  host: { identity: 41, display_name: "灰婆婆", portrait_ref: null },
  bond_stage: "親睦",
  line: "「渡河要五枚銅板，多一子我也不走。」她瞥了你一眼，「倒是你，身上聞起來有點……不對味。」",
  choices: [
    { keyword_id: "fare", label: "「就五枚，走嗎？」" },
    { keyword_id: "smell", label: "含糊帶過氣味" },
    { keyword_id: "chest", label: "直接問箱櫃下落" },
    { keyword_id: "silence", label: "保持沉默，觀察她下一步" },
  ],
};

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
