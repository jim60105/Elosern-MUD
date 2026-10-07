// Shared runtime test scaffolding (not a suite: vitest only collects
// *.test.js). Keeps the router stub and the synthetic payloads in one place so
// the component suites assert behaviour instead of re-declaring shapes.
import { mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import { vi } from "vitest";

export function stubRouter() {
  return createRouter({
    history: createMemoryHistory("/gm/"),
    routes: [
      { path: "/", name: "runtime-home" },
      { path: "/runtime/search", name: "runtime-search" },
      { path: "/runtime/object/:dbref/raw", name: "runtime-object-raw" },
      { path: "/runtime/:kind", name: "runtime-list" },
      { path: "/runtime/:kind/:id", name: "runtime-entity" },
    ],
  });
}

export function mountWith(component, { props = {}, slots, api, router = stubRouter(), attachTo } = {}) {
  return mount(component, {
    props,
    slots,
    attachTo,
    global: { plugins: [router], provide: { gmApi: api } },
  });
}

// A minimal fetch boundary double: `get(path)`/`post(path, body)` route through
// a caller-supplied table keyed by an exact path or a path prefix.
export function fakeApi(handlers = {}) {
  const calls = [];
  return {
    calls,
    async get(path) {
      calls.push({ method: "get", path });
      return resolve(handlers, path);
    },
    async post(path, body) {
      calls.push({ method: "post", path, body });
      return resolve(handlers, path, body);
    },
  };
}

async function resolve(handlers, path, body) {
  const entry = handlers[path] ?? handlers[path.split("?")[0]];
  if (entry === undefined) throw new Error(`unexpected request ${path}`);
  const value = typeof entry === "function" ? await entry(body) : entry;
  if (value instanceof Error) throw value;
  return value;
}

export function errorWith(code, message = "x", status = 400) {
  return Object.assign(new Error(message), { name: "GmApiError", code, message, status });
}

// --- wire fixtures ---------------------------------------------------------

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
        { key: "識別碼", label: "識別碼", value: "#12", mono: true },
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
      key: "services",
      title: "服務與職業",
      type: "table",
      columns: [
        { key: "component", label: "服務元件" },
        { key: "slot", label: "插槽", mono: true },
      ],
      rows: [
        {
          key: "GuildStaff",
          cells: {
            component: { value: "公會櫃檯" },
            slot: { value: "GuildStaff", mono: true },
          },
        },
      ],
      empty_note: "此 NPC 目前沒有服務元件。",
    },
    {
      key: "links",
      title: "相關連結",
      type: "chips",
      chips: [
        { key: "room", label: "合成廣場", link: { kind: "rooms", id: "3", label: "合成廣場" } },
        { key: "memories", label: "記憶", link: { kind: "memories", id: "owner:12", owner: "12" } },
      ],
    },
    {
      key: "memory_trace",
      title: "記憶證據",
      type: "ledger",
      rows: [
        {
          key: "call_id",
          label: "call_id",
          value: "ab".repeat(16),
          mono: true,
          link: { kind: "call", id: "ab".repeat(16) },
        },
      ],
    },
    { key: "persona", title: "人物設定", type: "empty", note: "人物設定目前無法讀取：缺漏。" },
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
      { key: "t_marker", category: "t_notes", value: { $unserializable: "set", repr: "{1, 2}" } },
    ],
    tags: [{ key: "t_tagged", category: "t_category" }],
    components: [{ name: "GuildStaff", fields: { service_id: "t_service" } }],
  },
};

export function listPage(items, nextCursor = null) {
  return { items, next_cursor: nextCursor };
}

export const MEMORY_ITEM = {
  id: "31",
  kind: "memories",
  dbref: null,
  label: "t_source",
  owner: "12",
  fields: [
    { key: "類別", label: "類別", value: "observation", mono: true },
    { key: "層級", label: "層級", value: "working", mono: true },
    {
      key: "來源",
      label: "來源",
      value: "t_source",
      mono: true,
      link: { kind: "narrative", id: "event:t_source", label: "事件" },
    },
  ],
};

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
        { key: "有效層級", label: "有效層級", value: "working", mono: true },
      ],
    },
    {
      key: "revisions",
      title: "修訂歷史",
      type: "table",
      columns: [
        { key: "revision", label: "修訂", mono: true },
        { key: "availability", label: "可用性", mono: true },
      ],
      rows: [
        {
          key: "2",
          cells: {
            revision: { value: 2, mono: true },
            availability: { value: "active", mono: true },
          },
        },
      ],
    },
  ],
};

export const SNAPSHOT_ITEM = {
  id: "t_snapshot_1",
  kind: "snapshots",
  dbref: null,
  label: "t_capability",
  owner: "12",
  fields: [
    { key: "能力", label: "能力", value: "t_capability", mono: true },
    { key: "區塊數", label: "區塊數", value: 1, mono: true },
  ],
};

export const RECALL_RESULT = {
  owner_id: "12",
  generation: 4,
  tokenizer_version: "t_tok_v1",
  ranker_version: "t_rank_v1",
  query: "合成",
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
      tick: 1,
      content: { note: "合成記憶" },
    },
  ],
  working: [],
  recalled: [
    {
      id: 31,
      tier: "core",
      category: "observation",
      salience: 3,
      confidence: 0.75,
      source_id: "t_source",
      tick: 1,
      content: { note: "合成記憶" },
      score: { lexical: 0.5, metadata: 0.25, final: 0.75 },
    },
  ],
};

export const DIALOGUE_PAGE = listPage([
  {
    id: "t_player_a",
    kind: "dialogue",
    dbref: null,
    label: "t_player_a",
    owner: "12",
    fields: [
      { key: "玩家", label: "玩家", value: "t_player_a", mono: true },
      { key: "紀元數", label: "紀元數", value: 2, mono: true },
    ],
    epochs: [],
  },
]);

export const DIALOGUE_DETAIL = {
  id: "t_player_a",
  kind: "dialogue",
  label: "t_player_a",
  dbref: null,
  sections: [
    {
      key: "epochs",
      title: "紀元與對話框",
      type: "groups",
      groups: [
        {
          key: "7",
          title: "第 1 紀元",
          note: "版本 t_version；成因 t_reason",
          rows: [
            {
              key: "11",
              label: "t_frame_1",
              value: "合成對話",
              link: { kind: "call", id: "cd".repeat(16) },
            },
          ],
        },
      ],
    },
  ],
};

export function spyFetch() {
  return vi.fn();
}
