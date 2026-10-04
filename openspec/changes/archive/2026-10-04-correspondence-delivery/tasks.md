## 1. Implement the bounded behavior

- [x] 1.1 Implement immutable letter/send records and indexed identity/due query; verify recipient/body preflight and one-hour boundary without movement effects.
- [x] 1.2 Register correspondence_delivery and extend fixed stage order and affected exact-order tests; verify command/combat/skip and non-hour-aligned sends.
- [x] 1.3 Integrate table/progress transactions and cache invalidation with clock rollback; verify late-stage failures, restart repetition and offline guaranteed delivery.

## 2. Evidence and handoff

- [x] 2.1 Add synthetic behavior tests for every delta scenario and use recorded/FakeLLMClient responses only; verify no permanent test calls live model/image services and any shipped-lore test is a registered data-contract test.
- [x] 2.2 Register each new/moved Evennia test module in exactly one `.github/evennia-shards.json` shard; obtain existing canonical main requirement IDs with `uv run --locked python -m tools.spec_traceability list` and annotate substantive tests. After delta sync makes new main IDs available, obtain them from that same tool rather than guessing; verify traceability and shard contracts.
- [x] 2.3 Update owning developer documentation/changelog and applicable command documentation, extend the observability catalog for new boundary events, and use only `world.observability` with IDs/counts/context and exception chains; verify logging privacy and focused facade assertions.
- [x] 2.4 Run focused tests, the actual changed-path recorded/offline smoke, `uv run --locked python -m tools.contract_gate`, and `openspec validate correspondence-delivery --strict`; record exercised results and leave broad browser/evidence gates CI-owned.

## Exercised evidence

- Focused Evennia run: correspondence delivery, clock, instance-stage wiring,
  and startup observability — 72 tests passed.
- Changed-path offline smoke: the seven correspondence tests passed, exercising
  actual send/table persistence, clock advancement, rollback, exact deadlines,
  command/combat/skip sources, and restart repetition without any generative I/O.
- Contract gate passed: all 1829 main requirements covered, zero traceability,
  observability, or test-data violations; manifest checks and 18 contracts passed.
- `openspec validate correspondence-delivery --strict` passed.
- Final single-round duck found the generic startup projector would consume
  correspondence progress. Reserved projector version 2 for its owning consumer
  and added startup-equivalent recovery assertions; the 72-test focused batch
  and contract/strict-spec gates passed again after the fix.
- The duck's non-blocking simultaneous send-identity race was addressed using
  atomic `get_or_create` and payload revalidation of the winning row. This does
  not add database-lock retries or claim parallel SQLite writers are supported.
- No player command changed, so command documentation is intentionally unchanged.
  New delta-only IDs remain for the archive/sync owner to obtain from the canonical
  listing after sync; the existing atomic-clock ID was obtained from that listing.
