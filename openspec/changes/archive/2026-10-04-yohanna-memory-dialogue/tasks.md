## 1. Implement the bounded behavior

- [x] 1.1 Replace every dialogue history writer/reader with durable pair-turn orchestration; verify restart, duplicate settlement, bounded-view preservation and stale-persona tests.
- [x] 1.2 Wire permissioned context into existing reply generation; verify paired informed/uninformed, relevant versus unrelated recall, schedule and offline regressions.
- [x] 1.3 Author and wire Yohanna plus the initial protection/revisit route using existing lore contracts; verify registered data-contract checks and synthetic multi-day acceptance chain.
- [x] 1.4 Run a controlled changed-path smoke with recorded generation (and a local live profile only when intentionally configured); verify selected provenance and response delivery without asserting live wording.

## 2. Evidence and handoff

- [x] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [x] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [x] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [x] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate yohanna-memory-dialogue --strict`; record exercised results and leave broad browser/evidence gates CI-owned.

## Exercised evidence

- Canonical IDs obtained from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/yohanna-ids.json`; only current main IDs were annotated. No delta sync or archive was performed.
- Focused typeclass/owned-dialogue/inventory batch: 65 tests, 64 passed initially; the authored-card MP warning was fixed and its contract passed in the subsequent 41-test batch.
- Delivery/guardrail batch: 93 tests passed (`commands.tests.test_party_commands`, both changed exploration modules, dialogue prompt and retry modules).
- Projection/recall/roster/authored-card batch: 41 tests passed.
- Final recorded/offline changed-path smoke: all 8 tests passed in `world.narrative.tests.test_dialogue_memory` and `world.imports.tests.test_yohanna_demo`. The real combat/projection/three-day clock/revisit path checked selected source provenance and delivered fixture speech; no live generation or image service was configured.
- `uv run --locked python -m tools.contract_gate`: passed, 1,828 requirements covered, zero traceability/lint/manifest violations, 18 repository contract tests passed.
- `openspec validate yohanna-memory-dialogue --strict`: valid.
- The guard rejected one initial 198-test discovery and one chained Evennia command before execution; subsequent supported standalone invocations stayed below 100 tests.
- A rollback-cache test initially found ghost room occupants after a failed demo setup; cache compensation was fixed and the final 8-test smoke passed.
- Browser, full-suite, and aggregate evidence/coverage checks remain CI-owned. Player command documentation is intentionally unchanged because no command surface changed.
