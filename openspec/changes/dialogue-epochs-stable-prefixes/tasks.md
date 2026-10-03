## 1. Implement the bounded behavior

- [ ] 1.1 Implement explicit epochs and retained summary provenance; verify failed/successful compaction and bounded offline history.
- [ ] 1.2 Refactor all dialogue prompt callers to stability-ordered sections and location-only current frames; verify same-epoch append-only bytes, cross-actor global prefixes and hard budgets.
- [ ] 1.3 Integrate version/persona invalidation and observability hashes/tokens; verify stale-persona, historical revisions and provider-caching-disabled behavior.
- [ ] 1.4 Measure rendered epoch-summary inputs and outputs for the supported profiles, commit per-profile summary soft targets/hard limits and the calibration report including completion/Deep Recall/safety reservations; verify oversized summaries remain bounded and preserve original turns.

## 2. Evidence and handoff

- [ ] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [ ] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [ ] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [ ] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate dialogue-epochs-stable-prefixes --strict`; record exercised results and leave broad browser/evidence gates CI-owned.
