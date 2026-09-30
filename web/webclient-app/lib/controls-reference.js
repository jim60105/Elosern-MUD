// Controls reference (H5, webclient-hud-05-overlays-and-command-line,
// task 6.6; localized by webclient-zh-tw-copy-and-labels): the client's own
// key and command reference, rendered as the help overlay's body. This is
// the single client-owned source of truth for what the client binds; the
// help overlay renders only what the client implements — no authored
// game-help content, no placeholders. The game's own `help` command output
// is reached by typing `help` into the command field (the client knows this
// path, and states it).
//
// Every row names a binding the code implements (AppShell `/` and ⌨,
// CommandLine, the dock's keyboard router and digit picks, MessageWindow,
// FullLogOverlay, DialogueChoices). `keys` are literal key names shown as key
// caps; `id` is the stable hook for the row.
export const CONTROLS_REFERENCE = [
  {
    id: "command-line",
    title: "指令列",
    entries: [
      {
        id: "slash",
        keys: ["/"],
        label: "展開指令列",
        detail: "在輸入欄以外按下，展開收合中的指令列並聚焦輸入欄；不會輸入斜線。",
      },
      {
        id: "keyboard-toggle",
        keys: ["⌨"],
        label: "切換指令列",
        detail: "訊息視窗右下角的 ⌨ 按鈕展開指令列並聚焦輸入欄；指令列已展開時再按一次則收合。",
      },
      {
        id: "send",
        keys: ["Enter"],
        label: "送出指令",
        detail:
          "唯一的送出方式；送出成功後指令列收合，焦點回到指令面板（對話中回到選項清單）。Shift+Enter 換行而不送出。",
      },
      {
        id: "history",
        keys: ["↑", "↓"],
        label: "瀏覽指令紀錄",
        detail: "在輸入欄中往前或往後瀏覽送出過的指令，尚未送出的草稿會保留。",
      },
      {
        id: "complete",
        keys: ["Tab"],
        label: "補全指令",
        detail:
          "依指令紀錄與房間的出口、對象補全草稿；多個候選時連按循環（Shift+Tab 反向），焦點不會離開輸入欄。",
      },
      {
        id: "collapse",
        keys: ["Esc"],
        label: "收合指令列",
        detail: "輸入欄有焦點時收合指令列，草稿保留到下次展開。",
      },
    ],
  },
  {
    id: "dock",
    title: "指令面板",
    entries: [
      {
        id: "arrows",
        keys: ["↑", "↓", "←", "→"],
        label: "移動焦點",
        detail:
          "探索時 ← → 依閱讀順序移動，↑ ↓ 移到上一列或下一列的相同位置；戰鬥指令為單欄清單，↑ ↓ 循環移動；範圍目標的格狀清單四個方向都能移動。",
      },
      {
        id: "digits",
        keys: ["1", "…", "9"],
        label: "依位置執行",
        detail: "直接執行目前清單的第 1 至 9 項，效果與按 Enter 相同；超出項目數的數字不作用。",
      },
      {
        id: "confirm",
        keys: ["Enter"],
        label: "執行",
        detail: "執行焦點所在的項目；停用的項目只顯示原因。",
      },
      {
        id: "space",
        keys: ["Space"],
        label: "勾選範圍目標",
        detail: "戰鬥中選擇範圍技能的目標時，勾選或取消焦點所在的對象。",
      },
      {
        id: "escape",
        keys: ["Esc"],
        label: "返回",
        detail: "由上而下關閉最上層：浮層 → 抽屜 → 指令列 → 指令面板的上一層。",
      },
    ],
  },
  {
    id: "reading",
    title: "閱讀與對話",
    entries: [
      {
        id: "page",
        keys: ["Enter", "Space"],
        label: "翻頁",
        detail: "訊息視窗有焦點時，先顯示正在打字的整頁，再按一次翻到下一頁；點擊訊息視窗也可以（選取文字時除外）。",
      },
      {
        id: "log",
        keys: ["日誌"],
        label: "開啟完整日誌",
        detail:
          "按下日誌，或在訊息視窗頂端繼續往上捲動，開啟停在最新一行的完整日誌；其中 ↑ ↓、PageUp、PageDown 捲動，Home 到最早、End 回到最新，Esc 關閉。",
      },
      {
        id: "choices",
        keys: ["↑", "↓", "1", "…", "9"],
        label: "對話選項",
        detail:
          "選項清單中 ↑ ↓ 循環移動、Home 與 End 跳到頭尾，數字鍵選擇對應編號，Enter 或 Space 選定；在「↦ 移動…」的出口中按 Esc 回到選項。",
      },
    ],
  },
];

// The single line stating how the game's own help output is reached (task
// 6.6: one line, not a placeholder for the absent authored guide). The
// command is literal command syntax and renders as code.
export const GAME_HELP_PATH = Object.freeze({
  before: "在指令列輸入 ",
  command: "help",
  after: "，即可查看遊戲內建的說明。",
});

export function controlsReferenceSection() {
  return {
    sections: CONTROLS_REFERENCE,
    gameHelpPath: GAME_HELP_PATH,
  };
}
