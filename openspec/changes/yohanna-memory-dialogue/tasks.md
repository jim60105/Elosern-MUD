## 1. Implement the bounded behavior

- [ ] 1.1 Replace every dialogue history writer/reader with durable pair-turn orchestration; verify restart, duplicate settlement, bounded-view preservation and stale-persona tests.
- [ ] 1.2 Wire permissioned context into existing reply generation; verify paired informed/uninformed, relevant versus unrelated recall, schedule and offline regressions.
- [ ] 1.3 Author and wire Yohanna plus the initial protection/revisit route using existing lore contracts; verify registered data-contract checks and synthetic multi-day acceptance chain.
- [ ] 1.4 Run a controlled changed-path smoke with recorded generation (and a local live profile only when intentionally configured); verify selected provenance and response delivery without asserting live wording.

## 2. Evidence and handoff

- [ ] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [ ] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [ ] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [ ] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate yohanna-memory-dialogue --strict`; record exercised results and leave broad browser/evidence gates CI-owned.
