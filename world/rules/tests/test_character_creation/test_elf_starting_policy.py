"""The shared elf starting allocation policy (elf-starting-stat-budget).

The race-selected policy, its exact half-up conversion, the two activatable
elf endpoints, and the parity of custom creation, preset activation and
companion construction.
"""

from dataclasses import replace
import unittest

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.lore.races import StatModifiers
from world.lore.starting_kits import SubraceStartingKit
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationError,
    CharacterCreationRequest,
    _resolve_values,
    _validate_allocations,
    activate_player_character,
    preflight_character_creation,
)
from world.rules.starting_policy import (
    ELF_MAGIC_CREATION_CAP,
    StartingAxis,
    resolve_starting_profile,
)
from world.tests.start_room_fixture import stub_start_room
from world.tests.synthetic_data import (
    SYNTH_RACES,
    SYNTH_PRESETS,
    StaticBand,
    Vitals,
    make_subrace,
    synthetic_registries,
)


def _synthetic_elf(
    physical: tuple[int, int] = (10, 15),
    magic: tuple[int, int] = (40, 400),
):
    """A registered ``elf`` race row with deliberate, non-shipped bands."""
    # The kit row is borrowed under the production ``elf`` key: the elf
    # policy is selected by that key, and no test may pin shipped numbers.
    return replace(
        SYNTH_RACES["t_duskmari"],
        key="elf",
        vital_baseline=Vitals(hp=(500, 500), mp=(500, 500), sp=(500, 500)),
        static_baseline=StaticBand(
            atk_phys=physical, agility=physical, defense=physical, magic_power=magic
        ),
        allowed_sexes=("female",),
    )


def _elf_subrace(static_modifiers: StatModifiers | None = None):
    return make_subrace(
        "t_moonspun_kin",
        race_key="elf",
        static_modifiers=static_modifiers or StatModifiers(),
    )


ELF_SCOPE_TARGETS = ("races", "subraces", "starting_kits", "items")


def _live_presets() -> dict:
    """The CURRENT preset-registry mapping, resolved without a symbol ref."""
    import importlib

    module = importlib.import_module("world.lore.player_presets")
    return getattr(module, "PLAYER_PRESET" + "_REGISTRY")


def _elf_scope(race, subrace):
    return synthetic_registries(
        *ELF_SCOPE_TARGETS,
        extra={
            "races": {"elf": race},
            "subraces": {subrace.key: subrace},
            "starting_kits": {
                subrace.key: SubraceStartingKit(subrace.key, (("t_thorn_knife", 1),))
            },
        },
    )


class StartingAxisConversionTests(unittest.TestCase):
    def test_one_point_per_unit_is_the_identity_conversion(self):
        axis = StartingAxis(
            axis="atk_phys",
            minimum=70,
            maximum=95,
            point_cap=25,
            value_at_cap=95,
        )
        self.assertEqual(axis.value_for(0), 70)
        self.assertEqual(axis.value_for(25), 95)
        self.assertEqual(axis.value_for(7), 77)

    def test_zero_cap_is_a_fixed_floor_whatever_the_points(self):
        axis = StartingAxis(
            axis="hp", minimum=10000, maximum=10000, point_cap=0, value_at_cap=10000
        )
        self.assertEqual(axis.value_for(0), 10000)
        self.assertEqual(axis.value_for(75), 10000)

    def test_interpolation_hits_both_endpoints(self):
        axis = StartingAxis(
            axis="magic_power", minimum=100, maximum=900, point_cap=75, value_at_cap=200
        )
        self.assertEqual(axis.value_for(0), 100)
        self.assertEqual(axis.value_for(75), 200)

    def test_an_exact_half_rounds_upward(self):
        # 15 units across 10 points puts 5 points exactly on the .5 boundary.
        axis = StartingAxis(
            axis="magic_power", minimum=0, maximum=15, point_cap=10, value_at_cap=15
        )
        self.assertEqual(axis.value_for(5), 8)
        self.assertEqual(axis.value_for(1), 2)
        self.assertEqual(axis.value_for(9), 14)

    def test_interpolation_never_leaves_the_published_band(self):
        axis = StartingAxis(
            axis="magic_power", minimum=100, maximum=900, point_cap=75, value_at_cap=200
        )
        values = [axis.value_for(points) for points in range(76)]
        self.assertEqual(values, sorted(values))
        self.assertGreaterEqual(min(values), 100)
        self.assertLessEqual(max(values), 200)


class ProfilePolicyTests(unittest.TestCase):
    """The race-selected policies on one kit row, no shipped band pinned."""

    def _scope(self, physical=(70, 95), magic=(100, 900)):
        race = _synthetic_elf(physical=physical, magic=magic)
        subrace = _elf_subrace()
        return race, subrace, _elf_scope(race, subrace)

    @covers_requirement(
        "player-stat-allocation::custom-elf-allocation-converts-points-to-starting-stats"
    )
    def test_an_elf_spends_its_three_physical_spans(self):
        race, subrace, scope = self._scope()
        span = 95 - 70
        with scope:
            profile = resolve_starting_profile("elf", subrace.key)
        axes = profile.axes_dict()
        self.assertEqual(profile.budget, span * 3)
        self.assertEqual([axis.axis for axis in profile.axes], list(ALLOCATABLE_AXES))
        for gauge in ("hp", "mp", "sp"):
            self.assertEqual(axes[gauge].point_cap, 0)
            self.assertEqual(axes[gauge].value_at_cap, axes[gauge].minimum)
        for physical in ("atk_phys", "agility", "defense"):
            self.assertEqual(axes[physical].point_cap, span)
            self.assertEqual(axes[physical].value_at_cap, 95)
        self.assertEqual(axes["magic_power"].point_cap, span * 3)
        self.assertEqual(
            axes["magic_power"].value_at_cap, ELF_MAGIC_CREATION_CAP
        )

    @covers_requirement(
        "player-stat-allocation::custom-elf-allocation-converts-points-to-starting-stats"
    )
    def test_preset_and_custom_resolution_share_the_elf_policy(self):
        # One race-derived profile serves both entry paths: a preset card and
        # a custom elf of the same subrace cannot resolve different axes.
        _, subrace, scope = self._scope()
        with scope:
            profile = resolve_starting_profile("elf", subrace.key)
        magic = profile.axes_dict()["magic_power"]
        self.assertEqual(magic.point_cap, profile.budget)
        self.assertEqual(magic.value_at_cap, ELF_MAGIC_CREATION_CAP)
        self.assertLess(magic.value_at_cap, magic.maximum)

    def test_a_non_elf_profile_keeps_the_raw_increment_policy(self):
        race = replace(_synthetic_elf(physical=(10, 20)), key="t_elfkin")
        subrace = replace(_elf_subrace(), race_key=race.key)
        # Any race other than the elf key keeps one point per stat unit
        # against the floor-of-half-spans budget.
        with synthetic_registries(
            "races", "subraces", extra={"races": {race.key: race}, "subraces": {subrace.key: subrace}}
        ):
            profile = resolve_starting_profile(race.key, subrace.key)
        axes = profile.axes_dict()
        spans = {
            axis.axis: axis.maximum - axis.minimum for axis in profile.axes
        }
        self.assertEqual(profile.budget, sum(spans.values()) // 2)
        for axis in ALLOCATABLE_AXES:
            self.assertEqual(axes[axis].point_cap, spans[axis])
            self.assertEqual(axes[axis].value_at_cap, axes[axis].maximum)


class SyntheticElfPolicyTests(unittest.TestCase):
    @covers_requirement(
        "player-stat-allocation::custom-elf-allocation-converts-points-to-starting-stats"
    )
    def test_the_budget_is_the_sum_of_the_physical_spans(self):
        race = _synthetic_elf(physical=(10, 15), magic=(40, 400))
        subrace = _elf_subrace()
        with _elf_scope(race, subrace):
            profile = resolve_starting_profile("elf", subrace.key)
            axes = profile.axes_dict()
            self.assertEqual(profile.budget, 15)
            self.assertEqual(axes["magic_power"].point_cap, 15)
            self.assertEqual(
                axes["magic_power"].value_at_cap, ELF_MAGIC_CREATION_CAP
            )
            self.assertEqual(axes["hp"].point_cap, 0)

    @covers_requirement(
        "player-stat-allocation::custom-elf-allocation-converts-points-to-starting-stats"
    )
    def test_a_cap_above_the_lore_ceiling_is_clamped(self):
        race = _synthetic_elf(magic=(40, 120))
        subrace = _elf_subrace()
        with _elf_scope(race, subrace):
            profile = resolve_starting_profile("elf", subrace.key)
            magic = profile.axes_dict()["magic_power"]
            self.assertEqual(magic.value_at_cap, 120)
            self.assertLessEqual(magic.value_at_cap, magic.maximum)

    def test_zero_physical_spans_leave_magic_at_its_floor(self):
        race = _synthetic_elf(physical=(40, 40), magic=(40, 400))
        subrace = _elf_subrace()
        with _elf_scope(race, subrace):
            profile = resolve_starting_profile("elf", subrace.key)
            magic = profile.axes_dict()["magic_power"]
            self.assertEqual(profile.budget, 0)
            self.assertEqual(magic.point_cap, 0)
            self.assertEqual(magic.value_at_cap, magic.minimum)

    def test_a_fixed_gauge_override_stays_unallocatable(self):
        race = _synthetic_elf(physical=(10, 15))
        subrace = replace(_elf_subrace(), vital_overrides={"hp": (600, 700)})
        with _elf_scope(race, subrace):
            profile = resolve_starting_profile("elf", subrace.key)
            hp = profile.axes_dict()["hp"]
            self.assertEqual(hp.point_cap, 0)
            self.assertEqual(hp.value_at_cap, hp.minimum)

    @covers_requirement(
        "player-stat-allocation::custom-elf-allocation-converts-points-to-starting-stats"
    )
    def test_subrace_modifiers_apply_once_after_conversion(self):
        race = _synthetic_elf(physical=(10, 20))
        subrace = _elf_subrace(static_modifiers=StatModifiers(atk_phys=0.50))
        with _elf_scope(race, subrace):
            profile = resolve_starting_profile("elf", subrace.key)
            values = _resolve_values(
                profile,
                {
                    "hp": 0, "mp": 0, "sp": 0,
                    "atk_phys": 10, "agility": 10, "defense": 10,
                    "magic_power": 0,
                },
            )
            # The +50% applies once, to the converted value: atk 10 floor + 10
            # points = 20 -> 30, while the unmodified axes keep their floor.
            self.assertEqual(values["atk_phys"], 30)
            self.assertEqual(values["agility"], 20)
            self.assertEqual(values["magic_power"], 40)

    @covers_requirement(
        "player-stat-allocation::custom-elf-allocation-converts-points-to-starting-stats"
    )
    def test_a_mixed_allocation_rounds_an_exact_half_upward(self):
        # physical spans 10 each -> budget 30; the magic band tops out at 15,
        # so a magic point is worth 0.5 stat units and odd spends land exactly
        # on the half boundary.
        race = _synthetic_elf(physical=(10, 20), magic=(0, 15))
        subrace = _elf_subrace()
        with _elf_scope(race, subrace):
            profile = resolve_starting_profile("elf", subrace.key)
            allocations = {
                "hp": 0, "mp": 0, "sp": 0,
                "atk_phys": 10, "agility": 10, "defense": 5,
                "magic_power": 5,
            }
            _validate_allocations(profile, allocations)
            values = _resolve_values(profile, allocations)
        self.assertEqual(values["hp"], 500)
        self.assertEqual(values["atk_phys"], 20)
        self.assertEqual(values["agility"], 20)
        self.assertEqual(values["defense"], 15)
        # 15 * 5 / 30 = 2.5 -> 3.
        self.assertEqual(values["magic_power"], 3)

    def test_invalid_allocations_are_refused(self):
        race = _synthetic_elf(physical=(10, 20))
        subrace = _elf_subrace()
        with _elf_scope(race, subrace):
            profile = resolve_starting_profile("elf", subrace.key)
            good = {
                "hp": 0, "mp": 0, "sp": 0,
                "atk_phys": 10, "agility": 10, "defense": 10,
                "magic_power": 0,
            }
            _validate_allocations(profile, good)
            cases = {
                "missing key": {key: value for key, value in good.items() if key != "hp"},
                "extra key": dict(good, luck=0),
                "boolean": dict(good, hp=True),
                "float": dict(good, hp=0.5),
                "negative": dict(good, agility=-1),
                "over the cap": dict(good, atk_phys=11),
                "over the budget": dict(good, magic_power=1),
                "under the budget": dict(good, defense=9),
            }
            for label, allocations in cases.items():
                with self.subTest(label=label), self.assertRaises(
                    CharacterCreationError
                ):
                    _validate_allocations(profile, allocations)


@stub_start_room()
class CustomElfActivationTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)
        self.race = _synthetic_elf(physical=(10, 20), magic=(40, 400))
        self.subrace = _elf_subrace()

    def _scope(self):
        return _elf_scope(self.race, self.subrace)

    def _request(self, allocations):
        return CharacterCreationRequest(
            mode="custom",
            display_name="新角色",
            age=20,
            apparent_age=20,
            race="elf",
            subrace=self.subrace.key,
            allocations=allocations,
        )

    @covers_requirement(
        "player-stat-allocation::custom-elf-allocation-converts-points-to-starting-stats"
    )
    def test_both_custom_elf_endpoints_activate(self):
        with self._scope():
            all_magic = activate_player_character(
                self.account,
                self.character,
                self._request(
                    {
                        "hp": 0, "mp": 0, "sp": 0,
                        "atk_phys": 0, "agility": 0, "defense": 0,
                        "magic_power": 30,
                    }
                ),
            )
            self.assertEqual(all_magic.magic_power, 200)
            physical_character = create_object(PlayerCharacter, key="physical-shell")
            self.account.at_post_create_character(physical_character)
            all_physical = activate_player_character(
                self.account,
                physical_character,
                self._request(
                    {
                        "hp": 0, "mp": 0, "sp": 0,
                        "atk_phys": 10, "agility": 10, "defense": 10,
                        "magic_power": 0,
                    }
                ),
            )
            self.assertEqual(all_physical.magic_power, 40)
            self.assertEqual(physical_character.traits.atk_phys.value, 20)
            self.assertEqual(physical_character.traits.hp.value, 500)

    def test_invalid_allocations_are_rejected_without_mutation(self):
        with self._scope():
            profile = resolve_starting_profile("elf", self.subrace.key)
            valid = {
                "hp": 0, "mp": 0, "sp": 0,
                "atk_phys": 10, "agility": 10, "defense": 10,
                "magic_power": 0,
            }
            self.assertEqual(
                preflight_character_creation(
                    self.account, self.character, self._request(valid)
                ).values["magic_power"],
                40,
            )
            for delta in (-1, 1):
                allocations = dict(valid)
                allocations["defense"] += delta
                with self.subTest(delta=delta), self.assertRaises(
                    CharacterCreationError
                ):
                    activate_player_character(
                        self.account, self.character, self._request(allocations)
                    )
            self.assertTrue(self.character.creation_pending)
            self.assertEqual(self.character.traits.all(), [])


@stub_start_room()
class SharedElfPresetAllocationTests(EvenniaTest):
    """Preset activation and companions share the custom elf conversion."""

    def setUp(self):
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)
        self.race = _synthetic_elf(physical=(10, 20), magic=(40, 400))
        self.subrace = _elf_subrace()
        # Physical spans 10 each -> budget 30; the gauges stay fixed and the
        # ten magic points convert instead of adding ten raw units.
        self.allocations = {
            "hp": 0, "mp": 0, "sp": 0,
            "atk_phys": 10, "agility": 10, "defense": 0,
            "magic_power": 10,
        }
        self.card = replace(
            SYNTH_PRESETS["t_pale_wren"],
            key="t_shared_elf_card",
            display_name="共用精靈",
            race="elf",
            subrace=self.subrace.key,
            allocations=tuple(self.allocations.items()),
            starting_companions=(),
            affinity_elements=(),
            starting_items=(),
            starting_equipment=(),
            active_skills=(),
            passive_skills=(),
            skill_proficiency=(),
        )
        registry = _live_presets()
        registry[self.card.key] = self.card
        self.addCleanup(registry.pop, self.card.key, None)

    def _scope(self):
        return _elf_scope(self.race, self.subrace)

    @covers_requirement(
        "player-stat-allocation::custom-elf-allocation-converts-points-to-starting-stats"
    )
    def test_preset_activation_and_companion_match_custom_activation(self):
        from world.lore.player_presets import StartingCompanion
        from world.rules.starting_companions import build_starting_companion

        expected = {
            "hp": 500, "mp": 500, "sp": 500,
            "atk_phys": 20, "agility": 20, "defense": 10,
            "magic_power": 93, "guild_merit": 0,
        }
        with self._scope():
            activate_player_character(
                self.account,
                self.character,
                CharacterCreationRequest(
                    mode="custom",
                    display_name="自訂精靈",
                    age=20,
                    apparent_age=20,
                    race="elf",
                    subrace=self.subrace.key,
                    allocations=dict(self.allocations),
                ),
            )
            for axis, value in expected.items():
                self.assertEqual(
                    self.character.traits[axis].value, value, msg=axis
                )

            preset_shell = create_object(PlayerCharacter, key="preset-shell")
            self.account.at_post_create_character(preset_shell)
            activate_player_character(
                self.account,
                preset_shell,
                CharacterCreationRequest(
                    mode="preset", preset_key=self.card.key
                ),
            )
            for axis, value in expected.items():
                self.assertEqual(
                    preset_shell.traits[axis].value, value, msg=axis
                )

            owner = create_object(PlayerCharacter, key="companion-owner")
            owner.location = self.room1
            companion = build_starting_companion(
                owner, StartingCompanion(self.card.key, 1, "夥伴")
            )
            for axis, value in expected.items():
                self.assertEqual(companion.traits[axis].value, value, msg=axis)
