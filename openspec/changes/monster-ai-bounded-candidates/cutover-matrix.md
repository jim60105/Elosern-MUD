# Assertion cutover and annotation ledger

This change adds a new capability, `monster-ai-legal-candidates`, and modifies
no existing requirement, so no canonical ID is retired and no existing
assertion is replaced. The `legacy` decision body, the player-facing command
surface and the browser action surface are untouched: every retained legacy
assertion still establishes permanent legacy behavior.

## ADDED requirements: annotation ledger

`tools.spec_traceability` indexes `openspec/specs/` only, so annotating a
delta-only ID during apply reports `unknown-requirement-id` and would leave
`tools.contract_gate` red on this branch. The repository convention (the
archived `monster-ai-legal-snapshots` change, `docs/development/spec-test-
traceability.md`) therefore attaches new-capability annotations in the same
batch as the archive's main-spec sync; this ledger records the agreed deferral
rather than representing the attachment as already done. The IDs below were
generated, not guessed, against the equivalent delta-applied tree with
`uv run --locked python -m tools.spec_traceability --repo-root <tree> list`
(the delta spec materialized as
`openspec/specs/monster-ai-legal-candidates/spec.md` beside the current
`openspec/specs/`); that run reported 2143 requirements and 0 errors, so the
four IDs are unique against the current contract.

| Canonical ID | Establishing tests | What the assertions establish |
| --- | --- | --- |
| `monster-ai-legal-candidates::candidate-plans-preserve-actual-skill-semantics` | `CandidateShapeTests.test_single_enumerates_one_plan_per_valid_target_in_declared_order`, `...test_an_order_tie_falls_back_to_stable_identifiers`, `...test_enemy_area_uses_exactly_one_legal_group_and_keeps_its_shorthand`, `...test_a_bounded_audience_set_is_enumerated_for_a_mixed_skill`, `...test_equivalent_routed_combinations_collapse_to_one_candidate`, `...test_a_roster_sensitive_skill_keeps_its_submitted_identity`, `...test_implicit_self_and_none_bindings_are_not_widened`, `...test_an_unresolvable_harmful_effect_excludes_the_skill_with_a_reason`, `...test_an_unresolved_buff_reference_excludes_the_skill_with_a_reason`, `...test_an_unresolved_act_reference_excludes_the_skill_with_a_reason`, `...test_a_group_without_hostile_damage_is_excluded_with_a_reason`, `CandidateRestrictionTests.test_a_shorthand_never_reaches_outside_the_decision` | A candidate is one of the skill's own authored shapes: one plan per valid SINGLE target in the declared order with stable-identifier ties, exactly one legal group for an enemy AREA skill, the bounded hostile/friendly/complete groups for a mixed-audience skill, one candidate per actual audience combination (two submitted rosters that route every effect to the same recipients collapse, while a resistible skill whose settlement contests the submitted roster keeps its own identity) and the implicit SELF/NONE binding; a self-bound effect still routes to the actor; a harmful effect the damage model cannot resolve (an unregistered damage element, or a buff/act reference the owning registry does not carry) and a group whose damage reaches no hostile recipient are excluded with a reason while supported alternatives stay eligible; a shorthand is retained only when its expansion is exactly the decision-scoped group, so a plan never names a participant outside the decision. |
| `monster-ai-legal-candidates::mandatory-single-target-restrictions-precede-utility` | `CandidateRestrictionTests.test_the_seal_narrows_to_the_first_bearer_in_player_first_order`, `...test_a_displaced_first_bearer_yields_the_next_remaining_bearer`, `...test_a_castable_nonstrike_alternative_keeps_the_displaced_target`, `...test_only_a_supported_hostile_plan_counts_as_the_attack_alternative`, `...test_a_self_heal_is_not_a_castable_attack_alternative`, `...test_area_groups_are_not_seal_restricted` | On real entities, an applicable seal narrows the hostile SINGLE base to its bearers in player-first then ascending-pk order; a displaced first bearer is dropped and the next remaining bearer is used when the actor has no genuinely castable non-strike hostile SINGLE alternative; a castable non-strike alternative keeps displaced targets reachable for non-strike plans while the strike-class plans still exclude them; a self-heal never counts as the alternative, and neither does a legal non-strike plan whose damage only ever routes to the actor's own side; AREA groups are not seal restricted. |
| `monster-ai-legal-candidates::canonical-deduplication-preserves-executable-representation` | `CandidateShapeTests.test_one_shorthand_and_one_explicit_roster_share_one_identity`, `...test_enemy_area_uses_exactly_one_legal_group_and_keeps_its_shorthand`, `...test_a_non_default_scale_is_preserved_on_the_shorthand_request` | One action has one identity regardless of representation: the retained plan keeps the authored AREA shorthand (`target_ids` stays empty, no character list), the identity equals the explicit recipient identifiers of the same group, a duplicate representation is not examined twice, and a non-default authored scale stays on both the retained request and the identity. |
| `monster-ai-legal-candidates::proposal-work-is-deterministically-bounded` | `CandidateBudgetTests.test_the_authored_default_budget_is_the_rulebook_value`, `...test_the_budget_is_configurable_inside_the_integer_bound`, `...test_exhaustion_reports_the_omitted_families_and_targets`, `...test_rejected_proposals_consume_the_budget`, `...test_the_mandatory_filter_probe_shares_the_candidate_budget`, `...test_an_unfinished_capability_search_never_erases_displaced_targets`, `...test_an_examined_plan_is_never_reported_as_omitted`, `...test_a_paid_examination_is_never_lost_to_a_later_proposal`, `...test_a_paid_candidate_survives_every_scope_offset`, `...test_slots_are_allocated_round_robin_across_families`, `...test_the_ring_offset_is_derived_from_the_decision_scope`, `...test_an_empty_legal_set_returns_no_plan`, `...test_a_single_enemy_still_yields_the_one_legal_plan`, `...test_enumeration_draws_no_selection_or_combat_dice`, `...test_enumerating_many_plans_issues_no_database_queries`, `...test_the_default_read_set_is_decision_local`, `CandidateRestrictionTests.test_enumerating_on_real_entities_writes_nothing`, `...test_a_legal_candidate_settles_through_the_resolver_and_commits` | The bound is the authored budget (256) and accepts only an integer in 1..4096; one decision has one budget and one examination ledger shared by the mandatory-filter capability search and the ring, so `examined` equals the candidates, rejections and mandatory-filter exclusions together and never exceeds the bound while no plan is validated twice; the capability search walks the targets round-robin across the relevant skills, keeps displaced targets when it cannot finish, and only removes them after every candidate plan against the hostile domain turned out not to be an attack; an examined legal plan stays a candidate even when the budget runs out before the ring reaches its family (and is never mislabelled as removed by a restriction), while an unaffordable proposal is skipped in place so a later family still uses what was already paid for; slots are allocated round-robin across canonical families and the ring starts at a scope-derived offset, so the same action set exists under every scope while a scope decides which family is examined first; exhaustion reports the omitted families and the proposals that were never examined (already examined ones are never relabelled); duplicates cannot consume a slot; an empty legal set returns `None` with no forced attack and no legacy fallback; enumeration draws no selection or combat dice, issues no database queries on the decision read set, writes no persisted attribute on real entities, and its canonical candidate still settles through the resolver and commits HP. |

## Out-of-scope regression fix shipped alongside

`1f9ec8f6` repairs a red master contract outside this change's delta scope
(authorized by the integration owner): commit `6554ae64` (the archived
`monster-ai-legal-snapshots` review fix) made the `skill_owned` condition build
a skill handler eagerly through a `dict.get` default, which broke the pure
fixture entities of `world.rules.tests.test_monster_ai_tuning`,
`test_monster_behaviour_policy` and `test_monster_behaviour_selection`. The fix
restores lazy, shared resolution; it touches no requirement text and adds no
annotation.

The finished-diff review then showed the same resolver touching a persisted
entity's lazy `skills` property before knowing whether the entity persists at
all, and the condition evaluator still materializing it through the
conferred-grants read. The follow-up narrows that: a persisted entity is
detected by its attribute store before the lazy property is touched, and the
grants read shares the same resolver. The regression is
`test_a_cold_modifier_read_mounts_no_skill_handler` in
`CandidateRestrictionTests` (a cold no-create modifier read on a real entity
attaches no skill handler), and the three labels above plus
`test_combat_modifiers` stay green.
