## 1. Implement the bounded behavior

- [ ] 1.1 Register StoryDirector prompt/schema and bounded candidate/request context; verify new-story gating, separate collaborator secrets and valid none.
- [ ] 1.2 Implement durable decision/beat scheduling and source uniqueness; verify one-beat maximum, restart deduplication and same-thread races.
- [ ] 1.3 Implement supported effect routing and stale-state revalidation; verify unsupported quest/appointment/physical effects and unauthorized-owner writes reject atomically.
- [ ] 1.4 Add end-to-end synthetic existing-story and validated confirmed-request tests through the authoring-record boundary with recorded generation; verify executable beats and no filler on exhaustion without requiring the sleep UI. Complete the public dream-to-beat smoke when dream-sleep-surface is also applied.

## 2. Evidence and handoff

- [ ] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [ ] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [ ] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [ ] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate story-director-beats --strict`; record exercised results and leave broad browser/evidence gates CI-owned.
