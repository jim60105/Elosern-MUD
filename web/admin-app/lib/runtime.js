// Runtime state inspection model (gm-portal-s3-runtime-state §4/§6).
//
// One place owns the kind registry, the filter vocabulary and the
// identifier-to-location mapping the runtime pages and GmEntityLink share.
// Every request goes through the existing single fetch boundary (lib/api.js);
// nothing here fetches, computes or caches server state.

export const LIST_DEFAULT_LIMIT = 50;
export const LIST_MAX_LIMIT = 200;
export const LIST_LIMIT_CHOICES = [25, 50, 100, 200];

//: The route names the runtime pages register (router.js).
export const RUNTIME_ROUTE = Object.freeze({
  home: "runtime-home",
  search: "runtime-search",
  raw: "runtime-object-raw",
  list: "runtime-list",
  entity: "runtime-entity",
});

//: The navigation tree: the kinds the runtime section exposes, in order.
//: ``memories``/``snapshots``/``dialogue`` are NPC tabs, not top-level kinds.
export const RUNTIME_KINDS = Object.freeze([
  Object.freeze({
    key: "accounts",
    label: "帳號",
    blurb: "帳號權限、歷程與擁有的角色",
    filters: Object.freeze([]),
  }),
  Object.freeze({
    key: "characters",
    label: "玩家角色",
    blurb: "真實屬性、偽裝數值、裝備與稱號",
    filters: Object.freeze([]),
  }),
  Object.freeze({
    key: "npcs",
    label: "NPC",
    blurb: "人物設定、服務元件、今日排程與敘事分頁",
    filters: Object.freeze([
      Object.freeze({ key: "location", label: "所在房間", type: "text", placeholder: "#12", mono: true }),
    ]),
  }),
  Object.freeze({
    key: "monsters",
    label: "魔物",
    blurb: "物種、變體、數值來源、配置與行為設定",
    filters: Object.freeze([
      Object.freeze({ key: "species", label: "物種鍵", type: "text", placeholder: "t_…", mono: true }),
      Object.freeze({ key: "region", label: "區域", type: "text", placeholder: "region_key", mono: true }),
    ]),
  }),
  Object.freeze({
    key: "rooms",
    label: "房間",
    blurb: "座標、出口、內容物與實例狀態",
    filters: Object.freeze([]),
  }),
  Object.freeze({
    key: "quests",
    label: "任務",
    blurb: "執行期任務紀錄與生成任務內容",
    filters: Object.freeze([
      Object.freeze({ key: "owner", label: "擁有角色", type: "text", placeholder: "#5", mono: true, required: true }),
      Object.freeze({ key: "generated", label: "只看生成任務", type: "checkbox" }),
    ]),
  }),
  Object.freeze({
    key: "narrative",
    label: "敘事紀錄",
    blurb: "事件、故事線、書信、夢境、決策、節拍、草稿與請求",
    filters: Object.freeze([
      Object.freeze({
        key: "subtype",
        label: "子類型",
        type: "select",
        default: "event",
        options: Object.freeze([
          Object.freeze({ value: "event", label: "事件" }),
          Object.freeze({ value: "thread", label: "故事線" }),
          Object.freeze({ value: "letter", label: "書信" }),
          Object.freeze({ value: "dream", label: "夢境" }),
          Object.freeze({ value: "decision", label: "導演決策" }),
          Object.freeze({ value: "beat", label: "排程節拍" }),
          Object.freeze({ value: "draft", label: "創作草稿" }),
          Object.freeze({ value: "request", label: "創作請求" }),
        ]),
      }),
      Object.freeze({ key: "owner", label: "擁有者", type: "text", placeholder: "識別碼", mono: true }),
      Object.freeze({ key: "status", label: "狀態", type: "text", placeholder: "status", mono: true }),
      Object.freeze({ key: "event_type", label: "事件類型", type: "text", placeholder: "event_type", mono: true }),
    ]),
  }),
  Object.freeze({
    key: "art",
    label: "美術資產",
    blurb: "主體、狀態、生成來源與畫廊任務",
    filters: Object.freeze([
      Object.freeze({
        key: "status",
        label: "狀態",
        type: "select",
        options: Object.freeze([
          Object.freeze({ value: "", label: "全部" }),
          Object.freeze({ value: "missing", label: "missing" }),
          Object.freeze({ value: "pending", label: "pending" }),
          Object.freeze({ value: "in_progress", label: "in_progress" }),
          Object.freeze({ value: "done", label: "done" }),
          Object.freeze({ value: "failed", label: "failed" }),
        ]),
      }),
      Object.freeze({ key: "kind", label: "種類", type: "text", placeholder: "kind", mono: true }),
    ]),
  }),
]);

export const RUNTIME_KIND_BY_KEY = Object.freeze(
  Object.fromEntries(RUNTIME_KINDS.map((kind) => [kind.key, kind])),
);

//: Label for a kind key, including the record-backed tab collections.
const KIND_LABELS = Object.freeze({
  ...Object.fromEntries(RUNTIME_KINDS.map((kind) => [kind.key, kind.label])),
  memories: "記憶",
  snapshots: "情境快照",
  dialogue: "對話",
  object: "物件",
});

export function kindLabel(kind) {
  return KIND_LABELS[kind] ?? kind ?? "";
}

//: The narrative subtype labels (also used by the list captions).
export const NARRATIVE_SUBTYPE_LABELS = Object.freeze(
  Object.fromEntries(
    (RUNTIME_KIND_BY_KEY.narrative.filters.find((filter) => filter.key === "subtype").options ?? []).map(
      (option) => [option.value, option.label],
    ),
  ),
);

//: Which kinds answer through the object raw route (dbref-backed).
const DBREF_KINDS = Object.freeze(["accounts", "characters", "npcs", "monsters", "rooms", "object"]);

export function isDbrefKind(kind) {
  return DBREF_KINDS.includes(kind);
}

export const SUBTYPE_PARAM = "subtype";

export function subtypeOf(kind, id) {
  if (kind !== "narrative") return null;
  const [subtype] = String(id ?? "").split(":", 1);
  return NARRATIVE_SUBTYPE_LABELS[subtype] ? subtype : null;
}

// --- identifiers ------------------------------------------------------------

function dbrefParam(identity) {
  return String(identity ?? "").replace(/^#/, "");
}

/** The owner query value a record-backed entity needs to resolve. */
export function ownerQuery(owner) {
  if (owner === null || owner === undefined || owner === "") return {};
  return { owner: String(owner).startsWith("#") ? String(owner) : `#${owner}` };
}

/**
 * The router location for one identifier link, or a plain-href/media
 * descriptor. ``null`` means the target is not addressable.
 */
export function linkTarget(link) {
  if (!link || typeof link !== "object" || !link.kind || link.id === null || link.id === undefined) {
    return null;
  }
  const kind = String(link.kind);
  if (kind === "media") {
    const href = String(link.id);
    return href ? { href } : null;
  }
  // Call identifiers open the existing S2 drawer instead of a route.
  if (kind === "call") {
    return link.id ? { callId: String(link.id) } : null;
  }
  if (kind === "object") {
    return {
      name: RUNTIME_ROUTE.raw,
      params: { dbref: dbrefParam(link.id) },
      query: {},
    };
  }
  if (!KIND_LABELS[kind]) return null;
  return {
    name: RUNTIME_ROUTE.entity,
    params: { kind, id: String(link.id) },
    query: ownerQuery(link.owner),
  };
}

/** A real href for a target, so modified clicks and no-router contexts work. */
export function targetHref(target, base = "/gm/") {
  if (!target) return null;
  if (target.href) return target.href;
  if (target.callId) return null;
  const query = new URLSearchParams(target.query ?? {}).toString();
  if (target.name === RUNTIME_ROUTE.raw) {
    return `${base}runtime/object/${encodeURIComponent(target.params.dbref)}/raw`;
  }
  const kind = encodeURIComponent(target.params.kind);
  return `${base}runtime/${kind}/${encodeURIComponent(target.params.id)}${query ? `?${query}` : ""}`;
}

/** The canonical location of an entity page. */
export function entityTarget(kind, id, { owner = null } = {}) {
  return { name: RUNTIME_ROUTE.entity, params: { kind, id: String(id) }, query: ownerQuery(owner) };
}

/** The canonical location of a kind's list page. */
export function kindListTarget(kind, filters = {}) {
  return { name: RUNTIME_ROUTE.list, params: { kind }, query: cleanFilters(filters) };
}

/** Drop empty filter values so URLs stay canonical. */
export function cleanFilters(filters = {}) {
  return Object.fromEntries(
    Object.entries(filters).filter(([, value]) => value !== "" && value !== null && value !== undefined),
  );
}

export function listHref(kind, filters = {}) {
  const query = new URLSearchParams(cleanFilters(filters)).toString();
  return `/gm/runtime/${encodeURIComponent(kind)}${query ? `?${query}` : ""}`;
}

// --- request paths ---------------------------------------------------------

export function listPath(kind, { cursor = null, limit = null, filters = {} } = {}) {
  const params = new URLSearchParams(cleanFilters(filters));
  if (limit) params.set("limit", String(limit));
  if (cursor) params.set("cursor", String(cursor));
  const query = params.toString();
  return `/state/${encodeURIComponent(kind)}${query ? `?${query}` : ""}`;
}

export function detailPath(kind, id, filters = {}) {
  const query = new URLSearchParams(cleanFilters(filters)).toString();
  return `/state/${encodeURIComponent(kind)}/${encodeURIComponent(id)}${query ? `?${query}` : ""}`;
}

export function rawPath(dbref) {
  return `/state/object/${encodeURIComponent(dbrefParam(dbref))}/raw`;
}

export function searchPath(query) {
  return `/state/search?q=${encodeURIComponent(String(query ?? ""))}`;
}

export function recallPath(dbref) {
  return `/state/npc/${encodeURIComponent(dbrefParam(dbref))}/recall`;
}

export const RECALL_QUERY_LIMIT = 2000;

//: The optional filter keys the cursor fingerprint covers (backend FILTER_KEYS).
export const FILTER_KEYS = Object.freeze([
  "owner",
  "subtype",
  "location",
  "species",
  "region",
  "status",
  "state",
  "kind",
  "category",
  "tier",
  "scope",
  "visibility",
  "event_type",
  "outcome",
  "thread",
  "sender",
  "recipient",
  "generated",
  "include_superseded",
  "include_inactive",
]);
