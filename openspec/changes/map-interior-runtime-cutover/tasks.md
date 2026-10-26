# Tasks

## 1. Closed implementation units

- [ ] 1.1 Convert all permanent room/prose/topology/scene sources, preserving place-key joins and special links, delete duplicate service/bootstrap declarations and document new ownership with temporary comparison evidence.
- [ ] 1.2 Make interior synchronization consume the map snapshot independently of service records; test standalone and service interiors, repeated sync, no duplicate spawning and unchanged mutable host/stock state.
- [ ] 1.3 Implement complete candidate validation and immutable bundle publication with authoritative external checks and partition freshness; inject bad references, stale artifact and persistent sync failure and assert prior registry/persistent/cache state remains intact.
- [ ] 1.4 Migrate every remaining map consumer family listed in the caller table, replace obsolete source contracts and update both command docs only if an intentional command surface changes.
- [ ] 1.5 Update full place/interior/grid-sync deltas, traceability and CI ownership; remove conversion tools and run focused adoption/sync and contract gates.

## Workflow follow-up

- This proposal is ready for review only. Implementation requires a new explicit apply assignment.
- Before eventual archive, obtain canonical requirement IDs from the effective merged specs and attach substantive discoverable tests; no uncovered-requirement waiver or new copied-data pin is permitted.
