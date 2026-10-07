## Purpose

Provide privileged, read-only live operational diagnosis from bounded process-local events and retained LLM transcripts while keeping the portal usable through partial service failures.

## ADDED Requirements

### Requirement: Landed foundation and transcript prerequisites
The dashboard SHALL depend on landed gm-portal-s1-foundation and gm-portal-s2a-llm-transcript, reusing web/gm/, gm_required/gm_path access coverage, the S1 API envelope/fetch boundary, admin-app component layer, and S2a call_id/transcript contract. All new APIs SHALL retain Developer/superuser access, 401/403 envelopes, gm_request and gm_denied events, and the separate same-origin GM bundle. No game/OOB contract or narrative access rule SHALL be weakened.

#### Scenario: Protected diagnostics
- **WHEN** anonymous, ordinary, Developer and superuser accounts request dashboard or call detail
- **THEN** the first two receive 401 unauthenticated and 403 forbidden respectively, the latter two receive authorized diagnostics, and request/denial logging and resolver coverage remain enforced

### Requirement: Bounded recent-event snapshots
After the operational line is written, recent events SHALL capture llm_call into a bounded LLM buffer (GM_RECENT_LLM_CAPACITY default 500) and all warn/error events into an issue buffer (GM_RECENT_ISSUE_CAPACITY default 200). Entries SHALL contain timestamp, level, event, caller, shallow-copied context, and one-line exception summary. Lock-guarded writes and snapshot copies SHALL support concurrent reactor writers/web readers. Overflow SHALL evict oldest entries; reload SHALL reset buffers. Sink failure SHALL not escape the facade or suppress an already-written log line.

#### Scenario: Bounds and isolation
- **WHEN** concurrent writers exceed capacity while readers take snapshots and mutate returned top-level context dictionaries
- **THEN** buffers remain bounded, oldest records are evicted and snapshot/list or top-level context mutations do not change stored entries

#### Scenario: Failed sink and reload
- **WHEN** the recent sink raises or the process reloads
- **THEN** logging returns normally with its line intact, and reload starts with empty recent buffers

### Requirement: Independent read-only dashboard sections
GET /gm/api/dashboard SHALL return one success-envelope snapshot with independently computed sections; a failing section SHALL contain {"error":{"code":"<snake_case>","message":"<zh-TW>"}} in its own slot without removing other sections. It SHALL fold Django responding and a real database-read health check from S1 into process health, and remove /gm/api/health. Reads SHALL never create a world clock or any persistent record. The snapshot SHALL include:
- services.sd: existing cached SD connectivity result/error code, hostname and checked-at; services.translate/cutout: real/fake/disabled backend type and latest related buffered failure.
- llm.layers: static enabled/model/hostname and buffered per-layer call count, ok/degraded/rejected counts, degrade-reason histogram, mean/p95 ms and last success time; no-call layers show no data and no active LLM probes.
- llm.recent: newest 50 calls, time/call_id/layer/ms/result/reason.
- art: counts per status, drain-script running, newest 10 failures with subject key/time.
- world: existing tick/date/daypart, connected sessions, active combats, live instances.
- errors.recent: newest 50 issues, time/level/event/caller/context/exception summary.
- process: start time, uptime, buffer capacities/fill and folded Django/database health.
Counts and latency statistics SHALL cover the retained bounded buffer, not claim lifetime totals after eviction; buffers SHALL not be rebuilt from transcript history.

#### Scenario: Normal snapshot without probes or writes
- **WHEN** configured services, profiles and runtime records are readable
- **THEN** every section reports its source data and limits, no LLM request is sent, and no persistent object or clock is created

#### Scenario: Independent failures
- **WHEN** each section source is made to fail in turn, including the database read
- **THEN** only its slot reports a stable error and all unaffected sections remain usable

#### Scenario: Empty and evicted LLM history
- **WHEN** a layer has no calls or its oldest calls have been evicted
- **THEN** no-call metrics display no data and nonempty counts/latencies describe only buffered calls

### Requirement: Validated retained call detail
GET /gm/api/llm/calls/<call_id> SHALL accept only ^[0-9a-f]{32}$, rejecting malformed identifiers with HTTP 400 invalid_call_id. Valid lookup SHALL return success data {"outcome":<record|null>,"exchanges":[<records>]} from S2a retained records, preserving exchange order. No records SHALL return HTTP 404 transcript_not_found; disabled transcripts SHALL return HTTP 409 transcript_disabled. An exchange-only or outcome-only call SHALL return available records without fabricated payloads.

#### Scenario: Detail result matrix
- **WHEN** permitted requests use malformed, absent, retained, disabled, exchange-only and outcome-only call identifiers
- **THEN** they receive the specified 400, 404, success, 409 and partial-record success results respectively in S1 envelopes

#### Scenario: Best-effort lookup read failure
- **WHEN** the never-raising transcript lookup skips unreadable files or malformed lines and returns no records or some readable records
- **THEN** empty results receive 404 transcript_not_found and readable results receive the normal available-record response without fabricated missing records or a guarantee that the scan was complete

### Requirement: Visibility-aware overview and payload drawer
The /gm/ overview SHALL render service status, layer metrics, world state, art queue, recent calls, recent warnings/errors and process freshness. It SHALL poll every five seconds, pause while document visibility is hidden, resume on visibility change, display last-updated time and provide manual refresh. Offline services SHALL render critical status cards without disabling the dashboard; partial errors SHALL be localized. Status SHALL use GmStatusBadge/.status-marker ok/warn/crit with text and shape, never color alone. A selected call SHALL open a drawer with outcome summary and one tab per exchange attempt, messages grouped by role, raw response JSON/text, matching outcome validation errors and copy-JSON control. Empty/disabled/expired transcript cases SHALL show explicit states. UI SHALL use Traditional Chinese and preserve data identifiers verbatim. Every new component SHALL have showcase-gated Storybook stories.

#### Scenario: Poll lifecycle
- **WHEN** the overview mounts, five seconds elapse, the tab hides and later becomes visible, or manual refresh is requested
- **THEN** visible polling refreshes data and timestamp, hidden polling stops and visible polling resumes without duplicate timers

#### Scenario: Payload and unavailable services
- **WHEN** a call with multiple attempts is selected while another dashboard service is offline
- **THEN** the drawer displays each attempt's role-grouped messages, response and validation errors with copy JSON, and the offline critical card does not prevent dashboard use
