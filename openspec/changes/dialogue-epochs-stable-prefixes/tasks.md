## 1. Implement the bounded behavior

- [x] 1.1 Implement explicit epochs and retained summary provenance; verify failed/successful compaction and bounded offline history.
- [x] 1.2 Refactor all dialogue prompt callers to stability-ordered sections and location-only current frames; verify same-epoch append-only bytes, cross-actor global prefixes and hard budgets.
- [x] 1.3 Integrate version/persona invalidation and observability hashes/tokens; verify stale-persona, historical revisions and provider-caching-disabled behavior.
- [x] 1.4 Measure rendered epoch-summary inputs and outputs for the supported profiles, commit per-profile summary soft targets/hard limits and the calibration report including completion/Deep Recall/safety reservations; verify oversized summaries remain bounded and preserve original turns.

## 2. Evidence and handoff

- [x] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [x] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [x] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [x] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate dialogue-epochs-stable-prefixes --strict`; record exercised results and leave broad browser/evidence gates CI-owned.

## Exercised implementation evidence (2026-10-04)

- 55 focused epoch, durable-dialogue, prompt and prompt-shipment tests passed.
- 88 NPC dialogue and profile regressions passed, preserving stale-persona rejection.
- 21 environment profile/inventory integration tests passed.
- Recorded compaction and disabled-profile smoke exercised the actual narrative
  owner, immutable snapshots, guardrail and FakeLLMClient without live services.
- Contract gate passed: 1829 requirements covered, zero traceability/lint
  violations, manifest checks and 18 repository contracts passed.
- Strict change validation passed. Calibration measurements are committed in
  `docs/development/dialogue-epoch-calibration.md`.
- Main-ID annotations cover existing substantive contracts. New dialogue-epochs
  IDs are intentionally obtained by the future sync/archive owner only after
  delta synchronization; this apply does not edit canonical main specs.
- Browser suites and complete evidence verification remain CI-owned.
