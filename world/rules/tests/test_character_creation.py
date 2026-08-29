"""Pure and Evennia-backed tests for deterministic player activation."""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
from unittest.mock import patch
import unittest

from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.lore.races import SUBRACE_REGISTRY
from world.lore.starting_kits import SUBRACE_STARTING_KIT_REGISTRY
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    MAX_PERSONA_FIELD_LENGTH,
    CharacterCreationError,
    CharacterCreationRequest,
    activate_player_character,
    preflight_character_creation,
    resolve_starting_profile,
    starting_magic_interval,
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
        self.assertEqual(human.budget, 181)
        foxkin = resolve_starting_profile("beastfolk", "foxkin")
        self.assertEqual(foxkin.bounds_dict()["mp"], (50, 70))

    def test_catkin_modifiers_are_recorded_for_post_allocation_use(self):
        profile = resolve_starting_profile("beastfolk", "catkin")
        self.assertEqual(profile.static_modifiers.atk_phys, -0.10)
        self.assertEqual(profile.static_modifiers.agility, 0.40)
        self.assertEqual(profile.static_modifiers.defense, -0.30)

    def test_magic_intervals_use_each_race_average(self):
        self.assertEqual(starting_magic_interval("human"), (27, 33))
        self.assertEqual(starting_magic_interval("beastfolk"), (9, 11))
        self.assertEqual(starting_magic_interval("elf"), (270, 330))


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
            self.account, self.character, self.request(), sampler=lambda low, high: low
        )
        self.assertEqual(result.magic_level, 27)
        self.assertEqual(self.character.key, "新角色")
        self.assertEqual((self.character.age, self.character.apparent_age), (20, 20))
        self.assertFalse(self.character.creation_pending)
        self.assertEqual(self.character.traits.magic_level.value, 27)
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

    def test_under_and_over_budget_reject_before_sampling(self):
        valid = balanced_allocations("human")
        for delta in (-1, 1):
            allocations = dict(valid)
            key = next(key for key in ALLOCATABLE_AXES if 0 <= allocations[key] + delta <= resolve_starting_profile("human").bounds_dict()[key][1] - resolve_starting_profile("human").bounds_dict()[key][0])
            allocations[key] += delta
            calls = []
            with self.subTest(delta=delta), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character,
                    self.request(allocations=allocations),
                    sampler=lambda low, high: calls.append((low, high)) or low,
                )
            self.assertEqual(calls, [])
            self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("player-character-creation::character-creation-enforces-adult-identity-and-registry-compatibility")
    def test_age_name_subrace_and_invalid_sampler_rejections_are_non_mutating(self):
        requests = (
            self.request(age=17),
            self.request(apparent_age=17),
            self.request(display_name="|rbad|n"),
            self.request(race="human", subrace="foxkin"),
        )
        for request in requests:
            with self.subTest(request=request), self.assertRaises(CharacterCreationError):
                activate_player_character(self.account, self.character, request)
            self.assertTrue(self.character.creation_pending)
            self.assertEqual(self.character.traits.all(), [])
        for sample in (26, 34, 27.0):
            with self.subTest(sample=sample), self.assertRaises(CharacterCreationError):
                activate_player_character(
                    self.account, self.character, self.request(),
                    sampler=lambda low, high, value=sample: value,
                )

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
            sampler=lambda low, high: low,
        )
        self.assertEqual(result.display_name, name)
        self.assertEqual(self.character.key, name)

    @covers_requirement("player-stat-allocation::starting-magic-level-is-sampled-from-a-race-owned-average-band")
    def test_preset_activation_uses_the_same_magic_sampler(self):
        result = activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="elf_guardian"),
            sampler=lambda low, high: high,
        )
        self.assertEqual(result.magic_level, 330)
        self.assertEqual(self.character.race, "elf")

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_preset_activation_grants_the_declared_skill_kit(self):
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        for preset_key in ("yuna_darknight", "human_wanderer", "elf_guardian"):
            with self.subTest(preset_key=preset_key):
                character = create_object(PlayerCharacter, key=f"shell-{preset_key}")
                self.account.at_post_create_character(character)
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                    sampler=lambda low, high: low,
                )
                self.assertEqual(
                    character.db.skills,
                    PLAYER_PRESET_REGISTRY[preset_key].skill_lists(),
                )
                self.assertFalse(character.creation_pending)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_preset_activation_grants_the_declared_starting_inventory(self):
        from world.lore.player_presets import PLAYER_PRESET_REGISTRY

        for preset_key in ("yuka_darknight", "violet_altoria", "human_wanderer"):
            with self.subTest(preset_key=preset_key):
                character = create_object(PlayerCharacter, key=f"kit-shell-{preset_key}")
                self.account.at_post_create_character(character)
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                    sampler=lambda low, high: low,
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
                    sampler=lambda low, high: low,
                )
                expected = SUBRACE_STARTING_KIT_REGISTRY[
                    subrace_key
                ].inventory_list()
                self.assertEqual(character.db.inventory, expected)
                self.assertGreater(len(expected), 0)
                self.assertFalse(character.creation_pending)

    def test_fault_after_trait_write_restores_all_state_and_handler_cache(self):
        self.character.db.magic_xp = 9
        before_traits = deepcopy(dict(self.character.traits.trait_data))
        old_key = self.character.key

        def fail(stage):
            if stage == "traits":
                raise RuntimeError("injected")

        with self.assertRaisesRegex(RuntimeError, "injected"):
            activate_player_character(
                self.account, self.character, self.request(), sampler=lambda low, high: low,
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.db.magic_xp, 9)
        self.assertEqual(dict(self.character.traits.trait_data), before_traits)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_every_observable_write_failure_restores_the_complete_shell(self):
        stages = (
            "identity", "traits", "age", "apparent_age", "race", "subrace",
            "magic_xp", "skill_proficiency", "skills", "skill_grants",
            "equipment", "inventory", "wallet", "quest_log", "guild_rank",
            "creation_pending", "portrait_policy",
        )
        for stage in stages:
            with self.subTest(stage=stage):
                character = create_object(PlayerCharacter, key=f"shell-{stage}")
                self.account.at_post_create_character(character)
                character.db.magic_xp = 9
                before = {
                    key: (
                        character.attributes.has(key),
                        deepcopy(character.attributes.get(key)),
                    )
                    for key in (
                        "age", "apparent_age", "race", "subrace",
                        "creation_pending", "magic_xp", "skill_proficiency",
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
                        sampler=lambda low, high: low, write_observer=fail,
                    )
                self.assertEqual(character.key, old_key)
                self.assertEqual(character.location, old_location)
                self.assertIn(character, self.account.characters)
                self.assertEqual(dict(character.traits.trait_data), before_traits)
                for key, (existed, value) in before.items():
                    self.assertEqual(character.attributes.has(key), existed, key)
                    self.assertEqual(character.attributes.get(key), value, key)

    def test_successful_activation_teleports_to_south_gate_without_clock(self):
        from evennia.utils.create import create_object as _co
        from typeclasses.rooms import Room
        from world.maps.bootstrap import SOUTH_GATE_XYZ, sync_grid
        from world.rules.onboarding import relocate_to_starting_location

        _co(Room, key="虛境", location=None)
        sync_grid()
        from evennia.contrib.grid.xyzgrid.xyzroom import XYZRoom

        south_gate = XYZRoom.objects.filter_xyz(xyz=SOUTH_GATE_XYZ).first()
        self.assertIsNotNone(south_gate)
        old_location = self.character.location
        result = activate_player_character(
            self.account, self.character, self.request(), sampler=lambda low, high: low
        )
        clock = __import__("world.rules.clock", fromlist=["get_world_clock"]).get_world_clock()
        tick_before = clock.tick
        relocate_to_starting_location(self.character)
        self.assertFalse(self.character.creation_pending)
        self.assertIs(self.character.location, south_gate)
        self.assertEqual(clock.tick, tick_before)
        self.assertIsNot(self.character.location, old_location)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_missing_south_gate_leaves_shell_and_activation_intact(self):
        from world.rules.onboarding import relocate_to_starting_location

        old_location = self.character.location
        activate_player_character(
            self.account, self.character, self.request(), sampler=lambda low, high: low
        )
        with patch("world.rules.onboarding._south_gate", return_value=None):
            relocate_to_starting_location(self.character)
        self.assertFalse(self.character.creation_pending)
        self.assertIs(self.character.location, old_location)

    @covers_requirement("player-character-creation::activation-is-an-all-or-nothing-deterministic-core-operation")
    def test_failed_relocation_never_rolls_back_activation(self):
        from world.rules.onboarding import relocate_to_starting_location

        activate_player_character(
            self.account, self.character, self.request(), sampler=lambda low, high: low
        )
        old_location = self.character.location

        def boom():
            raise RuntimeError("relocation failure")

        messages = []
        self.character.msg = lambda text, **kwargs: messages.append(str(text))
        with patch("world.rules.onboarding._south_gate", side_effect=boom):
            relocate_to_starting_location(self.character)
        self.assertFalse(self.character.creation_pending)
        self.assertIsNotNone(self.character.traits.magic_level)
        self.assertIs(self.character.location, old_location)
        self.assertTrue(any("南門" in message for message in messages))


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

    @covers_requirement("art-asset-lifecycle::successful-player-creation-and-validated-import-schedule-an-eligible-unique-portrait-through-transaction-on-commit")
    @covers_requirement("art-asset-lifecycle::every-player-activation-path-finalizes-the-portrait-lifecycle")
    def test_activation_sets_the_named_policy_and_schedules_exactly_one_ensure(self):
        from world.art.store import ArtAssetRecord

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            activate_player_character(
                self.account, self.character, self.request(),
                sampler=lambda low, high: low,
            )
        self.assertEqual(
            self.character.db.portrait_policy,
            {"mode": "named", "stable_key": str(self.character.pk)},
        )
        self.assertEqual(len(callbacks), 1)
        records = ArtAssetRecord.objects.filter(db_key=self._portrait_key())
        self.assertEqual(records.count(), 1)

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
            },
        )
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            _creation_activate_adapter(web, {})
        self.assertFalse(web.creation_pending)
        self.assertEqual(
            web.db.portrait_policy,
            {"mode": "named", "stable_key": str(web.pk)},
        )
        self.assertEqual(len(callbacks), 1)
        self.assertEqual(
            ArtAssetRecord.objects.filter(
                db_key=f"art:portrait:character:{web.pk}"
            ).count(),
            1,
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
                sampler=lambda low, high: low, write_observer=fail,
            )
        self.assertTrue(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("portrait_policy"))
        self.assertIsNone(self.character.db.portrait_policy)
        self.assertEqual(
            ArtAssetRecord.objects.filter(db_key=self._portrait_key()).count(),
            0,
        )


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
            sampler=lambda low, high: low,
        )
        self.assertEqual(result.display_name, "新角色")
        self.assertEqual(self.character.db.affinity_elements, ["fire", "wind"])
        character = create_object(PlayerCharacter, key="three-shell")
        self.account.at_post_create_character(character)
        with self.assertRaisesRegex(CharacterCreationError, "exceeds the human bound"):
            activate_player_character(
                self.account, character,
                self.request(affinity_elements=("fire", "wind", "water")),
                sampler=lambda low, high: low,
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
            sampler=lambda low, high: low,
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
                sampler=lambda low, high: low,
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
                        sampler=lambda low, high: low,
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
            sampler=lambda low, high: low,
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
            sampler=lambda low, high: low,
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
                        sampler=lambda low, high: low,
                    )
                self.assertTrue(character.creation_pending)
                self.assertFalse(character.attributes.has("affinity_elements"))

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_human_preset_persists_declared_affinity(self):
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="violet_altoria"),
            sampler=lambda low, high: low,
        )
        self.assertEqual(self.character.db.affinity_elements, ["fire", "wind"])

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_neutral_human_preset_stays_neutral(self):
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="human_wanderer"),
            sampler=lambda low, high: low,
        )
        self.assertEqual(self.character.db.affinity_elements, [])

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_elf_preset_seeds_affinity_from_subrace(self):
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="elf_guardian"),
            sampler=lambda low, high: low,
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
                sampler=lambda low, high: low,
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
                            sampler=lambda low, high: low,
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
            persona=PERSONA_BLOCK, sampler=lambda low, high: low,
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
                persona=PERSONA_BLOCK, sampler=lambda low, high: low,
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
            self.account, self.character, self.request(), sampler=lambda low, high: low
        )
        self.assertFalse(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("persona"))

    @covers_requirement("creation-persona-persistence::activation-persists-the-persona-block-in-the-import-card-shape")
    def test_custom_background_is_persisted_inside_the_persona_record(self):
        activate_player_character(
            self.account, self.character,
            self.request(background="在公會登記的新人冒險者"),
            sampler=lambda low, high: low,
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
            persona=PERSONA_BLOCK, sampler=lambda low, high: low,
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
                    sampler=lambda low, high: low,
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
                sampler=lambda low, high: low,
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
                    persona=persona, sampler=lambda low, high: low,
                )
            self.assertTrue(self.character.creation_pending)
            self.assertEqual(self.character.traits.all(), [])
            self.assertFalse(self.character.attributes.has("persona"))
