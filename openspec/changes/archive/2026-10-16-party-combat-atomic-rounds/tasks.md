# Tasks

Total estimate: **7.5 hours**, including implementation, focused verification, documentation and integration. Direct prerequisites and file/spec conflicts are in proposal.md and the shared batch contract. Each group lands its own tests/docs; the final group checks integration.

## 1. Bounded implementation and evidence (1.5h)

- [x] 1.1 Attach automatic execution to the last confirmation with durable revision admission/receipt; test duplicate final confirm, concurrent stale requests and terminal retries.

  Evidence: `test_final_confirmation_commits_once_and_clears_draft`,
  `test_technical_failure_preserves_accepted_final_draft`,
  `test_receipt_failure_after_terminal_clock_and_clear_restores_round`
  (terminal retry after the clock/clear writes, plus the fresh-interpreter
  receipt read) and the concurrent final-confirmation coverage in
  `test_combat_session_persistence.py`.

## 2. Bounded implementation and evidence (1.5h)

- [x] 2.1 Replace allied policy provisioning with one selected request per eligible actor, explicitly cap interactive allied positive action counts at one selected skill/item and retain zero locks; test no duplicate/fallback while enemy/noninteractive extra slots and liveness remain unchanged.

  Evidence: `_party_round_provider` plus the `is_interactive_ally` cap in
  `world/rules/combat/rounds.py::run_round`;
  `test_interactive_allies_cap_skill_and_item_without_enemy_cap_or_fallback`
  and the unchanged lock/slot/liveness scenarios in
  `test_initiative_and_turn_loop.py`.

## 3. Bounded implementation and evidence (1.5h)

- [x] 3.1 Extend the existing round transaction and cache snapshots to every actor, inventory mirror, draft, receipt and terminal write; inject failures after item, metadata and settlement writes and retry recovered draft.

  Evidence: the receipt and clock surfaces joined `_snapshot_round_touched`/
  `_snapshot_round_clock`; `test_outer_rollback_restores_the_deleted_mirror_and_surfaces`,
  `test_upkeep_failure_after_item_use_restores_everything`,
  `test_terminal_settlement_failure_after_item_use_restores_everything`,
  `test_termination_between_effects_and_persist_leaves_no_half_round`,
  `test_rolled_back_round_emits_no_round_boundary`,
  `test_a_fault_after_the_utility_action_rolls_back_everything` and the
  `COMMIT_FAILED` whole-round abort cover the injected failures and the
  retained-draft retry. The injected faults were re-pointed at the round
  body's own write after draft admission began writing first.

## 4. Bounded implementation and evidence (1h)

- [x] 4.1 Prove mid-round invalid target loses its action with no retarget/cost while prior actions/upkeep persist; prove valid misses still cost and upkeep/time occur once.

  Evidence: `test_earlier_defeat_invalidates_selected_spell_without_retarget_or_cost`,
  `test_valid_spell_miss_pays_cost_and_consumes_one_round` and
  `test_mid_round_invalidation_consumes_the_round_without_consuming_the_item`.

## 5. Bounded implementation and evidence (1h)

- [x] 5.1 Update related canonical requirement/test IDs, session/provider docs and manifests; retain existing nonlethal/exam policy, session stamps and observation journals.

  Evidence: the four MODIFIED ids are annotated on their establishing tests;
  the module/facade docstrings and the provider docstrings now describe draft
  admission; `tools.contract_gate` passes its manifests contract; the
  nonlethal/exam policy, session stamps and observation journals are unchanged
  and stay green in `test_combat_session_recovery.py`,
  `test_guild_exams.py` and `test_rules_observability.py`.

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

- [x] 6.1 Run focused transactional session, provider and item-turn tests plus tools.contract_gate and observability lint/focused event tests; record durable restart and concurrency outcomes.

  Evidence: focused modules pass standalone (session persistence, recovery,
  flow, item combat turns, initiative/action counts, party combat, round
  records, combat commands, friendly fire, sexual-coercion turn cost, rules
  observability, monster-AI selection, manual-campaign reports, markers, party
  offline loop, dialogue memory, climax settlement), plus the wider sweep of
  the 81 modules that touch the session; `tools.contract_gate` (traceability,
  the two lints, shard manifests, contracts) and
  `openspec validate --strict` pass. Durable restart, concurrency and the
  inapplicability of the process-local flag are recorded in design.md.
