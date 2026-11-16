## MODIFIED Requirements

### Requirement: Independent read-only dashboard sections
GET /gm/api/dashboard SHALL return one success-envelope snapshot with independently computed sections; a failing section SHALL contain {"error":{"code":"<snake_case>","message":"<zh-TW>"}} in its own slot without removing other sections. It SHALL fold Django responding and a real database-read health check from S1 into process health, and remove /gm/api/health. Reads SHALL never create a world clock or any persistent record. Its sections are enumerated below.

#### Scenario: Normal snapshot without probes or writes
- **WHEN** configured services, profiles and runtime records are readable
- **THEN** every section reports its source data and limits, no LLM request is sent, and no persistent object or clock is created

#### Scenario: Independent failures
- **WHEN** each section source is made to fail in turn, including the database read
- **THEN** only its slot reports a stable error and all unaffected sections remain usable

#### Scenario: Empty and evicted LLM history
- **WHEN** a layer has no calls or its oldest calls have been evicted
- **THEN** no-call metrics display no data and nonempty counts/latencies describe only buffered calls

#### Scenario: The service sections report connectivity and backends
- **WHEN** the snapshot's service sections are built
- **THEN** services.sd carries the existing cached SD connectivity result/error code, hostname and checked-at, and services.translate/cutout carry the real/fake/disabled backend type and latest related buffered failure

#### Scenario: The LLM sections report layer metrics and recent calls
- **WHEN** the snapshot's LLM sections are built
- **THEN** llm.layers carries static enabled/model/hostname and buffered per-layer call count, ok/degraded/rejected counts, degrade-reason histogram, mean/p95 ms and last success time, no-call layers show no data and no active LLM probes, and llm.recent lists the newest 50 calls with time/call_id/layer/ms/result/reason

#### Scenario: The art, world, and error sections report runtime state
- **WHEN** the snapshot's art, world, and errors sections are built
- **THEN** art carries current gallery-job counts per existing status vocabulary, drain-script running, and newest 10 recorded gallery errors with subject key/error time; settled jobs are absent from live counts; world carries existing tick/date/daypart, connected sessions, active combats, live instances; and errors.recent lists the newest 50 issues with time/level/event/caller/context/exception summary

#### Scenario: The process section reports health and buffers
- **WHEN** the snapshot's process section is built
- **THEN** it carries start time, uptime, buffer capacities/fill and folded Django/database health

#### Scenario: Statistics stay within the retained buffer
- **WHEN** counts and latency statistics are computed after eviction has occurred
- **THEN** they cover the retained bounded buffer, do not claim lifetime totals, and buffers are not rebuilt from transcript history

#### Scenario: Gallery errors survive terminal job deletion
- **WHEN** a synthetic gallery job fails and its terminal job is removed
- **THEN** dashboard failure rows still report its recorded gallery error without restoring a job; successful later publication clears that row and dashboard reads mutate nothing
