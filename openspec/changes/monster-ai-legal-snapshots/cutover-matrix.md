# Assertion cutover and annotation ledger

This change adds a new capability, `monster-ai-decision-inputs`, and modifies
no existing requirement, so no canonical ID is retired.

## Edited assertions (no retirement)

| Edited assertion | Role | Why it changed | Replacement evidence |
| --- | --- | --- | --- |
| `world.rules.tests.test_action_preview.AdjustedCostPreviewTests._bundle` (and the inline patch list in `...test_fractional_grant_percentage_parity_across_all_three_surfaces`) | The adjusted-cost parity fixtures patched `world.rules.action_preview.evaluate_combat_modifiers_no_create`. | The modifier read that `preview_skill` and `revalidate_submission` consume now lives in `world.rules.action.gates`, the shared gate module the resolver already used. The old preview-side binding no longer exists, so the patch target moved; every assertion and its expected value is unchanged. | The same three parity tests (`test_preview_enables_exactly_the_casts_preflight_allows_under_reduction`, `...test_preview_rejects_exactly_the_casts_preflight_rejects_under_reduction`, `...test_scaled_percentage_floors_identically_across_all_surfaces`, `...test_fractional_grant_percentage_parity_across_all_three_surfaces`) still observe preview, preflight and resolve agreeing on one patched bundle. |

## ADDED requirements: annotations deferred to the archive sync

`tools.spec_traceability` indexes `openspec/specs/` only, so annotating a
delta-only ID during apply reports `unknown-requirement-id` and would leave
`tools.contract_gate` red on this branch. The repository convention
(`docs/superpowers/specs/2026-09-02-observability-logging-design.md` §6 and the
archived `monster-ai-variant-tuning` change) attaches new-capability
annotations in the same batch as the archive's main-spec sync. The IDs below
were generated, not guessed, against the equivalent delta-applied tree with
`tools.spec_traceability list --repo-root <merged tree>`; the archive step
attaches each one to the tests named here.

| Canonical ID | Establishing tests | What the assertions establish |
| --- | --- | --- |
| `monster-ai-decision-inputs::decision-snapshots-are-read-only-and-public` | `DecisionSnapshotReadTests.test_the_snapshot_reads_storage_without_touching_a_handler`, `...test_building_a_snapshot_reads_each_input_once_per_participant`, `...test_queued_intent_and_disguised_stats_cannot_reach_the_snapshot`, `...test_the_fingerprint_is_the_snapshot_and_is_read_only`, `MonsterAIDecisionBoundaryTests.test_the_snapshot_writes_nothing_and_attaches_no_handler`, `...test_a_materialized_entity_gains_no_persistent_state`, `...test_a_stale_gauge_timestamp_is_never_regenerated`, `...test_a_persisted_buff_projects_without_mounting_the_handler`, `...test_two_participants_sharing_a_display_key_keep_distinct_identities` | A snapshot is built from persisted trait and buff storage and a directly constructed skill handler, so booby-trapped and absent handlers stay absent, persistent attributes and the database row count are unchanged, a stale gauge timestamp is never regenerated, and two participants sharing a display key keep distinct identities. The fingerprint is derived from the snapshot's own content, is frozen, and is unchanged when queued intent or `disguised_stats` change while settled state is fixed. |
| `monster-ai-decision-inputs::utility-legality-shares-all-deterministic-settlement-gates` | `test_a_cast_prerequisite_rejects_before_scoring_with_settlement_reason`, `test_a_contact_prerequisite_rejects_the_self_plan_and_accepts_the_solo_one`, `test_a_forbidden_self_target_is_a_shape_mismatch`, `test_a_dead_target_rejects_the_plan_before_scoring`, `test_a_vanished_participant_is_reported_missing`, `test_lost_capability_rejects_the_plan`, `test_a_plan_outside_the_decision_scope_is_rejected`, `...test_preview_submission_and_preflight_reject_the_same_cast`, `...test_a_contact_prerequisite_rejects_the_self_cast_for_every_surface`, `...test_a_stale_plan_is_refused_by_the_resolver_without_payment`, `...test_a_legal_plan_settles_through_the_resolver` | A skill that passes the older preview subset but fails a real cast or interaction prerequisite is excluded before scoring with `CAST_CONDITION_UNMET`, and the preview, the submission revalidation and `ActionResolver.preflight` all agree on it; the satisfied pair is enabled or successful on all three. A forbidden self target is a shape mismatch, a dead or missing target and a lost capability reject, and a plan that was legal when decided is refused by the resolver after an earlier action kills the target, with no resource paid. |
| `monster-ai-decision-inputs::snapshot-reads-are-reused-within-one-decision` | `test_validation_reuses_one_read_set_across_every_plan`, `...test_building_a_snapshot_reads_each_input_once_per_participant`, `...test_the_next_decision_sees_intervening_state_and_the_old_one_does_not`, `...test_a_drained_resource_rejects_the_next_decision` | Enumerating more plans on one decision's read set moves no read counter at all, while the decision's own owned-skill metadata is read once and reused and the live trait handler is never read; the next decision is built from fresh reads, so it sees the intervening health, resource and buff changes while the earlier snapshot stays frozen. |

## Shared-legality boundary

The ordered gates live once, in `world/rules/action/gates.py`, and are consumed
by the resolver steps, `preview_skill`, `revalidate_submission` and the monster
AI plan validation. The optional decision read set is threaded through the
shared target pipeline, the interaction/displacement gates and the lineage
predicate; every caller that omits it keeps the pre-existing live reads, which
is why the resolver's own behavior is unchanged.
