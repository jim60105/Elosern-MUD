# Tasks

## 1. Carry authoritative combat provenance

- [ ] 1.1 Add a frozen combat provenance value (engagement identity, round ordinal, action-slot ordinal) to the existing rules execution context and construct it from the durable combat record, verifying ordinary, opening and compressed execution each reach the resolver with non-empty provenance.
- [ ] 1.2 Thread the provenance through combat round, slot and upkeep submissions without parsing `narration_scope` or display text for persistence identity, verifying no combat producer still derives identity from an optional battlefield attribute.
- [ ] 1.3 Allocate the same authoritative engagement identity for examination construction, verifying a simulated examination and a hostile engagement at the same tick and participants keep distinct encounter identities.

## 2. Cut over sources and joins

- [ ] 2.1 Build combat action source IDs from engagement, round, slot and actor, verifying the same skill in distinct slots or rounds produces distinct immutable occurrences at one world tick.
- [ ] 2.2 Build resolver-independent upkeep source IDs from engagement, round, entity and transition discriminator, verifying repeated upkeeps in one round do not overwrite each other.
- [ ] 2.3 Put the unique encounter identity into action, milestone and terminal evidence and make selection join only on it, verifying a zero-time surrender followed by a new engagement retains both terminal encounters in selector output.
- [ ] 2.4 Remove the combat cast/tick fallback and migrate synthetic constructors, verifying a missing combat provenance in a combat context fails closed rather than being relabeled as an out-of-combat cast.
- [ ] 2.5 Document the combat provenance and encounter join contract and verify the document matches the typed fields consumers read.

## 3. Integration verification

- [ ] 3.1 Execute a real multi-round combat with a repeated skill and settle its outcome, verifying the rendered feed retains the distinct actions and outcomes in one encounter group with correct sources and counts.
- [ ] 3.2 Replay committed action, upkeep and terminal settlement notifications, verifying the original sources and projection progress are reused without new occurrences or erased awards.
- [ ] 3.3 Inject a failure after evidence recording in a real engagement, verifying action results and evidence roll back with the encounter state.
- [ ] 3.4 Run the focused combat, narrative and title test labels plus `uv run --locked python -m tools.contract_gate`, verifying no unrelated consumer changed behavior.
