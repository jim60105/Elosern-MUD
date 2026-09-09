"""Pure and Evennia-backed tests for deterministic player activation."""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
import inspect
from inspect import signature
from unittest.mock import patch
import unittest

from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.lore.player_presets import PLAYER_PRESET_REGISTRY
from world.lore.sex import DEFAULT_SEX
from world.lore.races import SUBRACE_REGISTRY
from world.lore.starting_kits import SUBRACE_STARTING_KIT_REGISTRY
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    MAX_PERSONA_FIELD_LENGTH,
    PERSONA_IMPORT_CARD_KEYS,
    CharacterCreationError,
    CharacterCreationRequest,
    activate_player_character,
    preflight_character_creation,
    resolve_preset_values,
    resolve_starting_profile,
)


def balanced_allocations(race: str, subrace: str | None = None) -> dict[str, int]:
    profile = resolve_starting_profile(race, subrace)
    remaining = profile.budget
    result = {key: 0 for key in ALLOCATABLE_AXES}
    for key, (lower, upper) in profile.bounds:
        value = min(upper - lower, remaining)
        result[key] = value
        remaining -= value
    if remaining:
        raise AssertionError("profile budget exceeds total spans")
    return result


class StartingProfileTests(unittest.TestCase):
    @covers_requirement("player-stat-allocation::custom-starting-stats-require-one-exact-finite-allocation-budget")
    def test_exact_budget_and_foxkin_override(self):
        human = resolve_starting_profile("human")
        self.assertEqual(human.budget, 224)
        foxkin = resolve_starting_profile("beastfolk", "foxkin")
        self.assertEqual(foxkin.bounds_dict()["mp"], (50, 70))

    def test_catkin_modifiers_are_recorded_for_post_allocation_use(self):
        profile = resolve_starting_profile("beastfolk", "catkin")
        self.assertEqual(profile.static_modifiers.atk_phys, -0.10)
        self.assertEqual(profile.static_modifiers.agility, 0.40)
        self.assertEqual(profile.static_modifiers.defense, -0.30)


class CharacterActivationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.account = create_account("creator", "creator@example.test", "testpassword", typeclass=Account)
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": "human",
            "subrace": "human_commoner",
            "allocations": balanced_allocations("human", "human_commoner"),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    @covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")
    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_activation_persists_identity_traits_and_empty_mechanical_state(self):
        old_id, old_location = self.character.id, self.character.location
        result = activate_player_character(
            self.account, self.character, self.request()
        )
        self.assertEqual(result.magic_power, 5)
        self.assertEqual(self.character.key, "新角色")
        self.assertEqual((self.character.age, self.character.apparent_age), (20, 20))
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(self.character.traits.magic_power.value, 5)
        self.assertEqual(self.character.traits.guild_merit.value, 0)
        self.assertEqual(self.character.db.skills, {"active": [], "passive": []})
        self.assertEqual(
            self.character.db.inventory,
            SUBRACE_STARTING_KIT_REGISTRY["human_commoner"].inventory_list(),
        )
        self.assertEqual(self.character.wallet, 0)
        self.assertEqual(self.character.id, old_id)
        self.assertEqual(self.character.location, old_location)
        self.assertIn(self.character, self.account.characters)

    @covers_requirement("player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands")
    def test_catkin_static_modifiers_apply_once_after_allocation(self):
        allocations = balanced_allocations("beastfolk", "catkin")
        request = self.request(
            race="beastfolk", subrace="catkin", allocations=allocations
        )
        checked = preflight_character_creation(self.account, self.character, request)
        profile = resolve_starting_profile("beastfolk", "catkin")
        bounds = profile.bounds_dict()
        for key in ("atk_phys", "agility", "defense"):
            raw = bounds[key][0] + allocations[key]
            expected = round(raw * (1 + getattr(profile.static_modifiers, key)))
            self.assertEqual(checked.values[key], expected)

    def test_under_and_over_budget_rejections_are_non_mutating(self):
        valid = balanced_allocations("human")
        for delta in (-1, 1):
            allocations = dict(valid)
            key = next(key for key in ALLOCATABLE_AXES if 0 <= allocations[key] + delta <= resolve_starting_profile("human").bounds_dict()[key][1] - resolve_starting_profile("human").bounds_dict()[key][0])
            allocations[key] += delta
            with self.subTest(delta=delta), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character,
                    self.request(allocations=allocations),
                )
            self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    def test_age_name_and_subrace_rejections_are_non_mutating(self):
        requests = (
            self.request(age=-1),
            self.request(apparent_age=10001),
            self.request(display_name="|rbad|n"),
            self.request(race="human", subrace="foxkin"),
        )
        for request in requests:
            with self.subTest(request=request), self.assertRaises(CharacterCreationError):
                activate_player_character(self.account, self.character, request)
            self.assertTrue(self.character.creation_pending)
            self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")
    def test_custom_creation_without_a_subrace_is_rejected(self):
        for missing in (None, "", "  ", "none"):
            with self.subTest(missing=missing):
                request = self.request(subrace=missing)
                with self.assertRaisesRegex(
                    CharacterCreationError, "requires a registered subrace"
                ):
                    activate_player_character(self.account, self.character, request)
                self.assertTrue(self.character.creation_pending)
                self.assertEqual(self.character.traits.all(), [])
                self.assertIsNone(self.character.age)

    def test_display_name_rejects_separators_and_the_shared_length_bound(self):
        for name in ("角色/名", "角色:名", "角色}名", "x" * 65):
            with self.subTest(name=name[:6]), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character,
                    self.request(display_name=name),
                )
            self.assertTrue(self.character.creation_pending)
            self.assertEqual(self.character.traits.all(), [])

    def test_64_character_display_name_is_accepted(self):
        name = "新" * 64
        result = activate_player_character(
            self.account, self.character,
            self.request(display_name=name),
        )
        self.assertEqual(result.display_name, name)
        self.assertEqual(self.character.key, name)

    @covers_requirement(
        "player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands",
        "player-stat-allocation::custom-starting-stats-require-one-exact-finite-allocation-budget",
    )
    def test_preset_activation_fixes_magic_power_deterministically(self):
        # The retired race-average sampler is replaced by the preset's own
        # allocation: sylwen_stillwater allocates 400 over the elf floor (100).
        result = activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="sylwen_stillwater"),
        )
        self.assertEqual(result.magic_power, 500)
        self.assertEqual(self.character.race, "elf")

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_preset_activation_grants_the_declared_skill_kit(self):
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        for preset_key in ("yuna_darknight", "elysa_snow", "sylwen_stillwater"):
            with self.subTest(preset_key=preset_key):
                character = create_object(PlayerCharacter, key=f"shell-{preset_key}")
                self.account.at_post_create_character(character)
                # Companion presets build their twin at the shell's location
                # (preset-companion-activation); production shells live in a
                # room at activation time, so tests place theirs too.
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                self.assertEqual(
                    character.db.skills,
                    PLAYER_PRESET_REGISTRY[preset_key].skill_lists(),
                )
                # None of these kits touches a lineage edge, so the closed
                # state is the declared state and the seed stays empty.
                self.assertEqual(dict(character.db.skill_proficiency or {}), {})
                self.assertFalse(character.creation_pending)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_preset_activation_closes_the_shipped_deep_kit(self):
        # violet_altoria is the one shipped preset touching the fire-tree
        # edges: its declared fire_ball needs fire_arrow >= 3. Activation
        # closes the chain (closure-added keys AFTER the declared ones) and
        # seeds the edge to exactly its required value, and clears the
        # preset-mode creation draft in the same transaction.
        character = create_object(PlayerCharacter, key="shell-violet-lineage")
        self.account.at_post_create_character(character)
        # violet_altoria now binds its companions during activation, which
        # spawns at the shell's location (preset-companion-activation).
        character.location = self.room1
        character.db.creation_draft = {
            "mode": "preset", "stage": "preset_selected",
            "preset_key": "violet_altoria",
        }
        activate_player_character(
            self.account, character,
            CharacterCreationRequest(mode="preset", preset_key="violet_altoria"),
        )
        self.assertEqual(
            character.db.skills,
            {
                "active": ["fire_ball", "wind_blade", "fire_arrow"],
                "passive": [
                    "magic_circle_comprehension", "precise_mana_control", "flight",
                ],
            },
        )
        self.assertEqual(character.db.skill_proficiency, {"fire_arrow": 150.0})
        self.assertFalse(character.attributes.has("creation_draft"))
        self.assertFalse(character.creation_pending)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_every_shipped_preset_declared_active_skill_is_usable_after_activation(self):
        # Scenario coverage for every shipped kit: after closure + seed,
        # can_use_skill passes for every declared active key.
        from world.rules.progression import can_use_skill
        from world.skills.registry import SKILL_REGISTRY

        for preset_key, preset in PLAYER_PRESET_REGISTRY.items():
            with self.subTest(preset_key=preset_key):
                character = create_object(
                    PlayerCharacter, key=f"gate-shell-{preset_key}"
                )
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                for skill_key in preset.active_skills:
                    with self.subTest(skill=skill_key):
                        self.assertTrue(
                            can_use_skill(character, SKILL_REGISTRY[skill_key])
                        )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_custom_activation_writes_empty_skills_and_proficiency(self):
        # Custom mode grants no skills, so the closure and seed are no-ops.
        activate_player_character(self.account, self.character, self.request())
        self.assertEqual(self.character.db.skills, {"active": [], "passive": []})
        self.assertEqual(dict(self.character.db.skill_proficiency or {}), {})

    def _synthetic_preset(self, key, **overrides):
        from world.lore.player_presets import PlayerPreset

        values = dict(
            key=key, display_name=f"合成{key}", age=20, apparent_age=20,
            race="human", subrace="human_commoner",
            allocations=tuple(balanced_allocations("human", "human_commoner").items()),
            emphasis="測試", sex="female",
        )
        values.update(overrides)
        return PlayerPreset(**values)

    def _activate_synthetic_preset(self, preset, shell_key):
        """Activate a registry-patched synthetic preset on a fresh shell."""
        from unittest.mock import patch
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        with patch.dict(PLAYER_PRESET_REGISTRY, {preset.key: preset}):
            character = create_object(PlayerCharacter, key=shell_key)
            self.account.at_post_create_character(character)
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=preset.key),
            )
        return character

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_synthetic_deep_preset_kit_arrives_gate_usable(self):
        # Scenario "A deep preset kit arrives gate-usable": firestorm's edge
        # (scorching_wave >= 3) is satisfied by nothing declared, so the
        # closure adds the whole chain and the seed lands on EXACTLY three
        # levels for every unsatisfied edge of the chain.
        from world.rules.progression import (
            SKILL_PROFICIENCY_XP_PER_LEVEL,
            can_use_skill,
        )
        from world.skills.registry import SKILL_REGISTRY

        preset = self._synthetic_preset(
            "test_lineage_deep", active_skills=("firestorm",)
        )
        character = self._activate_synthetic_preset(preset, "shell-lineage-deep")
        self.assertEqual(
            character.db.skills,
            {
                "active": ["firestorm", "fire_arrow", "fire_ball", "scorching_wave"],
                "passive": [],
            },
        )
        self.assertEqual(
            character.db.skill_proficiency,
            {
                "fire_arrow": 3 * SKILL_PROFICIENCY_XP_PER_LEVEL,
                "fire_ball": 3 * SKILL_PROFICIENCY_XP_PER_LEVEL,
                "scorching_wave": 3 * SKILL_PROFICIENCY_XP_PER_LEVEL,
            },
        )
        self.assertTrue(can_use_skill(character, SKILL_REGISTRY["firestorm"]))

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_declared_proficiency_below_the_seed_survives_activation(self):
        # Scenario "A declared proficiency beats the auto-seed": 120 XP is
        # level 2, below the scorching_wave >= 3 edge; the seed must not
        # overwrite the declared value -- while the seed still runs for every
        # OTHER unsatisfied edge of the closed chain.
        preset = self._synthetic_preset(
            "test_lineage_declared",
            active_skills=("firestorm",),
            skill_proficiency=(("scorching_wave", 120.0),),
        )
        character = self._activate_synthetic_preset(
            preset, "shell-lineage-declared"
        )
        self.assertEqual(
            character.db.skill_proficiency,
            {
                "scorching_wave": 120.0,  # declared wins, below the edge
                "fire_arrow": 150.0,  # the seed still runs for the rest
                "fire_ball": 150.0,
            },
        )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_declared_keys_keep_order_and_closure_added_keys_follow(self):
        # Declared (fire_ball, firestorm) keeps its order; the closure-added
        # keys (sorted registry order) follow the declared ones.
        preset = self._synthetic_preset(
            "test_lineage_order",
            active_skills=("fire_ball", "firestorm"),
            passive_skills=("defense_instinct",),
        )
        character = self._activate_synthetic_preset(preset, "shell-lineage-order")
        self.assertEqual(
            character.db.skills,
            {
                "active": [
                    "fire_ball", "firestorm",  # declared order
                    "fire_arrow", "scorching_wave",  # closure-added, sorted
                ],
                "passive": ["defense_instinct"],
            },
        )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_preset_activation_grants_the_declared_starting_inventory(self):
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        for preset_key in ("yuka_darknight", "violet_altoria", "elysa_snow"):
            with self.subTest(preset_key=preset_key):
                character = create_object(PlayerCharacter, key=f"kit-shell-{preset_key}")
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                expected = PLAYER_PRESET_REGISTRY[preset_key].inventory_list()
                self.assertEqual(character.db.inventory, expected)
                self.assertGreater(len(expected), 0)

    @covers_requirement("player-character-creation::custom-activation-grants-the-chosen-subrace-s-basic-starting-kit")
    def test_custom_activation_grants_each_subrace_starting_kit(self):
        for subrace_key, subrace in SUBRACE_REGISTRY.items():
            with self.subTest(subrace=subrace_key):
                character = create_object(
                    PlayerCharacter, key=f"custom-shell-{subrace_key}"
                )
                self.account.at_post_create_character(character)
                activate_player_character(
                    self.account, character,
                    self.request(
                        race=subrace.race_key,
                        subrace=subrace_key,
                        allocations=balanced_allocations(subrace.race_key, subrace_key),
                    ),
                )
                expected = SUBRACE_STARTING_KIT_REGISTRY[
                    subrace_key
                ].inventory_list()
                self.assertEqual(character.db.inventory, expected)
                self.assertGreater(len(expected), 0)
                self.assertFalse(character.creation_pending)

    # --- preset-starting-equipment ---------------------------------------

    _EQUIP_ITEMS = (
        ("plain_sword", 1), ("leather_armor", 1), ("guild_recruit_badge", 1),
        ("apothecary_beads", 1), ("wolf_fang_necklace", 1), ("healing_potion", 2),
    )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_preset_activation_wears_the_declared_starting_equipment(self):
        # Scenario "Declared starting equipment is worn at activation" plus
        # "Undeclared items stay in the pack": every declared key lands in
        # its registry slot through the sole writer, the carried-but-
        # undeclared accessory stays in the pack only, and equipped keys
        # remain in canonical inventory.
        preset = self._synthetic_preset(
            "test_equip_worn",
            starting_items=self._EQUIP_ITEMS,
            starting_equipment=(
                "plain_sword", "leather_armor", "guild_recruit_badge",
                "apothecary_beads",
            ),
        )
        character = self._activate_synthetic_preset(preset, "shell-equip-worn")
        self.assertEqual(
            dict(character.db.equipment),
            {
                "weapon_main": "plain_sword",
                "weapon_off": None,
                "armor": "leather_armor",
                "accessories": ["guild_recruit_badge", "apothecary_beads"],
            },
        )
        # Scenario 3.3: the beads' attached buff instance arrives with it.
        self.assertIn("item_regen_light:apothecary_beads", character.db.buffs)
        self.assertEqual(
            character.db.buffs["item_regen_light:apothecary_beads"][
                "definition_key"
            ],
            "item_regen_light",
        )
        # The undeclared carried accessory occupies no slot but stays held,
        # and equipped keys stay in canonical inventory.
        stored = set(character.db.equipment["accessories"])
        stored.update(
            v for v in (
                character.db.equipment["weapon_main"],
                character.db.equipment["weapon_off"],
                character.db.equipment["armor"],
            ) if v
        )
        self.assertNotIn("wolf_fang_necklace", stored)
        for key in ("wolf_fang_necklace", "plain_sword", "leather_armor",
                    "guild_recruit_badge", "apothecary_beads"):
            self.assertIn(key, character.db.inventory)
        self.assertFalse(character.creation_pending)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_worn_equipment_ceilings_are_computed_from_the_final_traits(self):
        # Scenario (risk pin, design R2): knight_platemail caps hp at +15;
        # the ceiling recomputation runs after _apply_trait_config, so the
        # stored mod is exactly the worn set's cap against the final base.
        preset = self._synthetic_preset(
            "test_equip_gauge",
            starting_items=(("knight_platemail", 1), ("apothecary_beads", 1)),
            starting_equipment=("knight_platemail", "apothecary_beads"),
        )
        character = self._activate_synthetic_preset(preset, "shell-equip-gauge")
        # The sole writer recomputes the hp ceiling's mod from scratch as
        # exactly the worn set's cap; GaugeTrait.max is derived as
        # (base + mod) * mult, so pinning mod pins the ceiling.
        self.assertEqual(character.traits.hp.mod, 15)
        self.assertIn("item_regen_light:apothecary_beads", character.db.buffs)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_rejected_equipment_toggle_rolls_activation_back(self):
        # Scenario "A rejected toggle rolls activation back" (design D3):
        # activation raises naming the key and the stable reason, and the
        # shell stays exactly as it was.
        from world.rules.equipment import EquipmentToggleReason, EquipmentToggleResult
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        preset = self._synthetic_preset(
            "test_equip_reject",
            starting_items=(("plain_sword", 1),),
            starting_equipment=("plain_sword",),
        )
        character = create_object(PlayerCharacter, key="shell-equip-reject")
        self.account.at_post_create_character(character)
        old_key = character.key
        rejected = EquipmentToggleResult(
            outcome="rejected", reason=EquipmentToggleReason.ITEM_NOT_HELD
        )
        with patch.dict(PLAYER_PRESET_REGISTRY, {preset.key: preset}), patch(
            "world.rules.character_creation.toggle_equipment",
            return_value=rejected,
        ):
            with self.assertRaisesRegex(
                CharacterCreationError,
                r"plain_sword.*item_not_held",
            ):
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(
                        mode="preset", preset_key=preset.key
                    ),
                )
        self.assertEqual(character.key, old_key)
        self.assertTrue(character.creation_pending)
        self.assertFalse(character.attributes.has("equipment"))
        self.assertFalse(character.attributes.has("buffs"))

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_failure_after_equipment_toggles_leaves_no_residue(self):
        # Scenario "A failed activation leaves no equipment or buff residue"
        # (design D5): the failure lands on the stage right after the toggle
        # loop, so equipment, buffs, and the gauge ceilings must ALL read
        # back at their pre-activation state in the in-process cache.
        preset = self._synthetic_preset(
            "test_equip_residue",
            starting_items=(("knight_platemail", 1), ("apothecary_beads", 1)),
            starting_equipment=("knight_platemail", "apothecary_beads"),
        )
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        character = create_object(PlayerCharacter, key="shell-equip-residue")
        self.account.at_post_create_character(character)
        old_key = character.key
        before_traits = deepcopy(dict(character.traits.trait_data))

        def fail(stage):
            if stage == "starting_equipment":
                raise RuntimeError("injected after toggles")

        with patch.dict(PLAYER_PRESET_REGISTRY, {preset.key: preset}):
            with self.assertRaisesRegex(RuntimeError, "injected after toggles"):
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(
                        mode="preset", preset_key=preset.key
                    ),
                    write_observer=fail,
                )
        self.assertEqual(character.key, old_key)
        self.assertTrue(character.creation_pending)
        # Assert through the attribute layer, never character.buffs: reading
        # the BuffHandler auto-creates an empty cache and would mask residue.
        self.assertFalse(character.attributes.has("equipment"))
        self.assertFalse(character.attributes.has("buffs"))
        self.assertEqual(dict(character.traits.trait_data), before_traits)
        self.assertEqual(character.traits.all(), [])

    @covers_requirement("player-character-creation::custom-activation-grants-the-chosen-subrace-s-basic-starting-kit")
    def test_custom_activation_leaves_every_equipment_slot_empty(self):
        activate_player_character(self.account, self.character, self.request())
        self.assertEqual(
            dict(self.character.db.equipment),
            {
                "weapon_main": None,
                "weapon_off": None,
                "armor": None,
                "accessories": [],
            },
        )

    def test_fault_after_trait_write_restores_all_state_and_handler_cache(self):
        self.character.db.guild_rank = "preserve-me"
        before_traits = deepcopy(dict(self.character.traits.trait_data))
        old_key = self.character.key

        def fail(stage):
            if stage == "traits":
                raise RuntimeError("injected")

        with self.assertRaisesRegex(RuntimeError, "injected"):
            activate_player_character(
                self.account, self.character, self.request(),
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.db.guild_rank, "preserve-me")
        self.assertEqual(dict(self.character.traits.trait_data), before_traits)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_every_observable_write_failure_restores_the_complete_shell(self):
        stages = (
            "identity", "traits", "age", "apparent_age", "race", "subrace",
            "skill_proficiency", "skills", "skill_grants",
            "equipment", "inventory", "wallet", "quest_log", "guild_rank",
            "creation_pending", "portrait_policy",
        )
        for stage in stages:
            with self.subTest(stage=stage):
                character = create_object(PlayerCharacter, key=f"shell-{stage}")
                self.account.at_post_create_character(character)
                character.db.guild_rank = 9
                before = {
                    key: (
                        character.attributes.has(key),
                        deepcopy(character.attributes.get(key)),
                    )
                    for key in (
                        "age", "apparent_age", "race", "subrace",
                        "creation_pending", "skill_proficiency",
                        "skills", "skill_grants", "equipment", "inventory",
                        "wallet", "quest_log", "guild_rank",
                        "portrait_policy",
                    )
                }
                before_traits = deepcopy(dict(character.traits.trait_data))
                old_key, old_location = character.key, character.location

                def fail(current, target=stage):
                    if current == target:
                        raise RuntimeError(target)

                with self.assertRaisesRegex(RuntimeError, stage):
                    activate_player_character(
                        self.account, character, self.request(),
                        write_observer=fail,
                    )
                self.assertEqual(character.key, old_key)
                self.assertEqual(character.location, old_location)
                self.assertIn(character, self.account.characters)
                self.assertEqual(dict(character.traits.trait_data), before_traits)
                for key, (existed, value) in before.items():
                    self.assertEqual(character.attributes.has(key), existed, key)
                    self.assertEqual(character.attributes.get(key), value, key)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_successful_activation_leaves_the_shell_in_place(self):
        """Activation performs no relocation and records no arrival."""
        from world.rules.clock import get_world_clock

        old_location = self.character.location
        activate_player_character(
            self.account, self.character, self.request()
        )
        clock = get_world_clock()
        tick_before = clock.tick
        self.assertFalse(self.character.creation_pending)
        self.assertIsNotNone(self.character.traits.magic_power)
        self.assertIs(self.character.location, old_location)
        self.assertEqual(clock.tick, tick_before)
        self.assertIsNone(self.character.attributes.get("map_knowledge"))

    # -- preset disguise layer + sexual baseline (preset-disguise-and-sexual-baseline)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    @covers_requirement("disguised-stats-boundary::disguised-stats-keys-are-readable-by-exactly-three-consumers-including-implemented-guild-registration")
    def test_preset_activation_persists_declared_disguise_without_touching_true_traits(self):
        # Scenario "A declared disguise layer is persisted": the mapping is
        # written inside the activation transaction, and the boundary holds
        # -- true traits are unchanged while the sanctioned accessor shows
        # the disguise.
        from world.rules.traits import get_display_value

        preset = self._synthetic_preset(
            "disguised_scout", disguised_stats=(("atk_phys", 99999), ("agility", 99998))
        )
        observed = []
        character = create_object(PlayerCharacter, key="creator-shell-disguise")
        self.account.at_post_create_character(character)
        with patch.dict(PLAYER_PRESET_REGISTRY, {preset.key: preset}):
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=preset.key),
                write_observer=observed.append,
            )
        self.assertIn("disguised_stats", observed)
        self.assertEqual(
            character.db.disguised_stats, {"atk_phys": 99999, "agility": 99998}
        )
        self.assertEqual(get_display_value(character, "atk_phys"), 99999)
        self.assertEqual(get_display_value(character, "agility"), 99998)
        self.assertNotEqual(
            character.traits.atk_phys.value, character.db.disguised_stats["atk_phys"]
        )
        self.assertNotEqual(
            character.traits.agility.value, character.db.disguised_stats["agility"]
        )

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_preset_activation_writes_none_for_an_empty_disguise_declaration(self):
        # Scenario "An empty disguise declaration writes None": the fresh
        # shell already reads None, so the write itself is evidenced through
        # the activation observer; the value stays the absent-reading None.
        preset = self._synthetic_preset("plain_scout")
        observed = []
        character = create_object(PlayerCharacter, key="creator-shell-plain")
        self.account.at_post_create_character(character)
        with patch.dict(PLAYER_PRESET_REGISTRY, {preset.key: preset}):
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=preset.key),
                write_observer=observed.append,
            )
        self.assertIn("disguised_stats", observed)
        self.assertIsNone(character.db.disguised_stats)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    @covers_requirement("sexual-state-handler::sexualstate-is-constructed-from-entity-db-sexual-when-a-raw-baseline-is-present")
    def test_preset_activation_seeds_the_handler_from_a_declared_baseline(self):
        # Scenario "A declared sexual baseline seeds the handler": db.sexual
        # equals to_record(), the lazily constructed entity.sexual derives
        # from it, and each omitted optional field floors through the
        # existing construction rule.
        from world.lore.player_presets import PresetSexualBaseline

        baseline = PresetSexualBaseline(
            arousal="微興奮", virgin=False, sensitivity=(("私處", "極高"),)
        )
        preset = self._synthetic_preset("hedonist_scout", sexual_baseline=baseline)
        character = self._activate_synthetic_preset(preset, "creator-shell-baseline")
        self.assertEqual(
            character.db.sexual,
            {"arousal": "微興奮", "virgin": False, "sensitivity": {"私處": "極高"}},
        )
        state = character.sexual
        self.assertFalse(state.virgin)
        self.assertEqual(state.sensitivity["私處"].level, "極高")
        self.assertEqual(state.wetness.level, "乾燥")
        self.assertEqual(state.shame.level, "無")
        self.assertEqual(state.exposure.level, "極低")
        self.assertEqual(state.climax_phase.level, "未達")
        self.assertEqual(state.arousal.level, "微興奮")

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_preset_without_a_baseline_keeps_the_lazy_generic_default(self):
        # Scenario "An undeclared sexual baseline preserves the lazy
        # default": the key stays absent and the generic floor state builds.
        preset = self._synthetic_preset("default_scout")
        character = self._activate_synthetic_preset(preset, "creator-shell-default")
        self.assertFalse(character.attributes.has("sexual"))
        state = character.sexual
        self.assertEqual(state.arousal.level, "平靜")
        self.assertTrue(state.virgin)
        self.assertEqual(state.wetness.level, "乾燥")

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_custom_activation_writes_neither_disguise_nor_baseline(self):
        # Task 3.4: custom mode preserves today's behavior exactly -- the
        # disguise layer stays at its shell-initialized None and the sexual
        # attribute is never written.
        observed = []
        activate_player_character(
            self.account, self.character, self.request(),
            write_observer=observed.append,
        )
        self.assertNotIn("disguised_stats", observed)
        self.assertNotIn("sexual", observed)
        self.assertFalse(self.character.attributes.has("sexual"))
        self.assertIsNone(self.character.db.disguised_stats)

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-disguise-layer-and-sexual-baseline")
    def test_failure_after_both_writes_restores_disguise_and_baseline(self):
        # Scenario "A failed activation leaves no disguise or baseline
        # residue": the observer fails at the ``sexual`` stage, which fires
        # only after both writes landed in the idmapper cache. Restore
        # returns each surface to its PRE-ACTIVATION state: the shell
        # pre-initializes disguised_stats to None (so it reads back None,
        # not absent) and never had a sexual key (so it is removed again);
        # the handler's derived sexual_traits must never have been built.
        from world.lore.player_presets import PresetSexualBaseline

        preset = self._synthetic_preset(
            "rolledback_scout",
            disguised_stats=(("atk_phys", 5),),
            sexual_baseline=PresetSexualBaseline(
                arousal="中等", virgin=False, sensitivity=(("耳朵", "高"),)
            ),
        )
        character = create_object(PlayerCharacter, key="creator-shell-rollback")
        self.account.at_post_create_character(character)
        old_key = character.key

        def fail(stage):
            if stage == "sexual":
                raise RuntimeError(stage)

        with patch.dict(PLAYER_PRESET_REGISTRY, {preset.key: preset}):
            with self.assertRaisesRegex(RuntimeError, "sexual"):
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset.key),
                    write_observer=fail,
                )
        self.assertEqual(character.key, old_key)
        self.assertTrue(character.creation_pending)
        self.assertIsNone(character.attributes.get("disguised_stats"))
        self.assertFalse(character.attributes.has("sexual"))
        self.assertFalse(character.attributes.has("sexual_traits"))


def _portrait_ensure_callbacks(callbacks):
    """The captured on_commit callbacks that schedule the portrait ensure.

    Activation may legitimately schedule other spec'd callbacks (the
    lore-codex panel push rides the origin reveal); the art-asset-lifecycle
    contract counts exactly one portrait-ensure registration.
    """
    return [
        callback
        for callback in callbacks
        if getattr(callback, "__qualname__", "").startswith("schedule_portrait_ensure")
    ]


class PortraitFinalizationTests(EvenniaTest):
    """Shared portrait finalization on every activation path
    (fix-creation-finalization-safety D3 / art-asset-lifecycle)."""

    def setUp(self):
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": "human",
            "subrace": "human_commoner",
            "allocations": balanced_allocations("human", "human_commoner"),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    def _portrait_key(self):
        return f"art:portrait:character:{self.character.pk}"

    def _gallery_jobs(self):
        from world.art.store import ArtAssetRecord

        return [
            record
            for record in ArtAssetRecord.objects.all()
            if str(record.db.gallery_image_id or "")
        ]

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    @covers_requirement("art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle")
    @covers_requirement(
        "art-gallery-autogen::automatic-character-portraits-produce-exactly-one-unbound-default-card"
    )
    def test_activation_sets_the_named_policy_and_schedules_exactly_one_ensure(self):
        from world.art.store import ArtAssetRecord

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            activate_player_character(
                self.account, self.character, self.request(),
            )
        self.assertEqual(
            self.character.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.character.pk)},
        )
        self.assertEqual(len(_portrait_ensure_callbacks(callbacks)), 1)
        # The retrofit: the committed creation owns exactly one gallery job,
        # never a classic fixed-identity record.
        jobs = self._gallery_jobs()
        self.assertEqual(len(jobs), 1)
        self.assertTrue(jobs[0].db_key.startswith(f"{self._portrait_key()}:gen:"))
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key=self._portrait_key()).count(), 0
        )

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    @covers_requirement("art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle")
    def test_web_activation_produces_identical_portrait_state(self):
        from web.webclient.actions.creation_actions import (
            _creation_activate_adapter,
            _creation_custom_adapter,
        )
        from world.art.store import ArtAssetRecord

        web = create_object(PlayerCharacter, key="web-shell")
        self.account.at_post_create_character(web)
        web.db_account = self.account
        _creation_custom_adapter(
            web,
            {
                "display_name": "網頁角色",
                "age": 20,
                "apparent_age": 20,
                "race": "human",
                "subrace": "human_commoner",
                "allocations": balanced_allocations("human", "human_commoner"),
                "background": None,
                "affinity_elements": [],
                "persona": None,
            },
        )
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            _creation_activate_adapter(web, {})
        self.assertFalse(web.creation_pending)
        self.assertEqual(
            web.db.portrait_policy,
            {"mode": "named", "stable_key": str(web.pk)},
        )
        self.assertEqual(len(_portrait_ensure_callbacks(callbacks)), 1)
        # Same retrofit on the web activation path: one gallery job, no
        # classic fixed-identity record.
        self.assertEqual(len(self._gallery_jobs()), 1)
        self.assertEqual(
            ArtAssetRecord.objects.filter(
                db_key=f"art:portrait:character:{web.pk}"
            ).count(),
            0,
        )

    @covers_requirement("art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle")
    def test_failed_activation_leaves_no_policy_and_no_job(self):
        from world.art.store import ArtAssetRecord
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        save_custom_draft(self.account, self.character, self.request())

        def fail(stage):
            if stage == "portrait_policy":
                raise RuntimeError("injected portrait failure")

        with self.assertRaisesRegex(RuntimeError, "injected portrait failure"):
            activate_draft(
                self.account, self.character,
                write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("portrait_policy"))
        self.assertIsNone(self.character.db.portrait_policy)
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key=self._portrait_key()).count(),
            0,
        )
        self.assertEqual(self._gallery_jobs(), [])

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_skipped_activation_establishes_the_policy_and_enqueues_nothing(self):
        from world.art import gallery as gallery_api
        from world.art.presenter import PLACEHOLDER_MISSING, resolve_entity
        from world.art.subjects import ArtSubject, ArtSubjectKind

        with self.captureOnCommitCallbacks(execute=True):
            activate_player_character(
                self.account, self.character, self.request(skip_portrait=True),
            )
        # The named policy exists on the skipped path too — the character
        # stays eligible for a later request.
        self.assertEqual(
            self.character.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.character.pk)},
        )
        self.assertEqual(self._gallery_jobs(), [])
        subject = ArtSubject(ArtSubjectKind.CHARACTER, str(self.character.pk))
        self.assertEqual(gallery_api.cards_for(subject), [])
        # Empty-gallery resolution reaches the chain's terminal fallback seam
        # (world.art.gallery_match.fallback_for): today the seam provides no
        # image, so the honest outcome is the placeholder; the moment the
        # gallery-builtin-fallbacks capability fills the seam this resolves to
        # an asset payload. Both halves are asserted against the same chain.
        payload = resolve_entity(self.character)
        self.assertEqual(payload["kind"], PLACEHOLDER_MISSING)
        with patch(
            "world.art.presenter.fallback_for",
            return_value={"identity": "fallback/character/default.png"},
        ):
            served = resolve_entity(self.character)
        self.assertEqual(served["kind"], "asset")

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_default_activation_still_schedules_one_generation(self):
        with self.captureOnCommitCallbacks(execute=True):
            activate_player_character(
                self.account, self.character, self.request(),
            )
        self.assertEqual(len(self._gallery_jobs()), 1)

    @covers_requirement(
        "art-gallery-autogen::player-creation-may-skip-the-automatic-portrait"
    )
    def test_a_rolled_back_skipped_activation_leaves_nothing(self):
        from world.rules.creation_wizard import activate_draft, save_custom_draft

        save_custom_draft(
            self.account, self.character, self.request(skip_portrait=True)
        )

        def fail(stage):
            if stage == "portrait_policy":
                raise RuntimeError("injected portrait failure")

        with self.assertRaisesRegex(RuntimeError, "injected portrait failure"):
            activate_draft(self.account, self.character, write_observer=fail)
        self.assertFalse(self.character.attributes.has("portrait_policy"))
        self.assertIsNone(self.character.db.portrait_policy)
        self.assertEqual(self._gallery_jobs(), [])


class AffinityCreationTests(EvenniaTest):
    """Custom and preset activation affinity (element-affinity-progression)."""

    def setUp(self):
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": "human",
            "subrace": "human_commoner",
            "allocations": balanced_allocations("human", "human_commoner"),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    @covers_requirement("player-character-creation::custom-creation-collects-a-race-bounded-affinity-element-set")
    def test_human_two_elements_accepted_three_rejected(self):
        result = activate_player_character(
            self.account, self.character,
            self.request(affinity_elements=("fire", "wind")),
        )
        self.assertEqual(result.display_name, "新角色")
        self.assertEqual(self.character.db.affinity_elements, ["fire", "wind"])
        character = create_object(PlayerCharacter, key="three-shell")
        self.account.at_post_create_character(character)
        with self.assertRaisesRegex(CharacterCreationError, "exceeds the human bound"):
            activate_player_character(
                self.account, character,
                self.request(affinity_elements=("fire", "wind", "water")),
            )
        self.assertTrue(character.creation_pending)
        self.assertFalse(character.attributes.has("affinity_elements"))

    @covers_requirement("player-character-creation::custom-creation-collects-a-race-bounded-affinity-element-set")
    def test_beastfolk_one_element_accepted_two_rejected(self):
        allocations = balanced_allocations("beastfolk", "foxkin")
        result = activate_player_character(
            self.account, self.character,
            self.request(
                race="beastfolk", subrace="foxkin", allocations=allocations,
                affinity_elements=("wind",),
            ),
        )
        self.assertEqual(self.character.db.affinity_elements, ["wind"])
        character = create_object(PlayerCharacter, key="beast-two-shell")
        self.account.at_post_create_character(character)
        with self.assertRaisesRegex(CharacterCreationError, "exceeds the beastfolk bound"):
            activate_player_character(
                self.account, character,
                self.request(
                    race="beastfolk", subrace="foxkin", allocations=allocations,
                    affinity_elements=("wind", "fire"),
                ),
            )
        self.assertTrue(character.creation_pending)

    @covers_requirement("player-character-creation::custom-creation-collects-a-race-bounded-affinity-element-set")
    def test_elf_supplied_set_rejected_and_subrace_seeds_at_activation(self):
        elf_allocations = balanced_allocations("elf", "fionnen")
        for supplied in (("light",), ("fire", "wind")):
            with self.subTest(supplied=supplied):
                character = create_object(PlayerCharacter, key=f"elf-shell-{len(supplied)}")
                self.account.at_post_create_character(character)
                with self.assertRaisesRegex(CharacterCreationError, "seeded from the subrace"):
                    activate_player_character(
                        self.account, character,
                        self.request(
                            race="elf", subrace="fionnen", allocations=elf_allocations,
                            affinity_elements=supplied,
                        ),
                    )
                self.assertTrue(character.creation_pending)
        activated = create_object(PlayerCharacter, key="elf-activate")
        self.account.at_post_create_character(activated)
        activate_player_character(
            self.account, activated,
            self.request(
                race="elf", subrace="fionnen", allocations=elf_allocations,
                affinity_elements=(),
            ),
        )
        self.assertEqual(activated.db.affinity_elements, ["light"])

    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_eolas_seeds_all_eight_and_each_is_favored(self):
        from world.lore.elements import ELEMENT_REGISTRY
        from world.rules.progression import element_affinity_multiplier

        eolas_allocations = balanced_allocations("elf", "eolas")
        character = create_object(PlayerCharacter, key="eolas-activate")
        self.account.at_post_create_character(character)
        activate_player_character(
            self.account, character,
            self.request(
                race="elf", subrace="eolas", allocations=eolas_allocations,
                affinity_elements=(),
            ),
        )
        self.assertEqual(
            set(character.db.affinity_elements), set(ELEMENT_REGISTRY)
        )
        for element in ELEMENT_REGISTRY:
            self.assertEqual(element_affinity_multiplier(character, element), 1.1)

    @covers_requirement("player-character-creation::custom-creation-collects-a-race-bounded-affinity-element-set")
    def test_unknown_and_duplicate_affinity_elements_are_rejected(self):
        for supplied, message in (
            (("luck",), "unknown element"),
            (("fire", "fire"), "duplicate element"),
        ):
            with self.subTest(supplied=supplied, message=message):
                character = create_object(PlayerCharacter, key=f"bad-affinity-{message.split()[0]}")
                self.account.at_post_create_character(character)
                with self.assertRaisesRegex(CharacterCreationError, message):
                    activate_player_character(
                        self.account, character,
                        self.request(affinity_elements=supplied),
                    )
                self.assertTrue(character.creation_pending)
                self.assertFalse(character.attributes.has("affinity_elements"))

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_human_preset_persists_declared_affinity(self):
        # violet_altoria binds companions at activation; the shell needs a room.
        self.character.location = self.room1
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="violet_altoria"),
        )
        self.assertEqual(self.character.db.affinity_elements, ["fire", "wind"])

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_neutral_human_preset_stays_neutral(self):
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="elysa_snow"),
        )
        self.assertEqual(self.character.db.affinity_elements, [])

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_elf_preset_seeds_affinity_from_subrace(self):
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="sylwen_stillwater"),
        )
        self.assertEqual(self.character.db.affinity_elements, ["light"])

    @covers_requirement("player-character-creation::custom-creation-collects-a-race-bounded-affinity-element-set")
    def test_affinity_write_failure_rolls_back_the_whole_activation(self):
        old_key = self.character.key

        def fail(stage):
            if stage == "affinity_elements":
                raise RuntimeError("injected affinity failure")

        with self.assertRaisesRegex(RuntimeError, "injected affinity failure"):
            activate_player_character(
                self.account, self.character,
                self.request(affinity_elements=("fire",)),
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("affinity_elements"))
        self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_invalid_subrace_seed_fails_closed(self):
        from dataclasses import replace

        from world.lore.races import SUBRACE_REGISTRY
        from world.rules import character_creation as cc

        real_fionnen = SUBRACE_REGISTRY["fionnen"]
        elf_allocations = balanced_allocations("elf", "fionnen")
        for bad_seed, message in (
            (("luck",), "unknown element"),
            (("light", "light"), "duplicate element"),
        ):
            with self.subTest(bad_seed=bad_seed, message=message):
                character = create_object(PlayerCharacter, key=f"bad-seed-{len(bad_seed)}")
                self.account.at_post_create_character(character)
                with patch.dict(
                    cc.SUBRACE_REGISTRY,
                    {"fionnen": replace(real_fionnen, affinity_elements=bad_seed)},
                ):
                    with self.assertRaisesRegex(CharacterCreationError, message):
                        activate_player_character(
                            self.account, character,
                            self.request(
                                race="elf", subrace="fionnen", allocations=elf_allocations,
                                affinity_elements=(),
                            ),
                        )
                self.assertTrue(character.creation_pending)
                self.assertFalse(character.attributes.has("affinity_elements"))



PERSONA_BLOCK = {
    "personality": "沉穩",
    "life_story": "來自邊境的小村，靠磨劍維生",
    "habit": "清晨練劍",
}


class PersonaActivationTests(EvenniaTest):
    """Activation-time persona persistence (creation-persona-persistence D3)."""

    def setUp(self):
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": "human",
            "subrace": "human_commoner",
            "allocations": balanced_allocations("human", "human_commoner"),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_concept_persona_persists_in_the_six_key_import_card_shape(self):
        result = activate_player_character(
            self.account, self.character, self.request(),
            persona=PERSONA_BLOCK,
        )
        self.assertEqual(result.display_name, "新角色")
        self.assertEqual(
            self.character.db.persona,
            {
                "identity": {},
                "personality": "沉穩",
                "life_story": "來自邊境的小村，靠磨劍維生",
                "habit": "清晨練劍",
                "appearance": {},
                "social_connection": {},
            },
        )
        self.assertFalse(self.character.creation_pending)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_persona_write_failure_rolls_back_the_whole_activation(self):
        old_key = self.character.key

        def fail(stage):
            if stage == "persona":
                raise RuntimeError("injected persona failure")

        with self.assertRaisesRegex(RuntimeError, "injected persona failure"):
            activate_player_character(
                self.account, self.character, self.request(),
                persona=PERSONA_BLOCK,
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertIsNone(self.character.db.persona)
        self.assertEqual(self.character.traits.all(), [])
        self.assertIsNone(self.character.age)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_draft_without_persona_writes_nothing(self):
        activate_player_character(
            self.account, self.character, self.request()
        )
        self.assertFalse(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("persona"))

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_custom_background_is_persisted_inside_the_persona_record(self):
        activate_player_character(
            self.account, self.character,
            self.request(background="在公會登記的新人冒險者"),
        )
        self.assertFalse(self.character.creation_pending)
        stored = self.character.db.persona
        self.assertEqual(stored["background"], "在公會登記的新人冒險者")
        for key in ("identity", "personality", "life_story", "habit",
                    "appearance", "social_connection"):
            self.assertIn(key, stored)

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_background_merges_with_a_concept_persona_block(self):
        activate_player_character(
            self.account, self.character,
            self.request(background="背景文字"),
            persona=PERSONA_BLOCK,
        )
        stored = self.character.db.persona
        self.assertEqual(stored["background"], "背景文字")
        self.assertEqual(stored["personality"], "沉穩")
        self.assertEqual(stored["life_story"], "來自邊境的小村，靠磨劍維生")

    def test_blank_or_over_bound_background_is_rejected_or_omitted(self):
        for background in ("  ", "", None):
            with self.subTest(background=background):
                activate_player_character(
                    self.account, self.character,
                    self.request(background=background),
                )
                self.assertFalse(self.character.creation_pending)
                if background in ("  ", "", None):
                    self.assertFalse(self.character.attributes.has("persona"))
                self.character.creation_pending = True
                self.character.attributes.reset_cache()
        with self.assertRaises(CharacterCreationError):
            activate_player_character(
                self.account, self.character,
                self.request(background="x" * (MAX_PERSONA_FIELD_LENGTH + 1)),
            )
        self.assertTrue(self.character.creation_pending)

    def test_malformed_persona_is_rejected_without_mutation(self):
        cases = (
            {"personality": "沉穩", "life_story": "故事"},
            {"personality": "沉穩", "life_story": "故事", "habit": "習慣", "extra": "x"},
            {"personality": "", "life_story": "故事", "habit": "習慣"},
            {
                "personality": "長" * 601,
                "life_story": "故事",
                "habit": "習慣",
            },
            {"personality": 5, "life_story": "故事", "habit": "習慣"},
        )
        for persona in cases:
            with self.subTest(persona=persona), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character, self.request(),
                    persona=persona,
                )
            self.assertTrue(self.character.creation_pending)
            self.assertEqual(self.character.traits.all(), [])
            self.assertFalse(self.character.attributes.has("persona"))

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-persona")
    def test_preset_activation_persists_the_registry_persona_record(self):
        # preset-persona-activation: the registry persona finally reaches
        # entity.db.persona inside the same activation transaction.
        preset = PLAYER_PRESET_REGISTRY["yuna_darknight"]
        self.character.location = self.room1
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="yuna_darknight"),
        )
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(dict(self.character.db.persona), preset.persona.to_record())
        self.assertTrue(self.character.db.persona["background"])

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-persona")
    def test_preset_and_custom_records_carry_the_import_card_key_set_plus_optional_background(self):
        custom = create_object(PlayerCharacter, key="creator-shell-custom-keys")
        self.account.at_post_create_character(custom)
        activate_player_character(
            self.account, custom, self.request(), persona=PERSONA_BLOCK
        )
        preset_shell = create_object(PlayerCharacter, key="creator-shell-preset-keys")
        self.account.at_post_create_character(preset_shell)
        activate_player_character(
            self.account, preset_shell,
            CharacterCreationRequest(mode="preset", preset_key="elysa_snow"),
        )
        # The six import-card keys are identical in both modes; ``background``
        # is present in each record only when that source supplied one.
        self.assertEqual(
            set(custom.db.persona), set(PERSONA_IMPORT_CARD_KEYS)
        )
        self.assertEqual(
            set(preset_shell.db.persona),
            set(PERSONA_IMPORT_CARD_KEYS) | {"background"},
        )

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-persona")
    def test_preset_persona_write_failure_rolls_back_the_whole_activation(self):
        old_key = self.character.key

        def fail(stage):
            if stage == "persona":
                raise RuntimeError("injected preset persona failure")

        with self.assertRaisesRegex(RuntimeError, "injected preset persona failure"):
            activate_player_character(
                self.account, self.character,
                CharacterCreationRequest(mode="preset", preset_key="nazka_bloodfang"),
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertIsNone(self.character.db.persona)
        self.assertEqual(self.character.traits.all(), [])
        self.assertIsNone(self.character.db.age)
        self.assertIsNone(self.character.db.skills)
        self.assertIsNone(self.character.db.inventory)

    def test_preset_mode_takes_precedence_over_a_custom_persona_argument(self):
        # ``persona`` is custom-mode only: the shared builder's preset branch
        # wins even if a mixed call hypothetically supplied one, so the
        # registry record can never be silently replaced by draft prose.
        from world.rules.character_creation import _ValidatedCreation, _persona_record_for

        validated = _ValidatedCreation(
            "艾莉莎", 24, 24, "human", "human_commoner", {}
        )
        record = _persona_record_for(
            validated,
            CharacterCreationRequest(mode="preset", preset_key="elysa_snow"),
            PERSONA_BLOCK,
        )
        self.assertEqual(
            record, PLAYER_PRESET_REGISTRY["elysa_snow"].persona.to_record()
        )
        # The persona argument lost: the prose is the registry card's, not the
        # draft block's (the shipped card now authors full prose).
        self.assertEqual(
            record["personality"],
            PLAYER_PRESET_REGISTRY["elysa_snow"].persona.personality,
        )
        self.assertNotEqual(record["personality"], PERSONA_BLOCK["personality"])


class SexCreationTests(EvenniaTest):
    """Optional sex channel: normalize, persist, reject, roll back
    (namegen-creation-ui D1)."""

    def setUp(self):
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)

    def request(self, **overrides):
        values = {
            "mode": "custom",
            "display_name": "  新角色  ",
            "age": 20,
            "apparent_age": 20,
            "race": "human",
            "subrace": "human_commoner",
            "allocations": balanced_allocations("human", "human_commoner"),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    def test_custom_sex_persists_on_the_activated_entity(self):
        activate_player_character(
            self.account, self.character, self.request(sex="female")
        )
        self.assertEqual(self.character.sex, "female")
        self.assertEqual(self.character.attributes.get("sex"), "female")

    @covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")
    def test_omitted_or_null_sex_normalizes_to_the_default(self):
        for value in ({"sex": None}, {}):
            with self.subTest(value=value):
                character = create_object(PlayerCharacter, key="shell-default")
                self.account.at_post_create_character(character)
                checked = preflight_character_creation(
                    self.account, character, self.request(**value)
                )
                self.assertEqual(checked.sex, DEFAULT_SEX)
                activate_player_character(
                    self.account, character, self.request(**value)
                )
                self.assertEqual(character.sex, DEFAULT_SEX)
                self.assertEqual(character.attributes.get("sex"), DEFAULT_SEX)

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    def test_sex_outside_the_vocabulary_is_rejected_without_mutation(self):
        for value in ("x", "Female", "horse", 5):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    CharacterCreationError, "sex must be one of"
                ):
                    activate_player_character(
                        self.account, self.character, self.request(sex=value)
                    )
        self.assertTrue(self.character.creation_pending)
        # The shell's AttributeProperty default persists at object creation;
        # the rejection must leave that prior value untouched.
        self.assertEqual(self.character.attributes.get("sex"), DEFAULT_SEX)
        self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("player-character-creation::character-creation-enforces-canonical-identity-and-registry-compatibility")
    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-sex")
    def test_preset_activation_persists_the_declared_sex(self):
        # The preset registry is the source of truth for the sex channel:
        # every shipped card declares "female", and a preset-mode request
        # (which never carries a sex) must not fall back to DEFAULT_SEX.
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        for preset_key, preset in PLAYER_PRESET_REGISTRY.items():
            with self.subTest(preset=preset_key):
                character = create_object(PlayerCharacter, key=f"shell-{preset_key}")
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                self.assertEqual(character.sex, preset.sex)
                self.assertEqual(character.attributes.get("sex"), preset.sex)
                self.assertNotEqual(character.sex, DEFAULT_SEX)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_sex_write_failure_rolls_back_the_whole_activation(self):
        def fail(stage):
            if stage == "sex":
                raise RuntimeError("injected")

        with self.assertRaisesRegex(RuntimeError, "injected"):
            activate_player_character(
                self.account, self.character, self.request(sex="male"),
                write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        # Rollback restores the pre-activation snapshot: the creation-time
        # AttributeProperty default, not the rejected write's "male".
        self.assertEqual(self.character.attributes.get("sex"), DEFAULT_SEX)
        self.assertEqual(self.character.traits.all(), [])


class PresetPersonaLengthSweepTests(unittest.TestCase):
    """The rules-side sweep enforces the persona prose cap at module import.

    ``world/lore/`` may not import ``world/rules/``, so
    ``MAX_PERSONA_FIELD_LENGTH`` is checked over the registry HERE
    (field-parity design 3.1): every string the persona record can carry —
    top-level prose, identity layers, appearance sub-keys, and both sides of a
    social-connection pair — must fit the cap.
    """

    @covers_requirement("player-character-creation::the-preset-registry-declares-a-full-persona-in-import-card-shape")
    def test_registry_sweep_raises_for_over_long_persona_prose(self):
        from world.lore.player_presets import (
            PresetAppearance,
            PresetIdentity,
            PresetPersona,
            PlayerPreset,
        )
        from world.rules.character_creation import (
            _validate_preset_persona_lengths,
        )

        def make(persona):
            return {"x": PlayerPreset(
                "x", "x", 18, 18, "human", "human_commoner", (), "e",
                sex="female", persona=persona,
            )}

        over = "長" * (MAX_PERSONA_FIELD_LENGTH + 1)
        ok = "長" * MAX_PERSONA_FIELD_LENGTH
        long_name = "名" * (MAX_PERSONA_FIELD_LENGTH + 1)
        for persona, message in (
            (PresetPersona(personality=over), r"persona\.personality"),
            (PresetPersona(background=over), r"persona\.background"),
            (PresetPersona(identity=PresetIdentity(hidden=over)), r"persona\.identity\.hidden"),
            (PresetPersona(appearance=PresetAppearance(feature=over)), r"persona\.appearance\.feature"),
            (PresetPersona(social_connection=(("甲", over),)), r"persona\.social_connection\.甲"),
            (PresetPersona(social_connection=((long_name, "舊識"),)), r"persona\.social_connection key"),
        ):
            with self.subTest(message=message), self.assertRaisesRegex(
                CharacterCreationError, message
            ):
                _validate_preset_persona_lengths(make(persona))
        # At-bound values pass, and so does the shipped registry itself.
        _validate_preset_persona_lengths(make(
            PresetPersona(personality=ok, background=ok)
        ))
        _validate_preset_persona_lengths(PLAYER_PRESET_REGISTRY)


class PresetValueResolverPurityTests(EvenniaTestCase):
    """``resolve_preset_values`` is callable with only a preset and writes nothing.

    Covers the delta scenario "The resolver is pure": one preset argument, no
    account, no character, no database, no world clock.
    """

    @covers_requirement("player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands")
    def test_resolver_reads_nothing_but_the_registry_and_writes_nothing(self):
        # Signature: exactly one positional parameter — no account, no character.
        params = list(signature(resolve_preset_values).parameters.values())
        self.assertEqual(
            [(p.name, p.kind) for p in params],
            [("preset", inspect.Parameter.POSITIONAL_OR_KEYWORD)],
        )
        preset = PLAYER_PRESET_REGISTRY["sylwen_stillwater"]
        # Zero queries proves no database read and no write; the world-clock
        # accessor always issues a search_script query, so a clock read fails
        # here too. Registries are plain in-memory dicts, so the resolver's
        # only legal inputs cost no queries.
        with self.assertNumQueries(0):
            first = resolve_preset_values(preset)
            second = resolve_preset_values(preset)
        self.assertEqual(first, second)
        # Each call hands back a fresh caller-owned mapping.
        self.assertIsNot(first, second)


class PresetValueResolverParityTests(EvenniaTest):
    """One resolver owns the computation for every shipped preset."""

    def setUp(self):
        super().setUp()
        self.account = create_account(
            "resolver", "resolver@example.test", "testpassword", typeclass=Account
        )

    @covers_requirement("player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands")
    def test_resolver_matches_activated_traits_axis_for_axis(self):
        axes = ALLOCATABLE_AXES + ("guild_merit",)
        for preset_key, preset in PLAYER_PRESET_REGISTRY.items():
            with self.subTest(preset=preset_key):
                expected = resolve_preset_values(preset)
                character = create_object(PlayerCharacter, key=f"value-shell-{preset_key}")
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                for axis in axes:
                    self.assertEqual(
                        character.traits[axis].value, expected[axis],
                        msg=f"{preset_key}/{axis}",
                    )
                self.assertFalse(character.creation_pending)

