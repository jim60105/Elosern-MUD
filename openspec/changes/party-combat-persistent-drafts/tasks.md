# Tasks

Total estimate: **6.5 hours**, including implementation, focused verification, documentation and integration. Prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Every group lands its own relevant tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [ ] 1.1 Add strict serializable draft/revision fields and round-trip tests; reject malformed kinds/IDs and verify no live objects are persisted.

## 2. Bounded implementation and evidence (1.5h)

- [ ] 2.1 Implement edit replacement, CAS draft_version and required-set recomputation; test partial, stale and changed-membership behavior without rolls, resources, AI or upkeep.

## 3. Bounded implementation and evidence (1h)

- [ ] 3.1 Add pure all-command preflight returning retained valid entries and member-specific reselection reasons; test equipment invalidation and capability/resource changes.

## 4. Bounded implementation and evidence (1h)

- [ ] 4.1 Restore unfinished confirmed drafts through reconnect/startup and clear them on session cleanup; test committed reload and unchanged round/world time.

## 5. Bounded implementation and evidence (0.75h)

- [ ] 5.1 Document durable record/API and revision semantics, update canonical annotations and shard ownership in the same tasks.

## 6. Integration gate (0.75h)

- [ ] 6.1 Run focused persistence/recovery/draft tests and tools.contract_gate; record restart evidence without claiming round execution from this slice alone.
