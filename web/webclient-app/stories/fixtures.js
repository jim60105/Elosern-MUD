// Deterministic offline fixtures for the core-family stories (B1). Every
// value mirrors a shape the C1 store getters will return for the same
// slice, so the offline showcase and the live views cannot drift. No live
// server, LLM, or imagegen data — fixed literals only.

export const NARRATIVE_SAMPLE = [
  { kind: "out", text: "你站在測試起點的石板廣場上，夜霧低垂，遠燈明滅。" },
  { kind: "sys", text: "—— 一則新的敘事 ——" },
  { kind: "in", text: "look" },
  {
    kind: "out",
    text:
      "<span class=\"color-033\">石板廣場</span> 夜色沉靜。" +
      "<span class=\"color-208 bgcolor-236\">霧燈</span> 在街角閃爍。",
  },
  { kind: "err", text: "冷風刮過後頸——有什麼東西在暗處移動。" },
  {
    kind: "out",
    text:
      "│  北面出口：石階  │\n" +
      "├────────────────┤\n" +
      "│  南門（wilderness）│",
  },
];

export const MARKUP_STRESS_SAMPLE = [
  {
    kind: "out",
    text:
      "<span style=\"color: #e06b6b;\">印章紅</span> 的提燈、" +
      "<span class=\"underline\">底線字樣</span>，" +
      "以及未被接受的字串 <div>原樣保留</div> 與 <i>斜體</i>。",
  },
  { kind: "out", text: "<br>換行測試：<br>第二行。" },
];

// Status/server-time slice backing the TopBar (status panel + serverTime).
export const STATUS_SLICE_SAMPLE = {
  connected: true,
  locationLabel: "測試起點",
  timeLabel: "春季 3 日 · 12:00",
};

export const PROMPT_SAMPLE = "<span class=\"color-111\">></span> ";

export const COMMAND_HISTORY_SAMPLE = ["look", "北", "talk 老周"];
