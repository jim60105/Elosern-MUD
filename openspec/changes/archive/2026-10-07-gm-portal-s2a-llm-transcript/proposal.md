## Why

Operators cannot inspect the request, response, or validation history behind silent LLM degradation. The approved S2 design makes retained call transcripts the diagnostic source before the dashboard consumes them.

## What Changes

- Add daily, retained JSONL transcripts with correlated exchange and outcome records for every guarded LLM call.
- Stamp guardrail, transport, retry, and cached-token events with one call identifier.
- **BREAKING** Repeal the no-prose-in-logs rule: restore letter arguments/body and dream-input diagnostics while preserving credential exclusion and bounded single-line operational logs.
- Amend the observability design and AGENTS.md to remove contradictory blanket prose prohibitions; document transcript settings and startup pruning.

## Capabilities

### New Capabilities
- `llm-transcript`: Retained full-payload call diagnostics, correlation, disabled behavior, and credential safety.

### Modified Capabilities
- `observability-logging`: Permit prose, truncate every context value, and restore affected operational event fields.

## Impact

One engineer-day observability slice using existing guardrail/transport and environment override seams; no dashboard, database migration, compatibility layer, new dependency, or compose change. Affects world/observability, world/ai, correspondence/dream callers, startup/settings, logging guidance, tests, and shard registration. Approved source: docs/superpowers/specs/2026-10-06-gm-portal-s2-dashboard-design.md §2.

## Batch:

depends-on: gm-portal-s1-foundation

S1 must be landed (it is now on master). Code conflicts: S2b shares observability facade/tests, settings documentation, and .github/evennia-shards.json; apply sequentially. S2a produces the call_id and transcript contracts S2b reads.
