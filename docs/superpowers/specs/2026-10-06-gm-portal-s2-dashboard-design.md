# GM Portal S2 Design: LLM Transcript and Operations Dashboard

- Date: 2026-10-06
- Status: Approved design
- Parent: `docs/superpowers/specs/2026-10-06-gm-portal-design.md` (sub-project S2)
- Amends: `docs/superpowers/specs/2026-09-02-observability-logging-design.md`

S2 is delivered as two OpenSpec changes in order:

- **S2a — LLM transcript and prose in logs.** An observability change that
  persists every LLM call payload to a dedicated transcript log and repeals the
  rule that keeps player prose and prompt content out of logs.
- **S2b — Operations dashboard.** The `/gm/` home view, fed by an in-memory
  recent-event buffer and the S2a transcript.

## 1. Usage context

The dashboard serves live use while developing or playtesting: the game runs,
the portal sits alongside, and the operator checks whether LLM layers are slow
or degrading, whether art generation is stuck, and what just failed. Data
covers "since this server process started" or "the most recent N". Historical
trend analysis across restarts is a non-goal; the transcript files are the
only data that survive a reload.

## 2. S2a: LLM transcript and prose in logs

### 2.1 Rule change

The observability design's rule that player-facing prose and prompt content
never enter logs is repealed. Logs may carry player input, letter bodies,
dream text, prompts, and model output.

Unchanged:

- Credentials never enter any log: API keys, authentication headers, and URL
  userinfo stay excluded; `_scrub_key` still applies to error text.
- The operational log stays single-line with every context value truncated at
  200 characters. Full content lives in the transcript, reachable by
  `call_id`.
- `event` stays a stable English snake_case identifier.
- In-world knowledge boundaries are not logging rules and are untouched:
  `private` visibility, `PRIVATE_AUTHORING_CATEGORIES`, and the memory, recall,
  and thread access checks in `world/narrative/` keep their behaviour.

### 2.2 Transcript module: `world/observability/transcript.py`

- Depends only on the standard library and Django settings. Never raises: any
  failure writes one line to stderr and returns.
- `write(record: dict) -> None` serialises the record as one JSON line
  (`ensure_ascii=False`) and appends it, under a process lock, to
  `server/logs/llm/YYYY-MM-DD.jsonl` (server local date). The directory is
  created on demand.
- `find(call_id: str) -> list[dict]` scans files from the newest date
  backwards within the retention window and returns every record with that
  `call_id`, in file order.
- `prune() -> None` deletes files older than the retention window. Called
  once from `at_server_start()`.
- Settings, wired through the existing environment-override mechanism and
  documented in `.env.example` and `docs/development/settings-and-environment.md`:
  - `LLM_TRANSCRIPT_ENABLED` (bool, default `True`). When false, `write` is a
    no-op and `find` reports disabled.
  - `LLM_TRANSCRIPT_RETENTION_DAYS` (int ≥ 1, default `14`).
- Containers already persist `/app/server/logs` through the `evennia-logs`
  volume; no compose change is needed.

### 2.3 Record shapes

Every LLM call goes through `world/ai/guardrail.py` `guarded_call()` (the
`option_proposal_service` and `world/narrative/epochs.py` wrappers only wrap
the inner client), so the guardrail and the transport are the only writers.

`call_id` is `uuid4().hex`, generated once at the start of `guarded_call`.
`ChatRequestDescriptor` gains optional `call_id` and `attempt` fields so the
transport can stamp its records.

One `exchange` record per attempt, written by `OpenAICompatClient` after the
request settles (success or failure):

```jsonc
{"kind": "exchange", "call_id": "…", "attempt": 0, "ts": "<ISO-8601>",
 "layer": "npc_dialogue", "profile": "<model>", "endpoint_host": "<host>",
 "ms": 8090,
 "request": { /* full request body */ },
 "status": 200,
 "response": { /* full response body, or the raw text if not JSON */ },
 "error": null /* or {"type": "…", "message": "<scrubbed>"} */}
```

One `outcome` record per guarded call, written by the guardrail at its
terminal point:

```jsonc
{"kind": "outcome", "call_id": "…", "ts": "<ISO-8601>",
 "layer": "npc_dialogue", "profile": "<model>", "ms": 16438,
 "result": "ok" /* | "degraded" | "rejected" */,
 "reason": null /* e.g. "transport_error", "invalid_output", "profile_disabled" */,
 "attempts": [{"attempt": 0, "validation_errors": ["…"]}],
 "final_text": "…" /* null when degraded or rejected */}
```

- `endpoint_host` is the hostname only.
- An `outcome` is written even when no transport call happens (profile
  disabled, unexpected error), so a missing LLM call is explainable.
- The fake client writes no `exchange` record; the guardrail's `outcome` still
  records the call.

### 2.4 Operational log changes

- `llm_call`, `llm_call_retry`, and `llm_cached_tokens_reported` gain
  `call_id`.
- Redactions are reverted:
  - `commands/correspondence.py`: `cmd_in` for `信件` logs `args` (truncated
    like every other command) instead of `args_count`.
  - `correspondence_reply_captured` and `correspondence_reply_failed` carry the
    letter body; failures carry `call_id` so the full prompt is read from the
    transcript rather than duplicated.
  - `dream_surface_generation_failed` carries the player input and `call_id`.
  - Comments that state the old rule (`world/narrative/context.py`,
    `world/narrative/dream_session.py`) are rewritten.
- The observability design document is amended in §3.1, the §3.4 rules list,
  and the affected event-catalog rows (`cmd_in` for `信件`,
  `llm_cached_tokens_reported`, the `correspondence_reply_*` rows,
  `dream_surface_generation_failed`, `llm_call`).

### 2.5 S2a tests

- Transcript unit tests against a temporary directory: write, date-file
  routing, `find` across days, retention pruning, disabled mode, and
  never-raises on unwritable paths and unserialisable values.
- Guardrail integration with the fake client and a recording transport: a
  retry followed by degradation yields matching `call_id` values across the
  `exchange` records, the `outcome` record, and the `llm_call` event.
- Contract test: no transcript record contains the API key, any request
  header, or URL userinfo.
- Existing assertions for the changed events are updated in the same change.

## 3. S2b: Operations dashboard

### 3.1 Recent-event buffer: `world/observability/recent.py`

- Two bounded, lock-guarded deques fed by the facade's `_emit` after the log
  line is written:
  - `llm_call` events (default capacity 500, `GM_RECENT_LLM_CAPACITY`).
  - All `warn` and `error` events (default capacity 200,
    `GM_RECENT_ISSUE_CAPACITY`).
- Entry: timestamp, level, event, caller, a shallow copy of `context`, and the
  one-line exception summary.
- Reads return snapshot copies. Writers run on the reactor thread and readers
  on web threads; Evennia serves Django from the server process, so both share
  memory.
- A failing sink is contained inside the facade's never-raises boundary.
- Contents reset on reload, by design (§1).

### 3.2 LLM health

Passive only. Per layer, health is derived from the buffered `llm_call`
events plus static profile configuration (enabled, model, endpoint host).
Layers with no calls since startup show 尚無資料. No probe requests are sent
to LLM endpoints.

### 3.3 `GET /gm/api/dashboard`

One snapshot. Each section is computed independently; a failing section
returns `{"error": {"code", "message"}}` in its slot and the rest of the
response is unaffected. S1's `/gm/api/health` is folded into this endpoint
and removed.

| Section | Source | Content |
| --- | --- | --- |
| `services.sd` | `world/art/connectivity.probe()` (existing TTL cache) | ok or error code, host, checked-at |
| `services.translate`, `services.cutout` | backend type from `resolve_translate_backend()` / `resolve_cutout_backend()`, plus the latest related issue in the buffer | active backend (real, fake, disabled), latest failure |
| `llm.layers[]` | profiles plus the `llm_call` buffer | enabled, model, endpoint host, call count, ok/degraded/rejected counts, degrade-reason histogram, mean and p95 latency, last success time |
| `llm.recent[]` | `llm_call` buffer, newest 50 | time, `call_id`, layer, ms, result, reason |
| `art` | `world/art/queue.py`, `ArtDrainScript` | count per status, drain script running, newest 10 failures (subject key, time) |
| `world` | `read_world_clock()`, Evennia `SESSION_HANDLER`, combat session records, live instances | tick, in-game date and daypart, connected sessions, active combats, live instances |
| `errors.recent[]` | issue buffer, newest 50 | time, level, event, caller, context, exception summary |
| `process` | server process | start time, uptime, buffer capacities and fill |

All reads are read-only; the endpoint never creates the world clock or any
record.

### 3.4 `GET /gm/api/llm/calls/<call_id>`

- `call_id` must match `^[0-9a-f]{32}$`; otherwise `400` `invalid_call_id`.
- Returns `{"outcome": {...} | null, "exchanges": [...]}` from
  `transcript.find`.
- No records: `404` `transcript_not_found`. Transcript disabled: `409`
  `transcript_disabled`.

### 3.5 Frontend

The S1 總覽 view becomes the dashboard.

```
+ 服務狀態 ------------------------------------------------------+
| ● sd-webui 正常   ● 翻譯 CT2   ● 去背 rembg   ● LLM n/m 啟用   |
+ LLM layers ---------------------+ 世界 -----------------------+
| layer  呼叫  降級率  p95  最近成功 | 第 12 日 黃昏 · tick 98231  |
| …                               | 線上 1 · 戰鬥 0 · 副本 2    |
+ 最近 LLM 呼叫（點選檢視 payload）-+ 美術佇列 -------------------+
| 12:34:36 action_options ok 8.1s | 等待 3 · 進行中 1 · 失敗 2  |
+ 最近警告與錯誤 -----------------+-----------------------------+
| 12:40 [error] <event> | <caller> | k=v tb: …                  |
+--------------------------------------------------------------+
```

- Polls every 5 seconds; pauses while the tab is hidden
  (`visibilitychange`); shows the last-updated time and a manual refresh
  control.
- Selecting an LLM call opens a payload drawer: the outcome summary, then one
  tab per attempt with request messages grouped by role, the raw response
  JSON, validation errors, and a copy-JSON control.
- Status uses `GmStatusBadge` (`.status-marker` ok/warn/crit) with text and
  shape, never colour alone.
- An offline service renders as a crit status card; the dashboard stays
  usable.

### 3.6 S2b tests

- Buffer: capacity bound, snapshot isolation, concurrent write/read, a
  failing sink not breaking the facade.
- Dashboard API: each section's normal and failure path, and section
  isolation; the endpoint creating no records.
- Call detail API: valid, malformed, not found, disabled.
- Vitest: polling pause and resume, payload drawer rendering.
- Storybook stories for the new components in the showcase coverage gate.
- New Python test modules registered in `.github/evennia-shards.json`.
