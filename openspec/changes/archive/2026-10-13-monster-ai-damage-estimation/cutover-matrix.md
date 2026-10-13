# Assertion cutover and annotation ledger

This change adds a new capability, `monster-ai-effect-estimation`, and modifies
no existing requirement, so no canonical ID is retired and no existing
assertion is replaced. The `legacy` decision body, the player-facing command
surface and the browser action surface are untouched: every retained legacy
assertion still establishes permanent legacy behavior, and the focused
regression labels listed below stayed green under the shared-scalar extraction
(`test_damage_bands`, `test_heal_effect_handler`, `test_effect_potency`,
`test_multi_strike_cap_widening`, `test_unconditional_multi_strike`,
`test_gauge_transfer`, `test_damage_divert`, `test_monster_ai_candidates`,
`test_monster_ai_snapshots`, `test_monster_ai_tuning`,
`test_monster_behaviour_profile`, `test_monster_behaviour_selection`,
`test_monster_behaviour_policy`, `test_conditional_damage`,
`test_terrain_marker`, `test_stat_breakdown`, `test_overwhelm_threshold`,
`test_npc_roster_validation`).

## ADDED requirements: annotation ledger

`tools.spec_traceability` indexes `openspec/specs/` only, so annotating a
delta-only ID during apply reports `unknown-requirement-id` and would leave
`tools.contract_gate` red on this branch. The repository convention (the
archived `monster-ai-legal-snapshots` and `monster-ai-bounded-candidates`
changes, `docs/development/spec-test-traceability.md`) therefore attaches
new-capability annotations in the same batch as the archive's main-spec sync;
this ledger records the agreed deferral rather than representing the attachment
as already done. The IDs below were generated, not guessed, against the
equivalent delta-applied tree with
`uv run --locked python -m tools.spec_traceability --repo-root <tree> list
--json-output <path>` (the delta spec materialized as
`openspec/specs/monster-ai-effect-estimation/spec.md` beside the current
`openspec/specs/`); that run reported 2146 requirements and 0 errors, so the
three IDs are unique against the current contract. All three live in
`world/rules/tests/test_monster_ai_estimation.py`, whose every assertion is
behavioral: the file-local probe participants and synthetic `t_`-named rows, a
real-entity fixture that settles the same plan through `ActionResolver`, and
independently known integers (the analyzer's own range arithmetic is never used
to produce an expectation).

| Canonical ID | Establishing tests | What the assertions establish |
| --- | --- | --- |
| `monster-ai-effect-estimation::damage-estimates-use-settlement-arithmetic-without-settlement` | `ScalarExpressionTests` (all six: the multiplier ladder, the margin, the strike amount, the heal amount, the two capacity caps and the floor, and the settlement handlers staging the same expressions), `SpreadProjectionTests.test_one_strike_averages_the_range_inside_every_capacity_branch`, `...test_a_two_strike_occurrence_caps_the_sum_not_the_average`, `...test_ordered_occurrences_bill_the_remaining_health_once`, `...test_a_hit_dependent_effect_reads_the_occurrences_own_gate`, `...test_a_staged_heal_never_exceeds_the_pre_action_gap`, `...test_the_estimate_rolls_nothing_mounts_nothing_and_writes_nothing`, `ScaleGateAndPoolTests.test_a_non_default_scale_scales_the_effects_and_their_cost`, `...test_a_gated_damage_occurrence_is_omitted_rather_than_marginalized`, `...test_independent_drain_gates_sum_rather_than_multiply`, `...test_a_health_drain_credits_only_the_projected_loss`, `...test_a_same_recipient_heal_gets_no_fresh_allowance`, `EstimationIntegrationTests.test_the_estimate_matches_the_settled_range_over_every_face`, `...test_the_drain_projection_matches_the_committed_pools` | The estimate is the analytic average of the 100 d100 faces through settlement's own margin, multiplier ladder, potency, defense subtraction, rider, floor and scale: a one-strike row against a 30-health recipient averages 11.0 capped and 11.65 nominal, not 11.65 capped; a two-strike occurrence averages the capped sums (3.75) rather than capping the summed average (5); a second occurrence bills only the health the first left (50, never 60.2); a hit-dependent drain reads its source occurrence's ONE shared gate (`1 - 0.5^2`) on that recipient's own branches, so two independently gated receivers recover 5 each and 10 in all rather than 2.5; a gated occurrence that would act on state its source already changed is omitted rather than credited on every branch; a half-scale cast lands the halved range (5.87) and is charged six mana; and both the 100-face resolved mean and the committed pools of a real cast match the projection. |
| `monster-ai-effect-estimation::uncertain-effects-have-conservative-explicit-limits` | `SpreadProjectionTests.test_a_missed_prerequisite_credits_nothing_at_all`, `...test_a_full_share_drain_credits_the_projected_actual_removal`, `...test_a_recovery_is_clamped_before_the_cost_is_deducted`, `...test_a_known_diversion_budget_reduces_the_estimate`, `...test_a_recipient_floor_caps_the_loss_at_one_stored_point`, `...test_an_evidence_conditional_strike_is_not_credited`, `...test_an_unvaluable_harm_is_refused_instead_of_zeroed`, `...test_a_hostile_benefit_is_refused_too`, `...test_an_enemy_side_status_is_unvalued_but_never_refused`, `...test_a_candidate_that_takes_from_a_friend_is_refused_while_others_survive`, `...test_a_plan_that_omits_nothing_classifies_as_exact`, `ScaleGateAndPoolTests.test_a_gated_damage_occurrence_is_omitted_rather_than_marginalized`, `...test_a_health_drain_credits_only_the_projected_loss`, `...test_an_unclassified_own_side_outcome_is_refused`, `...test_cleansing_a_hostile_recipient_is_refused`, `EstimationTuningTests.test_the_estimation_rulebook_leaves_move_the_fingerprint` | A failed prerequisite contributes no recovery and an exhausted prerequisite gate credits nothing (the projected actor delta is exactly the cost); a full share credits the projected actual removal (three held mana leave the actor at 13 after a ten-mana payment, matching the committed pools); a recovery is clamped by its room before the cost is deducted (a full twenty-mana pool leaves ten, never thirteen) and a health drain credits only the loss the recipient actually takes (nothing once the same action has emptied it); a live diversion absorbs the authored fraction of each landing strike clamped by the budget left and the pool paid from, while a spent budget absorbs nothing; a nonlethal recipient's crossing floors at one stored point (19 lost, not 20); an evidence-conditional strike and an over-crediting conditional are not credited, and an occurrence that omits nothing classifies EXACT; unvaluable own-side harm (a grant revocation, an allied drain, a self-debuff) and an unmodeled hostile benefit (a status or a heal handed to the enemy) are refused with typed reasons, while an enemy-side status is merely unvalued with diagnostics and supported siblings survive. |
| `monster-ai-effect-estimation::health-and-resource-features-are-bounded-and-signed` | `SpreadProjectionTests.test_one_strike_averages_the_range_inside_every_capacity_branch`, `...test_allied_healing_moves_the_feature_the_other_way`, `...test_enemy_healing_is_a_harm`, `...test_own_side_damage_is_a_negative_term`, `...test_a_staged_heal_never_exceeds_the_pre_action_gap`, `...test_a_non_finite_read_is_a_typed_state_not_an_exception`, `ScaleGateAndPoolTests.test_the_cost_feature_spans_every_charged_pool` | Damage and recovery normalize by the affected faction's eligible live maximum-health sum (floored at one), so an 11.0 loss against a 30-health enemy is 0.3667 and ten useful points of a 40-health ally are 0.25, while the damage feature is exactly the enemy loss over that sum minus the own-side loss over the ally sum; enemy damage and allied healing are positive while ally damage and enemy healing are negative; waste is the excess nominal effect over the total absolute nominal magnitude (0.65 / 11.65); finishing is the modeled knockout likelihood over the eligible live enemy count (0.10 for ten crossing faces); cost is the mean charged fraction of every pool the plan charges (0.35 over two pools, 0.25 when one holds nothing) at the plan's scale; and a non-finite read is a typed invalid state instead of a value or an exception. |

## Post-implementation review corrections

The finished-diff review found seven behavioral defects and one evidence defect,
all corrected in the follow-up commits with the regressions listed above:
the plan's cast scale was not reaching the health arithmetic at all; an
uncertain prerequisite gate was credited marginally on branches it never
reached (it is now omitted when the effect would act on state its source
occurrence already changed, and only weighted when the pool it acts on is
independent of that occurrence); an area drain multiplied its recipients' gates
into a joint requirement and could erase one recipient's removal with another's
closed gate; a health drain credited its request rather than the projected
loss, and the actor's room was applied after the gate expectation instead of
before it; an actor-bound effect's execution gate was read from the actor
instead of from the routed recipients the prerequisite actually filters; a
diversion budget was keyed by the instance alone (an instance key is local to
one holder) and was depleted across occurrences although settlement stages
every occurrence against the persisted budget and only pays in commit order;
an unclassified outcome (a grant revocation on the actor's own side, a cleanse
handed to an enemy, a state-magnitude heal aimed at an enemy) was valued at
zero rather than refused; and the first acceptance ledger claimed clauses its
tests did not establish, which the added regressions and this rewritten table
now cover.

## Points where this change diverges from a design-document statement

Both were verified in the current source and are recorded here rather than
silently absorbed:

1. The attack design says costs are paid before effects are accounted for.
   Settlement stages the effect pendings first and appends the actor's resource
   deduction last (`world/rules/action/resolver.py`, applied in list order by
   `world/rules/action/transaction.py::_commit`), so a recovery is clamped by
   its own pool bound *before* the payment leaves it. The estimator models
   settlement, and
   `SpreadProjectionTests.test_a_recovery_is_clamped_before_the_cost_is_deducted`
   pins the difference.
2. A non-finite number stored in a static combat trait raises inside the
   decision snapshot's own fold (`SkillHandler.stored_effective_values` rounds
   `base * multiplier`) before any estimator sees it. That fold belongs to the
   archived `monster-ai-legal-snapshots` capability, so this change neither
   widens nor weakens it: the estimator's own boundary is exercised through the
   decision read it consumes, and the reported gap is left visible for the
   owning capability.
