# Assertion cutover and annotation ledger

This change modifies two `monster-behaviour-profile` requirements in place and
adds four, so no canonical ID is retired. It replaces one source-layout
assertion that its own runtime change made false, and it must annotate the
replacement through behavior rather than through module layout.

## Retired assertion

| Retired assertion | Role | Why it is false now | Replacement evidence | Owner |
| --- | --- | --- | --- | --- |
| `test_the_behaviour_selection_path_reads_no_species_identity` (`world/lore/tests/test_monster_species_content.py`): an AST scan asserting `world/rules/monster_behaviour.py` never references `MONSTER_SPECIES_REGISTRY`, `MONSTER_VARIANT_REGISTRY`, `monster_species`, `species_key` or `variant_key` | Source layout | This change requires runtime resolution to validate the actual species/variant pair, so the module now reads exactly those identities | `test_narrated_ability_prose_grants_no_ownership_or_effect` constructs a kit-less registered row whose prose names a registered skill and observes that it owns no such skill (`db.skills is None`, `owned_keys()` excludes it). The remaining assertions of the same requirement (`test_no_registry_string_names_a_skill_behaviour_or_combat_trait`, `test_no_registry_field_stands_in_for_an_ability_seam`) stay in place | `world/lore/tests/test_monster_species_content.py` |

## MODIFIED requirements: retained IDs, reviewed assertions

| Requirement ID | Retained establishing tests |
| --- | --- |
| `monster-behaviour-profile::behaviour-parameters-are-data-driven-not-hardcoded-in-python` | `world.rules.tests.test_monster_behaviour_profile.MonsterBehaviourProfileTests.test_rulebook_covers_distinct_tier_defaults_and_override` (mandatory-four-field rulebook shape, now allowing the two optional fields) and `world.rules.tests.test_monster_ai_tuning.MonsterBehaviourAuthoringTests.test_the_authored_tier_default_and_strategy_drive_the_decision` (a synthetic rulebook's authored tier default and target strategy reach a real legacy decision, replacing the retired source-text inspection) |
| `monster-behaviour-profile::monster-behaviour-tree-resolves-to-a-real-archetype-defaulting-from-threat-tier` | `world.rules.tests.test_monster_behaviour_profile.MonsterBehaviourProfileTests.test_unset_profile_defaults_for_every_tier` and `world.rules.tests.test_monster_ai_tuning.MonsterAIDecisionTests.test_the_actual_stored_binding_decides_the_mode` (the actual stored binding decides the mode and a repaired reference resolves to a typed invalid state instead of raising) |

## ADDED requirements: annotations deferred to the archive sync

`tools.spec_traceability` indexes `openspec/specs/` only, so annotating a
delta-only ID during apply always reports `unknown-requirement-id` and would
leave `tools.contract_gate` red on this branch. The repository convention
(`docs/superpowers/specs/2026-09-02-observability-logging-design.md` §6, and the
`dream-story-dispatch` archive commit) attaches new-capability annotations in
the same batch as the archive's main-spec sync. The IDs below were generated
against the equivalent delta-applied tree with
`tools.spec_traceability list --repo-root <merged tree>`; the archive step
attaches each one to the test named here.

| Canonical ID (generated, not guessed) | Establishing test | What the assertion establishes |
| --- | --- | --- |
| `monster-behaviour-profile::variant-intelligence-is-explicit-and-independent` | `world.rules.tests.test_monster_ai_tuning.MonsterAITuningLoaderTests.test_variant_maps_require_registered_pairs_and_integers`, `...test_utility_activation_coverage_requires_intelligence`, `MonsterAIDecisionTests.test_independent_variants_keep_their_own_intelligence` | Intelligence is an explicit per-variant integer 0..100 on a registered pair; inactive legacy values are validated as strictly as active ones; two variants of one species keep independent values and no tier or archetype supplies one |
| `monster-behaviour-profile::mode-selection-honors-actual-variant-and-behavior-binding` | `MonsterAIDecisionTests.test_a_variant_override_wins_over_the_archetype_mode`, `...test_a_repaired_pair_is_never_trusted`, `...test_utility_without_a_pair_or_intelligence_is_typed_invalid`, `...test_tier_only_and_unregistered_monsters_stay_legacy`, `...test_a_non_monster_has_no_monster_resolution` | A validated variant override wins, a repaired pair is never trusted, utility without a pair or intelligence yields a typed invalid state, and every untuned or tier-only monster keeps legacy |
| `monster-behaviour-profile::ai-tuning-is-strict-and-startup-scoped` | `MonsterAITuningLoaderTests.test_each_mandatory_legacy_field_is_required`, `...test_unknown_archetype_and_top_level_fields_are_rejected`, `...test_weights_must_be_the_complete_named_schema`, `...test_decision_mode_and_budget_are_strictly_typed`, `...test_tier_default_mapping_must_cover_exactly_the_tier_registry`, `...test_a_variant_referencing_an_unknown_archetype_is_rejected`, `world.rules.tests.test_monster_behaviour_profile.MonsterBehaviourProfileTests.test_all_six_archetypes_stay_available_with_all_legacy_production_modes` | One malformed or omitted field fails the load with the named configuration error, and the six authored archetypes stay available and legacy |
| `monster-behaviour-profile::session-tuning-has-a-reproducible-lifetime` | `world.rules.tests.test_monster_ai_tuning.SessionAITuningTests.test_recording_is_keyed_by_session_and_actor`, `...test_an_active_session_keeps_the_tuning_the_process_loaded`, `...test_a_restarted_process_reconstructs_with_the_new_startup_tuning`, `...test_recording_re_resolves_a_repaired_binding`, `...test_a_non_monster_is_not_recorded`, `MonsterAISessionBoundaryTests.test_recording_resolves_the_constructed_monster_and_stores_nothing`, `...test_the_production_enemy_policy_records_the_same_tuning`, `...test_terminal_cleanup_drops_only_its_own_session`, `MonsterAITuningLoaderTests.test_fingerprint_is_reproducible_and_moves_with_every_input` | A session records an immutable resolution with the configuration fingerprint; an active process keeps startup tuning through a disk edit loaded from an edited rulebook file; a restart reconstructs with the new startup tuning; terminal cleanup drops only its own session; the fingerprint moves with the algorithm version, budget, mode, each weight, intelligence, each behaviour leaf, tier defaults and referenced variant bindings, and not with display names |

## Fingerprint input scope

The fingerprint covers every decision-relevant rulebook input this process
consumes today: the algorithm version, the candidate budget, the tier default
map, the four behaviour leaves and mode and weights of each archetype, the
variant intelligence and mode maps, and the authored binding of every variant
those maps name. Estimator-side inputs (skill effect arithmetic, cost rules)
belong to the same projection, and the estimator that consumes them
(`monster-ai-damage-estimation`, dispatched by `monster-ai-attack-selection`)
extends it in its own change. The behaviour leaves are the estimation rules
that exist at this point in the roadmap, so they are what the sensitivity test
mutates; no skill-registry projection is invented ahead of its consumer.

## Runtime binding contract (post-review correction)

`resolve_monster_ai` reads the stored binding without materializing it and
distinguishes the unset placeholder (no value, or the empty string) from an
unreadable stored value: the former selects the tier default, the latter
(unknown key or repaired non-string) returns `invalid_binding`. `utility_weights`
stays genuinely optional, so a four-mandatory-field legacy archetype loads while
an archetype authored `utility` must declare both intelligence coverage and its
weights.
