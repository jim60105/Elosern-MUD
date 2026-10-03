## 1. Implement the bounded behavior

- [ ] 1.1 Implement durable engagement extraction and eligibility filters; verify passive receipt, knowledge/location/schedule failures and confirmed new direction.
- [ ] 1.2 Implement deterministic scoring/ties/cooldowns and focus limits; verify repeated offline ordering and preservation of unselected threads.
- [ ] 1.3 Calibrate weights/limits on synthetic labeled candidate sets and record measured decisions; verify expected eligible/focus results.

## 2. Evidence and handoff

- [ ] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [ ] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [ ] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [ ] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate narrative-attention --strict`; record exercised results and leave broad browser/evidence gates CI-owned.
