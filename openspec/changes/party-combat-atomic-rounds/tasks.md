# Tasks

Total estimate: **7.5 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [ ] 1.1 Attach automatic execution to the last confirmation with durable revision admission/receipt; test duplicate final confirm, concurrent stale requests and terminal retries.

## 2. Bounded implementation and evidence (1.5h)

- [ ] 2.1 Replace allied policy provisioning with one selected request per eligible actor, explicitly cap interactive allied positive action counts at one selected skill/item and retain zero locks; test no duplicate/fallback while enemy/noninteractive extra slots and liveness remain unchanged.

## 3. Bounded implementation and evidence (1.5h)

- [ ] 3.1 Extend the existing round transaction and cache snapshots to every actor, inventory mirror, draft, receipt and terminal write; inject failures after item, metadata and settlement writes and retry recovered draft.

## 4. Bounded implementation and evidence (1h)

- [ ] 4.1 Prove mid-round invalid target loses its action with no retarget/cost while prior actions/upkeep persist; prove valid misses still cost and upkeep/time occur once.

## 5. Bounded implementation and evidence (1h)

- [ ] 5.1 Update related canonical requirement/test IDs, session/provider docs and manifests; retain existing nonlethal/exam policy, session stamps and observation journals.

  Traceability ordering (`docs/development/spec-test-traceability.md`):
  `tools.spec_traceability` resolves ids against main specs under
  `openspec/specs/` only, so the ids this change ADDS (`final member
  confirmation …`, `round revisions execute at most once …`, `execution-time
  invalidation …`) do not exist yet and cannot be annotated now: an annotation
  with one of them fails `tools.spec_traceability check` with
  `unknown-requirement-id`. The four MODIFIED requirement ids
  (`a-round-and-its-settlement-form-one-atomic-persistence-unit`,
  `combat-boundaries-emit-observability-events`,
  `combat-item-use-occupies-one-initiative-ordered-round`,
  `the-turn-loop-consumes-actions-per-turn-as-the-round-s-action-count-with-zero-skipping-before-actionresolver-is-called`)
  are annotated on their establishing tests now.

  The two REMOVED ids still exist in the main spec until `openspec archive`
  syncs the delta, so the SEVEN existing annotations that reference them pass
  `check` today (they are what currently keeps those two requirements covered);
  no new test may take them on. At archive time, after the sync removes the two
  headings, (a) annotate the complete-draft, at-most-once-revision and
  execution-invalidation tests with the three new canonical ids and (b) re-point
  the seven annotations across these six files
  (`test_combat_party.py`,
  `test_combat_session_recovery.py`, `test_item_combat_turn.py`,
  `test_engage_and_player_rounds.py` ×2, `test_engage_group_flow.py`,
  `test_submission_structural_contract.py`) onto the surviving ids named in the
  delta's own Migration notes, or those ids become `unknown-requirement-id`.

## 6. Integration gate (1h)

- [ ] 6.1 Run focused transactional session, provider and item-turn tests plus tools.contract_gate and observability lint/focused event tests; record durable restart and concurrency outcomes.
