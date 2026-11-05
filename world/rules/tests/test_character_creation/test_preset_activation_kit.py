"""Slice of ``test_character_creation``: CharacterActivationTests,
PresetActivationCommittedReloadTests."""
from django.test import TransactionTestCase
from tools.spec_traceability import covers_requirement
from copy import deepcopy
import inspect
from inspect import signature
from dataclasses import replace
from unittest.mock import patch
import unittest
from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from world.lore.races import StatModifiers
from world.lore.starting_kits import SubraceStartingKit
from world.lore.sex import DEFAULT_SEX
from typeclasses.rooms import Room
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
from world.skills.equipment import EquipmentSlot
from world.tests.synthetic_data import (
    SYNTH_ITEMS,
    SYNTH_PRESETS,
    SYNTH_RACES,
    SYNTH_SKILLS,
    SYNTH_SUBRACES,
    StaticBand,
    Vitals,
    _SYNTH_ELEMENT,
    make_element,
    make_item,
    make_race,
    make_preset,
    make_subrace,
    make_skill,
    synthetic_registries,
)
from world.skills.registry import SkillPrerequisite
from world.rules.tests._combat_session_helpers import (
    live_skill_registry,
    open_synthetic_scope,
)

from ._support import (
    _BEADS_ROW,
    _DEEP_PRESET,
    _LINEAGE_SKILLS,
    _NEUTRAL_WEAPON,
    _PACK_TRINKET,
    _PLATEMAIL_ROW,
    _STRONG_BORN,
    _STRONG_FOLK,
    _edge_xp,
    _kit_inventory,
    _live_presets,
    _race_key,
    balanced_allocations,
)


@synthetic_registries(
    "races",
    "static_tiers",
    "subraces",
    "starting_kits",
    "presets",
    "skills",
    "items",
    "prices",
    "elements",
    extra={
        "races": {_STRONG_FOLK.key: _STRONG_FOLK},
        "subraces": {_STRONG_BORN.key: _STRONG_BORN},
        "starting_kits": {
            _STRONG_BORN.key: SubraceStartingKit(
                _STRONG_BORN.key, (("t_thorn_knife", 1),)
            )
        },
        "skills": _LINEAGE_SKILLS,
        "presets": {_DEEP_PRESET.key: _DEEP_PRESET},
        "items": {
            _PLATEMAIL_ROW.key: _PLATEMAIL_ROW,
            _BEADS_ROW.key: _BEADS_ROW,
            _NEUTRAL_WEAPON.key: _NEUTRAL_WEAPON,
            _PACK_TRINKET.key: _PACK_TRINKET,
        },
    },
)
@patch.dict(
    "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
    {"t_duskmari": 2, "t_strong_folk": 1},
    clear=True,
)
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
            "race": _race_key(),
            "subrace": next(iter(SYNTH_SUBRACES)),
            "allocations": balanced_allocations(_race_key(), next(iter(SYNTH_SUBRACES))),
        }
        values.update(overrides)
        return CharacterCreationRequest(**values)

    @covers_requirement(
        "player-stat-allocation::player-starting-profiles-are-derived-from-immutable-lore-bands",
        "player-stat-allocation::custom-starting-stats-require-one-exact-finite-allocation-budget",
    )
    def test_preset_activation_fixes_magic_power_deterministically(self):
        # The retired race-average sampler is replaced by the preset's own
        # allocation: the value is the scoped profile's static floor plus the
        # card's magic_power allocation (mechanics, not a shipped number).
        card = SYNTH_PRESETS["t_pale_wren"]
        # The card declares a starting companion, which spawns at the
        # shell's location (preset-companion-activation).
        self.character.location = self.room1
        result = activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key=card.key),
        )
        floor = resolve_starting_profile(card.race, card.subrace).bounds_dict()["magic_power"][0]
        self.assertEqual(result.magic_power, floor + dict(card.allocations)["magic_power"])
        self.assertEqual(self.character.race, card.race)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_preset_activation_grants_the_declared_skill_kit(self):
        # The deep card's closure-added keys are covered by the dedicated
        # close/order tests; parity here is declared-state equality.
        for preset_key in sorted(set(SYNTH_PRESETS) - {_DEEP_PRESET.key}):
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
                    _live_presets()[preset_key].skill_lists(),
                )
                self.assertFalse(character.creation_pending)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_preset_activation_closes_the_deep_kit(self):
        # The in-scope deep card declares only the tree's crown: activation
        # closes the chain (closure-added keys AFTER the declared ones),
        # seeds each unsatisfied edge to exactly its threshold, and clears
        # the preset-mode creation draft in the same transaction.
        character = create_object(PlayerCharacter, key="shell-lineage-close")
        self.account.at_post_create_character(character)
        character.location = self.room1
        character.db.creation_draft = {
            "mode": "preset", "stage": "preset_selected",
            "preset_key": _DEEP_PRESET.key,
        }
        activate_player_character(
            self.account, character,
            CharacterCreationRequest(mode="preset", preset_key=_DEEP_PRESET.key),
        )
        self.assertEqual(
            character.db.skills,
            {
                "active": ["t_rite_crown", "t_rite_mid"],
                "passive": ["t_rite_root"],
            },
        )
        self.assertEqual(
            character.db.skill_proficiency,
            {
                "t_rite_root": _edge_xp(3),
                "t_rite_mid": _edge_xp(3),
            },
        )
        self.assertFalse(character.attributes.has("creation_draft"))
        self.assertFalse(character.creation_pending)

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_every_in_scope_preset_declared_active_skill_is_usable_after_activation(self):
        # Scenario coverage for every card in the scoped registry: after
        # closure + seed, can_use_skill passes for every declared active key.
        from world.rules.progression import can_use_skill

        registry = live_skill_registry()
        for preset_key, preset in _live_presets().items():
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
                        self.assertTrue(can_use_skill(character, registry[skill_key]))

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_custom_activation_writes_empty_skills_and_proficiency(self):
        # Custom mode grants no skills, so the closure and seed are no-ops.
        activate_player_character(self.account, self.character, self.request())
        self.assertEqual(self.character.db.skills, {"active": [], "passive": []})
        self.assertEqual(dict(self.character.db.skill_proficiency or {}), {})

    def _synthetic_preset(self, key, **overrides):
        from world.lore.player_presets import PlayerPreset

        race_key = _race_key()
        subrace_key = next(iter(SYNTH_SUBRACES))
        values = dict(
            key=key, display_name=f"合成{key}", age=20, apparent_age=20,
            race=race_key, subrace=subrace_key,
            allocations=tuple(balanced_allocations(race_key, subrace_key).items()),
            emphasis="測試", sex="female",
        )
        values.update(overrides)
        return PlayerPreset(**values)

    def _activate_synthetic_preset(self, preset, shell_key):
        """Activate a registry-patched synthetic preset on a fresh shell."""
        character = create_object(PlayerCharacter, key=shell_key)
        self.account.at_post_create_character(character)
        with synthetic_registries("presets", extra={"presets": {preset.key: preset}}):
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=preset.key),
            )
        return character

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_declared_proficiency_below_the_seed_survives_activation(self):
        # Scenario "A declared proficiency beats the auto-seed": 120 XP is
        # level 2, below the >= 3 edge; the seed must not overwrite the
        # declared value -- while the seed still runs for every OTHER
        # unsatisfied edge of the closed chain.
        preset = self._synthetic_preset(
            "t_lineage_declared",
            active_skills=("t_rite_crown",),
            skill_proficiency=(("t_rite_mid", 120.0),),
        )
        character = self._activate_synthetic_preset(
            preset, "shell-lineage-declared"
        )
        self.assertEqual(
            character.db.skill_proficiency,
            {
                "t_rite_mid": 120.0,  # declared wins, below the edge
                "t_rite_root": _edge_xp(3),  # the seed still runs
            },
        )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_declared_keys_keep_order_and_closure_added_keys_follow(self):
        # Declared (hush mend, cinder cleave) keeps its order; the
        # closure-added root (sorted registry order) follows the declared
        # ones, and a declared passive stays last.
        preset = self._synthetic_preset(
            "t_lineage_order",
            active_skills=("t_rite_mid", "t_rite_crown"),
            passive_skills=("t_steady_stride",),
        )
        character = self._activate_synthetic_preset(preset, "shell-lineage-order")
        self.assertEqual(
            character.db.skills,
            {
                "active": ["t_rite_mid", "t_rite_crown"],  # declared order
                "passive": [
                    "t_steady_stride",  # declared
                    "t_rite_root",  # closure-added passive follows
                ],
            },
        )

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-starting-inventory")
    def test_preset_activation_grants_the_declared_starting_inventory(self):
        for preset_key in sorted(_live_presets()):
            with self.subTest(preset_key=preset_key):
                character = create_object(PlayerCharacter, key=f"kit-shell-{preset_key}")
                self.account.at_post_create_character(character)
                character.location = self.room1
                activate_player_character(
                    self.account, character,
                    CharacterCreationRequest(mode="preset", preset_key=preset_key),
                )
                expected = _live_presets()[preset_key].inventory_list()
                self.assertEqual(character.db.inventory, expected)
                self.assertGreater(len(expected), 0)

    @covers_requirement("player-character-creation::custom-activation-grants-the-chosen-subrace-s-basic-starting-kit")
    def test_custom_activation_grants_each_subrace_starting_kit(self):
        for subrace_key, subrace in SYNTH_SUBRACES.items():
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
                self.assertEqual(
                    character.db.inventory, _kit_inventory(subrace_key)
                )
                self.assertGreater(len(character.db.inventory), 0)
                self.assertFalse(character.creation_pending)


@synthetic_registries(
    "races",
    "static_tiers",
    "subraces",
    "starting_kits",
    "presets",
    "skills",
    "items",
    "prices",
    "elements",
)
@patch.dict(
    "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
    {"t_duskmari": 2, "t_strong_folk": 1},
    clear=True,
)
class PresetActivationCommittedReloadTests(TransactionTestCase):
    """Real construction, closure/mastery and committed-reload evidence.

    ``TransactionTestCase`` (the base ``EquipmentGrowthCommittedReloadTests``
    also chooses) because this probe exists to observe committed state: the
    atomic ``TestCase`` wrapper would hide whether the reads came from storage
    at all.
    """

    def setUp(self):
        # A wilderness-entering test in the same worker leaves ndb-stamped
        # rows cached that Evennia's non-forced teardown flush cannot evict;
        # creating a character then resolves its home through the ghost and
        # writes a dangling reference. Same documented remedy as
        # ``WildernessDefeatMixin``.
        from evennia.objects.models import ObjectDB

        ObjectDB.flush_instance_cache(force=True)
        super().setUp()
        self.room = create_object(Room, key="preset_reload_room")
        self.account = create_account(
            "reload-owner", "reload-owner@example.test", "testpassword",
            typeclass=Account,
        )

    def _card(self, key, **overrides):
        from world.lore.player_presets import PlayerPreset

        race_key = _race_key()
        subrace_key = next(iter(SYNTH_SUBRACES))
        values = dict(
            key=key, display_name=f"合成{key}", age=20, apparent_age=20,
            race=race_key, subrace=subrace_key,
            allocations=tuple(balanced_allocations(race_key, subrace_key).items()),
            emphasis="測試", sex="female",
        )
        values.update(overrides)
        return PlayerPreset(**values)

    def _reread(self, character):
        """Return a freshly loaded instance of one committed character row.

        Both idmapper caches are force-evicted -- ``ObjectDB`` (an
        NAttribute-holding object refuses the soft flush) and ``Attribute``,
        where skills and proficiency live -- so every observation below reads
        storage rather than the activating process's own handler state.
        """
        from evennia.objects.models import ObjectDB
        from evennia.typeclasses.attributes import Attribute

        for model in (ObjectDB, Attribute):
            model.flush_instance_cache(force=True)
        fresh = PlayerCharacter.objects.get(pk=character.pk)
        self.assertIsNot(fresh, character)
        return fresh

    @covers_requirement("player-character-creation::preset-activation-grants-the-preset-s-declared-skill-kit")
    def test_mastery_card_activation_survives_a_committed_reload(self):
        # The card declares only an elemental mastery: activation must close
        # the element's tree, seed the terminal row to exactly its edge, keep
        # the mastery itself usable (its freeform entitlement), store the
        # resolver's own trait values literally, and leave a never-activated
        # control character untouched -- all observed after a committed
        # re-read.
        from world.rules.progression import can_use_skill, freeform_ladder_for

        registry = live_skill_registry()
        mastery = registry["t_glowmire_mastery"]
        bloom = registry["t_glowmire_bloom"]
        card = self._card("t_reload_mastery", passive_skills=(mastery.key,))

        control = create_object(
            PlayerCharacter, key="reload-control", location=self.room
        )
        self.account.at_post_create_character(control)
        control.race = _race_key()
        control.apply_race_baseline()
        control_before = {
            # A detached snapshot: the live attribute value could be mutated
            # in place by a later write, which would silently rewrite the
            # "before" side of the comparison.
            "skills": deepcopy(control.db.skills),
            "proficiency": dict(control.db.skill_proficiency or {}),
            "traits": {axis: control.traits[axis].base for axis in ALLOCATABLE_AXES},
        }

        character = create_object(
            PlayerCharacter, key="reload-shell", location=self.room
        )
        self.account.at_post_create_character(character)
        with synthetic_registries("presets", extra={"presets": {card.key: card}}):
            activate_player_character(
                self.account, character,
                CharacterCreationRequest(mode="preset", preset_key=card.key),
            )

        fresh = self._reread(character)
        expected = resolve_preset_values(card)
        for axis in ALLOCATABLE_AXES:
            self.assertEqual(fresh.traits[axis].base, expected[axis], msg=axis)
        self.assertIn(bloom.key, fresh.db.skills["active"])
        self.assertIn(mastery.key, fresh.db.skills["passive"])
        self.assertEqual(
            fresh.db.skill_proficiency[bloom.key],
            _edge_xp(mastery.prerequisites[0].min_proficiency),
        )
        self.assertTrue(can_use_skill(fresh, mastery))
        self.assertTrue(freeform_ladder_for(fresh, bloom))

        # The control character is re-read from storage too, so "untouched"
        # is observed on committed state rather than on the writer's own
        # handler caches.
        fresh_control = self._reread(control)
        self.assertEqual(fresh_control.db.skills, control_before["skills"])
        self.assertEqual(
            dict(fresh_control.db.skill_proficiency or {}),
            control_before["proficiency"],
        )
        for axis in ALLOCATABLE_AXES:
            self.assertEqual(
                fresh_control.traits[axis].base,
                control_before["traits"][axis],
                msg=axis,
            )
