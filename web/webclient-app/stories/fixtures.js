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

// ---------------------------------------------------------------------------
// B2 action-dock family fixtures (webclient-vue-03-showcase-action).
//
// Every value mirrors a validated `context_actions` v5 slice — the exact
// server-authored shapes (the v5 exploration form's action/navigation
// affordances and the suggestions envelope) — so the offline showcase and
// the live (C1 store) views cannot drift. Fixed literals only.
// ---------------------------------------------------------------------------

// v5 exploration-form action + navigation affordances, one bounded frame:
// enabled and disabled action entries (disabled_reason carries the
// server-authored note) and a local navigation surface.
export const EXPLORATION_AFFORDANCES_SAMPLE = [
  {
    action_id: "explore.move",
    label: "走往北岸大道",
    params: { exit_ref: "north", current_node: 42 },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  },
  {
    action_id: "explore.look",
    label: "觀察房間",
    params: { room: true },
    freeform: false,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  },
  {
    action_id: "explore.talk_freeform",
    label: "與灰婆婆自由交談",
    params: { npc_id: 9 },
    freeform: true,
    navigation: false,
    enabled: true,
    disabled_reason: null,
  },
  {
    action_id: "explore.wait",
    label: "等待",
    params: { daypart: "dusk" },
    freeform: false,
    navigation: false,
    enabled: false,
    disabled_reason: { code: "recovery", message: "正在調息，無法行動" },
  },
  {
    surface: "guild",
    label: "公會",
    navigation: true,
    enabled: true,
    disabled_reason: null,
  },
];

// A target selection frame (`target-<identity>` item keys) — the combat
// target menu shape: identity/display_name/state derived entries.
export const TARGET_ITEMS_SAMPLE = [
  { identity: "e1", label: "灰袍盜賊", enabled: true, disabled_reason: null },
  { identity: "e2", label: "斷刃巡衛", enabled: false, disabled_reason: { code: "down", message: "已倒地" } },
  { identity: "a2", label: "同行劍士", enabled: true, disabled_reason: null },
];

// v5 suggestions envelope, one per stream status (ready 3..5 cards,
// degraded 0..5 cards; label is 1..24 code points with at least one CJK
// character; hint is at most 60 code points or absent).
export const SUGGESTIONS_GENERATING_SAMPLE = { status: "generating" };

export const SUGGESTIONS_READY_SAMPLE = {
  status: "ready",
  cards: [
    {
      kind: "known_action",
      action_code: "explore.look",
      label: "查看房間",
      params: { room: true },
    },
    {
      kind: "known_action",
      action_code: "explore.wait",
      label: "等到黃昏",
      params: { daypart: "dusk" },
      hint: "先休息一會兒再行動",
    },
    {
      kind: "known_action",
      action_code: "explore.talk_scripted",
      label: "與灰婆婆交談",
      params: { npc_id: 7, keyword_id: "問候" },
    },
    {
      kind: "freeform",
      action_code: "explore.talk_freeform",
      label: "我們聊聊好嗎？",
      params: { npc_id: 9 },
      hint: "說任何想說的話",
    },
  ],
};

export const SUGGESTIONS_DEGRADED_EMPTY_SAMPLE = {
  status: "degraded",
  cards: [],
};

export const SUGGESTIONS_UNAVAILABLE_SAMPLE = { status: "unavailable" };
