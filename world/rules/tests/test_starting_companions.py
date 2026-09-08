"""Tests for the preset companion declaration bounds and the NPC builder.

The lore-side shape validation lives with its validator in
``world/lore/tests/test_player_presets.py``; this module covers the rules-side
bounds sweep and the deterministic builder, including the differential parity
claim: a companion built from a card must equal a PLAYER activated from the
same card, not merely re-read the same helper the builder itself calls.
"""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import LLMNPC
from typeclasses.rooms import Room
from world.lore.player_presets import (
    PLAYER_PRESET_REGISTRY,
    PlayerPreset,
    StartingCompanion,
)
from world.lore.races import SUBRACE_REGISTRY
from world.rules.character_creation import (
    ALLOCATABLE_AXES,
    CharacterCreationRequest,
    activate_player_character,
)
from world.rules.starting_companions import (
    StartingCompanionError,
    _validate_preset_companion_bounds,
    build_starting_companion,
)

_YUKA = "yuka_darknight"
_YUNA = "yuna_darknight"


_HUMAN_ALLOCATIONS = (
    ("hp", 50), ("mp", 50), ("sp", 50), ("atk_phys", 10),
    ("agility", 10), ("defense", 11), ("magic_power", 43),
)


def _probe_preset(**overrides) -> PlayerPreset:
    values = dict(
        key="probe", display_name="探測者", age=18, apparent_age=18, race="human",
        subrace="human_commoner", allocations=_HUMAN_ALLOCATIONS, emphasis="e",
        sex="female",
    )
    values.update(overrides)
    return PlayerPreset(**values)


class CompanionBoundsSweepTests(unittest.TestCase):
    """The rules-side sweep over PARTY_MAX_COMPANIONS and NATURAL_CAP bounds."""

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_registry_ships_within_the_swept_bounds(self):
        # The import-time sweep already accepted the shipped registry; running
        # it again proves the shipped cards stay inside the rules constants.
        _validate_preset_companion_bounds(PLAYER_PRESET_REGISTRY)

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_over_bound_companion_count_names_the_offending_preset(self):
        from world.rules.party import PARTY_MAX_COMPANIONS

        preset = _probe_preset(
            starting_companions=tuple(
                StartingCompanion(key, 50, "夥伴")
                for key in list(PLAYER_PRESET_REGISTRY)[: PARTY_MAX_COMPANIONS + 1]
            )
        )
        with self.assertRaisesRegex(
            StartingCompanionError, "more than the party cap"
        ):
            _validate_preset_companion_bounds({"probe": preset})

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_out_of_range_affinity_names_the_offending_preset(self):
        partner = next(key for key in PLAYER_PRESET_REGISTRY if key != "probe")
        for affinity in (0, -1, 100, True, False, "50", None):
            preset = _probe_preset(
                starting_companions=(StartingCompanion(partner, affinity, "夥伴"),)
            )
            with self.subTest(affinity=affinity), self.assertRaisesRegex(
                StartingCompanionError, "outside 1"
            ):
                _validate_preset_companion_bounds({"probe": preset})
        # The 1 and NATURAL_CAP boundaries pass.
        for affinity in (1, 99):
            _validate_preset_companion_bounds(
                {
                    "probe": _probe_preset(
                        starting_companions=(
                            StartingCompanion(partner, affinity, "夥伴"),
                        )
                    )
                }
            )

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_an_overlong_relationship_label_names_the_offending_preset(self):
        # The label is injected into the built persona's social_connection,
        # which PersonaStore renders as prose under the same field cap.
        from world.rules.character_creation import MAX_PERSONA_FIELD_LENGTH

        partner = next(key for key in PLAYER_PRESET_REGISTRY if key != "probe")
        preset = _probe_preset(
            starting_companions=(
                StartingCompanion(partner, 50, "關" * (MAX_PERSONA_FIELD_LENGTH + 1)),
            )
        )
        with self.assertRaisesRegex(StartingCompanionError, "persona"):
            _validate_preset_companion_bounds({"probe": preset})


class _BuilderCase(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.hall = create_object(
            Room,
            key="companion hall",
        )
        self.owner = create_object(PlayerCharacter, key="悠奈的持有者")
        self.owner.race = "human"
        self.owner.apply_race_baseline()
        self.owner.location = self.hall


class CompanionBuildTests(_BuilderCase):
    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_built_companion_matches_a_player_activated_from_the_same_card(self):
        """Differential parity: companion vs. real activation, not vs. helpers."""
        account = create_account(
            "twin-account", "twin@example.test", "testpassword", typeclass=Account
        )
        shell = create_object(PlayerCharacter, key="twin-shell")
        account.at_post_create_character(shell)
        activate_player_character(
            account, shell, CharacterCreationRequest(mode="preset", preset_key=_YUKA)
        )
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
        )
        self.assertEqual(companion.race, shell.race)
        self.assertEqual(companion.subrace, shell.subrace)
        self.assertEqual(companion.sex, shell.sex)
        for axis in ALLOCATABLE_AXES + ("guild_merit",):
            self.assertEqual(
                companion.traits[axis].value, shell.traits[axis].value, msg=axis
            )
        self.assertEqual(companion.db.skills, shell.db.skills)
        self.assertEqual(
            companion.db.skill_proficiency, shell.db.skill_proficiency
        )
        self.assertEqual(companion.db.inventory, shell.db.inventory)
        self.assertEqual(companion.db.equipment, shell.db.equipment)
        self.assertEqual(
            companion.db.affinity_elements, shell.db.affinity_elements
        )
        self.assertEqual(companion.db.age, shell.db.age)
        self.assertEqual(companion.db.apparent_age, shell.db.apparent_age)
        self.assertEqual(companion.db.disguised_stats, shell.db.disguised_stats)
        # The persona is the card's record plus exactly the owner link.
        self.assertEqual(
            companion.db.persona,
            {
                **shell.db.persona,
                "social_connection": {
                    **shell.db.persona["social_connection"],
                    self.owner.key: "雙胞胎姊姊",
                },
            },
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_the_companion_is_an_llmnpc_beside_its_owner(self):
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
        )
        # Plain NPC fails commands/invite.py's gate; LLMNPC stays re-invitable.
        self.assertIsInstance(companion, LLMNPC)
        self.assertEqual(companion.location, self.hall)
        self.assertEqual(companion.key, "悠花")

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_an_elf_companion_seeds_affinity_elements_from_its_subrace(self):
        preset = PLAYER_PRESET_REGISTRY[_YUKA]
        self.assertEqual(preset.race, "elf")
        self.assertEqual(preset.affinity_elements, ())
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
        )
        seed = SUBRACE_REGISTRY[preset.subrace].affinity_elements
        self.assertEqual(companion.db.affinity_elements, list(seed))

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_declared_equipment_is_worn_with_buffs_and_synced_ceilings(self):
        # A temporary card carries AND declares worn: the toggle preflight
        # requires canonical inventory ownership, exactly like shipped cards.
        # knight_platemail carries the rulebook {hp: 15} gauge cap;
        # apothecary_beads attaches the item_regen_light buff.
        card = _probe_preset(
            key="gear_probe",
            display_name="武裝探測者",
            starting_items=(
                ("knight_platemail", 1), ("apothecary_beads", 1),
                ("healing_potion", 1),
            ),
            starting_equipment=("knight_platemail", "apothecary_beads"),
        )
        PLAYER_PRESET_REGISTRY["gear_probe"] = card
        self.addCleanup(PLAYER_PRESET_REGISTRY.pop, "gear_probe", None)
        companion = build_starting_companion(
            self.owner, StartingCompanion("gear_probe", 40, "夥伴")
        )
        equipment = companion.db.equipment
        self.assertEqual(equipment["armor"], "knight_platemail")
        self.assertEqual(equipment["accessories"], ["apothecary_beads"])
        # Equipped items remain in canonical inventory.
        self.assertIn("knight_platemail", companion.db.inventory)
        self.assertEqual(companion.traits.hp.mod, 15)
        self.assertIn(
            "item_regen_light:apothecary_beads", set(companion.buffs.all)
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_the_persona_names_the_owning_player(self):
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUNA, 95, "雙胞胎妹妹")
        )
        self.assertEqual(
            companion.db.persona["social_connection"][self.owner.key],
            "雙胞胎妹妹",
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_a_taken_name_takes_a_pk_suffix_while_the_portrait_subject_stays(self):
        # The design's named edge: a persisted character literally holds the
        # partner preset's display name (display-name uniqueness is NOT
        # enforced at activation, so this is reachable).
        holder = create_object(PlayerCharacter, key="悠花")
        holder.location = self.hall
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
        )
        self.assertEqual(companion.key, f"悠花-{companion.pk}")
        self.assertEqual(
            companion.db.portrait_policy,
            {"mode": "named", "stable_key": str(companion.pk)},
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_the_builder_writes_no_affinity_party_or_player_state(self):
        party_before = self.owner.db.party
        companion = build_starting_companion(
            self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
        )
        self.assertIsNone(companion.db.relations_data)
        self.assertEqual(companion.relations.affinity_for(self.owner), 0)
        self.assertIsNone(companion.db.party_member)
        self.assertEqual(self.owner.db.party, party_before)

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_a_failure_mid_build_leaves_no_persisted_companion(self):
        # A late mechanical step (imported at the builder's top level) fails
        # after the object exists: the compensation must delete it and re-raise.
        with patch(
            "world.rules.starting_companions.ensure_npc_canonical_age",
            side_effect=RuntimeError("simulated write failure"),
        ):
            with self.assertRaises(RuntimeError):
                build_starting_companion(
                    self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
                )
        self.assertFalse(ObjectDB.objects.filter(db_key="悠花").exists())

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_a_rejected_equipment_toggle_fails_the_build(self):
        card = _probe_preset(
            key="bad_gear_probe",
            display_name="壞裝探測者",
            starting_items=(("knight_platemail", 1),),
            # Declared worn but NOT carried -> ITEM_NOT_HELD rejection.
            starting_equipment=("apothecary_beads",),
        )
        PLAYER_PRESET_REGISTRY["bad_gear_probe"] = card
        self.addCleanup(PLAYER_PRESET_REGISTRY.pop, "bad_gear_probe", None)
        with self.assertRaisesRegex(StartingCompanionError, "was rejected"):
            build_starting_companion(
                self.owner, StartingCompanion("bad_gear_probe", 40, "夥伴")
            )
        self.assertFalse(
            ObjectDB.objects.filter(db_key="壞裝探測者").exists()
        )

    @covers_requirement("starting-companions::a-companion-is-built-from-its-partner-preset-as-a-live-llmnpc")
    def test_an_owner_without_location_raises_before_any_object_exists(self):
        self.owner.location = None
        before = ObjectDB.objects.count()
        with self.assertRaisesRegex(StartingCompanionError, "no location"):
            build_starting_companion(
                self.owner, StartingCompanion(_YUKA, 95, "雙胞胎姊姊")
            )
        self.assertEqual(ObjectDB.objects.count(), before)


class CompanionBoundsSweepRegistration(_BuilderCase):
    """The sweep is a real import-time gate, not a dormant helper."""

    @covers_requirement("starting-companions::a-preset-declares-its-starting-companions-by-partner-preset-key")
    def test_importing_the_module_sweeps_the_shipped_registry(self):
        # Re-running the module-bottom sweep must be clean on the shipped
        # registry, and the twins sit at exactly the seeded affinity bound
        # family the sweep protects (95 <= NATURAL_CAP).
        _validate_preset_companion_bounds(PLAYER_PRESET_REGISTRY)
        for preset in (PLAYER_PRESET_REGISTRY[_YUNA], PLAYER_PRESET_REGISTRY[_YUKA]):
            for declaration in preset.starting_companions:
                self.assertEqual(declaration.affinity, 95)
