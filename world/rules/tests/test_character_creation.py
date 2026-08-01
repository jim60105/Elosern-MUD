"""Pure and Evennia-backed tests for deterministic player activation."""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
import unittest

from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
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
            "subrace": None,
            "allocations": balanced_allocations("human"),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    @covers_requirement("player-character-creation::character-creation-offers-preset-and-custom-modes")
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
        self.assertEqual(self.character.db.inventory, [])
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

    @covers_requirement("player-stat-allocation::starting-magic-level-is-sampled-from-a-race-owned-average-band")
    def test_preset_activation_uses_the_same_magic_sampler(self):
        result = activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="elf_guardian"),
            sampler=lambda low, high: high,
        )
        self.assertEqual(result.magic_level, 330)
        self.assertEqual(self.character.race, "elf")

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
            "creation_pending",
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
