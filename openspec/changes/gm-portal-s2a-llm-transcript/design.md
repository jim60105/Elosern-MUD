## Context

See proposal.md for motivation. The approved S2 design §2 amends the logging design. S1 has landed on master. guarded_call owns retry/validation/degrade settlement; OpenAICompatClient owns real HTTP exchange settlement. Option-proposal and dialogue-epoch wrappers must preserve descriptor metadata rather than become additional writers.

## Goals / Non-Goals

**Goals:** Full diagnostic records without changing deterministic behavior, credential safety, one outcome per call, bounded operational prose, one engineer-day using existing seams.

**Non-Goals:** Dashboard/buffer, analytics, ORM records, active probes, compatibility layers, migrations, compose edits, new logging framework or dependencies.

## Decisions

1. Add world/observability/transcript.py with only stdlib and Django settings dependencies. Public write(record: dict) -> None, find(call_id: str) -> list[dict], prune() -> None use a shared process lock for append/read/prune. find reports disabled through an explicit enabled-status seam consumed by S2b (disabled is not an exception or an empty-list not-found). Ordinary operational failures produce one contained stderr line; stderr failure is contained too. Use local dates, UTF-8 and ensure_ascii=False. Retention includes today and retention_days-1 earlier dates; scan newest files first and preserve line order. Isolate malformed lines/read failures so diagnostics cannot interrupt gameplay. Keep a synchronous file sink rather than adding a worker/queue lifecycle.
2. Generate uuid4().hex before profile resolution at guarded_call entry. Extend frozen ChatRequestDescriptor with optional call_id and attempt defaults, preserve them through wrappers, and set attempt on each retry descriptor. Keep correlation outside wire bodies/headers. Consolidate terminal recording with the existing llm_call terminal seam, retaining rejected-on-raising-fallback and original exception semantics. Thread actual call_id to correspondence/dream failure sites even when a Deferred fails; do not infer it from the newest log entry.
3. Transport writes exchange after every settled request, including network failure and invalid/non-JSON responses, while guardrail writes outcome only. Record exactly the approved §2.3 fields, nullable status/error/reason, attempt validation errors and final accepted text. Fake clients record outcomes only. Capture full body before output extraction; never serialize headers, API keys, or credential-bearing URLs. Reuse _scrub_key and strip URL userinfo from diagnostics without dropping prompt prose.
4. Existing operational facade remains the only operational sink. Enforce single-line and 200-character truncation for all context types, add call_id to llm_call/retry/cached usage, and restore only the approved correspondence/dream fields. Dedicated full-payload transcript writes are confined to the observability module; production callers do not import logging or Evennia logger.
5. Wire LLM_TRANSCRIPT_ENABLED=True and LLM_TRANSCRIPT_RETENTION_DAYS=14 (integer >=1) through the existing environment mechanism. Add prune once to at_server_start's ordered startup catalog and migrate ordering assertions. Existing evennia-logs volume persists files; no compose change.
6. Amend logging design §3.1, §3.4 rules-list intent (the current file places the AGENTS rules in §3.3), and affected catalog rows: cmd_in for letters, llm_call/retry/cached tokens, correspondence_reply_* and dream_surface_generation_failed. Remove contradictory blanket prose prohibitions in AGENTS.md and old context/dream-session comments, retaining field-specific minimal event choices and private narrative access. Update .env.example and docs/development/settings-and-environment.md.

## Risks / Trade-offs

- Full prose persists on disk: retain the configured window and privileged future lookup; credentials remain prohibited.
- Disk errors must not affect gameplay: temp-directory tests cover serialization, permissions, settings and read/prune failures, including stderr containment.
- Cross-wrapper metadata loss: recording-transport tests cover actual guarded retries and cached-token correlation; existing caller assertions are updated, not bypassed.
- Traceability indexes main specs only: obtain canonical IDs using tools.spec_traceability list after synchronization, annotate substantive tests with literal covers_requirement IDs, and never invent IDs or claim proposed specs are already covered.
