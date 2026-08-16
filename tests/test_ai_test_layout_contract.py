"""Repository contract: the AI long test files stay split into themed modules.

Pins the post-split layout of the ``world/ai/tests`` scenario-director and
npc-dialogue families: the eight themed modules exist, every pre-split class
lives in exactly one expected module, every ``covers_requirement`` annotation
stays on the same method, and each split module imports its family's shared
helpers module (no duplicated helper code).
"""

from pathlib import Path
import ast
import unittest

from tools.spec_traceability import covers_requirement


REPO_ROOT = Path(__file__).resolve().parents[1]
AI_TESTS = REPO_ROOT / "world" / "ai" / "tests"

#: The post-split scenario-director family modules.
DIRECTOR_SPLIT_MODULES = {
    "test_scenario_director_proposals.py",
    "test_scenario_director_prompts.py",
    "test_scenario_director_validation.py",
    "test_scenario_director_registration.py",
}

#: The post-split npc-dialogue family modules.
DIALOGUE_SPLIT_MODULES = {
    "test_npc_dialogue_prompts.py",
    "test_npc_dialogue_validators.py",
    "test_npc_dialogue_registration.py",
    "test_npc_dialogue_retry.py",
}

#: Every pre-split class and the single themed module it must live in.
CLASS_MODULES = {
    "AffinityPromptTests": "test_npc_dialogue_prompts.py",
    "AffinityValidatorUnitTests": "test_npc_dialogue_validators.py",
    "BlueprintCharacterizationTypeTests": "test_scenario_director_proposals.py",
    "CharacterizationValidatorTests": "test_scenario_director_validation.py",
    "DegradePathTests": "test_npc_dialogue_retry.py",
    "NPCDialoguePromptTests": "test_npc_dialogue_prompts.py",
    "OfferQuestValidatorUnitTests": "test_npc_dialogue_validators.py",
    "PartyInviteValidatorUnitTests": "test_npc_dialogue_validators.py",
    "PersonaPromptTests": "test_npc_dialogue_prompts.py",
    "RegistrationGateTests": "test_npc_dialogue_registration.py",
    "RegistryRestoreRegressionTests": "test_scenario_director_registration.py",
    "ReplyEntryPointTests": "test_npc_dialogue_registration.py",
    "RevealLoreValidatorUnitTests": "test_npc_dialogue_validators.py",
    "ScenarioDirectorEntryPointTests": "test_scenario_director_registration.py",
    "ScenarioDirectorOfflineTestRuleTests": "test_scenario_director_registration.py",
    "ScenarioDirectorPromptTests": "test_scenario_director_prompts.py",
    "ScenarioDirectorProposalTypeTests": "test_scenario_director_proposals.py",
    "ScenarioDirectorRegistrationTests": "test_scenario_director_registration.py",
    "ScenarioDirectorStartupRegistrationTests": "test_scenario_director_registration.py",
    "ScenarioDirectorTemplatePoolTests": "test_scenario_director_registration.py",
    "ScenarioDirectorValidatorTests": "test_scenario_director_validation.py",
    "SceneBoundValidatorTests": "test_scenario_director_validation.py",
    "SecretSetValidatorUnitTests": "test_npc_dialogue_validators.py",
    "StartupRegistrationTests": "test_npc_dialogue_registration.py",
    "ValidatorRetryTests": "test_npc_dialogue_retry.py"
}

#: The pre-split covers_requirement inventory: class -> {method -> [requirement ids]}.
PRE_SPLIT_ANNOTATIONS = {
    "AffinityPromptTests": {
        "test_affinity_block_carries_the_true_value_cap_and_stage": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_prompts_stay_byte_identical_with_and_without_the_block": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_recordless_player_omits_the_affinity_block": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ]
    },
    "AffinityValidatorUnitTests": {
        "test_affinity_validator_keeps_the_original_error_text": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_no_leak_validator_is_bound_to_its_own_call_numbers": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_no_leak_validator_rejects_value_and_cap_substrings": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_relation_payload_requires_exactly_one_integer_delta_in_range": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_relation_validator_ignores_other_intent_kinds": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ]
    },
    "BlueprintCharacterizationTypeTests": {
        "test_characterization_differences_change_the_content_digest": [
            "blueprint-portrait-policy::the-blueprint-lifecycle-preserves-the-characterization-fields"
        ],
        "test_field_less_blueprint_round_trips_byte_identically": [
            "blueprint-portrait-policy::the-blueprint-lifecycle-preserves-the-characterization-fields"
        ],
        "test_frozen_portrait_value_object_passes_the_immutability_guard": [
            "blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization"
        ],
        "test_mutable_containers_are_still_rejected_under_a_portrait_field": [
            "blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization"
        ],
        "test_round_trip_preserves_all_four_characterization_fields": [
            "blueprint-portrait-policy::the-blueprint-lifecycle-preserves-the-characterization-fields"
        ]
    },
    "CharacterizationValidatorTests": {
        "test_conflicting_duplicate_key_rejects_and_retries": [
            "scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields"
        ],
        "test_digit_only_portrait_stable_key_rejects_and_retries": [
            "art-stable-key-contract::the-character-portrait-keyspace-reserves-the-digit-only-region-for-player-characters",
            "blueprint-portrait-policy::quest-blueprint-npc-req-entries-may-declare-portrait-policy-and-characterization",
            "scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields"
        ],
        "test_elven_tier_named_occupant_passes_within_the_elf_band": [
            "scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields"
        ],
        "test_field_less_entries_validate_unchanged": [
            "scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields"
        ],
        "test_malformed_portrait_object_rejects_and_retries": [
            "scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields"
        ],
        "test_overlong_display_name_rejects_and_retries": [
            "scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields"
        ],
        "test_unpaired_underage_or_non_integer_declarations_reject_and_retry": [
            "scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields"
        ],
        "test_valid_named_occupant_with_ages_passes_validation": [
            "scenario-director::blueprint-validation-accepts-and-bounds-the-optional-npc-characterization-fields"
        ]
    },
    "DegradePathTests": {
        "test_degraded_call_changes_no_state": [
            "npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline"
        ],
        "test_disabled_profile_resolves_to_none_with_zero_client_calls": [
            "npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline"
        ],
        "test_exhausted_retries_resolve_to_none_within_the_budget": [
            "npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline"
        ],
        "test_transport_failure_resolves_to_none_with_one_client_call": [
            "npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline"
        ]
    },
    "NPCDialoguePromptTests": {
        "test_disguised_stats_are_injected_so_a_disguised_elf_reads_as_weak": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_identical_inputs_produce_byte_identical_prompts": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_oversized_memory_is_truncated_deterministically_with_a_marker": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_prompt_is_bounded_and_contains_no_live_entity_reference": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_prompt_uses_entity_keys_with_no_true_stats_present": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_system_message_fixes_role_language_and_output_contract": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ]
    },
    "OfferQuestValidatorUnitTests": {
        "test_malformed_offer_quest_payloads_are_rejected": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_offer_quest_validator_ignores_other_intent_kinds": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_quest_key_boundary_is_exactly_64_code_points": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_valid_offer_quest_payload_passes": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_whitelist_and_schema_carry_offer_quest": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ]
    },
    "PartyInviteValidatorUnitTests": {
        "test_party_validator_ignores_other_intent_kinds": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_whitelist_and_schema_carry_party_invite": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ]
    },
    "PersonaPromptTests": {
        "test_absent_npc_persona_keeps_the_byte_identical_baseline": [
            "persona-dialogue-injection::the-npc-s-own-persona-feeds-the-dialogue-system-message"
        ],
        "test_absent_player_persona_omits_the_block_byte_identically": [
            "persona-dialogue-injection::the-player-s-persona-feeds-the-user-payload-as-player-persona"
        ],
        "test_npc_persona_block_lands_in_the_system_message": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona",
            "persona-dialogue-injection::the-npc-s-own-persona-feeds-the-dialogue-system-message"
        ],
        "test_persona_block_within_the_store_bound_is_injected_in_full": [
            "persona-dialogue-injection::the-npc-s-own-persona-feeds-the-dialogue-system-message"
        ],
        "test_player_persona_lands_beside_affinity_in_the_user_payload": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona",
            "persona-dialogue-injection::the-player-s-persona-feeds-the-user-payload-as-player-persona"
        ]
    },
    "RegistrationGateTests": {
        "test_calling_after_registry_reset_errbacks_with_named_error": [
            "npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline"
        ],
        "test_calling_before_registration_errbacks_with_named_error": [
            "npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline"
        ],
        "test_duplicate_registration_is_a_noop_keeping_the_first": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_foreign_same_name_validator_does_not_pass_the_registration_gate": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_foreign_schema_registration_is_not_silently_overridden": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_partial_hook_registration_failure_leaves_no_npc_dialogue_hooks": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_partial_own_state_is_rolled_back_on_a_later_failure": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ]
    },
    "RegistryRestoreRegressionTests": {
        "test_registries_hold_exactly_the_pre_test_contents_after_a_mutating_test": [
            "evennia-test-optimization::tests-restore-process-global-registry-state"
        ]
    },
    "ReplyEntryPointTests": {
        "test_degraded_call_resolves_to_none_never_a_sentinel": [
            "npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline"
        ],
        "test_explicit_none_client_is_rejected_before_any_transport_work": [
            "npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline"
        ],
        "test_none_client_priority_over_an_exploding_memory_iterable": [
            "npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline"
        ],
        "test_returned_value_is_a_plain_frozen_value_with_no_write_back_path": [
            "npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline"
        ],
        "test_schema_valid_reply_resolves_with_no_retry": [
            "npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline"
        ],
        "test_valid_reply_resolves_to_a_frozen_reply_with_no_state_change": [
            "npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline"
        ]
    },
    "RevealLoreValidatorUnitTests": {
        "test_malformed_reveal_lore_payloads_are_rejected": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_reveal_lore_field_boundary_is_exactly_64_code_points": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_reveal_lore_validator_ignores_other_intent_kinds": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_valid_reveal_lore_payload_passes": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_whitelist_and_schema_carry_reveal_lore": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ]
    },
    "ScenarioDirectorEntryPointTests": {
        "test_calling_before_registration_errbacks_with_named_error": [
            "scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context"
        ],
        "test_context_misfitting_blueprint_is_replaced_by_a_fitting_template": [
            "scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context"
        ],
        "test_disabled_profile_draws_a_template_with_zero_client_calls": [
            "scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context"
        ],
        "test_explicit_none_client_errbacks_before_any_prompt_or_transport_work": [
            "scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context"
        ],
        "test_identical_degraded_contexts_draw_identical_templates": [
            "scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context",
            "scenario-director::the-hand-written-template-pool-provides-offline-quest-generation"
        ],
        "test_transport_failure_and_exhausted_retries_draw_a_template": [
            "scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context"
        ],
        "test_unsatisfiable_context_errbacks_with_template_error": [
            "scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context"
        ],
        "test_valid_context_fitting_blueprint_resolves_with_no_state_change": [
            "guardrail::guarded-generative-calls-validate-retry-then-degrade",
            "scenario-director::generate-quest-blueprint-runs-the-guarded-pipeline-and-enforces-the-request-context"
        ]
    },
    "ScenarioDirectorOfflineTestRuleTests": {
        "test_no_live_client_constructor_or_socket_in_scenario_director_tests": [
            "scenario-director::the-scenario-director-layer-preserves-the-single-writer-and-transport-boundaries"
        ]
    },
    "ScenarioDirectorPromptTests": {
        "test_identical_contexts_produce_byte_identical_prompts": [
            "scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful"
        ],
        "test_oversized_context_is_bounded_and_valid": [
            "scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful"
        ],
        "test_system_message_names_the_blueprint_contract_and_fidelity": [
            "scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful"
        ],
        "test_user_message_carries_keys_and_no_live_objects": [
            "scenario-director::scenariodirector-prompt-construction-is-deterministic-bounded-and-faithful"
        ]
    },
    "ScenarioDirectorProposalTypeTests": {
        "test_content_cannot_be_mutated_after_construction": [
            "scenario-director::questblueprint-is-the-closed-deeply-immutable-ai-proposal-type"
        ],
        "test_mutable_containers_are_rejected_at_construction": [
            "scenario-director::questblueprint-is-the-closed-deeply-immutable-ai-proposal-type"
        ],
        "test_non_contiguous_stage_indices_fail_construction": [
            "scenario-director::questblueprint-is-the-closed-deeply-immutable-ai-proposal-type"
        ],
        "test_unknown_quest_type_fails_construction": [
            "scenario-director::questblueprint-is-the-closed-deeply-immutable-ai-proposal-type"
        ],
        "test_valid_blueprint_preserves_explicit_stage_indices": [
            "scenario-director::questblueprint-is-the-closed-deeply-immutable-ai-proposal-type"
        ]
    },
    "ScenarioDirectorRegistrationTests": {
        "test_duplicate_registration_is_a_noop": [
            "scenario-director::hook-registration-is-atomic-idempotent-and-boot-tolerant"
        ],
        "test_partial_hook_failure_leaves_no_scenario_director_hooks": [
            "scenario-director::hook-registration-is-atomic-idempotent-and-boot-tolerant"
        ]
    },
    "ScenarioDirectorStartupRegistrationTests": {
        "test_startup_seam_registers_the_scenario_director_layer": [
            "scenario-director::hook-registration-is-atomic-idempotent-and-boot-tolerant"
        ],
        "test_startup_seam_survives_a_foreign_scenario_director_registration": [
            "scenario-director::hook-registration-is-atomic-idempotent-and-boot-tolerant"
        ]
    },
    "ScenarioDirectorTemplatePoolTests": {
        "test_cold_start_import_has_no_module_level_cycle": [
            "scenario-director::the-hand-written-template-pool-provides-offline-quest-generation"
        ],
        "test_degraded_draw_is_deterministic_and_context_fitting": [
            "scenario-director::the-hand-written-template-pool-provides-offline-quest-generation"
        ],
        "test_every_entry_compiles_to_a_registrable_definition": [
            "scenario-director::the-hand-written-template-pool-provides-offline-quest-generation"
        ],
        "test_every_entry_validates_against_schema_and_validators": [
            "scenario-director::the-hand-written-template-pool-provides-offline-quest-generation"
        ],
        "test_instance_layer_template_validates_compiles_and_registers_with_requirements": [
            "scene-builder::the-hand-written-template-pool-gains-an-instance-layer-scene-so-offline-play-exercises-the-materializer"
        ],
        "test_malformed_underage_template_is_rejected_at_registration": [
            "blueprint-portrait-policy::the-hand-written-template-pool-may-carry-characterization-fields"
        ],
        "test_offline_request_can_produce_a_materializable_instance_quest": [
            "scene-builder::the-hand-written-template-pool-gains-an-instance-layer-scene-so-offline-play-exercises-the-materializer"
        ],
        "test_pool_is_non_empty": [
            "scenario-director::the-hand-written-template-pool-provides-offline-quest-generation"
        ],
        "test_valid_named_template_registers": [
            "blueprint-portrait-policy::the-hand-written-template-pool-may-carry-characterization-fields"
        ]
    },
    "ScenarioDirectorValidatorTests": {
        "test_malformed_rank_reward_and_item_shapes_are_rejected": [
            "guardrail::semantic-validators-are-pluggable-and-layer-scoped",
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ],
        "test_non_contiguous_stage_indices_are_rejected": [
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ],
        "test_npc_persona_and_background_are_validated_through_the_shared_helper": [
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ],
        "test_out_of_band_reward_copper_is_rejected": [
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ],
        "test_unknown_archetype_is_rejected": [
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ],
        "test_unknown_issuer_is_rejected": [
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ],
        "test_unknown_monster_tier_is_rejected": [
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ],
        "test_unknown_npc_tier_is_rejected": [
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ],
        "test_unknown_rank_is_rejected_and_retried_with_error_appended": [
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ],
        "test_valid_bounded_blueprint_passes_on_first_attempt": [
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ],
        "test_validators_tolerate_malformed_root_and_stage_shapes": [
            "scenario-director::semantic-validators-bound-rank-reward-archetype-npc-tier-and-every-world-reference"
        ]
    },
    "SceneBoundValidatorTests": {
        "test_bound_defeat_quantity_exceeding_is_rejected_and_retried": [
            "scenario-director::scene-bound-proposal-stages-are-validated-before-publication"
        ],
        "test_escort_stage_at_anchor_is_rejected_and_retried": [
            "quest-blueprint::escort-quests-require-a-bound-protected-entity-path",
            "scenario-director::scene-bound-proposal-stages-are-validated-before-publication"
        ],
        "test_escort_stage_at_instance_is_rejected_and_retried": [
            "scenario-director::scene-bound-proposal-stages-are-validated-before-publication"
        ],
        "test_occupant_stage_at_anchor_is_rejected_and_retried": [
            "scenario-director::scene-bound-proposal-stages-are-validated-before-publication"
        ],
        "test_reach_quantity_two_is_rejected_and_retried": [
            "quest-blueprint::reach-and-escort-objectives-accept-only-quantity-one",
            "scenario-director::scene-bound-proposal-stages-are-validated-before-publication"
        ],
        "test_unknown_anchor_near_is_rejected_and_retried": [
            "scenario-director::scene-bound-proposal-stages-are-validated-before-publication"
        ],
        "test_valid_instance_bound_payload_passes_guardrail_and_compiles": [
            "scenario-director::scene-bound-proposal-stages-are-validated-before-publication"
        ]
    },
    "SecretSetValidatorUnitTests": {
        "test_secret_set_passes_disguised_and_unbound_numbers": [
            "persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values"
        ],
        "test_secret_set_rejects_every_bound_number_and_folds_fullwidth_digits": [
            "persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values"
        ]
    },
    "StartupRegistrationTests": {
        "test_startup_seam_registers_the_layer_with_the_sentinel_fallback": [
            "npc-dialogue::the-generative-dialogue-layer-preserves-the-transport-and-single-writer-boundaries"
        ],
        "test_startup_seam_survives_a_foreign_npc_dialogue_registration": [
            "npc-dialogue::the-generative-dialogue-layer-preserves-the-transport-and-single-writer-boundaries"
        ]
    },
    "ValidatorRetryTests": {
        "test_empty_nonchinese_and_placeholder_speech_are_rejected_and_retried": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_empty_secret_set_installs_no_leak_check": [
            "persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values"
        ],
        "test_fullwidth_digit_echo_is_rejected_and_retried": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_interleaved_calls_keep_their_own_leak_context": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_interleaved_calls_keep_their_own_secret_sets": [
            "persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values"
        ],
        "test_item_intent_with_invalid_payload_is_rejected_and_retried": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_leak_exhausts_retries_and_degrades_never_presenting_the_number": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_malformed_exam_payload_is_rejected_and_retried": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_malformed_party_invite_payload_is_rejected_and_retried": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_missing_or_extra_delta_payload_is_rejected_and_retried": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_missing_target_rank_is_rejected_and_retried": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_no_affinity_context_disables_the_leak_check": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_out_of_range_delta_payload_is_rejected_and_retried": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_overlong_speech_is_rejected_and_degrades_to_none": [
            "npc-dialogue::npc-dialogue-degrades-to-greeting-or-silence-offline"
        ],
        "test_secret_set_echo_is_rejected_and_retried_without_any_affinity_record": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona",
            "persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values"
        ],
        "test_secret_set_exhausts_retries_and_degrades_never_presenting_the_number": [
            "persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values"
        ],
        "test_secret_set_passes_a_disguised_value_echo": [
            "persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values"
        ],
        "test_secret_set_with_affinity_context_covers_both_sources": [
            "persona-dialogue-injection::the-no-leak-validator-binds-a-per-call-bounded-secret-set-including-disguise-true-values"
        ],
        "test_speech_echoing_the_secret_value_is_rejected_and_retried": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_speech_mentioning_only_the_stage_name_passes": [
            "npc-dialogue::npc-dialogue-prompts-are-deterministic-bounded-and-inject-disguised-stats-affinity-context-and-persona"
        ],
        "test_unknown_intent_kind_is_rejected_and_retried_with_error_appended": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_valid_adjust_relation_delta_passes_on_the_first_attempt": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ],
        "test_valid_bounded_reply_passes_on_the_first_attempt": [
            "npc-dialogue::npc-dialogue-runs-a-guarded-generative-reply-pipeline"
        ],
        "test_valid_party_invite_payload_passes_on_the_first_attempt": [
            "npc-dialogue::intent-extraction-is-whitelisted-and-shape-validated-per-kind"
        ]
    }
}

#: Module-level helpers moved into the family helpers modules; a split module
#: must import its family's helpers module when its classes use any of them.
DIRECTOR_HELPERS = {
    "_raw", "_semantic_reset", "_fallback_reset", "_schema_reset", "_reset_all",
    "await_result", "_item", "_location", "_stage", "_blueprint", "_payload",
    "_context", "_instance_payload",
}
DIALOGUE_HELPERS = {
    "_raw", "_semantic_reset", "_fallback_reset", "_schema_reset", "_reset_all",
    "await_result", "_npc_context", "_player_context", "_memory", "_reply_text",
    "_HeldDialogueClient",
}
FAMILY_HELPERS = {
    "test_scenario_director_proposals.py": "_director_helpers",
    "test_scenario_director_prompts.py": "_director_helpers",
    "test_scenario_director_validation.py": "_director_helpers",
    "test_scenario_director_registration.py": "_director_helpers",
    "test_npc_dialogue_prompts.py": "_dialogue_helpers",
    "test_npc_dialogue_registration.py": "_dialogue_helpers",
    "test_npc_dialogue_retry.py": "_dialogue_helpers",
}


def _class_annotations(path: Path) -> dict[str, dict[str, list[str]]]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    out = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        methods = {}
        for child in node.body:
            if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            ids = []
            for decorator in child.decorator_list:
                if not (isinstance(decorator, ast.Call) and isinstance(decorator.func, ast.Name)):
                    continue
                if decorator.func.id != "covers_requirement":
                    continue
                for arg in decorator.args:
                    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                        ids.append(arg.value)
            if ids:
                methods[child.name] = sorted(ids)
        if methods:
            out[node.name] = methods
    return out


def _helpers_import(path: Path) -> str | None:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module:
            if node.module.endswith(("_director_helpers", "_dialogue_helpers")):
                return node.module.rsplit(".", 1)[-1]
    return None


class AiTestLayoutContractTests(unittest.TestCase):
    @covers_requirement(
        "evennia-test-optimization::ai-test-modules-are-split-into-themed-helpers-backed-modules"
    )
    def test_scenario_director_family_splits_into_the_four_themed_modules(self):
        discovered = {path.name for path in AI_TESTS.glob("test_scenario_director_*.py")}
        self.assertEqual(discovered, DIRECTOR_SPLIT_MODULES)

    @covers_requirement(
        "evennia-test-optimization::ai-test-modules-are-split-into-themed-helpers-backed-modules"
    )
    def test_npc_dialogue_family_splits_into_the_four_themed_modules(self):
        discovered = {path.name for path in AI_TESTS.glob("test_npc_dialogue_*.py")}
        self.assertEqual(discovered, DIALOGUE_SPLIT_MODULES)

    @covers_requirement(
        "evennia-test-optimization::ai-test-modules-are-split-into-themed-helpers-backed-modules"
    )
    def test_every_pre_split_class_sits_in_its_expected_module(self):
        for path in sorted(AI_TESTS.glob("test_*.py")):
            if path.name not in CLASS_MODULES.values():
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            actual = {
                node.name for node in tree.body if isinstance(node, ast.ClassDef)
            }
            for class_name, module in CLASS_MODULES.items():
                if module == path.name:
                    self.assertIn(class_name, actual)
            expected_for_module = {
                class_name
                for class_name, module in CLASS_MODULES.items()
                if module == path.name
            }
            self.assertEqual(actual & set(CLASS_MODULES), expected_for_module)

    @covers_requirement(
        "evennia-test-optimization::ai-test-modules-are-split-into-themed-helpers-backed-modules"
    )
    def test_requirement_annotations_stay_on_the_same_methods(self):
        observed = {}
        for path in sorted(AI_TESTS.glob("test_*.py")):
            if path.name not in CLASS_MODULES.values():
                continue
            for class_name, methods in _class_annotations(path).items():
                observed[class_name] = methods
        self.assertEqual(observed, PRE_SPLIT_ANNOTATIONS)

    @covers_requirement(
        "evennia-test-optimization::ai-test-modules-are-split-into-themed-helpers-backed-modules"
    )
    def test_split_modules_use_and_do_not_redefine_family_helpers(self):
        for path in sorted(AI_TESTS.glob("test_*.py")):
            if path.name not in FAMILY_HELPERS:
                continue
            with self.subTest(module=path.name):
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
                family_helpers = (
                    DIRECTOR_HELPERS
                    if FAMILY_HELPERS[path.name] == "_director_helpers"
                    else DIALOGUE_HELPERS
                )
                used_helpers = {
                    node.id
                    for node in ast.walk(tree)
                    if isinstance(node, ast.Name)
                    and isinstance(node.ctx, ast.Load)
                    and node.id in family_helpers
                }
                if used_helpers:
                    self.assertEqual(
                        _helpers_import(path), FAMILY_HELPERS[path.name]
                    )
                defined = {
                    node.name
                    for node in tree.body
                    if (isinstance(node, ast.FunctionDef)
                        or isinstance(node, ast.ClassDef))
                    and node.name in family_helpers
                }
                self.assertEqual(defined, set())


if __name__ == "__main__":
    unittest.main()
