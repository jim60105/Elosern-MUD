// Deterministic, offline fixtures for the GM stories (synthetic values).
export const SESSION = Object.freeze({
  account_name: "operator_01",
  permission_level: "Developer",
  server_time: "2026-10-07T14:32:05+08:00",
  game_version: "0.1.0",
});

export const HEALTH_COLUMNS = [
  { key: "label", label: "項目" },
  { key: "key", label: "識別碼", mono: true },
  { key: "value", label: "回報值", mono: true },
  { key: "status", label: "狀態" },
];

export const HEALTH_ROWS = [
  { key: "django", label: "Django 回應", value: "ok", status: { status: "ok", label: "正常" } },
  { key: "database", label: "資料庫讀取", value: "readable", status: { status: "ok", label: "可讀取" } },
];

export function stage(children, { padding = "32px", maxWidth = "880px" } = {}) {
  return { style: { padding, maxWidth }, children };
}

// --- Operations dashboard (gm-portal-s2b-dashboard) -------------------------
// Synthetic snapshot; epoch seconds anchored to a fixed instant so stories
// are deterministic.
export const NOW = 1791334800;

const call = (offset, layer, result, ms, reason = null, index = 0) => ({
  ts: NOW - offset,
  call_id: `${(index + 10).toString(16).padStart(2, "0")}`.repeat(16),
  layer,
  profile: layer === "npc_dialogue" ? "synthetic-large" : "synthetic-small",
  ms,
  result,
  reason,
});

export const DASHBOARD = Object.freeze({
  services: {
    sd: { ok: true, code: null, host: "sd.local.test", checked_at: NOW - 42, from_cache: true },
    translate: {
      backend: "real",
      class_name: "CTranslate2Backend",
      latest_failure: {
        ts: NOW - 380,
        level: "warn",
        event: "art_translate_failed",
        code: "art_translate_unavailable",
        exc: "TranslateError: model layout missing @ world/art/translate_ct2.py:211",
      },
    },
    cutout: { backend: "disabled", class_name: null, latest_failure: null },
    llm: { enabled: 6, total: 8 },
  },
  llm: {
    layers: [
      { layer: "narrator", enabled: true, model: "synthetic-small", endpoint_host: "llm.local.test", calls: 48, ok: 46, degraded: 2, rejected: 0, reasons: { invalid_output: 2 }, mean_ms: 2140, p95_ms: 5120, last_success_at: NOW - 12 },
      { layer: "npc_dialogue", enabled: true, model: "synthetic-large", endpoint_host: "llm.local.test", calls: 22, ok: 14, degraded: 7, rejected: 1, reasons: { transport_error: 5, invalid_output: 2 }, mean_ms: 8120, p95_ms: 16438, last_success_at: NOW - 64 },
      { layer: "action_options", enabled: true, model: "synthetic-small", endpoint_host: "llm.local.test", calls: 31, ok: 28, degraded: 3, rejected: 0, reasons: { invalid_output: 3 }, mean_ms: 1630, p95_ms: 3900, last_success_at: NOW - 5 },
      { layer: "dream", enabled: true, model: "synthetic-large", endpoint_host: "llm.local.test", calls: 0, ok: 0, degraded: 0, rejected: 0, reasons: {}, mean_ms: null, p95_ms: null, last_success_at: null },
      { layer: "correspondence", enabled: true, model: "synthetic-small", endpoint_host: "llm.local.test", calls: 3, ok: 3, degraded: 0, rejected: 0, reasons: {}, mean_ms: 4300, p95_ms: 5010, last_success_at: NOW - 900 },
      { layer: "scene_builder", enabled: true, model: "synthetic-small", endpoint_host: "llm.local.test", calls: 9, ok: 9, degraded: 0, rejected: 0, reasons: {}, mean_ms: 940, p95_ms: 1300, last_success_at: NOW - 150 },
      { layer: "story_director", enabled: false, model: "synthetic-large", endpoint_host: "llm.local.test", calls: 0, ok: 0, degraded: 0, rejected: 0, reasons: {}, mean_ms: null, p95_ms: null, last_success_at: null },
      { layer: "title_nomination", enabled: false, model: "synthetic-small", endpoint_host: "llm.local.test", calls: 0, ok: 0, degraded: 0, rejected: 0, reasons: {}, mean_ms: null, p95_ms: null, last_success_at: null },
    ],
    recent: [
      call(5, "action_options", "ok", 1630, null, 0),
      call(12, "narrator", "ok", 2210, null, 1),
      call(31, "npc_dialogue", "degraded", 16438, "transport_error", 2),
      call(64, "npc_dialogue", "ok", 8090, null, 3),
      call(70, "npc_dialogue", "rejected", 120, "unexpected_error:KeyError", 4),
      call(95, "narrator", "degraded", 6100, "invalid_output", 5),
      call(150, "scene_builder", "ok", 940, null, 6),
    ],
    window: { retained: 113, capacity: 500 },
  },
  art: {
    counts: { missing: 4, pending: 3, in_progress: 1, done: 128, failed: 2 },
    drain: { exists: true, running: true },
    failures: [
      { subject_key: "monster:forest_wolf:tier_2", kind: "monster", error: "sd_http_error", ts: NOW - 600 },
      { subject_key: "character:synthetic_traveller", kind: "character", error: "art_cutout_unavailable", ts: NOW - 4200 },
    ],
  },
  world: {
    clock: { tick: 982310, year: 3, season: "霜月", day: 12, hour: 18, minute: 40, daypart: "黃昏" },
    sessions: 1,
    accounts: 1,
    active_combats: 0,
    live_instances: 2,
  },
  errors: {
    recent: [
      { ts: NOW - 31, level: "warn", event: "llm_transport_error", caller: "world.ai.client._safe_log_error:302", context: { endpoint: "http://llm.local.test/v1/chat/completions", kind: "timeout" }, exc: "LLMTransportError: request timed out after 60s @ world/ai/client.py:288" },
      { ts: NOW - 70, level: "error", event: "dream_surface_generation_failed", caller: "server.dream_service.act:144", context: { action: "say", call_id: "0e".repeat(16), char: 7, input: "我想回到那座鐘樓。", session_id: "dream-7-3" }, exc: "KeyError: 'phase' @ world/ai/dream.py:480" },
      { ts: NOW - 380, level: "warn", event: "art_translate_failed", caller: "world.art.translate.translate_description:88", context: { code: "art_translate_unavailable", record: "art:monster:forest_wolf:tier_2" }, exc: null },
    ],
    window: { retained: 3, capacity: 200 },
  },
  process: {
    django: "ok",
    database: "readable",
    started_at: NOW - 8040,
    uptime_s: 8040,
    buffers_started_at: NOW - 8031,
    now: NOW,
    buffers: { llm: { fill: 113, capacity: 500 }, issues: { fill: 3, capacity: 200 } },
  },
});

export const CALL_DETAIL = Object.freeze({
  outcome: {
    kind: "outcome",
    call_id: "0c".repeat(16),
    ts: "2026-10-07T14:32:05.120+08:00",
    layer: "npc_dialogue",
    profile: "synthetic-large",
    ms: 16438,
    result: "degraded",
    reason: "invalid_output",
    attempts: [
      { attempt: 0, validation_errors: ["'reply' is a required property"] },
      { attempt: 1, validation_errors: [] },
    ],
    final_text: null,
  },
  exchanges: [
    {
      kind: "exchange",
      call_id: "0c".repeat(16),
      attempt: 0,
      ts: "2026-10-07T14:31:57.030+08:00",
      layer: "npc_dialogue",
      profile: "synthetic-large",
      endpoint_host: "llm.local.test",
      ms: 8090,
      request: {
        model: "synthetic-large",
        temperature: 0.8,
        max_tokens: 800,
        messages: [
          { role: "system", content: "你是村口的守衛，只說角色內的話。" },
          { role: "user", content: "旅人：請問北方的森林最近安全嗎？" },
        ],
      },
      status: 200,
      response: { choices: [{ message: { content: "{\"mood\": \"wary\"}" } }], usage: { prompt_tokens: 812, completion_tokens: 21 } },
      error: null,
    },
    {
      kind: "exchange",
      call_id: "0c".repeat(16),
      attempt: 1,
      ts: "2026-10-07T14:32:05.110+08:00",
      layer: "npc_dialogue",
      profile: "synthetic-large",
      endpoint_host: "llm.local.test",
      ms: 8040,
      request: {
        model: "synthetic-large",
        messages: [
          { role: "system", content: "你是村口的守衛，只說角色內的話。" },
          { role: "user", content: "旅人：請問北方的森林最近安全嗎？" },
          { role: "user", content: "Validation failed: 'reply' is a required property" },
        ],
      },
      status: null,
      response: null,
      error: { type: "timeout", message: "request timed out after 60s" },
    },
  ],
});

export function fakeApi(responses) {
  return {
    async get(path) {
      const value = typeof responses === "function" ? responses(path) : responses[path];
      if (value instanceof Error) throw value;
      return value;
    },
    post: async () => ({}),
  };
}
