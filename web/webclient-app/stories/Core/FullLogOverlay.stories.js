import { h, nextTick, onMounted, ref } from "vue";
import FullLogOverlay from "../../components/FullLogOverlay.vue";
import { NARRATIVE_SAMPLE } from "../fixtures.js";

// FullLogOverlay (H1, webclient-hud-01-shell-and-scene, design D4;
// webclient-full-log-frame): the scrollable view of the complete retained
// narrative in the shared reference frame. It renders the same line stream
// through the preserved `narrative-renderer.js` (one markup path), styles
// each input echo in place as its response's heading, traps focus while
// open, closes on Escape, and restores focus to the opener. While the reader
// is above the end, the footer offers 回到最新 (with 新內容 once a line has
// arrived).

// A long session: several responses with an aside, an error line and a
// box-drawing map wider than the reading column.
const WIDE_MAP = [
  "┌────────┬────────┬────────┬────────┬────────┬────────┬────────┬────────┐",
  "│北門哨塔│石階步道│冒險公會│中央廣場│  鐘樓  │市集東口│ 港務局 │灰河碼頭│",
  "└────────┴────────┴────────┴────────┴────────┴────────┴────────┴────────┘",
].join("\n");

function longSession() {
  const lines = [
    { kind: "out", text: "你站在冒險者公會大廳的門口，晨霧還沒散去，櫃檯後的書記正在整理昨夜送來的委託單。" },
  ];
  const commands = ["look", "移動 中央廣場", "交談 書記", "look", "地圖", "移動 灰河碼頭", "look"];
  commands.forEach((command, index) => {
    lines.push({ kind: "in", text: command });
    lines.push({
      kind: "out",
      text:
        "鐘樓敲過第七聲，河面的霧氣沿著石階慢慢爬上廣場，攤販把帆布掀開，" +
        "一股烤栗子的甜味混著潮濕的木頭氣息飄了過來。遠處有人吆喝著新到的貨。",
    });
    if (index === 1) lines.push({ kind: "sys", text: "（系統）你獲得了 12 枚銅幣。" });
    if (index === 2) lines.push({ kind: "err", text: "你無法往那個方向走。" });
    if (index === 4) lines.push({ kind: "out", text: WIDE_MAP });
    lines.push({ kind: "out", text: "書記抬起頭：「今天也來接委託嗎？任務板上新貼了三張單子。」" });
  });
  return lines.map((line, index) => ({ ...line, seq: index + 1 }));
}

// Opens the log the way the client does (focusSelf: trapped focus, scrolled
// to the latest line). `review` then scrolls to the top and lets one line
// arrive, the state in which 回到最新 carries its 新內容 cue.
const renderOverlay = (args) => ({
  setup() {
    const overlay = ref(null);
    const lines = ref(args.lines);
    onMounted(async () => {
      await nextTick();
      overlay.value?.focusSelf();
      if (args.review) {
        const scroll = document.querySelector('[data-testid="fulllog-scroll"]');
        if (scroll) scroll.scrollTop = 0;
        lines.value = [
          ...lines.value,
          { seq: lines.value.length + 1, kind: "out", text: "一陣急促的鐘聲從港口傳來。" },
        ];
      }
    });
    return () =>
      h("div", { style: "position: relative; min-height: 100vh; background: var(--ink-950);" }, [
        h(FullLogOverlay, { ref: overlay, lines: lines.value, onClose: () => {} }),
      ]);
  },
});

export default {
  title: "Core/FullLogOverlay",
  component: FullLogOverlay,
  parameters: {
    layout: "fullscreen",
    docs: {
      description: {
        component:
          "The complete retained narrative, reachable in one action from the " +
          "message window's `日誌` control, in the shared reference frame. " +
          "Scrollable, focus-trapped, Escape-closing, with focus restored to " +
          "the opener and a 回到最新 control while the reader is above the end.",
      },
    },
  },
};

export const FullLog = {
  render: renderOverlay,
  args: { lines: NARRATIVE_SAMPLE },
};

export const LongSession = {
  render: renderOverlay,
  args: { lines: longSession() },
};

export const ReviewingEarlier = {
  render: renderOverlay,
  args: { lines: longSession(), review: true },
};
