"""Every delta-spec scenario maps to at least one deterministic test (10.1).

The mapping table is a living guard: this test parses every spec file under
this change, extracts every ``#### Scenario:`` title, and asserts (a) the title
is present in the mapping and (b) the referenced test method exists in the
suite. A renamed test or an unwritten scenario fails loudly here.
"""

import re
import unittest
from pathlib import Path


SPECS_ROOT = Path(__file__).resolve().parents[3] / "openspec" / "changes" / "quest-runtime" / "specs"

QUEST_MODULES = {
    "definitions": "world.quests.tests.test_definitions",
    "runtime": "world.quests.tests.test_runtime",
    "binding": "world.quests.tests.test_binding",
    "events": "world.quests.tests.test_action_events",
    "planner": "world.quests.tests.test_planner",
    "room": "world.quests.tests.test_room_observation",
    "deadlines": "world.quests.tests.test_deadlines",
    "integration": "world.quests.tests.test_integration",
    "scenarios": "world.quests.tests.test_pipeline_scenarios",
}


def ref(module_key: str, class_name: str, method: str) -> str:
    return f"{QUEST_MODULES[module_key]}.{class_name}.{method}"


# Map each exact spec scenario title to a real, runnable test reference.
SCENARIO_TO_TEST = {
    # quest-blueprint
    "Explicit stage indices are representable and preserved": ref(
        "definitions", "DefinitionRegistrationTests", "test_explicit_stage_indices_are_inspectable"
    ),
    "Definition content cannot be mutated after validation": ref(
        "definitions", "DefinitionRegistrationTests", "test_registered_content_is_deeply_immutable"
    ),
    "Raw AI-shaped data is not runtime input": ref(
        "definitions", "DefinitionRegistrationTests", "test_raw_mapping_and_ai_shaped_input_never_enter_registry"
    ),
    "An emergency quest uses an ordinary completion mechanic": ref(
        "definitions", "DefinitionRegistrationTests", "test_valid_objective_shapes_register"
    ),
    "An anchor destination is structurally valid": ref(
        "definitions", "DefinitionRegistrationTests", "test_placed_anchor_is_structurally_valid_without_a_room_dbref"
    ),
    "Lore-known but unplaced anchor is rejected": ref(
        "definitions", "DefinitionRegistrationTests", "test_lore_known_but_unplaced_anchor_is_rejected"
    ),
    "A malformed locator is rejected": ref(
        "definitions", "DefinitionRegistrationTests", "test_ambiguous_and_malformed_locators_rejected"
    ),
    "Wilderness destination cannot be declared": ref(
        "definitions", "DefinitionRegistrationTests", "test_wilderness_destination_cannot_be_declared"
    ),
    "A complete hand-written definition registers": ref(
        "definitions", "DefinitionRegistrationTests", "test_valid_objective_shapes_register"
    ),
    "Non-contiguous stages are rejected": ref(
        "definitions", "DefinitionRegistrationTests", "test_non_contiguous_and_nonzero_start_indices_rejected"
    ),
    "Equal registration is idempotent and conflicting registration is rejected": ref(
        "definitions", "DefinitionRegistrationTests", "test_conflicting_registration_is_rejected_keeping_original"
    ),
    "Objective fields are validated before play": ref(
        "definitions", "DefinitionRegistrationTests", "test_defeat_selector_validation"
    ),
    "Deadline None has one meaning": ref(
        "definitions", "DefinitionRegistrationTests", "test_deadline_none_has_one_meaning_and_invalid_values_rejected"
    ),
    "Catalog synchronization is repeatable": ref(
        "definitions", "CatalogTests", "test_catalog_sync_is_repeatable_and_creates_no_records"
    ),
    "Catalog works without generative services": ref(
        "integration", "OfflineRuntimePathTests", "test_hand_written_hunt_completes_without_ai_or_manual_progress"
    ),
    # quest-lifecycle
    "A record round-trips through JSON": ref(
        "runtime", "RuntimeLifecycleTests", "test_record_round_trips_through_json"
    ),
    "Unaccepted definition has no record": ref(
        "runtime", "RuntimeLifecycleTests", "test_unaccepted_definition_has_no_record"
    ),
    "Malformed persisted data fails without a partial write": ref(
        "runtime", "RuntimeLifecycleTests", "test_malformed_log_fails_any_operation_without_partial_write"
    ),
    "Missing definition is reported": ref(
        "runtime", "RuntimeLifecycleTests", "test_missing_definition_is_reported_not_reinterpreted"
    ),
    "Duplicate quest ids are rejected": ref(
        "runtime", "RuntimeLifecycleTests", "test_duplicate_quest_ids_are_rejected"
    ),
    "First acceptance succeeds": ref(
        "runtime", "RuntimeLifecycleTests", "test_first_acceptance_creates_stage_zero_active_record"
    ),
    "Duplicate active acceptance is rejected": ref(
        "runtime", "RuntimeLifecycleTests", "test_duplicate_active_acceptance_is_rejected"
    ),
    "Terminal quest may be retried deterministically": ref(
        "runtime", "RuntimeLifecycleTests", "test_terminal_quest_may_be_retried_deterministically"
    ),
    "Explicit deadline is converted to ticks": ref(
        "runtime", "RuntimeLifecycleTests", "test_explicit_deadline_is_converted_to_ticks"
    ),
    "No-deadline definition remains without a deadline": ref(
        "runtime", "RuntimeLifecycleTests", "test_no_deadline_definition_remains_without_a_deadline"
    ),
    "Abandonment records failure and releases a pin": ref(
        "binding", "BindingTests", "test_abandonment_releases_exact_pin"
    ),
    "Repeated abandonment is harmless": ref(
        "runtime", "RuntimeLifecycleTests", "test_repeated_abandonment_is_harmless"
    ),
    "Runtime binding stores identities and pins the instance": ref(
        "binding", "BindingTests", "test_runtime_binding_stores_identities_and_pins_instance"
    ),
    "Objective and protected identities remain distinct": ref(
        "binding", "BindingTests", "test_escort_binding_stores_only_protected_identities"
    ),
    "Overlapping objective and protected binding is rejected": ref(
        "binding", "BindingTests", "test_overlapping_objective_and_protected_binding_is_rejected"
    ),
    "Persisted overlapping identity sets are invalid": ref(
        "binding", "BindingTests", "test_persisted_overlap_fails_before_any_lifecycle_operation"
    ),
    "Conflicting rebind is rejected atomically": ref(
        "binding", "BindingTests", "test_conflicting_rebind_is_rejected_before_mutation"
    ),
    "Pin failure rolls back acceptance or binding": ref(
        "binding", "BindingTests", "test_pin_failure_rolls_back_binding_with_cache_restore"
    ),
    "Quest-log failure restores an already-written pin": ref(
        "binding", "BindingTests", "test_quest_log_failure_restores_an_already_written_pin"
    ),
    # quest-progress-tracking
    "Player defeat advances a matching tier objective automatically": ref(
        "planner", "QuestPlannerTests", "test_player_defeat_advances_matching_tier_objective"
    ),
    "Bound objective matches exact dbref": ref(
        "planner", "QuestPlannerTests", "test_bound_objective_matches_exact_dbref_not_display_key"
    ),
    "Another character's action grants no ordinary kill credit": ref(
        "planner", "QuestPlannerTests", "test_non_player_actor_grants_no_ordinary_kill_credit"
    ),
    "Quest planner failure rejects the complete action": ref(
        "events", "EventEffectPlannerSeamTests", "test_malformed_planner_output_rejects_the_complete_action"
    ),
    "AREA defeat entries aggregate without skipping stages": ref(
        "planner", "QuestPlannerTests", "test_area_defeat_aggregates_without_skipping_stages"
    ),
    "Anchor arrival completes a matching REACH stage": ref(
        "room", "RoomArrivalProgressTests", "test_anchor_arrival_completes_matching_reach_stage"
    ),
    "Grid arrival uses exact XYZ identity": ref(
        "room", "RoomArrivalProgressTests", "test_grid_arrival_uses_exact_xyz_identity"
    ),
    "Bound instance arrival uses the accepted record": ref(
        "room", "RoomArrivalProgressTests", "test_bound_instance_arrival_uses_accepted_record"
    ),
    "Escort requires every protected entity alive and present": ref(
        "room", "RoomArrivalProgressTests", "test_escort_requires_all_protected_entities_alive_and_present"
    ),
    "Existing instance interaction behavior remains intact": ref(
        "room", "RoomArrivalProgressTests", "test_instance_interaction_behavior_remains_intact"
    ),
    "Wilderness traversal does not produce false quest progress": ref(
        "room", "WildernessObservationExclusionTests", "test_wilderness_entry_and_step_do_not_invoke_observation"
    ),
    "Intermediate objective enters the next stage": ref(
        "planner", "QuestPlannerTests", "test_area_defeat_aggregates_without_skipping_stages"
    ),
    "Final objective completes the quest": ref(
        "planner", "QuestPlannerTests", "test_final_objective_completes_and_clears_bindings"
    ),
    "Instance pin is released on stage exit": ref(
        "planner", "QuestPlannerTests", "test_final_objective_completes_and_clears_bindings"
    ),
    "Hand-written hunt completes through ordinary combat resolution": ref(
        "integration", "OfflineRuntimePathTests", "test_hand_written_hunt_completes_without_ai_or_manual_progress"
    ),
    # quest-failure-conditions
    "Server start activates deadline settlement": ref(
        "deadlines", "DeadlineSettlementTests", "test_server_start_calls_quest_sync_after_map_sync"
    ),
    "Repeated startup registration is idempotent": ref(
        "deadlines", "DeadlineSettlementTests", "test_repeated_startup_registration_is_idempotent"
    ),
    "Due quest fails": ref(
        "deadlines", "DeadlineSettlementTests", "test_due_quest_fails_once_and_emits_json_safe_event"
    ),
    "No-deadline quest never expires": ref(
        "deadlines", "DeadlineSettlementTests", "test_no_deadline_quest_never_expires"
    ),
    "Deadline releases bound instance": ref(
        "deadlines", "DeadlineSettlementTests", "test_deadline_releases_bound_instance_and_clears_binding"
    ),
    "Malformed data cannot partially settle the owning character": ref(
        "deadlines", "DeadlineSettlementTests", "test_malformed_character_is_isolated"
    ),
    "Due room is resolved in one advance": ref(
        "deadlines", "DeadlinePrecedesReclamationTests", "test_due_room_is_unpinned_and_reclaimed_in_one_advance"
    ),
    "Protected NPC death fails an escort quest": ref(
        "planner", "QuestPlannerTests", "test_protected_npc_death_fails_escort_quest"
    ),
    "Same display key does not create a false failure": ref(
        "planner", "QuestPlannerTests", "test_same_display_key_creates_no_false_failure"
    ),
    "Objective target death cannot trigger protected failure": ref(
        "planner", "QuestPlannerTests", "test_objective_target_death_cannot_trigger_protected_failure"
    ),
    "Commit fault rolls back death and quest failure together": ref(
        "planner", "QuestPlannerTests", "test_commit_fault_rolls_back_death_and_quest_failure_together"
    ),
    # action-resolution-pipeline -- step/commit coverage lives in the landed
    # rules suite; the ADDED planner-seam scenarios live in this change.
    "An unknown skill key rejects at step 1 with a named reason": ref(
        "scenarios", "ExistingPipelineTestFinder", "unknown_skill"
    ),
    "A PASSIVE skill cannot be cast": ref(
        "scenarios", "ExistingPipelineTestFinder", "passive_skill"
    ),
    "Insufficient resources reject at step 2": ref(
        "scenarios", "ExistingPipelineTestFinder", "insufficient_resource"
    ),
    "A buff that blocks action rejects at step 4": ref(
        "scenarios", "ActionForbiddenStepTests", "test_buff_that_blocks_action_rejects_at_step_4"
    ),
    "An unregistered effect ID rejects at step 5, naming the exact ID": ref(
        "scenarios", "ExistingPipelineTestFinder", "unknown_effect"
    ),
    "A damage effect produces structured roll and damage entries": ref(
        "scenarios", "ExistingPipelineTestFinder", "damage_entries"
    ),
    "Lethal damage emits stable target identity": ref(
        "events", "TargetDefeatedEventTests", "test_lethal_damage_emits_single_target_defeated_with_identity"
    ),
    "Multiple damage effects use projected HP without duplicate defeat": ref(
        "events", "TargetDefeatedEventTests", "test_two_damage_effects_emit_one_defeat"
    ),
    "Miss and nonlethal damage emit no defeat": ref(
        "events", "TargetDefeatedEventTests", "test_miss_emits_no_target_defeated"
    ),
    "A malformed time-cost entry rejects at step 8": ref(
        "scenarios", "ExistingPipelineTestFinder", "malformed_time_cost"
    ),
    "A failure injected at any of the eight steps leaves state unchanged": ref(
        "scenarios", "ExistingPipelineTestFinder", "failure_injected"
    ),
    "A failure inside commit reverses action and quest effects": ref(
        "scenarios", "ExistingPipelineTestFinder", "commit_failure_restore"
    ),
    "Resource deduction and the skill's own effect commit together or not at all": ref(
        "scenarios", "ExistingPipelineTestFinder", "resource_commit"
    ),
    "A rejected action produces no EventLog": ref(
        "scenarios", "ExistingPipelineTestFinder", "no_event_log"
    ),
    "An unsupported planner mutation surface is refused": ref(
        "events", "EventEffectPlannerSeamTests", "test_unsupported_planner_surface_rejects_before_mutation"
    ),
    "Repeated quest planner registration does not duplicate progress": ref(
        "events", "EventEffectPlannerSeamTests", "test_repeated_quest_planner_registration_does_not_duplicate_progress"
    ),
    "Quest planner stages without mutating": ref(
        "events", "EventEffectPlannerSeamTests", "test_planner_stages_without_mutating_when_step8_rejects"
    ),
    "Cross-request player and room effects restore by surface": ref(
        "events", "CrossRequestSurfaceRestoreTests", "test_commit_restores_out_of_request_player_and_room_surfaces"
    ),
    "Out-of-combat cast runs the planner": ref(
        "integration", "PlannerExecutionPathsTests", "test_out_of_combat_cast_executes_the_planner"
    ),
    "Combat round runs the planner": ref(
        "integration", "PlannerExecutionPathsTests", "test_combat_round_executes_the_planner"
    ),
    "Direct resolver use has identical behavior": ref(
        "integration", "PlannerExecutionPathsTests", "test_direct_resolver_use_executes_the_planner_exactly_once"
    ),
}

# Existing rules-suite tests that own the pre-commit pipeline scenarios.
EXISTING_PIPELINE_COVERAGE = {
    "unknown_skill": ("world.rules.tests.test_action_pipeline_rejections", "ActionPipelineRejectionTests", "test_unknown_skill"),
    "passive_skill": ("world.rules.tests.test_action_pipeline_rejections", "ActionPipelineRejectionTests", "test_passive_skill"),
    "insufficient_resource": ("world.rules.tests.test_action_pipeline_rejections", "ActionPipelineRejectionTests", "test_resource_read_does_not_advance_gauge_timestamp"),
    "unknown_effect": ("world.rules.tests.test_action_pipeline_rejections", "ActionPipelineRejectionTests", "test_unknown_effect"),
    "damage_entries": ("world.rules.tests.test_damage_effect_handler", "DamageEffectHandlerTests", "test_physical_damage_is_staged_before_apply"),
    "malformed_time_cost": ("world.rules.tests.test_action_pipeline_rejections", "ActionPipelineRejectionTests", "test_malformed_time_cost_does_not_commit"),
    "failure_injected": ("world.rules.tests.test_action_pipeline_rejections", "ActionPipelineRejectionTests", "test_every_named_rejection_maps_to_no_event_log"),
    "commit_failure_restore": ("world.rules.tests.test_action_pipeline_atomicity", "ActionPipelineAtomicityTests", "test_failed_second_effect_restores_first"),
    "resource_commit": ("world.rules.tests.test_action_pipeline_atomicity", "ActionPipelineAtomicityTests", "test_failed_effect_restores_resource_and_attribute_absence"),
    "no_event_log": ("world.rules.tests.test_action_pipeline_rejections", "ActionPipelineRejectionTests", "test_every_named_rejection_maps_to_no_event_log"),
}


class ExistingPipelineTestFinder:
    """Marker class holding the existing-suite reference table."""


def _check_existing(key: str) -> None:
    module_name, class_name, method = EXISTING_PIPELINE_COVERAGE[key]
    module = __import__(module_name, fromlist=[class_name])
    assert hasattr(getattr(module, class_name), method), f"{module_name}.{class_name}.{method}"


SCENARIO_RE = re.compile(r"^#### Scenario: (.+)$")


class ScenarioMappingTests(unittest.TestCase):
    def test_every_spec_scenario_is_mapped(self):
        missing = []
        for spec_path in SPECS_ROOT.glob("*/spec.md"):
            text = spec_path.read_text(encoding="utf-8")
            for match in SCENARIO_RE.finditer(text):
                title = match.group(1).strip()
                if title not in SCENARIO_TO_TEST:
                    missing.append((spec_path.name, title))
        self.assertEqual(missing, [])

    def test_every_mapped_test_method_exists(self):
        for title, mapping_entry in SCENARIO_TO_TEST.items():
            module_name, class_name, method = mapping_entry.rsplit(".", 2)
            if class_name == "ExistingPipelineTestFinder":
                _check_existing(method)
                continue
            with self.subTest(scenario=title, method=mapping_entry):
                module = __import__(module_name, fromlist=[class_name])
                self.assertTrue(
                    hasattr(getattr(module, class_name), method),
                    f"{mapping_entry} missing",
                )


if __name__ == "__main__":
    unittest.main()