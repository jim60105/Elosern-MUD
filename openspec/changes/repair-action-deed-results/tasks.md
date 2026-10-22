# Tasks

## 1. Normalize authoritative settled action results

- [x] 1.1 Replace the optional resistance-roll parsing in `world/narrative/action_adapters.py` with the authoritative absent-roll convention, then verify a real auto-comply adult action resolves through the rules resolver without raising and its evidence retains the actual verdict.
- [x] 1.2 Normalize the effect kinds actually emitted by production handlers (`pleasure_gain`, `buff_applied`, `self_buff_applied`, `buffs_cleansed`) and remove the divergent alternate vocabulary path, verifying one committed test per family retains actor, recipient and result.
- [x] 1.3 Record the actual settled effect amount rather than the requested amount, verifying a clamped gain leaves an untouched recipient unchanged and states the committed result.
- [x] 1.4 Add a focused producer-to-renderer regression that settles a legal auto-comply adult action and verifies its evidence is stored and readable, replacing any seed-only payload assertion.
- [x] 1.5 Document the accepted settled-result vocabulary beside the existing narrative evidence contract and verify the document matches the adapter's accepted kinds.

## 2. Preserve authorized adult result families

- [x] 2.1 Extend the recipient-authorized projection in `world/narrative/recent_deeds.py` with own-state transitions, counter changes and distinct resistance outcomes, verifying actor, recipient and untouched-control projections differ only by knowable fields.
- [x] 2.2 Keep those result families through grouping and rendered JSON with their supporting source IDs, verifying a rendered-feed test retains each family and its actual roles.
- [x] 2.3 Join milestones attached to an action occurrence before repetition compression, verifying consecutive matching actions with one attached milestone count twice and retain every source.
- [x] 2.4 Add the facade event for repaired evidence normalization and verify `uv run --locked python -m tools.observability_lint check` passes with the focused adapter tests in the same batch.

## 3. Integration verification

- [x] 3.1 Run a real adult and skill settlement through committed storage and selection into rendered material, verifying structured adult results survive prompt construction and counts represent committed occurrences only.
- [x] 3.2 Inject a failure after the evidence write but before the action commit, verifying the action, effects, gauges and evidence roll back together and no nomination is admitted.
- [x] 3.3 Run the focused action and title test labels plus `uv run --locked python -m tools.contract_gate`, verifying no regression outside the changed contracts.
