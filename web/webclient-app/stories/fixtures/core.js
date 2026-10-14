import { fixtureDigest } from "./art_panels.js";

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
  timeLabel: "春季 3 日 ‧ 12:00",
};

export const PROMPT_SAMPLE = "<span class=\"color-111\">></span> ";

export const COMMAND_HISTORY_SAMPLE = ["look", "北", "talk 老周"];

// Roster slice backing CharacterSwitcher (webclient-character-roster, MC5).
// Each row's `portrait` IS the complete canonical artwork descriptor (change
// unified-portrait-image-contract): the retired flat field copy is gone.
export const ROSTER_CHARACTERS_SAMPLE = [
  {
    identity: 1,
    name: "艾莉亞",
    current: true,
    pending: false,
    portrait: {
      subject_id: "portrait:character:1",
      revision: fixtureDigest("roster-1"),
      generation_subject: "portrait:character:1",
      generation_state: "done",
      attempts: [
        {
          type: "image",
          source_id: "portrait.classic:portrait:character:1",
          rank: 40,
          resource: {
            resource_id: "portrait/character/char_1.webp",
            version: fixtureDigest("char-1"),
            url: "/art/portraits/char_1.webp",
            origin: "runtime",
            geometry: {
              image_size: null,
              face_rect: { x: 0.3, y: 0.1, w: 0.4, h: 0.4 },
              stage: { scale: 1, x: 0, y: 0 },
              aspect_ratio: "3/4",
            },
          },
        },
      ],
      terminal: null,
      retention_sources: [],
    },
  },
  {
    identity: 2,
    name: "雷恩",
    current: false,
    pending: false,
    portrait: {
      subject_id: "portrait:character:2",
      revision: fixtureDigest("roster-2"),
      generation_subject: "portrait:character:2",
      generation_state: "pending",
      attempts: [],
      terminal: null,
      retention_sources: [],
    },
  },
  {
    identity: 3,
    name: "新冒險者",
    current: false,
    pending: true,
    portrait: {
      subject_id: "3",
      revision: fixtureDigest("roster-3"),
      generation_subject: null,
      generation_state: null,
      attempts: [],
      terminal: null,
      retention_sources: [],
    },
  },
];