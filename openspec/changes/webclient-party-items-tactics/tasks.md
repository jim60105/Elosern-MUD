# Tasks

Total estimate: **7 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [ ] 1.1 Implement actor-local item list/detail/target/review and shared command payloads; test companion-only stock, no-effect disabled reasons, SELF and targeted item scopes.

## 2. Bounded implementation and evidence (1h)

- [ ] 2.1 Enable Defend/Dodge/Taunt rows with authoritative availability and stage enemy selection; test zero-cost display, valid target loss and no fake effects on draft save.

## 3. Bounded implementation and evidence (1.5h)

- [ ] 3.1 Route in-combat drawer use through the same actor command flow while preserving free bag/equipment operations; test no actorless use bypass, no companion equipment UI and revalidation after equipment changes.

## 4. Bounded implementation and evidence (1h)

- [ ] 4.1 Extend warnings and focus/lock state to item/tactic paths; test duplicate click, cancel/back, actor switching, stale inventory and preserved confirmed drafts.

## 5. Bounded implementation and evidence (1h)

- [ ] 5.1 Add real component/stories and bounded browser journey for companion item and tactics; update client command docs, canonical IDs and shard ownership.

## 6. Integration gate (1h)

- [ ] 6.1 Run focused Node/Vitest/item-adapter tests and one bounded browser method plus tools.contract_gate; verify quantities change only from canonical committed panels.
