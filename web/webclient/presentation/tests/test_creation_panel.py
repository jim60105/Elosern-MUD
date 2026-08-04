"""Exact ``creation`` schema, presenter, and isolation tests.

Covers the D2 shared bounds, the version-1 payload validation, deterministic
preset/profile ordering, the draft shape for both stages, the worst-case
envelope size, the all-ceilings byte gate, and the isolation of a corrupt
draft and non-creation modes.
"""

from tools.spec_traceability import covers_requirement

from copy import deepcopy
import unittest

from evennia.utils.create import create_account, create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.accounts import Account
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.rooms import Room
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.creation import (
    AGE_MAXIMUM,
    AGE_MINIMUM,
    APPARENT_AGE_MAXIMUM,
    APPARENT_AGE_MINIMUM,
    CREATION_SCHEMA_VERSION,
    CreationPanelError,
    MAX_BACKGROUND_CODE_POINTS,
    MAX_DESCRIPTION_CODE_POINTS,
    MAX_DISPLAY_NAME_CODE_POINTS,
    MAX_EMPHASIS_CODE_POINTS,
    MAX_EXPLANATION_CODE_POINTS,
    MAX_LABEL_CODE_POINTS,
    MAX_NAME_LENGTH,
    MAX_PRESET_KEY_CODE_POINTS,
    MAX_PRESETS,
    MAX_PROFILES,
    MAX_RACES,
    MAX_RACE_KEY_CODE_POINTS,
    MAX_SPECIALTY_CODE_POINTS,
    MAX_SUBRACES,
    MAX_SUBRACE_KEY_CODE_POINTS,
    MIN_NAME_LENGTH,
    validate_creation,
)
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    json_byte_size,
)
from web.webclient.presentation.registry import (
    build_production_registry,
)
from world.rules.character_creation import resolve_starting_profile
from world.rules.creation_wizard import (
    ALLOCATABLE_AXES,
    CreationView,
    build_custom_form,
    build_preset_cards,
)


def _valid_payload(draft=None, custom=None, presets=None):
    """A schema-valid creation payload derived from the immutable registries."""
    view = CreationView(
        presets=build_preset_cards() if presets is None else presets,
        custom=build_custom_form() if custom is None else custom,
        draft=draft,
    )
    from web.webclient.presentation.creation import _serialize

    return _serialize(view)


def _set_presets_count(count):
    cards = list(build_preset_cards())
    filler = cards[0]
    while len(cards) < count:
        cards.append(filler)
    return tuple(cards)


class CreationPanelValidationTests(unittest.TestCase):
    """Pure payload-validation tests for every bound in D2."""

    def test_valid_realistic_payload_round_trips(self):
        payload = _valid_payload()
        validated = validate_creation(payload)
        self.assertEqual(validated["schema_version"], CREATION_SCHEMA_VERSION)
        self.assertTrue(validated["available"])
        self.assertEqual(validated["kind"], "creation")
        self.assertIsNone(validated["draft"])
        self.assertEqual(len(validated["presets"]), 3)
        self.assertEqual(
            [card["key"] for card in validated["presets"]],
            ["human_wanderer", "foxkin_scout", "elf_guardian"],
        )

    @covers_requirement("webclient-character-creation-ui::creation-presentation-derives-finite-controls-from-immutable-registries")
    def test_deterministic_preset_and_profile_ordering(self):
        payload = validate_creation(_valid_payload())
        self.assertEqual(
            [card["key"] for card in payload["presets"]],
            ["human_wanderer", "foxkin_scout", "elf_guardian"],
        )
        profile_keys = [(p["race"], p["subrace"]) for p in payload["custom"]["profiles"]]
        self.assertEqual(profile_keys[0], ("human", None))
        self.assertEqual(profile_keys[1], ("beastfolk", None))
        self.assertIn(("elf", "fionnen"), profile_keys)
        self.assertEqual(
            [axis["axis"] for axis in payload["custom"]["profiles"][0]["axes"]],
            list(ALLOCATABLE_AXES),
        )

    def test_schema_version_kind_and_availability_discriminators(self):
        for mutate, label in (
            (lambda p: p.update(schema_version=2), "schema_version"),
            (lambda p: p.update(available=False), "available"),
            (lambda p: p.update(kind="services"), "kind"),
        ):
            with self.subTest(label=label):
                payload = _valid_payload()
                mutate(payload)
                with self.assertRaises(CreationPanelError):
                    validate_creation(payload)

    def test_preset_card_bounds(self):
        with self.assertRaises(Exception):
            validate_creation(_valid_payload(presets=_set_presets_count(MAX_PRESETS + 1)))
        base = _valid_payload()
        base["presets"] = base["presets"][:1]
        card = base["presets"][0]
        with self.subTest("key"):
            card["key"] = "x" * (MAX_PRESET_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))
        card["key"] = "human_wanderer"
        with self.subTest("display_name"):
            card["display_name"] = "x" * (MAX_DISPLAY_NAME_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))
        card["display_name"] = "艾琳"
        with self.subTest("race"):
            card["race"] = "x" * (MAX_RACE_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))
        card["race"] = "human"
        with self.subTest("race_description"):
            card["race_description"] = "x" * (MAX_DESCRIPTION_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))
        card["race_description"] = "描述"
        with self.subTest("emphasis"):
            card["emphasis"] = "x" * (MAX_EMPHASIS_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))
        card["emphasis"] = "配點"
        with self.subTest("background"):
            card["background"] = "x" * (MAX_BACKGROUND_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))

    def test_preset_card_unknown_field_rejected(self):
        payload = _valid_payload()
        payload["presets"][0]["persona"] = "forbidden"
        with self.assertRaises(Exception):
            validate_creation(payload)

    def test_name_and_adult_bounds_are_exact(self):
        for mutate, label in (
            (lambda c: c["name"].update(min_length=0), "min_length"),
            (lambda c: c["name"].update(max_length=81), "max_length"),
            (lambda c: c["adult"].update(age_minimum=17), "age_minimum"),
            (lambda c: c["adult"].update(age_maximum=10001), "age_maximum"),
            (lambda c: c["adult"].update(apparent_age_minimum=17), "apparent_age_minimum"),
            (lambda c: c["adult"].update(apparent_age_maximum=10001), "apparent_age_maximum"),
        ):
            with self.subTest(label=label):
                payload = _valid_payload()
                mutate(payload["custom"])
                with self.assertRaises(Exception):
                    validate_creation(payload)
        payload = _valid_payload()
        self.assertEqual(payload["custom"]["name"]["min_length"], MIN_NAME_LENGTH)
        self.assertEqual(payload["custom"]["name"]["max_length"], MAX_NAME_LENGTH)
        self.assertEqual(payload["custom"]["adult"]["age_minimum"], AGE_MINIMUM)
        self.assertEqual(payload["custom"]["adult"]["age_maximum"], AGE_MAXIMUM)
        self.assertEqual(
            payload["custom"]["adult"]["apparent_age_minimum"], APPARENT_AGE_MINIMUM
        )
        self.assertEqual(
            payload["custom"]["adult"]["apparent_age_maximum"], APPARENT_AGE_MAXIMUM
        )

    def test_race_option_bounds(self):
        payload = _valid_payload()
        with self.subTest("count"):
            races = list(payload["custom"]["races"])
            while len(races) < MAX_RACES + 1:
                races.append(races[0])
            payload["custom"]["races"] = races
            with self.assertRaises(Exception):
                validate_creation(payload)
        payload = _valid_payload()
        race = payload["custom"]["races"][0]
        with self.subTest("key"):
            race["key"] = "x" * (MAX_RACE_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        race["key"] = "human"
        with self.subTest("description"):
            race["description"] = "x" * (MAX_DESCRIPTION_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        race["description"] = "描述"
        with self.subTest("subraces-not-list"):
            race["subraces"] = "fionnen"
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        race["subraces"] = ["fionnen", "x" * (MAX_SUBRACE_KEY_CODE_POINTS + 1)]
        with self.subTest("subrace-key-bound"):
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))

    def test_subraces_map_bounds(self):
        payload = _valid_payload()
        with self.subTest("count"):
            subraces = dict(payload["custom"]["subraces"])
            filler = subraces[next(iter(subraces))]
            while len(subraces) < MAX_SUBRACES + 1:
                subraces["extra" + str(len(subraces))] = filler
            payload["custom"]["subraces"] = subraces
            with self.assertRaises(Exception):
                validate_creation(payload)
        payload = _valid_payload()
        entry = payload["custom"]["subraces"]["fionnen"]
        with self.subTest("display_name_zh"):
            entry["display_name_zh"] = "x" * (MAX_SPECIALTY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        entry["display_name_zh"] = "斐歐恩族"
        with self.subTest("specialty"):
            entry["specialty"] = "x" * (MAX_SPECIALTY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))

    def test_profile_bounds(self):
        payload = _valid_payload()
        with self.subTest("count"):
            profiles = list(payload["custom"]["profiles"])
            while len(profiles) < MAX_PROFILES + 1:
                profiles.append(profiles[0])
            payload["custom"]["profiles"] = profiles
            with self.assertRaises(Exception):
                validate_creation(payload)
        payload = _valid_payload()
        profile = payload["custom"]["profiles"][0]
        with self.subTest("race"):
            profile["race"] = "x" * (MAX_RACE_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        profile["race"] = "human"
        with self.subTest("subrace"):
            profile["subrace"] = "x" * (MAX_SUBRACE_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        profile["subrace"] = None
        with self.subTest("axes-count"):
            profile["axes"] = profile["axes"][:5]
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        profile["axes"] = [dict(axis) for axis in profile["axes"]]  # 6 again
        with self.subTest("axis-unknown"):
            profile["axes"][0]["axis"] = "luck"
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        profile["axes"][0]["axis"] = "hp"
        with self.subTest("label"):
            profile["axes"][0]["label"] = "x" * (MAX_LABEL_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        profile["axes"][0]["label"] = "生命值"
        with self.subTest("explanation"):
            profile["axes"][0]["explanation"] = "x" * (MAX_EXPLANATION_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        profile["axes"][0]["explanation"] = "說明"
        with self.subTest("minimum-greater-maximum"):
            profile["axes"][0]["minimum"] = 10
            profile["axes"][0]["maximum"] = 5
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))

    def test_profile_budget_matches_resolve_starting_profile(self):
        payload = validate_creation(_valid_payload())
        for profile in payload["custom"]["profiles"]:
            resolved = resolve_starting_profile(profile["race"], profile["subrace"])
            self.assertEqual(profile["budget"], resolved.budget)
            for axis in profile["axes"]:
                bound = resolved.bounds_dict()[axis["axis"]]
                self.assertEqual((axis["minimum"], axis["maximum"]), (0, bound[1] - bound[0]))

    def test_draft_preset_stage_shape(self):
        draft = {"mode": "preset", "stage": "preset_selected", "preset_key": "human_wanderer"}
        payload = _valid_payload(draft=draft)
        validated = validate_creation(payload)
        self.assertEqual(validated["draft"]["preset_key"], "human_wanderer")
        bad = deepcopy(payload)
        bad["draft"]["stage"] = "custom_filled"
        with self.assertRaises(Exception):
            validate_creation(bad)
        bad = deepcopy(payload)
        bad["draft"]["preset_key"] = "x" * (MAX_PRESET_KEY_CODE_POINTS + 1)
        with self.assertRaises(Exception):
            validate_creation(bad)

    def test_draft_custom_stage_shape(self):
        draft = {
            "mode": "custom",
            "stage": "custom_filled",
            "display_name": "新角色",
            "age": 20,
            "apparent_age": 20,
            "race": "human",
            "subrace": None,
            "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
        }
        payload = _valid_payload(draft=draft)
        validated = validate_creation(payload)
        self.assertEqual(validated["draft"]["mode"], "custom")
        bad = deepcopy(payload)
        bad["draft"]["age"] = 17
        with self.assertRaises(Exception):
            validate_creation(bad)
        bad = deepcopy(payload)
        bad["draft"]["allocations"] = {"hp": 0}
        with self.assertRaises(Exception):
            validate_creation(bad)
        bad = deepcopy(payload)
        bad["draft"]["allocations"]["hp"] = 10001
        with self.assertRaises(Exception):
            validate_creation(bad)
        bad = deepcopy(payload)
        bad["draft"]["mode"] = "unknown"
        with self.assertRaises(Exception):
            validate_creation(bad)

    def test_worst_case_realistic_payload_fits_comfortably(self):
        payload = validate_creation(_valid_payload())
        size = json_byte_size(payload)
        self.assertLess(
            size,
            MAX_CANONICAL_JSON_BYTES // 4,
            f"realistic creation payload must be far below the envelope: {size} bytes",
        )

    def test_all_ceilings_payload_is_rejected_by_the_byte_gate(self):
        # Maximize every string field and every count at once. Per-field bounds
        # are ceilings, not a guarantee that combinations fit, so the byte gate
        # must reject the structurally maximal payload.
        def huge(value):
            return "x" * value

        card = {
            "key": "p" * MAX_PRESET_KEY_CODE_POINTS,
            "display_name": huge(MAX_DISPLAY_NAME_CODE_POINTS),
            "race": "r" * MAX_RACE_KEY_CODE_POINTS,
            "race_description": huge(MAX_DESCRIPTION_CODE_POINTS),
            "subrace": "s" * MAX_SUBRACE_KEY_CODE_POINTS,
            "emphasis": huge(MAX_EMPHASIS_CODE_POINTS),
            "background": huge(MAX_BACKGROUND_CODE_POINTS),
        }
        race = {
            "key": "r" * MAX_RACE_KEY_CODE_POINTS,
            "description": huge(MAX_DESCRIPTION_CODE_POINTS),
            "subraces": ["s" * MAX_SUBRACE_KEY_CODE_POINTS] * MAX_SUBRACES,
        }
        subrace_entry = {
            "display_name_zh": huge(MAX_SPECIALTY_CODE_POINTS),
            "common_name_zh": huge(MAX_SPECIALTY_CODE_POINTS),
            "specialty": huge(MAX_SPECIALTY_CODE_POINTS),
        }

        def axes():
            result = []
            for index, axis in enumerate(ALLOCATABLE_AXES):
                # The -1..-0 suffix keeps every label distinct while staying at
                # the exact ceiling so the byte gate, not the label bound, is
                # what rejects this structurally maximal payload.
                entry = {
                    "axis": axis,
                    "label": huge(MAX_LABEL_CODE_POINTS - 1) + str(index),
                    "explanation": huge(MAX_EXPLANATION_CODE_POINTS),
                    "minimum": 0,
                    "maximum": 10000,
                }
                result.append(entry)
            return result

        profile = {
            "race": "r" * MAX_RACE_KEY_CODE_POINTS,
            "subrace": "s" * MAX_SUBRACE_KEY_CODE_POINTS,
            "budget": 999999,
            "axes": axes(),
        }
        payload = {
            "schema_version": 1,
            "available": True,
            "kind": "creation",
            "draft": None,
            "presets": [dict(card) for _ in range(MAX_PRESETS)],
            "custom": {
                "name": {"min_length": 1, "max_length": MAX_NAME_LENGTH},
                "adult": {
                    "age_minimum": AGE_MINIMUM,
                    "age_maximum": AGE_MAXIMUM,
                    "apparent_age_minimum": APPARENT_AGE_MINIMUM,
                    "apparent_age_maximum": APPARENT_AGE_MAXIMUM,
                },
                "races": [dict(race) for _ in range(MAX_RACES)],
                "subraces": {
                    "s%d" % i: dict(subrace_entry) for i in range(MAX_SUBRACES)
                },
                "profiles": [dict(profile) for _ in range(MAX_PROFILES)],
            },
        }
        self.assertGreater(
            json_byte_size(payload),
            MAX_CANONICAL_JSON_BYTES,
            "all-ceilings payload must exceed the envelope to prove the gate",
        )
        with self.assertRaises(CreationPanelError):
            validate_creation(payload)

    @covers_requirement("webclient-character-creation-ui::creation-presentation-derives-finite-controls-from-immutable-registries")
    def test_no_persona_or_import_only_field_is_ever_exposed(self):
        payload = validate_creation(_valid_payload())
        for forbidden in (
            "persona",
            "skills",
            "equipment",
            "inventory",
            "magic_level",
            "import",
            "portrait_ref",
            "age",
            "apparent_age",
        ):
            self.assertNotIn(forbidden, payload)
            self.assertNotIn(forbidden, payload["custom"])
            for card in payload["presets"]:
                self.assertNotIn(forbidden, card)
            for profile in payload["custom"]["profiles"]:
                self.assertNotIn(forbidden, profile)


class CreationPanelPresenterTests(EvenniaTest):
    def setUp(self):
        super().setUp()
        self.account = create_account(
            "creator", "creator@example.test", "testpassword", typeclass=Account
        )
        self.character = create_object(PlayerCharacter, key="pending-shell")
        self.account.at_post_create_character(self.character)
        self.registry = build_production_registry()
        self.context = PresentationContext(actor=self.character, protocol_version=1)

    def _render(self):
        return self.registry.render("creation", self.context)

    @covers_requirement("webclient-character-creation-ui::the-creation-panel-is-an-exact-read-only-creation-mode-panel")
    def test_pending_character_receives_the_creation_panel(self):
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "creation")
        self.assertEqual(payload["schema_version"], CREATION_SCHEMA_VERSION)
        self.assertIsNone(payload["draft"])
        self.assertEqual(len(payload["presets"]), 3)
        self.assertEqual(len(payload["custom"]["profiles"]), 13)
        # The read model is side-effect free: canonical state is unchanged.
        self.assertTrue(self.character.creation_pending)
        self.assertEqual(self.character.traits.all(), [])

    @covers_requirement("webclient-character-creation-ui::the-creation-panel-is-an-exact-read-only-creation-mode-panel")
    def test_activated_character_receives_only_the_unavailable_form(self):
        from world.rules.character_creation import (
            CharacterCreationRequest,
            activate_player_character,
        )
        from world.rules.creation_wizard import save_custom_draft

        save_custom_draft(
            self.account,
            self.character,
            CharacterCreationRequest(
                mode="custom",
                display_name="已啟用角色",
                age=20,
                apparent_age=20,
                race="human",
                subrace=None,
                allocations={
                    "hp": 50, "mp": 50, "sp": 50,
                    "atk_phys": 10, "agility": 10, "defense": 11,
                },
            ),
        )
        activate_player_character(
            self.account, self.character,
            CharacterCreationRequest(
                mode="custom",
                display_name="已啟用角色",
                age=20,
                apparent_age=20,
                race="human",
                subrace=None,
                allocations={
                    "hp": 50, "mp": 50, "sp": 50,
                    "atk_phys": 10, "agility": 10, "defense": 11,
                },
            ),
            sampler=lambda low, high: low,
        )
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("presets", payload)
        self.assertNotIn("custom", payload)
        self.assertNotIn("draft", payload)
        self.assertEqual(payload["reason"]["code"], "creation_unavailable")

    @covers_requirement("webclient-character-creation-ui::the-creation-panel-is-an-exact-read-only-creation-mode-panel")
    def test_combat_character_receives_only_the_unavailable_form(self):
        # A pending shell carries a valid active session record: creation must
        # be unavailable even though the character is still creation-pending.
        room = create_object(Room, key="creation arena")
        monster = create_object(Monster, key="creation goblin")
        self.character.location = room
        self.character.db.active_combat = {
            "session_id": "hostile:1:1",
            "mode": "hostile",
            "room_id": int(room.pk),
            "player_ids": [int(self.character.pk)],
            "enemy_ids": [int(monster.pk)],
            "fled_ids": [],
            "knocked_out_ids": [],
            "rounds_elapsed": 0,
            "exam_id": None,
        }
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("presets", payload)

    def test_corrupt_draft_degrades_only_the_draft_slot(self):
        self.character.creation_draft = {"version": 1, "garbage": True}
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["draft"])
        self.assertEqual(len(payload["presets"]), 3)
        self.assertEqual(len(payload["custom"]["profiles"]), 13)
        # The whole panel remains schema-valid.
        validate_creation(payload)

    def test_semantically_broken_draft_degrades_only_the_draft_slot(self):
        # A draft that is structurally a custom draft but violates the adult
        # gate (underage) must not take the whole panel unavailable.
        self.character.creation_draft = {
            "version": 1,
            "mode": "custom",
            "stage": "custom_filled",
            "display_name": "年輕角色",
            "age": 17,
            "apparent_age": 20,
            "race": "human",
            "subrace": None,
            "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
        }
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["draft"])
        self.assertEqual(len(payload["presets"]), 3)
        validate_creation(payload)

    def test_saved_draft_round_trips_through_the_presenter(self):
        from world.rules.creation_wizard import save_custom_draft
        from world.rules.character_creation import CharacterCreationRequest

        save_custom_draft(
            self.account,
            self.character,
            CharacterCreationRequest(
                mode="custom",
                display_name="  新角色  ",
                age=20,
                apparent_age=20,
                race="human",
                subrace=None,
                allocations={
                    "hp": 50, "mp": 50, "sp": 50,
                    "atk_phys": 10, "agility": 10, "defense": 11,
                },
            ),
        )
        payload = self._render()
        self.assertEqual(payload["draft"]["mode"], "custom")
        self.assertEqual(payload["draft"]["display_name"], "新角色")
        self.assertEqual(payload["draft"]["age"], 20)


if __name__ == "__main__":
    unittest.main()
