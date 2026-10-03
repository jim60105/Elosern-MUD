## 1. Implement the bounded behavior

- [x] 1.1 Implement record/revision/effective metadata and generation counters; verify immutable originals and revision replay.
- [x] 1.2 Implement transactional owner projection and progress consumption; verify interruption and duplicate sources cannot duplicate cognition.
- [x] 1.3 Implement normal/historical access views; verify informed/uninformed owners and private-authoring exclusion before scoring.

## 2. Evidence and handoff

- [x] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [x] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [x] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [x] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate narrative-owner-memory --strict`; record exercised results and leave broad browser/evidence gates CI-owned.
