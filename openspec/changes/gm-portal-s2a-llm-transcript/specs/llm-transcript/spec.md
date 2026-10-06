## Purpose

Provide retained full-payload LLM diagnostics correlated across transport attempts and terminal guarded-call outcomes without disrupting gameplay or logging credentials.

## ADDED Requirements

### Requirement: Retained daily transcript storage
Transcripts SHALL append one UTF-8 JSON line per record with non-ASCII text preserved to server/logs/llm/YYYY-MM-DD.jsonl using server local date and a process lock, creating the directory on demand. Lookup SHALL scan newest dates backwards within the retention window and return every matching call record in file order within each file. Startup SHALL prune files older than that window once per server start. LLM_TRANSCRIPT_ENABLED SHALL default true; when false writes SHALL be no-ops and lookup SHALL explicitly report disabled rather than an empty successful lookup. LLM_TRANSCRIPT_RETENTION_DAYS SHALL default 14 and accept integers at least 1 through existing environment overrides. Operational storage/serialization/read/prune failures SHALL never propagate; they SHALL emit one best-effort stderr line and return.

#### Scenario: Records across dates
- **WHEN** matching and unrelated records are written on two local dates and lookup is requested for one call
- **THEN** only matching records are returned, newest file first and append order within each file, with full Unicode payloads preserved

#### Scenario: Retention boundary
- **WHEN** startup pruning runs with retention 14
- **THEN** today and the previous 13 local dates remain eligible and older dated transcript files are removed

#### Scenario: Disabled and broken storage
- **WHEN** transcripts are disabled, or storage is unwritable or a record is unserialisable
- **THEN** disabled writes do nothing and lookup reports disabled; storage failures return without raising and issue a best-effort stderr diagnostic

### Requirement: Correlated exchanges and terminal outcomes
Every guarded call SHALL generate one uuid4 hexadecimal call_id at entry, reused across all attempts and its operational events. Each real transport attempt SHALL write one exchange when settled, successful or failed, containing kind, call_id, zero-based attempt, ISO-8601 ts, layer, profile model, hostname-only endpoint_host, elapsed ms, full request body, HTTP status or null when absent, full parsed response or raw non-JSON response text, and null error or scrubbed error type/message. Every guarded call SHALL write exactly one terminal outcome containing kind, call_id, ts, layer, profile, total ms, result (ok/degraded/rejected), nullable reason, attempt validation-errors list, and final_text (accepted text only, otherwise null). Disabled profiles and unexpected errors SHALL still produce outcomes without inventing exchanges. Fake clients SHALL write no exchange. Existing retry/degrade behavior and exception propagation SHALL remain unchanged.

#### Scenario: Retry then degradation
- **WHEN** a recording real transport returns invalid output until the retry budget is exhausted
- **THEN** each attempt exchange and the single degraded outcome share the call_id with llm_call and retry events, record validation errors, and leave final_text null

#### Scenario: Accepted response
- **WHEN** an attempt passes schema and semantic validation
- **THEN** one ok outcome records the accepted final_text and each settled attempt has one exchange

#### Scenario: No transport or unexpected error
- **WHEN** a profile is disabled, a fake client is used, or an unexpected pipeline/fallback error occurs
- **THEN** exactly one truthful terminal outcome is recorded, fake/disabled calls invent no exchanges, and unexpected errors are re-raised unchanged

### Requirement: Credential exclusion without prose redaction
Transcripts and operational events SHALL exclude API keys, request headers, authentication headers, and URL userinfo; endpoint_host SHALL contain only the hostname and error text SHALL retain existing key scrubbing. Player inputs, prompts, and model output SHALL be retained as payload content, not blanket-redacted. Credential-bearing error text SHALL be scrubbed before any transcript or operational write.

#### Scenario: Credential-bearing request failure
- **WHEN** a request uses a configured API key, headers, and URL userinfo and fails with error text containing those credentials
- **THEN** no transcript or operational record contains those credentials or any request header, while non-secret request messages remain available
