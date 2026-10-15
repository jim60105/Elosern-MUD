# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration. Prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Every group lands its own relevant tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [ ] 1.1 Add closed tactical requests and validated constants; test zero MP/SP, consecutive use, actor eligibility and enemy nonavailability.

## 2. Bounded implementation and evidence (1.5h)

- [ ] 2.1 Activate Defend/Dodge at the round-start hook and implement shared scalar inputs; prove slow actor protection, 40 to 26 flooring, bypass/upkeep exceptions and no-check behavior.

## 3. Bounded implementation and evidence (1.5h)

- [ ] 3.1 Use the same context in AI estimation and every per-strike hit check; pin solid-hit/critical placement, AREA checks and no initiative/flee changes.

## 4. Bounded implementation and evidence (1h)

- [ ] 4.1 Test round-end, rollback, disconnect and next-round expiry without stacking or durable buff leakage; update affected developer arithmetic docs.

## 5. Bounded implementation and evidence (0.75h)

- [ ] 5.1 Update canonical traceability and fixture/shard ownership; migrate scalar callsites without optional compatibility branches.

## 6. Integration gate (0.75h)

- [ ] 6.1 Run focused tactical/scalar/estimator/round tests and tools.contract_gate; run observability lint only if boundary logging changed.
