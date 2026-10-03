## 1. Implement the bounded behavior

- [ ] 1.1 Author and expose branch letter service via existing anchoring plus text send/collect/read commands; verify any-branch acquisition, recipient ambiguity and context rejection.
- [ ] 1.2 Add browser server actions/read models and client controls with matching text behavior; verify unauthorized owner and uncollected-body requests are rejected.
- [ ] 1.3 Record first-read transactionally once and preserve collected unread state; verify portable reread and duplicate submissions.
- [ ] 1.4 Update both command docs and their contract tests; verify actual keys/aliases/syntax/context agree with server behavior.

## 2. Evidence and handoff

- [ ] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [ ] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [ ] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [ ] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate correspondence-player-surface --strict`; record exercised results and leave broad browser/evidence gates CI-owned.
