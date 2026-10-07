## Why

Playtesting needs a live operational overview without parsing logs or exposing out-of-character diagnostics in the game client. The S2a transcript makes recent LLM failures explainable from the portal.

## What Changes

- Add bounded in-process recent LLM and issue buffers fed after facade log writes.
- Add read-only dashboard snapshots and validated transcript-detail APIs with independent section failure handling.
- **BREAKING** Remove /gm/api/health and its callers/tests; fold Django/database health into /gm/api/dashboard without a compatibility route.
- Replace the S1 overview with a five-second, visibility-aware dashboard and call payload drawer using existing GM components.
- Add deterministic backend/frontend coverage, Storybook coverage, settings documentation, shard registration, and requirement traceability.

## Capabilities

### New Capabilities
- `gm-operations-dashboard`: Bounded recent events, read-only operational snapshot, transcript lookup, and polling/payload UI.

### Modified Capabilities
- `gm-portal-access-api`: Replace the foundation health route with protected dashboard and transcript routes.
- `gm-portal-spa`: Replace the skeleton overview while preserving isolated build and history navigation.
- `observability-logging`: Allow the facade to feed its observability-local recent-event sink.

## Impact

One engineer-day vertical dashboard slice, reusing landed web/gm/, gm_required/gm_path, API envelopes, lib/api.js and admin-app components. Requires landed S1 and S2a, no active LLM probing, durable event store, historical analytics, state mutation, migrations, or game-client changes. Source: docs/superpowers/specs/2026-10-06-gm-portal-s2-dashboard-design.md §3.

## Batch:

depends-on: gm-portal-s1-foundation
depends-on: gm-portal-s2a-llm-transcript

Code conflicts: S1 owns web/gm/ routes/tests and admin-app overview; S2a shares observability, settings docs, and .github/evennia-shards.json. Apply only after both land; do not implement in parallel with S2a.
