# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [ ] 1.1 Implement the shared agility contest and eligibility/no-pursuer/no-acting-allies branches; test slowest ally, fastest pursuer and ignored accuracy/Dodge.

## 2. Bounded implementation and evidence (1.5h)

- [ ] 2.1 Commit all-party success with carried downed members, no invented destination/healing and one elapsed round; test enemy inactivity and terminal cleanup/time once.

## 3. Bounded implementation and evidence (1.5h)

- [ ] 3.1 Implement failure as consumed allied opportunities plus enemy initiative/upkeep, without tactical benefits; test defeated pursuers, invalid enemy capability and fresh next draft.

## 4. Bounded implementation and evidence (1h)

- [ ] 4.1 Exercise rollback after flee/session/time writes, double confirm and normal-round race; prove no subset escape or duplicate settlement.

## 5. Bounded implementation and evidence (0.75h)

- [ ] 5.1 Document party versus enemy flee contracts, update canonical IDs, test annotations and shard ownership.

## 6. Integration gate (0.75h)

- [ ] 6.1 Run focused retreat/disengage/provider/settlement tests plus tools.contract_gate and observability lint/focused event tests.
