// Deterministic, offline runtime-state fixtures for the GM stories
// (gm-portal-s3-runtime-state). Synthetic values only: no shipped catalog key
// or label appears here, and every payload has the exact wire shape the
// readers return, so a story shows the real component behaviour.
import { GmApiError } from "../lib/api.js";

export const NPC_DETAIL = {
  id: "12",
  kind: "npcs",
  label: "合成守衛",
  dbref: 12,
  typeclass: "typeclasses.npcs.NPC",
  sections: [
    {
      key: "identity",
      title: "身分",
      type: "ledger",
      rows: [
        { key: "名稱", label: "名稱", value: "合成守衛" },
        { key: "識別碼", label: "識別碼", value: "#12", mono: true, tone: "gold" },
        {
          key: "所在房間",
          label: "所在房間",
          value: "#3",
          mono: true,
          link: { kind: "rooms", id: "3", label: "合成廣場" },
        },
      ],
    },
    {
      key: "resources",
      title: "資源",
      type: "tiles",
      tiles: [
        { key: "hp", label: "生命", value: 180, unit: "/ 180" },
        { key: "mp", label: "魔力", value: 12, unit: "/ 40" },
        { key: "sp", label: "體力", value: 7, unit: "/ 60" },
      ],
    },
    {
      key: "services",
      title: "服務與職業",
      type: "table",
      columns: [
        { key: "component", label: "服務元件" },
        { key: "slot", label: "插槽", mono: true },
        { key: "fields", label: "欄位", mono: true },
      ],
      rows: [
        {
          key: "GuildStaff",
          cells: {
            component: { value: "公會櫃檯" },
            slot: { value: "t_guild_slot", mono: true },
            fields: { value: "service_id=t_service", mono: true },
          },
        },
        {
          key: "ScriptedDialogue",
          cells: {
            component: { value: "腳本對話" },
            slot: { value: "t_dialogue_slot", mono: true },
            fields: { value: "dialogue_key=t_dialogue", mono: true },
          },
        },
      ],
      empty_note: "此 NPC 目前沒有服務元件。",
    },
    {
      key: "persona",
      title: "人物設定",
      type: "groups",
      note: "版本 2（世代 1）",
      groups: [
        {
          key: "身分",
          title: "身分",
          rows: [
            { key: "公開身分", label: "公開身分", value: "渡口的記錄員" },
            { key: "隱秘身分", label: "隱秘身分", value: "曾為信差" },
          ],
        },
        { key: "外貌", title: "外貌", rows: [{ key: "外貌", label: "外貌", value: "穿著灰色短褂" }] },
      ],
    },
    {
      key: "links",
      title: "相關連結",
      type: "chips",
      chips: [
        { key: "room", label: "合成廣場", link: { kind: "rooms", id: "3", label: "合成廣場" } },
        { key: "quests", label: "任務紀錄", link: { kind: "quests", id: "owner:12", owner: "12" } },
        { key: "memories", label: "記憶", link: { kind: "memories", id: "owner:12", owner: "12" } },
        { key: "dialogue", label: "對話", link: { kind: "dialogue", id: "12", owner: "12" } },
      ],
    },
    {
      key: "memory_trace",
      title: "S2 證據連結",
      type: "ledger",
      rows: [
        {
          key: "call_id",
          label: "call_id",
          value: "ab".repeat(16),
          mono: true,
          link: { kind: "call", id: "ab".repeat(16) },
        },
        { key: "trace_id", label: "trace_id", value: "t_trace_1", mono: true },
      ],
    },
    {
      key: "wallet",
      title: "錢包",
      error: { code: "source_unavailable", message: "此區塊的來源目前不存在或無法使用。" },
    },
  ],
};

export const NPC_RAW = {
  id: "12",
  kind: "npcs",
  label: "合成守衛",
  dbref: 12,
  typeclass: "typeclasses.npcs.NPC",
  raw: {
    ref: { $ref: "#12", typeclass: "typeclasses.npcs.NPC", key: "合成守衛" },
    dbref: 12,
    key: "合成守衛",
    typeclass: "typeclasses.npcs.NPC",
    location: { $ref: "#3", typeclass: "typeclasses.rooms.Room", key: "合成廣場" },
    date_created: "2026-10-07T01:02:03",
    attributes: [
      { key: "t_count", category: "", value: 7 },
      { key: "t_flag", category: "", value: true },
      { key: "t_plain_note", category: "t_notes", value: "備註" },
      { key: "t_link", category: "", value: { $ref: "#3", typeclass: "typeclasses.rooms.Room", key: "合成廣場" } },
      { key: "t_marker", category: "t_notes", value: { $unserializable: "set", repr: "{'t_a', 't_b'}" } },
      { key: "t_slot::field", category: "", value: "合成欄位" },
    ],
    tags: [
      { key: "t_tagged", category: "t_category" },
      { key: "t_other", category: "" },
    ],
    components: [{ name: "t_guild_slot", fields: { service_id: "t_service" } }],
  },
};

export const ART_DETAIL = {
  id: "art:t_subject",
  kind: "art",
  label: "t_subject",
  dbref: null,
  typeclass: "",
  raw: { record: { status: "failed", attempt_count: 3, last_error_code: "art_sd_unavailable" } },
  sections: [
    {
      key: "identity",
      title: "身分",
      type: "ledger",
      rows: [
        { key: "記錄鍵", label: "記錄鍵", value: "art:t_subject", mono: true },
        { key: "狀態", label: "狀態", value: "failed", mono: true, tone: "warn" },
        { key: "縮圖", label: "縮圖", value: "沒有可用的檔案", mono: true },
      ],
    },
    { key: "prompt", title: "來源敘述", type: "text", text: "一頭在合成礁石上休息的合成禽鳥。" },
    { key: "gallery", title: "畫廊任務", type: "empty", note: "這不是畫廊任務記錄。" },
  ],
};

export const MEMORY_ITEMS = [
  {
    id: "31",
    kind: "memories",
    dbref: null,
    label: "t_source",
    owner: "12",
    fields: [
      { key: "類別", label: "類別", value: "observation", mono: true },
      { key: "層級", label: "層級", value: "working", mono: true },
      { key: "可用性", label: "可用性", value: "active", mono: true },
      { key: "知識範圍", label: "知識範圍", value: "witnessed", mono: true },
      { key: "顯著度", label: "顯著度", value: 3, mono: true },
      { key: "信心", label: "信心", value: 0.75, mono: true },
      { key: "tick", label: "tick", value: 120, mono: true },
      {
        key: "來源",
        label: "來源",
        value: "t_source",
        mono: true,
        link: { kind: "narrative", id: "event:t_source", label: "事件" },
      },
      { key: "內容", label: "內容", value: '{"note": "合成記憶"}', mono: true },
      { key: "主體", label: "主體", value: "t_subject", mono: true },
    ],
  },
];

export const MEMORY_DETAIL = {
  id: "31",
  kind: "memories",
  label: "t_source",
  dbref: null,
  sections: [
    {
      key: "identity",
      title: "記憶紀錄",
      type: "ledger",
      rows: [
        { key: "紀錄", label: "紀錄", value: 31, mono: true },
        { key: "擁有者", label: "擁有者", value: "12", mono: true },
        { key: "有效層級", label: "有效層級", value: "working", mono: true },
        { key: "有效可用性", label: "有效可用性", value: "active", mono: true },
        { key: "最新修訂", label: "最新修訂", value: 2, mono: true },
      ],
    },
    {
      key: "revisions",
      title: "修訂歷史",
      type: "table",
      columns: [
        { key: "revision", label: "修訂", mono: true },
        { key: "availability", label: "可用性", mono: true },
        { key: "tier", label: "層級", mono: true },
        { key: "supersedes", label: "取代", mono: true },
      ],
      rows: [
        {
          key: "2",
          cells: {
            revision: { value: 2, mono: true },
            availability: { value: "active", mono: true },
            tier: { value: "working", mono: true },
            supersedes: { value: "31", mono: true },
          },
        },
        {
          key: "1",
          cells: {
            revision: { value: 1, mono: true },
            availability: { value: "active", mono: true },
            tier: { value: "working", mono: true },
            supersedes: { value: "—", mono: true },
          },
        },
      ],
      empty_note: "此記憶沒有修訂紀錄。",
    },
  ],
};

export const SNAPSHOT_ITEMS = [
  {
    id: "t_snapshot_2",
    kind: "snapshots",
    dbref: null,
    label: "t_capability",
    owner: "12",
    fields: [
      { key: "能力", label: "能力", value: "t_capability", mono: true },
      { key: "擁有者世代", label: "擁有者世代", value: 4, mono: true },
      { key: "建立時間", label: "建立時間", value: "2026-10-07T01:02:03", mono: true },
      { key: "區塊數", label: "區塊數", value: 3, mono: true },
      { key: "截斷決策數", label: "截斷決策數", value: 0, mono: true },
    ],
  },
];

export const SNAPSHOT_DETAIL = {
  id: "t_snapshot_2",
  kind: "snapshots",
  label: "t_capability",
  dbref: null,
  sections: [
    {
      key: "identity",
      title: "情境快照",
      type: "ledger",
      rows: [
        { key: "快照識別", label: "快照識別", value: "t_snapshot_2", mono: true },
        { key: "能力", label: "能力", value: "t_capability", mono: true },
        { key: "擁有者世代", label: "擁有者世代", value: 4, mono: true },
      ],
    },
    {
      key: "sections",
      title: "區塊",
      type: "table",
      columns: [
        { key: "name", label: "區塊", mono: true },
        { key: "tokens", label: "token 數", mono: true },
      ],
      rows: [
        {
          key: "0",
          cells: { name: { value: "t_section_a", mono: true }, tokens: { value: 412, mono: true } },
        },
      ],
      empty_note: "此快照沒有保存任何區塊。",
    },
    {
      key: "tokens",
      title: "token 計量",
      type: "tree",
      value: { used: 412, limit: 1500, remaining: 1088 },
    },
    { key: "truncation", title: "截斷與捨棄", type: "bullets", items: ["t_source_a（超出上限）"] },
    {
      key: "evidence",
      title: "S2 證據連結",
      type: "ledger",
      rows: [
        {
          key: "call_id",
          label: "call_id",
          value: "cd".repeat(16),
          mono: true,
          link: { kind: "call", id: "cd".repeat(16) },
        },
      ],
    },
  ],
};

export const RECALL_RESULT = {
  owner_id: "12",
  generation: 4,
  tokenizer_version: "t_tok_v1",
  ranker_version: "t_rank_v1",
  query: "合成記憶",
  thread_id: null,
  thread_revision: 0,
  core: [
    {
      id: 31,
      tier: "core",
      category: "observation",
      salience: 3,
      confidence: 0.75,
      source_id: "t_source",
      tick: 120,
      content: { note: "合成記憶", subject: "t_subject" },
    },
  ],
  working: [
    {
      id: 32,
      tier: "working",
      category: "observation",
      salience: 2,
      confidence: 0.6,
      source_id: "",
      tick: 121,
      content: { note: "合成工作記憶" },
    },
  ],
  recalled: [
    {
      id: 31,
      tier: "core",
      category: "observation",
      salience: 3,
      confidence: 0.75,
      source_id: "t_source",
      tick: 120,
      content: { note: "合成記憶" },
      score: { lexical: 0.512, metadata: 0.25, final: 0.762 },
    },
  ],
};

export const DIALOGUE_ITEMS = [
  {
    id: "t_player_a",
    kind: "dialogue",
    dbref: null,
    label: "t_player_a",
    owner: "12",
    fields: [
      { key: "玩家", label: "玩家", value: "t_player_a", mono: true },
      { key: "紀元數", label: "紀元數", value: 2, mono: true },
      { key: "對話框數", label: "對話框數", value: 3, mono: true },
    ],
    epochs: [],
  },
  {
    id: "t_player_b",
    kind: "dialogue",
    dbref: null,
    label: "t_player_b",
    owner: "12",
    fields: [
      { key: "玩家", label: "玩家", value: "t_player_b", mono: true },
      { key: "紀元數", label: "紀元數", value: 1, mono: true },
      { key: "對話框數", label: "對話框數", value: 1, mono: true },
    ],
    epochs: [],
  },
];

export const DIALOGUE_DETAIL = {
  id: "t_player_a",
  kind: "dialogue",
  label: "t_player_a",
  dbref: null,
  sections: [
    {
      key: "identity",
      title: "對話",
      type: "ledger",
      rows: [
        { key: "NPC", label: "NPC", value: "12", mono: true },
        { key: "玩家", label: "玩家", value: "t_player_a", mono: true },
        { key: "紀元數", label: "紀元數", value: 2, mono: true },
      ],
    },
    {
      key: "epochs",
      title: "紀元與對話框",
      type: "groups",
      groups: [
        {
          key: "7",
          title: "第 1 紀元",
          note: "版本 t_version；成因 t_reason；摘要 合成摘要；快照 t_snapshot_2",
          rows: [
            {
              key: "11",
              label: "t_frame_1",
              value: "旅人：請問北方的森林最近安全嗎？",
              link: { kind: "call", id: "cd".repeat(16) },
            },
            { key: "12", label: "t_frame_2", value: "守衛：夜裡別走岔路。" },
          ],
        },
        {
          key: "8",
          title: "第 2 紀元",
          note: "版本 t_version；成因 t_reason",
          rows: [{ key: "13", label: "t_frame_3", value: "旅人：（沉默）" }],
        },
      ],
    },
  ],
};

export const LIST_PAGE = {
  items: [
    {
      id: "12",
      kind: "npcs",
      dbref: 12,
      label: "合成守衛",
      fields: [
        { key: "職業", label: "職業", value: "公會櫃檯、腳本對話" },
        { key: "稱號", label: "稱號", value: "合成頭銜" },
        { key: "所在房間", label: "所在房間", value: "合成廣場" },
      ],
    },
    {
      id: "13",
      kind: "npcs",
      dbref: 13,
      label: "合成商人",
      fields: [
        { key: "職業", label: "職業", value: "商人" },
        { key: "稱號", label: "稱號", value: "—" },
        { key: "所在房間", label: "所在房間", value: "合成市集" },
      ],
    },
  ],
  next_cursor: "t_cursor_1",
};

export const MONSTER_ITEMS = {
  items: [
    {
      id: "41",
      kind: "monsters",
      dbref: 41,
      label: "合成禽鳥",
      fields: [
        { key: "物種", label: "物種", value: "合成禽鳥" },
        { key: "變體", label: "變體", value: "t_variant_ordinary", mono: true },
        { key: "威脅階級", label: "威脅階級", value: "t_faint", mono: true },
        { key: "數值來源", label: "數值來源", value: "暫定階級區間" },
      ],
    },
  ],
  next_cursor: null,
};

/**
 * A fetch-boundary double for the runtime stories: an exact path or its
 * path-without-query resolves to the bound payload (or throws it when the
 * payload is a GmApiError).
 */
export function fakeRuntimeApi(table) {
  const resolve = (path) => {
    const entry = table[path] ?? table[path.split("?")[0]];
    if (entry === undefined) throw new GmApiError("object_not_found", { status: 404, message: "找不到指定的物件。" });
    if (entry instanceof Error) return Promise.reject(entry);
    return Promise.resolve(entry);
  };
  return {
    get: (path) => resolve(path),
    post: (path) => resolve(path),
  };
}

export function stage(children, { padding = "32px", maxWidth = "1040px" } = {}) {
  return { style: { padding, maxWidth }, children };
}
