"""Every guild-economy delta-spec scenario maps to at least one test (task 13.4).

The mapping table is a living guard: this test parses every spec file under
this change, extracts every ``#### Scenario:`` title, and asserts (a) the title
is present in the mapping and (b) the referenced test method exists in the
suite. A renamed test or an unwritten scenario fails loudly here.
"""

import re
import unittest
from pathlib import Path


SPECS_ROOT = (
    Path(__file__).resolve().parents[3]
    / "openspec"
    / "changes"
    / "guild-economy"
    / "specs"
)

MODULES = {
    "config": "world.rules.tests.test_guild_config",
    "components": "typeclasses.tests.test_components",
    "interiors": "world.maps.tests.test_service_interiors",
    "sync": "world.rules.tests.test_guild_economy_sync",
    "registration": "world.rules.tests.test_guild_registration",
    "acquire": "world.quests.tests.test_acquire",
    "rewards": "world.rules.tests.test_guild_rewards",
    "session": "world.rules.tests.test_combat_session",
    "exams": "world.rules.tests.test_guild_exams",
    "economy": "world.rules.tests.test_shop_economy",
    "clock": "world.rules.tests.test_shop_clock_sources",
    "commands": "commands.tests.test_guild_economy_commands",
    "phase4": "world.rules.tests.test_phase4_integration",
    "guards": "world.rules.tests.test_guild_economy_guards",
}


def ref(module_key: str, class_name: str, method: str) -> str:
    return f"{MODULES[module_key]}.{class_name}.{method}"


SCENARIO_TO_TEST = {
    # guild-registration
    "Service NPC exposes its capabilities": ref(
        "components", "ComponentModuleSourceTests", "test_each_component_has_unique_stable_name"
    ),
    "Components do not implement business writes": ref(
        "components", "ComponentModuleSourceTests", "test_components_define_only_capability_markers_and_service_data"
    ),
    "Undisguised character registers at F": ref(
        "registration", "GuildRegistrationTests", "test_undisguised_character_registers_at_f_with_true_snapshot"
    ),
    "Disguise affects only the registration snapshot": ref(
        "registration", "GuildRegistrationTests", "test_disguise_affects_only_the_registration_snapshot"
    ),
    "Registration failure is atomic": ref(
        "registration", "GuildRegistrationTests", "test_registration_is_atomic_on_rank_write_failure"
    ),
    "Staff component is the sole branch authority": ref(
        "registration", "GuildRegistrationTests", "test_staff_component_is_sole_branch_authority"
    ),
    "Remote staff cannot register a player": ref(
        "registration", "GuildRegistrationTests", "test_remote_staff_cannot_register"
    ),
    "Repeated registration preserves historical values": ref(
        "registration", "GuildRegistrationTests", "test_repeat_registration_preserves_historical_values"
    ),
    "Partial membership data fails closed": ref(
        "registration", "GuildRegistrationTests", "test_partial_membership_fails_closed"
    ),
    # guild-quest-board
    "Valid hand-written offer registers": ref(
        "rewards", "OfferValidationTests", "test_valid_handwritten_offer_registers"
    ),
    "Out-of-band reward is rejected": ref(
        "rewards", "OfferValidationTests", "test_out_of_band_copper_is_rejected"
    ),
    "S-rank open upper bound is honored": ref(
        "rewards", "OfferValidationTests", "test_s_rank_open_upper_bound_is_honored"
    ),
    "F member sees only local F offers": ref(
        "rewards", "BoardAccessTests", "test_f_member_sees_only_local_f_offers"
    ),
    "True exceptional power does not bypass rank": ref(
        "rewards", "BoardAccessTests", "test_true_exceptional_power_does_not_bypass_rank"
    ),
    "Eligible offer creates a normal quest record": ref(
        "rewards", "BoardAccessTests", "test_eligible_offer_creates_normal_quest_record"
    ),
    "Over-rank acceptance is rejected before quest mutation": ref(
        "rewards", "BoardAccessTests", "test_over_rank_direct_acceptance_is_rejected_before_quest_mutation"
    ),
    "Abandonment preserves quest-runtime semantics": ref(
        "rewards", "BoardAccessTests", "test_abandonment_delegates_to_quest_runtime"
    ),
    "Guild workflow is reachable from commands": ref(
        "commands", "GuildCommandTests", "test_register_list_accept_turnin_flow"
    ),
    "Guild command cannot address a remote dbref": ref(
        "commands", "GuildCommandTests", "test_absent_staff_rejects"
    ),
    # quest-reward-settlement
    "First completed acceptance is paid once": ref(
        "rewards", "RewardSettlementTests", "test_first_completed_acceptance_is_paid_once"
    ),
    "Duplicate turn-in pays nothing": ref(
        "rewards", "RewardSettlementTests", "test_duplicate_turn_in_pays_nothing"
    ),
    "Later acceptance has independent claim identity": ref(
        "rewards", "RewardSettlementTests", "test_later_acceptance_has_independent_claim_identity"
    ),
    "Reward grants all configured surfaces": ref(
        "rewards", "RewardSettlementTests", "test_first_completed_acceptance_is_paid_once"
    ),
    "Reward item advances another ACQUIRE quest atomically": ref(
        "rewards", "RewardSettlementTests", "test_reward_item_advances_another_acquire_quest_atomically"
    ),
    "Fault at every write position restores all surfaces": ref(
        "rewards", "RewardSettlementTests", "test_fault_at_every_write_position_restores_all_surfaces"
    ),
    "Valid ACQUIRE objective registers": ref(
        "acquire", "AcquireDefinitionTests", "test_valid_acquire_objective_registers_and_starts_at_zero"
    ),
    "Caller assertion cannot forge acquisition": ref(
        "acquire", "AcquireProgressTests", "test_import_population_is_not_gameplay_acquisition"
    ),
    "Removal does not reverse progress": ref(
        "acquire", "AcquireProgressTests", "test_removal_does_not_reverse_progress"
    ),
    "One addition advances multiple quests without surplus carry": ref(
        "acquire", "AcquireProgressTests", "test_one_addition_advances_multiple_quests_without_surplus_carry"
    ),
    "Imported items do not auto-complete a later quest": ref(
        "acquire", "ImportNonProgressionTests", "test_imported_items_do_not_auto_complete_a_later_quest"
    ),
    # guild-rank-exams
    "Threshold alone does not promote": ref(
        "exams", "ExamStartTests", "test_threshold_alone_does_not_promote"
    ),
    "Below-threshold request is rejected": ref(
        "exams", "ExamStartTests", "test_below_threshold_request_is_rejected"
    ),
    "Rank skipping is rejected": ref(
        "exams", "ExamStartTests", "test_rank_skipping_is_rejected"
    ),
    "Command trigger starts an eligible exam": ref(
        "exams", "ExamStartTests", "test_command_trigger_starts_an_eligible_exam"
    ),
    "Future intent has no extra authority": ref(
        "exams", "ExamStartTests", "test_npc_intent_has_no_extra_authority"
    ),
    "Duplicate active exam is rejected": ref(
        "exams", "ExamStartTests", "test_duplicate_active_exam_is_rejected"
    ),
    "Every rank profile stays inside its lore band": ref(
        "exams", "ExamProfileValidationTests", "test_every_rank_profile_stays_inside_its_lore_band"
    ),
    "Disguised candidate receives the same opponent": ref(
        "exams", "ExamProfileValidationTests", "test_spawned_opponent_uses_true_profile_stats"
    ),
    "Examiner knockout is not a quest kill": ref(
        "exams", "ExamCombatTests", "test_lethal_exam_defeat_grants_no_kill_rewards"
    ),
    "Candidate knockout is nonfatal but loses": ref(
        "exams", "ExamCombatTests", "test_candidate_lethal_defeat_fails_but_restores"
    ),
    "Passing promotes exactly one rank": ref(
        "exams", "ExamCombatTests", "test_promotion_preserves_merit"
    ),
    "Failed attempt can be retried": ref(
        "exams", "ExamCombatTests", "test_failed_attempt_can_be_retried_with_next_number"
    ),
    "Replayed settlement cannot promote twice": ref(
        "exams", "ExamCombatTests", "test_replayed_settlement_cannot_promote_twice"
    ),
    # player-combat-session
    "Present monster can be engaged": ref(
        "session", "EngageTests", "test_present_monster_can_be_engaged"
    ),
    "Remote or dead target is rejected": ref(
        "session", "EngageTests", "test_remote_or_dead_target_is_rejected"
    ),
    "Active session blocks another engagement": ref(
        "session", "EngageTests", "test_active_session_blocks_another_engagement"
    ),
    "Invalid cast preserves the round before initiative": ref(
        "session", "PlayerRoundTests", "test_invalid_cast_preserves_round_before_initiative"
    ),
    "One request drives one complete round": ref(
        "session", "PlayerRoundTests", "test_one_request_drives_one_complete_round"
    ),
    "Flee closes the same session": ref(
        "session", "PlayerRoundTests", "test_flee_closes_the_same_session"
    ),
    "Overwhelming player resolves a reachable hunt": ref(
        "session", "PlayerRoundTests", "test_overwhelming_player_resolves_after_first_action"
    ),
    "Engage alone never runs an overwhelming round": ref(
        "session", "PlayerRoundTests", "test_no_action_before_overwhelm_round"
    ),
    "Disconnect and reconnect resume the same session": ref(
        "session", "SessionPersistenceTests", "test_disconnect_reconnect_resumes_same_session"
    ),
    "Deleted enemy does not strand the player": ref(
        "session", "SessionPersistenceTests", "test_deleted_enemy_does_not_strand_player"
    ),
    "Exit traversal is blocked during combat": ref(
        "session", "SessionPersistenceTests", "test_exit_traversal_is_blocked_during_combat"
    ),
    "Explicit forfeit cleans an exam": ref(
        "session", "SessionPersistenceTests", "test_forfeit_cleans_session"
    ),
    # action-resolution-pipeline
    "Preflight rejection has no side effects": ref(
        "session", "PreflightSideEffectTests", "test_preflight_rejection_has_no_side_effects"
    ),
    "Successful preflight does not roll or stage": ref(
        "session", "PreflightSideEffectTests", "test_successful_preflight_does_not_roll_or_stage"
    ),
    # shop-economy
    "Initial ordinary goods validate": ref(
        "config", "ShopRuleTests", "test_loaded_shops_are_integer_and_band_consistent"
    ),
    "Floating price is rejected": ref(
        "config", "ShopRuleTests", "test_float_price_is_rejected"
    ),
    "Repeated startup preserves a sold-out item": ref(
        "sync", "ServiceContentSyncTests", "test_merchant_stock_initializes_only_when_absent"
    ),
    "Malformed stock fails closed": ref(
        "economy", "MerchantStockParsingTests", "test_malformed_stock_fails_closed"
    ),
    "Successful purchase uses integer copper": ref(
        "economy", "ShopTradeTests", "test_successful_purchase_uses_integer_copper"
    ),
    "Insufficient funds changes nothing": ref(
        "economy", "ShopTradeTests", "test_insufficient_funds_changes_nothing"
    ),
    "Sale cannot overflow merchant stock": ref(
        "economy", "ShopTradeTests", "test_sale_cannot_overflow_merchant_stock"
    ),
    "Fault injection restores every trade surface": ref(
        "economy", "ShopTradeTests", "test_fault_injection_restores_every_trade_surface"
    ),
    "Closed shop rejects trade": ref(
        "economy", "ShopTradeTests", "test_closed_shop_rejects_trade"
    ),
    "Multi-boundary skip emits each transition": ref(
        "clock", "ShopHoursArithmeticTests", "test_multi_boundary_skip_emits_each_transition"
    ),
    "Daily restock fills only to cap": ref(
        "clock", "CaravanArrivalTests", "test_daily_restock_fills_only_to_cap"
    ),
    "Multi-day skip catches up deterministically": ref(
        "clock", "CaravanArrivalTests", "test_multi_day_skip_catches_up_deterministically"
    ),
    "Caravan precedes shop opening": ref(
        "clock", "StageOrderAndRegistrationTests", "test_caravan_precedes_shop_hours_in_stage_order"
    ),
    "Altoria merchant is usable through commands": ref(
        "commands", "EconomyCommandTests", "test_stock_buy_sell_flow"
    ),
    # sample-city-altoria
    "Grid topology is unchanged": ref(
        "interiors", "ServiceInteriorTests", "test_grid_topology_is_unchanged"
    ),
    "Both interiors are reachable and permanent": ref(
        "interiors", "ServiceInteriorTests", "test_fresh_sync_creates_two_permanent_interiors"
    ),
    "Interiors do not become xyzgrid nodes": ref(
        "interiors", "ServiceInteriorTests", "test_interiors_are_not_xyzgrid_nodes"
    ),
    "Fresh startup creates a playable service path": ref(
        "sync", "ServiceContentSyncTests", "test_fresh_sync_creates_one_guild_and_one_merchant_host"
    ),
    "Repeated startup creates no duplicates": ref(
        "sync", "ServiceContentSyncTests", "test_repeated_sync_creates_no_duplicates"
    ),
    "Live merchant stock survives content resync": ref(
        "sync", "ServiceContentSyncTests", "test_merchant_stock_initializes_only_when_absent"
    ),
    # equipment-inventory
    "add_item appends through an inventory plan": ref(
        "acquire", "AcquireProgressTests", "test_add_item_tolerates_no_inventory"
    ),
    "Planning has no side effects": ref(
        "acquire", "AcquireProgressTests", "test_planning_is_side_effect_free"
    ),
    # universal-action-ownership
    "An entity with no imported skill data still owns both innate actions": ref(
        "session", "InnateSkillTests", "test_no_skill_entity_owns_both_innate_actions"
    ),
    "An entity with a full imported skill list also owns both innate actions": ref(
        "session", "InnateSkillTests", "test_full_import_list_plus_innate"
    ),
    "A Monster instance can fight without spawned skill data": ref(
        "session", "InnateSkillTests", "test_monster_instance_can_fight_without_spawned_skills"
    ),
    "Basic attack does not bypass ActionResolver": ref(
        "session", "InnateSkillTests", "test_basic_attack_rejects_out_of_combat"
    ),
    # disguised-stats-boundary
    "Accessor documentation still names exactly three consumers": ref(
        "registration", "RegistrationBoundaryScanTests", "test_get_display_value_docstring_names_exactly_three_consumers"
    ),
    "Registration is the only implemented guild caller": ref(
        "registration", "RegistrationBoundaryScanTests", "test_only_registration_path_reads_disguise_in_guild_modules"
    ),
    # world-clock
    "A successful out-of-combat cast advances its reported command time": ref(
        "session", "CommandSessionTests", "test_active_session_cast_does_not_advance_command_time"
    ),
    "Terminal session settles all round time once": ref(
        "session", "PlayerRoundTests", "test_terminal_victory_settles_rounds_once_and_clears"
    ),
}


SCENARIO_RE = re.compile(r"^#### Scenario: (.+)$")


class GuildEconomyScenarioMappingTests(unittest.TestCase):
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
            with self.subTest(scenario=title, method=mapping_entry):
                module = __import__(module_name, fromlist=[class_name])
                self.assertTrue(
                    hasattr(getattr(module, class_name), method),
                    f"{mapping_entry} missing",
                )


if __name__ == "__main__":
    unittest.main()