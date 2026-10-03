## 1. Implement the bounded behavior

- [ ] 1.1 Implement permissioned composition and thin descriptors using existing contracts; verify repeated inputs and inaccessible-source tests.
- [ ] 1.2 Implement rendered budget accounting and measured profile settings; verify headings, reservations and hard overflow.
- [ ] 1.3 Persist snapshots and generation invalidation; verify mutation-after-capture, restart and retry provenance.
- [ ] 1.4 Extend facade/catalog events; verify normal ID/count logging and controlled debug opt-in.

## 2. Evidence and handoff

- [ ] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [ ] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [ ] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [ ] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate narrative-context-snapshots --strict`; record exercised results and leave broad browser/evidence gates CI-owned.
