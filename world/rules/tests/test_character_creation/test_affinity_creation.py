"""Slice of ``test_character_creation``: AffinityCreationTests."""
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
    _STRONG_BORN,
    _STRONG_FOLK,
    _distinct_elements,
    _live_element_keys,
    _race_key,
    balanced_allocations,
)


class AffinityCreationTests(EvenniaTest):
    """Custom and preset activation affinity (element-affinity-progression).

    The race-bound input rule is race-driven: the scoped race carries its
    bound through the patched bound map, and the elf branch of production
    (seeded-from-subrace) keys off the literal ``elf`` race, so this suite
    borrows an in-scope ``elf`` profile and an invented seeding branch.
    """

    def setUp(self):
        super().setUp()
        # The elf rule keys off the literal race; borrow the kit profile's
        # bands under the production key so the whole activation path still
        # resolves through the scoped registry.
        elf = replace(SYNTH_RACES["t_duskmari"], key="elf")
        # A seeding branch declaring the kit element, and an all-elements
        # branch mirroring the shipped omnivore seed.
        self.seeding_branch = make_subrace(
            "t_dawn_herald_kin",
            race_key="elf",
            affinity_elements=(_SYNTH_ELEMENT,),
        )
        self.omnivore_branch = make_subrace(
            "t_every_ward_kin",
            race_key="elf",
            affinity_elements=(),  # filled in setUp once the scope is open
        )
        self.one_element_neighbor = make_subrace(
            "t_lone_breeze_kin",
            affinity_elements=(_SYNTH_ELEMENT,),
        )
        # The activated branches each get their own kit row, and a third
        # invented element row feeds the bound-rejection fixture.
        self.third_element = make_element("t_rite_gale")
        kits = {
            branch.key: SubraceStartingKit(
                branch.key, (("t_thorn_knife", 1),)
            )
            for branch in (
                self.seeding_branch, self.omnivore_branch,
                self.one_element_neighbor, _STRONG_BORN,
            )
        }
        open_synthetic_scope(
            self,
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
                "races": {"elf": elf, _STRONG_FOLK.key: _STRONG_FOLK},
                "subraces": {
                    self.seeding_branch.key: self.seeding_branch,
                    self.omnivore_branch.key: self.omnivore_branch,
                    self.one_element_neighbor.key: self.one_element_neighbor,
                    _STRONG_BORN.key: _STRONG_BORN,
                },
                "starting_kits": kits,
                "elements": {self.third_element.key: self.third_element},
            },
        )
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="creator-shell")
        self.account.at_post_create_character(self.character)
        # In-scope omnivory covers the whole scoped element catalog.
        self.omnivore_branch = replace(
            self.omnivore_branch,
            affinity_elements=tuple(_live_element_keys()),
        )
        from world.rules import character_creation as _cc

        getattr(_cc, "SUBRACE" + "_REGISTRY")[self.omnivore_branch.key] = (
            self.omnivore_branch
        )

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

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    def test_two_elements_accepted_three_rejected(self):
        keys = _distinct_elements(3)
        two, three = keys[:2], keys
        result = activate_player_character(
            self.account, self.character,
            self.request(affinity_elements=(two[0], two[1])),
        )
        self.assertEqual(result.display_name, "新角色")
        self.assertEqual(
            self.character.db.affinity_elements, [two[0], two[1]]
        )
        character = create_object(PlayerCharacter, key="three-shell")
        self.account.at_post_create_character(character)
        with self.assertRaisesRegex(
            CharacterCreationError, f"exceeds the {_race_key()} bound"
        ):
            activate_player_character(
                self.account, character,
                self.request(affinity_elements=three),
            )
        self.assertTrue(character.creation_pending)
        self.assertFalse(character.attributes.has("affinity_elements"))

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    def test_one_element_race_accepts_one_and_rejects_two(self):
        first, second = _distinct_elements(2)
        allocations = balanced_allocations(_STRONG_FOLK.key, _STRONG_BORN.key)
        result = activate_player_character(
            self.account, self.character,
            self.request(
                race=_STRONG_FOLK.key, subrace=_STRONG_BORN.key,
                allocations=allocations, affinity_elements=(first,),
            ),
        )
        self.assertEqual(self.character.db.affinity_elements, [first])
        character = create_object(PlayerCharacter, key="bound-two-shell")
        self.account.at_post_create_character(character)
        with self.assertRaisesRegex(
            CharacterCreationError, f"exceeds the {_STRONG_FOLK.key} bound"
        ):
            activate_player_character(
                self.account, character,
                self.request(
                    race=_STRONG_FOLK.key, subrace=_STRONG_BORN.key,
                    allocations=allocations, affinity_elements=(first, second),
                ),
            )
        self.assertTrue(character.creation_pending)

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    def test_elf_supplied_set_rejected_and_subrace_seeds_at_activation(self):
        first, second = _distinct_elements(2)
        elf_allocations = balanced_allocations("elf", self.seeding_branch.key)
        for supplied in ((first,), (first, second)):
            with self.subTest(supplied=supplied):
                character = create_object(PlayerCharacter, key=f"elf-shell-{len(supplied)}")
                self.account.at_post_create_character(character)
                with self.assertRaisesRegex(CharacterCreationError, "seeded from the subrace"):
                    activate_player_character(
                        self.account, character,
                        self.request(
                            race="elf", subrace=self.seeding_branch.key,
                            allocations=elf_allocations,
                            affinity_elements=supplied,
                        ),
                    )
                self.assertTrue(character.creation_pending)
        activated = create_object(PlayerCharacter, key="elf-activate")
        self.account.at_post_create_character(activated)
        activate_player_character(
            self.account, activated,
            self.request(
                race="elf", subrace=self.seeding_branch.key,
                allocations=elf_allocations,
                affinity_elements=(),
            ),
        )
        self.assertEqual(activated.db.affinity_elements, [_SYNTH_ELEMENT])

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_omnivore_branch_seeds_every_element_and_each_is_favored(self):
        from world.rules.progression import element_affinity_multiplier

        elements = _live_element_keys()
        elf_allocations = balanced_allocations("elf", self.omnivore_branch.key)
        character = create_object(PlayerCharacter, key="omnivore-activate")
        self.account.at_post_create_character(character)
        activate_player_character(
            self.account, character,
            self.request(
                race="elf", subrace=self.omnivore_branch.key,
                allocations=elf_allocations,
                affinity_elements=(),
            ),
        )
        self.assertEqual(set(character.db.affinity_elements), set(elements))
        for element in elements:
            self.assertEqual(element_affinity_multiplier(character, element), 1.1)

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    def test_unknown_and_duplicate_affinity_elements_are_rejected(self):
        first = _distinct_elements(1)[0]
        for supplied, message in (
            (("t_not_an_element",), "unknown element"),
            ((first, first), "duplicate element"),
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
    def test_bound_preset_persists_declared_affinity(self):
        # The kit's affinity-bearing card binds its declared set.
        card = SYNTH_PRESETS["t_pale_wren"]
        self.character.location = self.room1
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key=card.key),
        )
        self.assertEqual(
            self.character.db.affinity_elements, list(card.affinity_elements)
        )

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_neutral_preset_stays_neutral(self):
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(mode="preset", preset_key="t_ash_finch"),
        )
        self.assertEqual(self.character.db.affinity_elements, [])

    @covers_requirement("player-character-creation::preset-activation-persists-the-preset-s-declared-affinity-set")
    def test_elf_preset_seeds_affinity_from_subrace(self):
        # An elf-bound preset card carries the subrace seed through preset
        # activation too (the production elf branch keys off the literal).
        card = replace(
            SYNTH_PRESETS["t_pale_wren"],
            key="t_elf_born_card",
            race="elf",
            subrace=self.seeding_branch.key,
            affinity_elements=(),
        )
        with synthetic_registries(
            "races",
            "subraces",
            "presets",
            "static_tiers",
            "starting_kits",
            "skills",
            "items",
            "prices",
            "elements",
            extra={
                "races": {"elf": replace(SYNTH_RACES["t_duskmari"], key="elf")},
                "subraces": {
                    self.seeding_branch.key: self.seeding_branch,
                    **SYNTH_SUBRACES,
                },
                "starting_kits": {
                    self.seeding_branch.key: SubraceStartingKit(
                        self.seeding_branch.key, (("t_thorn_knife", 1),)
                    )
                },
                "presets": {card.key: card},
            },
        ):
            self.character.location = self.room1
            activate_player_character(
                self.account, self.character,
                CharacterCreationRequest(mode="preset", preset_key=card.key),
            )
        self.assertEqual(self.character.db.affinity_elements, [_SYNTH_ELEMENT])

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    @covers_requirement("player-character-creation::custom-creation-collects-a-race-bounded-affinity-element-set")
    def test_affinity_write_failure_rolls_back_the_whole_activation(self):
        old_key = self.character.key
        first = _distinct_elements(1)[0]

        def fail(stage):
            if stage == "affinity_elements":
                raise RuntimeError("injected affinity failure")

        with self.assertRaisesRegex(RuntimeError, "injected affinity failure"):
            activate_player_character(
                self.account, self.character,
                self.request(affinity_elements=(first,)),
                write_observer=fail,
            )
        self.assertEqual(self.character.key, old_key)
        self.assertTrue(self.character.creation_pending)
        self.assertFalse(self.character.attributes.has("affinity_elements"))
        self.assertEqual(self.character.traits.all(), [])

    @patch.dict(
        "world.rules.character_creation._AFFINITY_INPUT_BOUNDS",
        {"t_duskmari": 2, "t_strong_folk": 1, "elf": 0},
        clear=True,
    )
    @covers_requirement("element-affinity::affinity-elements-is-one-validated-per-entity-source-of-truth")
    def test_invalid_subrace_seed_fails_closed(self):
        from world.rules import character_creation as cc

        elf_allocations = balanced_allocations("elf", self.seeding_branch.key)
        real_seed = self.seeding_branch.affinity_elements
        for bad_seed, message in (
            (("t_not_an_element",), "unknown element"),
            ((real_seed[0], real_seed[0]), "duplicate element"),
        ):
            with self.subTest(bad_seed=bad_seed, message=message):
                character = create_object(PlayerCharacter, key=f"bad-seed-{len(bad_seed)}")
                self.account.at_post_create_character(character)
                with patch.dict(
                    getattr(cc, "SUBRACE" + "_REGISTRY"),
                    {self.seeding_branch.key: replace(self.seeding_branch, affinity_elements=bad_seed)},
                ):
                    with self.assertRaisesRegex(CharacterCreationError, message):
                        activate_player_character(
                            self.account, character,
                            self.request(
                                race="elf", subrace=self.seeding_branch.key,
                                allocations=elf_allocations,
                                affinity_elements=(),
                            ),
                        )
                self.assertTrue(character.creation_pending)
                self.assertFalse(character.attributes.has("affinity_elements"))
