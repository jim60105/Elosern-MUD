# Affected requirement inventory

This is the exhaustive current-requirement disposition for the selected families, based on the main specs at `afa974d4`. Canonical current IDs come from `uv run --locked python -m tools.spec_traceability list --json-output ...`, not manual normalization. Delta files are authoritative full replacements. Legacy scenario **headings** remain under MODIFIED because strict validation requires them; their bodies cease asserting shipped identities. A REMOVED heading retires its ID. New IDs must be generated from the future effective specs during apply.

Every MODIFIED block preserves all original scenario headings and unrelated assertions with zero coverage loss. In particular, the large `sample-city-altoria` xyzgrid block keeps every topology, permanent-interior and doorway scenario; only selected merchandise-membership bodies change. The 164 discovered planning annotation sites are Python decorators, not a count-based completion bound for JS or metadata.

## 1+5 Monster

### `monster-resource-abilities::crocodile-bite-is-one-authored-shared-engine-physical-resource-skill`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **Crocodile bite is one authored shared-engine physical resource skill**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/skills/tests/test_skill_registry/test_registry_contract.py:544 `test_tide_devouring_bite_data_contract`

### `monster-resource-abilities::successful-bite-drains-mp-and-recovers-only-actual-removal`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **Successful bite drains MP and recovers only actual removal**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/rules/tests/test_skill_hit_dependencies.py:301 `test_synthetic_transfer_partial_zero_mp_and_caster_cap`; world/rules/tests/test_skill_hit_dependencies.py:401 `test_critical_defeat_crossing`; world/rules/tests/test_skill_hit_dependencies.py:452 `test_two_species_execute_shared_drain_with_isolated_hit_state`

### `monster-resource-abilities::affordability-precedes-effects-and-recovery-precedes-costs`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **Affordability precedes effects and recovery precedes costs**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/rules/tests/test_skill_hit_dependencies.py:301 `test_synthetic_transfer_partial_zero_mp_and_caster_cap`

### `monster-resource-abilities::production-crocodile-delivery-includes-real-combat-and-persistence-evidence`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **Production crocodile delivery includes real combat and persistence evidence**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/rules/tests/test_crocodile_resource_skill.py:35 `test_production_drain_session_payment_controls_and_reload`

### `monster-resource-abilities::crocodile-ecology-documents-implemented-limits`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **Crocodile ecology documents implemented limits**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/lore/tests/test_monster_species_content.py:209 `test_the_published_narrative_is_the_approved_zh_tw_prose`

### `monster-resource-abilities::穗鳴雀-owns-its-approved-contact-resource-ability`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **穗鳴雀 owns its approved contact resource ability**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/skills/tests/test_skill_registry/test_registry_contract.py:588 `test_grain_shaking_peck_data_contract`

### `monster-resource-abilities::穗鳴雀-timed-modifier-follows-its-authored-recipient-and-lifetime`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **穗鳴雀 timed modifier follows its authored recipient and lifetime**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/rules/tests/test_sway_whistle_sparrow_resource_skill.py:43 `test_production_enemy_rider_payment_refresh_controls_and_reload`

### `monster-resource-abilities::穗鳴雀-payment-and-atomicity-retain-the-shared-transaction`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **穗鳴雀 payment and atomicity retain the shared transaction**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/rules/tests/test_effect_audiences/test_effect_routing_pipeline_rollback_and_composite_effects.py:257 `test_composite_effects_are_actual_state_changes_with_atomic_rollback`

### `monster-resource-abilities::穗鳴雀-public-ecology-reflects-the-completed-contact-kit`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **穗鳴雀 public ecology reflects the completed contact kit**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/lore/tests/test_monster_species_content.py:209 `test_the_published_narrative_is_the_approved_zh_tw_prose`; world/lore/tests/test_monster_species_content.py:235 `test_the_author_private_notes_keep_the_unknown_origin_boundary`

### `monster-resource-abilities::潮燈蟹-owns-its-approved-contact-resource-ability`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **潮燈蟹 owns its approved contact resource ability**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/skills/tests/test_skill_registry/test_registry_contract.py:629 `test_lamp_carapace_claw_data_contract`

### `monster-resource-abilities::潮燈蟹-timed-modifier-follows-its-authored-recipient-and-lifetime`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **潮燈蟹 timed modifier follows its authored recipient and lifetime**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/rules/tests/test_tide_lamp_crab_resource_skill.py:53 `test_production_self_guard_miss_ally_refresh_payment_and_reload`

### `monster-resource-abilities::潮燈蟹-payment-and-atomicity-retain-the-shared-transaction`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **潮燈蟹 payment and atomicity retain the shared transaction**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/rules/tests/test_effect_audiences/test_effect_routing_pipeline_rollback_and_composite_effects.py:257 `test_composite_effects_are_actual_state_changes_with_atomic_rollback`

### `monster-resource-abilities::潮燈蟹-public-ecology-reflects-the-completed-contact-kit`
- Current: `openspec/specs/monster-resource-abilities/spec.md` · **潮燈蟹 public ecology reflects the completed contact kit**
- Disposition: **REMOVED**. Use generic declaration, transfer, transaction, lifetime, documentation and consumer-evidence requirements.
- Current annotations: world/lore/tests/test_monster_species_content.py:209 `test_the_published_narrative_is_the_approved_zh_tw_prose`

### `monster-species-registry::numeric-combat-profiles-and-danger-grades-are-balance-gated-slots-never-invented-values`
- Current: `openspec/specs/monster-species-registry/spec.md` · **Numeric combat profiles and danger grades are balance-gated slots, never invented values**
- Disposition: **REMOVED**. Use Authored profile requirements are declared per variant.
- Current annotations: world/lore/tests/test_monster_species_registry.py:488 `test_an_unknown_habitat_tier_or_grade_is_rejected`; world/lore/tests/test_monster_species_registry.py:545 `test_a_partial_profile_cannot_be_constructed`; world/lore/tests/test_monster_species_registry.py:552 `test_an_unpopulated_or_non_integer_or_negative_value_is_rejected`; world/lore/tests/test_monster_species_registry.py:561 `test_a_complete_profile_is_accepted_and_projected_verbatim`; world/lore/tests/test_monster_species_registry.py:587 `test_a_magic_flavoured_variant_reads_none_and_never_an_inferred_number`; world/lore/tests/test_monster_species_content.py:311 `test_every_shipped_variant_carries_a_complete_profile_and_registered_grade`; world/lore/tests/test_monster_species_content.py:335 `test_every_shipped_profile_and_grade_lies_inside_its_declared_tier_band`; world/lore/tests/test_monster_species_content.py:386 `test_every_shipped_variant_constructs_an_individual_with_those_values`

### `monster-species-registry::special-abilities-are-narrative-boundaries-with-a-named-mechanics-prerequisite-never-fake-skills`
- Current: `openspec/specs/monster-species-registry/spec.md` · **Special abilities are narrative boundaries with a named mechanics prerequisite, never fake skills**
- Disposition: **REMOVED**. Use Narrative and executable monster configurations remain separate.
- Current annotations: world/lore/tests/test_monster_species_content.py:468 `test_no_registry_string_names_a_skill_behaviour_or_combat_trait`; world/lore/tests/test_monster_species_content.py:504 `test_no_registry_field_stands_in_for_an_ability_seam`; world/lore/tests/test_monster_species_content.py:513 `test_the_behaviour_selection_path_reads_no_species_identity`

### `monster-species-registry::approved-bestiary-narrative-lands-as-zh-tw-display-strings-and-synchronizes-idempotently`
- Current: `openspec/specs/monster-species-registry/spec.md` · **Approved bestiary narrative lands as zh-TW display strings and synchronizes idempotently**
- Disposition: **REMOVED**. Use Authored monster narratives synchronize without a fixed roster.
- Current annotations: world/lore/tests/test_monster_species_registry.py:783 `test_the_step_mirrors_exactly_the_species_and_variant_records`; world/lore/tests/test_monster_species_registry.py:799 `test_repeating_the_step_is_a_no_op`; world/lore/tests/test_monster_species_registry.py:823 `test_the_mirror_touches_no_monster_room_quest_or_art_record`; world/lore/tests/test_monster_species_registry.py:834 `test_one_boundary_event_carries_the_registry_context`; world/lore/tests/test_monster_species_content.py:151 `test_the_registry_carries_the_six_approved_species_and_no_others`; world/lore/tests/test_monster_species_content.py:174 `test_the_registry_carries_the_twelve_approved_variant_directions`; world/lore/tests/test_monster_species_content.py:209 `test_the_published_narrative_is_the_approved_zh_tw_prose`; world/lore/tests/test_monster_species_content.py:256 `test_every_published_string_is_verbatim_approved_prose_in_order`

### `monster-species-registry::the-approved-first-batch-profiles-and-grades-are-user-approved-literals`
- Current: `openspec/specs/monster-species-registry/spec.md` · **The approved first-batch profiles and grades are user-approved literals**
- Disposition: **REMOVED**. Use Shipped profile completeness follows authored declarations.
- Current annotations: world/lore/tests/test_monster_species_content.py:311 `test_every_shipped_variant_carries_a_complete_profile_and_registered_grade`

## 1 Monster

### `monster-action-policy::authored-crocodile-behavior-uses-the-existing-first-owned-strategy`
- Current: `openspec/specs/monster-action-policy/spec.md` · **Authored crocodile behavior uses the existing first-owned strategy**
- Disposition: **REMOVED**. Use Authored monster kits use shared policy selection and fallback.
- Current annotations: world/rules/tests/test_monster_flee_decision.py:65 `test_shipped_thresholds_and_tier_defaults_are_valid`; world/rules/tests/test_crocodile_resource_skill.py:35 `test_production_drain_session_payment_controls_and_reload`

### `monster-action-policy::穗鳴雀-contact-kit-uses-existing-first-owned-policy-and-fallback`
- Current: `openspec/specs/monster-action-policy/spec.md` · **穗鳴雀 contact kit uses existing first-owned policy and fallback**
- Disposition: **REMOVED**. Use Authored monster kits use shared policy selection and fallback.
- Current annotations: world/rules/tests/test_sway_whistle_sparrow_resource_skill.py:43 `test_production_enemy_rider_payment_refresh_controls_and_reload`

### `monster-action-policy::潮燈蟹-contact-kit-uses-existing-first-owned-policy-and-fallback`
- Current: `openspec/specs/monster-action-policy/spec.md` · **潮燈蟹 contact kit uses existing first-owned policy and fallback**
- Disposition: **REMOVED**. Use Authored monster kits use shared policy selection and fallback.
- Current annotations: world/rules/tests/test_tide_lamp_crab_resource_skill.py:53 `test_production_self_guard_miss_ally_refresh_payment_and_reload`

### `monster-individual-construction::穗鳴雀-construction-persists-both-approved-contact-kits`
- Current: `openspec/specs/monster-individual-construction/spec.md` · **穗鳴雀 construction persists both approved contact kits**
- Disposition: **REMOVED**. Use Shipped variants construct their declared configuration through the common boundary.
- Current annotations: world/lore/tests/test_monster_species_content.py:386 `test_every_shipped_variant_constructs_an_individual_with_those_values`

### `monster-individual-construction::潮燈蟹-construction-persists-both-approved-contact-kits`
- Current: `openspec/specs/monster-individual-construction/spec.md` · **潮燈蟹 construction persists both approved contact kits**
- Disposition: **REMOVED**. Use Shipped variants construct their declared configuration through the common boundary.
- Current annotations: world/lore/tests/test_monster_species_content.py:386 `test_every_shipped_variant_constructs_an_individual_with_those_values`

### `monster-species-registry::variant-skill-kits-and-behavior-references-are-immutable-authored-configuration`
- Current: `openspec/specs/monster-species-registry/spec.md` · **Variant skill kits and behavior references are immutable authored configuration**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/skills/tests/test_skill_registry/test_registry_contract.py:544 `test_tide_devouring_bite_data_contract`; world/skills/tests/test_skill_registry/test_registry_contract.py:588 `test_grain_shaking_peck_data_contract`; world/skills/tests/test_skill_registry/test_registry_contract.py:629 `test_lamp_carapace_claw_data_contract`; world/rules/tests/test_monster_individual.py:371 `test_kit_and_behaviour_profile_validation_and_assignment`

## 2 NPC

### `npc-profile-registry::altoria-lower-terrace-hosts-carry-individual-authored-profiles-and-rewritten-dialogue`
- Current: `openspec/specs/npc-profile-registry/spec.md` · **Altoria lower-terrace hosts carry individual authored profiles and rewritten dialogue**
- Disposition: **REMOVED**. Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics.
- Current annotations: world/lore/tests/test_npc_profile_slice_content.py:128 `test_altoria_lower_slice_hosts_and_tables`

### `npc-profile-registry::altoria-middle-terrace-trade-hosts-carry-individual-authored-profiles-and-rewritten-dialogue`
- Current: `openspec/specs/npc-profile-registry/spec.md` · **Altoria middle-terrace trade hosts carry individual authored profiles and rewritten dialogue**
- Disposition: **REMOVED**. Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics.
- Current annotations: world/lore/tests/test_npc_profile_slice_content.py:135 `test_altoria_trade_slice_hosts_and_tables`

### `npc-profile-registry::guild-branch-master-and-rank-examiners-carry-individual-authored-profiles-and-rewritten-dialogue`
- Current: `openspec/specs/npc-profile-registry/spec.md` · **Guild branch master and rank examiners carry individual authored profiles and rewritten dialogue**
- Disposition: **REMOVED**. Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics.
- Current annotations: world/rules/tests/test_npc_roster_validation.py:375 `test_persistent_person_passes_with_no_scripted_home_table`; world/rules/tests/test_npc_roster_validation.py:450 `test_qualified_person_missing_profile_is_reported`; world/lore/tests/test_npc_profile_slice_content.py:142 `test_altoria_guild_slice_host_people_and_table`

### `npc-profile-registry::altoria-upper-terrace-hosts-carry-individual-authored-profiles-and-rewritten-dialogue`
- Current: `openspec/specs/npc-profile-registry/spec.md` · **Altoria upper-terrace hosts carry individual authored profiles and rewritten dialogue**
- Disposition: **REMOVED**. Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics.
- Current annotations: world/lore/tests/test_npc_profile_slice_content.py:162 `test_altoria_upper_slice_hosts_and_tables`

### `npc-profile-registry::village-ciaran-first-home-hosts-carry-individual-authored-profiles-and-rewritten-dialogue`
- Current: `openspec/specs/npc-profile-registry/spec.md` · **Village Ciaran first-home hosts carry individual authored profiles and rewritten dialogue**
- Disposition: **REMOVED**. Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics.
- Current annotations: world/lore/tests/test_npc_profile_slice_content.py:169 `test_ciaran_homes_a_slice_hosts_and_tables`

### `npc-profile-registry::village-ciaran-second-home-hosts-carry-individual-authored-profiles-and-rewritten-dialogue`
- Current: `openspec/specs/npc-profile-registry/spec.md` · **Village Ciaran second-home hosts carry individual authored profiles and rewritten dialogue**
- Disposition: **REMOVED**. Use Every registry-derived host has complete individual characterization and Authored host dialogue preserves service semantics.
- Current annotations: world/lore/tests/test_npc_profile_slice_content.py:176 `test_ciaran_homes_b_slice_hosts_and_tables`

### `guild-registration::service-hosts-are-created-and-converged-from-a-declarative-yaml-roster`
- Current: `openspec/specs/guild-registration/spec.md` · **Service hosts are created and converged from a declarative YAML roster**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/maps/tests/test_service_interiors.py:208 `test_one_unresolvable_exterior_warns_and_skips_only_that_place`; world/rules/tests/test_guild_config/test_service_host_roster.py:121 `test_shipped_roster_reproduces_the_removed_yaml_rows_exactly`; world/rules/tests/test_guild_config/test_service_host_roster.py:362 `test_named_offenses_raise_the_catalog_error_family_without_db_access`; world/rules/tests/test_guild_config/test_service_host_roster.py:470 `test_derived_shop_row_collision_with_guild_registry_row_is_rejected`; world/rules/tests/test_guild_economy_sync/test_service_host_roster_authority.py:73 `test_all_rows_unresolvable_still_converge_and_never_touch_roster_hosts`; world/rules/tests/test_guild_economy_sync/test_service_content_sync.py:53 `test_fresh_sync_creates_one_guild_and_one_merchant_host`; world/rules/tests/test_guild_economy_sync/test_service_content_sync.py:155 `test_repeated_sync_creates_no_duplicates`; world/rules/tests/test_guild_economy_sync/test_service_host_identity.py:258 `test_resync_never_rewrites_authored_identity`; world/rules/tests/test_guild_economy_sync/test_service_host_identity.py:298 `test_one_added_place_row_yields_a_complete_working_location`; world/rules/tests/test_guild_economy_sync/test_service_host_identity.py:624 `test_unresolvable_anchor_room_skips_only_its_row`

### `npc-identity-titles::a-single-deterministic-composer-renders-the-npc-full-identity`
- Current: `openspec/specs/npc-identity-titles/spec.md` · **A single deterministic composer renders the NPC full identity**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_npc_identity.py:206 `test_titled_npc_composes_with_full_width_separator`; world/rules/tests/test_npc_identity.py:216 `test_untitled_npc_degrades_to_plain_name`; world/rules/tests/test_npc_identity.py:223 `test_player_and_monster_never_compose`; world/rules/tests/test_npc_identity.py:231 `test_player_and_monster_carrying_a_stray_title_row_never_compose`; world/rules/tests/test_npc_identity.py:242 `test_malformed_stored_state_degrades_without_raising`; world/rules/tests/test_npc_identity.py:250 `test_corrupt_stored_strings_degrade_instead_of_rendering`; world/rules/tests/test_npc_identity.py:268 `test_overlong_stored_title_is_content_legal_and_still_composes`; world/rules/tests/test_npc_identity.py:279 `test_a_raising_title_accessor_degrades_to_the_plain_name`; world/rules/tests/test_npc_identity.py:285 `test_an_unreadable_key_degrades_instead_of_composing_ambiguity`; world/rules/tests/test_npc_identity.py:309 `test_stored_title_is_read_back_stripped`; world/rules/tests/test_npc_identity.py:316 `test_llmnpc_subclass_composes`; world/rules/tests/test_npc_identity.py:322 `test_boundary_composition_stays_under_panel_bound`; web/webclient/presentation/tests/test_exploration_panel/test_wilderness_and_npc_titles.py:238 `test_composed_bounds_hold_for_legal_and_overlong_titles`

### `npc-identity-titles::the-import-face-rejects-a-name-already-used-by-an-existing-npc`
- Current: `openspec/specs/npc-identity-titles/spec.md` · **The import face rejects a name already used by an existing NPC**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/imports/tests/test_batch_all_or_nothing.py:181 `test_existing_npc_collision_fails_the_whole_batch`; world/imports/tests/test_batch_all_or_nothing.py:198 `test_existing_llmnpc_collision_is_rejected_too`

### `npc-identity-titles::blueprint-scene-occupants-spawn-under-the-authored-name-with-the-authored-title`
- Current: `openspec/specs/npc-identity-titles/spec.md` · **Blueprint scene occupants spawn under the authored name with the authored title**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/quests/tests/test_scene_builder/test_characterization.py:84 `test_surrounding_whitespace_never_reaches_the_entity_key`; world/quests/tests/test_scene_builder/test_characterization.py:96 `test_full_characterization_is_materialized_fully`

### `webclient-contextual-hud::stage-actors-present-the-player-and-the-dialogue-host-with-a-speaking-state`
- Current: `openspec/specs/webclient-contextual-hud/spec.md` · **Stage actors present the player and the dialogue host with a speaking state**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: web/tests/browser/test_browser_exploration_dialogue.py:284 `test_dialogue_stage_collapses_the_band_and_stands_both_actors`; web/webclient/tests/test_node_suite_evidence.py:734 `test_stage_actor_vitest_evidence_passes`

### `human-guild-hosts::altoria-qualifications-select-one-persistent-adventurer-per-branch-and-target`
- Current: `openspec/specs/human-guild-hosts/spec.md` · **Altoria qualifications select one persistent adventurer per branch and target**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_human_guild_hosts.py:99 `test_occupied_key_is_suffixed_once_and_reuse_preserves_all_live_state`; world/rules/tests/test_human_guild_hosts.py:142 `test_qualification_selects_actual_person_when_hosts_colocate_and_fails_closed`

### `human-guild-hosts::normal-hosts-own-literal-bases-gear-and-usable-complete-human-skill-lineages`
- Current: `openspec/specs/human-guild-hosts/spec.md` · **Normal hosts own literal bases gear and usable complete human skill lineages**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_human_guild_hosts.py:120 `test_normal_lineage_has_prerequisites_and_resolver_accepts_top_skill`; world/rules/tests/test_human_guild_hosts.py:173 `test_invalid_age_gear_voice_or_duplicate_person_rejects_before_creation`

### `human-guild-hosts::hosts-live-in-connected-residences-and-traverse-authored-recurring-guild-visits`
- Current: `openspec/specs/human-guild-hosts/spec.md` · **Hosts live in connected residences and traverse authored recurring guild visits**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_human_guild_hosts.py:200 `test_connected_weekly_occurrences_traverse_real_exits_and_repeat`; world/rules/tests/test_human_guild_hosts.py:213 `test_locked_weekly_arrival_remains_absent_with_no_teleport`

### `place-attendant-hosts::adding-the-blueprint-changes-no-shipped-host`
- Current: `openspec/specs/place-attendant-hosts/spec.md` · **Adding the blueprint changes no shipped host**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_config/test_service_host_roster.py:171 `test_the_attendant_blueprint_ships_without_moving_any_baseline_row`; world/rules/tests/test_guild_config/test_service_host_roster.py:641 `test_every_shipped_place_authors_a_complete_host_except_the_shelter`

### `altoria-hospitality::the-capital-has-a-tavern-an-inn-and-a-bathhouse`
- Current: `openspec/specs/altoria-hospitality/spec.md` · **The capital has a tavern, an inn and a bathhouse**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_config/test_service_host_roster.py:809 `test_the_three_hospitality_rows_are_their_own_literal_data_contract`; world/rules/tests/test_guild_config/test_service_host_roster.py:857 `test_the_hospitality_place_rows_pin_the_lane_and_bathhouse_front`; world/rules/tests/test_guild_economy_sync/test_altoria_hospitality.py:137 `test_the_three_rooms_sync_once_enterably_and_carry_a_talking_host`; world/rules/tests/test_guild_economy_sync/test_altoria_hospitality.py:196 `test_the_lane_shares_one_exterior_under_two_distinct_doorway_names`

### `altoria-hospitality::each-host-s-dialogue-teaches-what-its-location-is-for`
- Current: `openspec/specs/altoria-hospitality/spec.md` · **Each host's dialogue teaches what its location is for**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_economy_sync/test_altoria_hospitality.py:364 `test_each_host_s_table_speaks_in_character_without_command_tokens`

### `altoria-learning-and-exchange::the-capital-has-an-academy-a-merchant-hall-and-covered-market-stalls`
- Current: `openspec/specs/altoria-learning-and-exchange/spec.md` · **The capital has an academy, a merchant hall and covered market stalls**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_config/test_service_host_roster.py:1044 `test_the_two_learning_exchange_rows_are_their_own_literal_data_contract`; world/rules/tests/test_guild_config/test_service_host_roster.py:1091 `test_the_learning_exchange_place_rows_pin_the_three_exteriors`; world/rules/tests/test_guild_config/test_service_host_roster.py:1116 `test_the_stalls_row_is_host_less_in_the_shape_hostless_places_reserved`; world/rules/tests/test_guild_economy_sync/test_altoria_learning_exchange.py:274 `test_the_three_rooms_sync_once_and_the_stalls_survive_resync_host_less`; world/rules/tests/test_guild_economy_sync/test_altoria_learning_exchange.py:339 `test_the_shared_exteriors_resolve_their_doorway_counts`

### `altoria-crown-and-watch::the-capital-has-a-palace-a-noble-quarter-a-guardhouse-and-a-drill-yard`
- Current: `openspec/specs/altoria-crown-and-watch/spec.md` · **The capital has a palace, a noble quarter, a guardhouse and a drill yard**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_config/test_service_host_roster.py:914 `test_the_three_crown_watch_rows_are_their_own_literal_data_contract`; world/rules/tests/test_guild_config/test_service_host_roster.py:969 `test_the_crown_watch_place_rows_pin_the_four_exteriors`; world/rules/tests/test_guild_config/test_service_host_roster.py:993 `test_the_palace_row_is_host_less_in_the_shape_hostless_places_reserved`; world/rules/tests/test_guild_economy_sync/test_altoria_crown_watch.py:206 `test_the_four_rooms_sync_once_and_the_palace_survives_resync_host_less`; world/rules/tests/test_guild_economy_sync/test_altoria_crown_watch.py:483 `test_each_staffed_table_resolves_teaches_and_never_shops`

### `ciaran-village-commons::the-village-has-a-communal-shelter-a-sword-instructor-and-an-elder`
- Current: `openspec/specs/ciaran-village-commons/spec.md` · **The village has a communal shelter, a sword instructor and an elder**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_config/test_service_host_roster.py:737 `test_the_three_commons_rows_are_their_own_literal_data_contract`; world/rules/tests/test_guild_economy_sync/test_ciaran_village_commerce.py:487 `test_three_commons_sync_once_and_the_training_ground_holds_two_doorways`

### `ciaran-village-crafts::the-village-supplies-adornments-and-remedies-from-two-more-homes`
- Current: `openspec/specs/ciaran-village-crafts/spec.md` · **The village supplies adornments and remedies from two more homes**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_economy_sync/test_ciaran_village_commerce.py:134 `test_village_interiors_doorways_and_hosts_appear_after_sync`; world/rules/tests/test_guild_economy_sync/test_ciaran_village_commerce.py:193 `test_village_titles_avoid_commercial_words`; world/rules/tests/test_guild_economy_sync/test_ciaran_village_commerce.py:369 `test_crescent_earring_is_offered_by_one_village_shop_at_its_moved_price`

### `ciaran-village-commerce::the-village-s-hosts-are-its-own-people`
- Current: `openspec/specs/ciaran-village-commerce/spec.md` · **The village's hosts are its own people**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_economy_sync/test_ciaran_village_commerce.py:165 `test_village_hosts_carry_authored_minority_identity`

### `altoria-sanctum::the-sanctuary-s-host-ministers-and-does-not-trade`
- Current: `openspec/specs/altoria-sanctum/spec.md` · **The sanctuary's host ministers and does not trade**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_economy_sync/test_altoria_sanctum.py:217 `test_the_priest_answers_without_trading_and_the_deacon_keeps_the_counter`

### `sample-city-altoria::altoria-service-content-synchronizes-idempotently-without-resetting-live-state`
- Current: `openspec/specs/sample-city-altoria/spec.md` · **Altoria service content synchronizes idempotently without resetting live state**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/maps/tests/test_service_interiors.py:108 `test_repeated_sync_reuses_tags_reapplies_desc_and_duplicates_no_doorway`; world/rules/tests/test_guild_economy_sync/test_altoria_adornments_remedies.py:79 `test_specialist_interiors_are_permanent_reachable_and_hosted`; world/rules/tests/test_guild_economy_sync/test_altoria_adornments_remedies.py:101 `test_specialist_shops_are_open_and_tradeable_from_the_counter`; world/rules/tests/test_guild_economy_sync/test_service_content_sync.py:53 `test_fresh_sync_creates_one_guild_and_one_merchant_host`

## 3 Starter

### `title-system::compose-title-is-the-single-pure-composition-of-the-full-title`
- Current: `openspec/specs/title-system/spec.md` · **compose_title is the single pure composition of the full title**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_titles/test_title_state_collection.py:127 `test_compose_matrix_joins_non_empty_parts_fixed_first`; world/rules/tests/test_titles/test_title_state_collection.py:139 `test_compose_reads_only_the_equipped_slots`

### `title-system::the-fixed-title-lore-registry-validates-and-syncs-idempotently`
- Current: `openspec/specs/title-system/spec.md` · **The fixed-title lore registry validates and syncs idempotently**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/lore/tests/test_sync.py:29 `test_sync_all_is_idempotent_and_complete`; world/lore/tests/test_titles_registry.py:224 `test_shipped_rows_validate_against_the_live_faces`; world/lore/tests/test_titles_registry.py:230 `test_registry_publication_is_immutable`

### `title-system::guild-registration-and-rank-promotion-grant-paired-titles-atomically`
- Current: `openspec/specs/title-system/spec.md` · **Guild registration and rank promotion grant paired titles atomically**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_titles/test_title_guild_pairing.py:124 `test_first_quest_epithet_grant_banks_and_auto_equips_the_epithet_slot`; world/rules/tests/test_titles/test_title_guild_pairing.py:142 `test_rank_titles_pair_one_to_one_with_the_guild_ranks`; world/rules/tests/test_titles/test_title_guild_pairing.py:160 `test_registration_banks_the_rank_title_only`; world/rules/tests/test_titles/test_title_guild_pairing.py:171 `test_registration_rollback_leaves_no_titles_and_cannot_double_grant`; world/rules/tests/test_titles/test_title_guild_pairing.py:226 `test_promotion_banks_the_rank_title_inside_the_transaction`; world/rules/tests/test_titles/test_title_guild_pairing.py:249 `test_promotion_rollback_revokes_the_grant_and_the_notice`

### `guild-registration::guild-registration-grants-the-paired-starter-titles-atomically`
- Current: `openspec/specs/guild-registration/spec.md` · **Guild registration grants the paired starter titles atomically**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_titles/test_title_guild_pairing.py:160 `test_registration_banks_the_rank_title_only`; world/rules/tests/test_titles/test_title_guild_pairing.py:171 `test_registration_rollback_leaves_no_titles_and_cannot_double_grant`

### `quest-reward-settlement::the-first-ever-reward-claim-grants-the-starter-epithet-atomically`
- Current: `openspec/specs/quest-reward-settlement/spec.md` · **The first-ever reward claim grants the starter epithet atomically**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_rewards.py:662 `test_first_ever_claim_grants_the_starter_epithet`; world/rules/tests/test_guild_rewards.py:683 `test_later_claims_never_re_grant`; world/rules/tests/test_guild_rewards.py:696 `test_rolled_back_first_claim_revokes_the_epithet`; world/rules/tests/test_guild_rewards.py:731 `test_the_grant_is_definition_independent`; commands/tests/test_talk_turnin_commands.py:153 `test_talk_turnin_later_claims_stay_title_silent`; web/webclient/actions/tests/test_service_actions.py:440 `test_turnin_echoes_the_first_claim_epithet_then_stays_silent`

## 4 Shops

### `sample-city-altoria::the-sample-city-s-xyzgrid-remains-thirteen-exterior-nodes-while-permanent-service-interiors-are-attached`
- Current: `openspec/specs/sample-city-altoria/spec.md` · **The sample city's xyzgrid remains thirteen exterior nodes while permanent service interiors are attached**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/maps/tests/test_service_interiors.py:92 `test_grid_topology_is_unchanged`; world/maps/tests/test_service_interiors.py:171 `test_one_exterior_carrying_two_places_yields_two_doorways`; world/rules/tests/test_guild_config/test_commerce_rulebook_slices.py:298 `test_the_moved_offers_travel_field_for_field`; world/rules/tests/test_guild_economy_sync/test_altoria_adornments_remedies.py:79 `test_specialist_interiors_are_permanent_reachable_and_hosted`; world/rules/tests/test_guild_economy_sync/test_altoria_adornments_remedies.py:101 `test_specialist_shops_are_open_and_tradeable_from_the_counter`; world/lore/tests/test_assortments.py:173 `test_capital_shops_redistribute_the_pre_split_set_without_overlap`; world/lore/tests/test_assortments.py:206 `test_adornments_bundle_is_exactly_the_capital_accessory_slot_goods`

### `commerce-assortments::an-assortment-may-not-contain-a-keepsake-band-item`
- Current: `openspec/specs/commerce-assortments/spec.md` · **An assortment may not contain a keepsake-band item**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_guild_config/test_assortment_shop_rules.py:174 `test_keepsake_band_item_is_rejected_at_any_price`

### `commerce-assortments::a-shop-s-offered-goods-are-derived-from-the-assortments-it-references`
- Current: `openspec/specs/commerce-assortments/spec.md` · **A shop's offered goods are derived from the assortments it references**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_shop_economy.py:774 `test_shop_referencing_unknown_assortment_is_rejected`; world/rules/tests/test_shop_economy.py:802 `test_one_shop_overlapping_its_own_assortments_is_rejected`; world/rules/tests/test_shop_economy.py:841 `test_two_shops_sharing_a_key_resolve_it_at_their_own_prices`; world/rules/tests/test_guild_config/test_assortment_shop_rules.py:341 `test_overlapping_assortments_within_one_shop_are_rejected`

### `shop-economy::item-and-shop-identities-are-immutable-while-numeric-trade-rules-are-yaml-and-lore-constrained`
- Current: `openspec/specs/shop-economy/spec.md` · **Item and shop identities are immutable while numeric trade rules are YAML and lore-constrained**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_shop_economy.py:185 `test_unknown_or_unsellable_item_rejected`; world/rules/tests/test_guild_config/test_item_offer_definitions.py:38 `test_initial_items_have_lore_price_identity_without_numbers`

### `lore-item-catalog::a-non-sellable-item-never-reaches-a-merchant-transaction`
- Current: `openspec/specs/lore-item-catalog/spec.md` · **A non-sellable item never reaches a merchant transaction**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_shop_economy.py:203 `test_non_sellable_item_refuses_trade_and_outranks_shop_listing`

## 4 Equipment

### `equipment-effects::the-new-equipment-roster-is-registered-and-tradeable`
- Current: `openspec/specs/equipment-effects/spec.md` · **The new equipment roster is registered and tradeable**
- Disposition: **REMOVED**. Use Equipment membership and stocking are authored data.
- Current annotations: world/rules/tests/test_equipment_effect_rulebook.py:654 `test_new_items_are_registered_offered_and_price_resolvable`; world/rules/tests/test_equipment_effect_rulebook.py:676 `test_every_equipment_price_table_key_resolves`

### `equipment-effects::church-of-light-equipment-obeys-its-canon-doctrine`
- Current: `openspec/specs/equipment-effects/spec.md` · **Church-of-Light equipment obeys its canon doctrine**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/rules/tests/test_equipment_effect_rulebook.py:760 `test_named_church_set_satisfies_doctrine`; world/rules/tests/test_equipment_effect_rulebook.py:768 `test_sanctuary_devices_satisfy_doctrine_without_healing`; world/rules/tests/test_equipment_effect_rulebook.py:779 `test_vestment_cannot_borrow_sanctuary_device_healing_exemption`; world/rules/tests/test_equipment_effect_rulebook.py:802 `test_imperial_and_elven_items_are_excluded_from_church_subsets`; world/rules/tests/test_equipment_effect_rulebook.py:837 `test_negative_pleasure_gain_violates_doctrine`; world/rules/tests/test_equipment_effect_rulebook.py:850 `test_negative_bias_violates_doctrine`; world/rules/tests/test_equipment_effect_rulebook.py:858 `test_negative_heal_gain_violates_doctrine`; world/rules/tests/test_equipment_effect_rulebook.py:871 `test_church_item_without_heal_or_immunity_violates_doctrine`

### `equipment-effects::registration-and-tradeability-are-independent`
- Current: `openspec/specs/equipment-effects/spec.md` · **Registration and tradeability are independent**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/skills/tests/test_equipment.py:211 `test_unstocked_equipment_item_equips_and_applies_adjustments`; world/rules/tests/test_equipment_effect_rulebook.py:580 `test_unstocked_equipment_item_loads_clean`

### `lore-registries::human-starting-kits-express-lineage-character-not-an-affluence-ladder`
- Current: `openspec/specs/lore-registries/spec.md` · **Human starting kits express lineage character, not an affluence ladder**
- Disposition: **MODIFIED**. Same heading and ID; generalize selected body/scenarios only.
- Current annotations: world/lore/tests/test_starting_kits.py:227 `test_human_kits_match_the_lineage_table`

## Explicitly retained selected-area requirements

These remain current contracts, not roster approval tables. Their tests may lose roster snapshots without changing IDs.

- `monster-species-registry`: frozen keyed registries; variant ownership/default-ordinary membership; public projection; habitat is not spawn authority; every profile/grade inside its declared band.
- `monster-individual-construction`: the existing shared entry point, identity validation, active/passive order, behavior binding, fallback, atomicity and committed reload.
- `npc-profile-registry`: immutable keyed profiles, registry assembly, live-source inventory equality, startup fail-closed/orphan/source diagnostics, age validation. Six replaced slices no longer limit completeness.
- `place-driven-service-sync`, `settlement-place-registry`, `npc-persona-card`, `npc-canonical-age`: existing source/assembly and identity-shape contracts. Location keys/order, coordinates, doorways and settlement culture tests retain their own assertions.
- `lore-item-catalog`: registration, complete metadata, retirement reference closure, unstocked equipment and price-band integrity. Non-sellable precedence is explicitly strengthened in its delta.
- `commerce-assortments`: reusable frozen bundle identity, reference validation, per-shop numeric accounting and balance-file organization.
- `equipment-effects`: effect bijection/closed identity, slot validation, budgets, gauge prohibition, purity, immunity and prose rendering. Named equipment in a small synthetic mechanism fixture is not an approved roster; migrate accidental live dependencies when touching these tests.
- `military-equipment`: **both current requirements stay unchanged**, including the six E-S pairs `military_e_sword`/`military_e_armor`, `military_d_sword`/`military_d_armor`, `military_c_sword`/`military_c_armor`, `military_b_sword`/`military_b_armor`, `military_a_sword`/`military_a_armor`, `military_s_sword`/`military_s_armor`. `guild-exam-restrictions` and `guild-rank-exams` stay unchanged. This named exception exists because examiner kits and normal rank-matched examiner gear depend on it.
- `title-system`: clergy ladder and names, guild-rank titles including 「F級冒險者」, six category tabs and all non-starter predicate catalogs remain unchanged.
- Every other capability is unchanged, including places/settlements, divine mystery/elemental mastery names, sexual acts and balance. `human-guild-hosts` persistent-person requirements change personnel membership, not examiner-facing rank/military content.

## Aggregate

61 current requirements: 32 MODIFIED, 29 REMOVED; 25 existing capabilities; 15 general ADDED requirements.

Acceptance includes zero stale removed-ID annotations, meaningful direct coverage of every new/retained affected requirement, and unchanged coverage for deliberately retained contracts. No allowlist or fabricated evidence is permitted.
