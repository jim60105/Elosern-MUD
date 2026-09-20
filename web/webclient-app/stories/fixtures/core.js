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
  { kind: "err", text: "冷風颳過後頸——有什麼東西在暗處移動。" },
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

// Roster slice backing CharacterSwitcher (webclient-character-roster, MC5).
export const ROSTER_CHARACTERS_SAMPLE = [
  {
    identity: 1,
    name: "艾莉亞",
    current: true,
    pending: false,
    portrait: {
      subject_key: "char_1",
      status: "done",
      url: "/art/portraits/char_1.webp",
      aspect_ratio: "3/4",
      alt: "艾莉亞的肖像",
      placeholder: null,
      face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
    },
  },
  {
    identity: 2,
    name: "雷恩",
    current: false,
    pending: false,
    portrait: {
      subject_key: "char_2",
      status: "pending",
      url: null,
      aspect_ratio: "3/4",
      alt: "雷恩的肖像",
      placeholder: { kind: "generating", label: "肖像生成中" },
    },
  },
  {
    identity: 3,
    name: "新冒險者",
    current: false,
    pending: true,
    portrait: {
      subject_key: null,
      status: "missing",
      url: null,
      aspect_ratio: "3/4",
      alt: "新冒險者的肖像",
      placeholder: { kind: "silhouette", label: "建立中" },
    },
  },
];