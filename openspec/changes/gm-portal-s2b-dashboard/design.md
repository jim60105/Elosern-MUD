## Context

See proposal.md for motivation. Implement only after S1 and S2a land. Evennia serves Django within the server process, sharing reactor-written observability memory with web threads. Reuse web/gm/ access/responses/routes, web/admin-app/lib/api.js and GmPanel/Table/Empty/Error/StatusBadge rather than creating alternate conventions.

## Goals / Non-Goals

**Goals:** One engineer-day vertical read-only overview with truthful bounded-window metrics, section isolation and on-demand retained payloads.

**Non-Goals:** Cross-restart metrics, event database, active LLM probes, service mutations, compatibility health alias, game-client imports, new infrastructure or data migrations.

## Decisions

1. world/observability/recent.py owns two lock-guarded deques and copies context at ingestion and snapshot. Facade _emit feeds it after the primary operational write (including stderr fallback when available), without an early return bypass. Never recurse through facade logging on sink failure. Preserve debug gating, full error traceback, caller depth and never-raises behavior. A warning llm_call qualifies for both buffers. Copy isolation is shallow, as approved; nested values are not promised deep immutability.
2. Add positive integer GM_RECENT_LLM_CAPACITY=500 and GM_RECENT_ISSUE_CAPACITY=200 via the existing environment mechanism; document in settings-and-environment.md and .env.example. No persistent model. Start/uptime use process lifecycle, not request arrival; reload creates a new empty buffer epoch. Count fill/capacity from snapshots.
3. Add protected GET dashboard/detail using gm_path/gm_required and responses helpers. Take buffer snapshots once and compute independent services, llm, art, world, errors and process slots. Contain subservice failures locally where possible (SD must not hide translation/cutout); facade-log source failures with exc and source context. Section slots use nested errors inside overall success envelope. Process includes django responding and real database readability, replacing S1 health; delete old view/URL/frontend caller/tests and update access resolver contracts.
4. Sources are exactly approved §3.3: cached world.art.connectivity.probe; resolve_translate_backend/resolve_cutout_backend and related recent issues; profile registry and llm_call events; queue counts and ArtDrainScript; read_world_clock (never get/create), SESSION_HANDLER, combat records and live instances. Derive statistics from retained llm_call entries: denominator includes all results, degradation histogram counts degraded reasons, average/p95 use ms values, p95 nearest-rank sorted sample ceil(.95*n)-1; empty latency/last-success are null and UI says no data. Disabled state remains explicit even without samples. No endpoint LLM requests.
5. Detail validates lowercase 32-digit hex before lookup, checks S2a enabled status, calls transcript.find, separates outcome and exchanges without inventing missing records, and applies 400/404/409 as approved. Transcript storage failures must not fabricate a successful payload. Preserve file ordering, including cross-date attempts; display attempt numbers explicitly. No arbitrary path construction from input.
6. Overview retains session/header identity, replaces health with snapshot, and uses existing components. Poll every five seconds only while visible; clear timers/listeners on unmount and restart a single timer on resume. Prevent overlapping poll/manual requests and stale responses replacing newer snapshots. Fetch payload only on call selection; ignore stale selected-call results. Drawer uses outcome plus per-exchange tabs, role-grouped messages, raw JSON or raw text responses, attempt-correlated validation errors and clipboard JSON. Outcome-only fake/disabled calls remain meaningful without tabs. Local section errors/offline cards do not hide usable panels. Keep text/shape status cues and Traditional Chinese UI without authoring new lore.
7. Add deterministic colocated buffer and Evennia API tests, Vitest polling/drawer tests and Storybook stories integrated into existing showcase. New Python modules are registered exactly once in .github/evennia-shards.json; if browser tests are added also register their methods in browser-shards.json. Obtain canonical requirement IDs from tools.spec_traceability list after syncing, add substantive literal covers_requirement annotations (including frontend evidence bridge where appropriate), and do not manually guess proposed IDs.

## Risks / Trade-offs

- Bounded metrics are not whole-process totals after eviction: label the retained-window scope in UI/docs.
- Polling invokes the existing SD TTL cache only; no duplicate cache or LLM probing.
- Source read helpers can accidentally initialize records: tests spy on all create/get-or-create seams and compare persistent counts for empty-world reads.
- Full transcripts may expire or be disabled after calls enter memory: drawer shows explicit expired/disabled states.
- Shared observability/settings/shard files conflict with S2a: serial dependency, no parallel application.
