"""Exact ``creation`` schema, presenter, and isolation tests.

Covers the D2 shared bounds, the version-3 payload validation (player-owned
draft persona plus the optional transient proposal slot with its five
transient-fill keys), deterministic
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
    AFFINITY_ELEMENT_KEYS,
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
    MAX_PROPOSAL_NAME_CODE_POINTS,
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
    read_draft,
)


def _valid_payload(draft=None, custom=None, presets=None, proposal=None):
    """A schema-valid creation payload derived from the immutable registries."""
    view = CreationView(
        presets=build_preset_cards() if presets is None else presets,
        custom=build_custom_form() if custom is None else custom,
        draft=draft,
    )
    from web.webclient.presentation.creation import _serialize

    payload = _serialize(view)
    if proposal is not None:
        # The wire dict rides directly for validation tests; the presenter
        # path serializes the snapshot itself.
        payload["proposal"] = proposal
    return payload


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
        self.assertEqual(len(validated["presets"]), 8)
        self.assertEqual(
            [card["key"] for card in validated["presets"]],
            [
                "human_wanderer",
                "foxkin_scout",
                "elf_guardian",
                "violet_altoria",
                "lidzia_rosenthal",
                "yuka_darknight",
                "yuna_darknight",
                "elosia_shadowmoon",
            ],
        )

    @covers_requirement("webclient-character-creation-ui::creation-presentation-derives-finite-controls-from-immutable-registries")
    def test_deterministic_preset_and_profile_ordering(self):
        payload = validate_creation(_valid_payload())
        self.assertEqual(
            [card["key"] for card in payload["presets"]],
            [
                "human_wanderer",
                "foxkin_scout",
                "elf_guardian",
                "violet_altoria",
                "lidzia_rosenthal",
                "yuka_darknight",
                "yuna_darknight",
                "elosia_shadowmoon",
            ],
        )
        profile_keys = [(p["race"], p["subrace"]) for p in payload["custom"]["profiles"]]
        self.assertEqual(profile_keys[0], ("human", "human_royal"))
        self.assertEqual(profile_keys[1], ("human", "human_noble"))
        self.assertIn(("elf", "fionnen"), profile_keys)
        self.assertEqual(
            [axis["axis"] for axis in payload["custom"]["profiles"][0]["axes"]],
            list(ALLOCATABLE_AXES),
        )

    def test_schema_version_kind_and_availability_discriminators(self):
        for mutate, label in (
            (lambda p: p.update(schema_version=1), "schema_version"),
            (lambda p: p.update(schema_version=2), "legacy schema_version 2"),
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

    def test_preset_card_empty_prose_and_subrace_bound_are_rejected(self):
        base = _valid_payload()
        base["presets"] = base["presets"][:1]
        card = base["presets"][0]
        for field in ("display_name", "race_description", "emphasis", "background"):
            with self.subTest(field=field):
                card[field] = "   "
                with self.assertRaises(Exception):
                    validate_creation(deepcopy(base))
        card["display_name"] = "艾琳"
        card["race_description"] = "描述"
        card["emphasis"] = "配點"
        card["background"] = "背景"
        with self.subTest("subrace bound"):
            card["subrace"] = "x" * (MAX_SUBRACE_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))

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
            "subrace": "human_commoner",
            "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
        }
        payload = _valid_payload(draft=draft)
        validated = validate_creation(payload)
        self.assertEqual(validated["draft"]["mode"], "custom")
        # The serializer always renders the required nullable persona key; a
        # draft without player persona prose ships an explicit null
        # (retool-concept-transient-fill D2/D3).
        self.assertIsNone(validated["draft"]["persona"])
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
        bad = deepcopy(payload)
        bad["draft"]["persona"] = {"personality": "沉穩"}
        with self.assertRaises(Exception):
            validate_creation(bad)

    @covers_requirement("concept-transient-fill::persona-rides-the-custom-draft-payload-and-activation")
    def test_draft_custom_persona_block_round_trips_verbatim(self):
        draft = {
            "mode": "custom",
            "stage": "custom_filled",
            "display_name": "新角色",
            "age": 20,
            "apparent_age": 20,
            "race": "human",
            "subrace": "human_commoner",
            "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
            "persona": {
                "personality": "沉穩",
                "life_story": "來自邊境的小村",
                "habit": "清晨練劍",
            },
        }
        payload = _valid_payload(draft=draft)
        validated = validate_creation(payload)
        self.assertEqual(validated["draft"]["persona"], draft["persona"])
        for mutate, label in (
            # A missing prose key, an extra key, blank text, or a field over
            # the 600-code-point bound all degrade the payload at the gate.
            (lambda d: d["draft"]["persona"].pop("habit"), "missing key"),
            (lambda d: d["draft"]["persona"].update(extra="x"), "extra key"),
            (lambda d: d["draft"]["persona"].update(personality="  "), "blank"),
            (
                lambda d: d["draft"]["persona"].update(habit="長" * 601),
                "over bound",
            ),
            (lambda d: d["draft"].update(persona="沉穩"), "non-object"),
        ):
            with self.subTest(label=label):
                bad = deepcopy(payload)
                mutate(bad)
                with self.assertRaises(Exception):
                    validate_creation(bad)

    def test_worst_case_realistic_payload_fits_comfortably(self):
        payload = validate_creation(_valid_payload())
        size = json_byte_size(payload)
        self.assertLess(
            size,
            MAX_CANONICAL_JSON_BYTES // 3,
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
        affinity_element = {
            "key": "fire",
            "label": "l" * MAX_LABEL_CODE_POINTS,
        }
        affinity_elements = [
            dict(affinity_element, key=key)
            for key in ("fire", "water", "wind", "earth", "lightning", "ice", "light", "dark")
        ]
        payload = {
            "schema_version": CREATION_SCHEMA_VERSION,
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
                "affinity": {
                    "human": {"maximum": 2, "elements": list(affinity_elements)},
                    "beastfolk": {"maximum": 1, "elements": list(affinity_elements)},
                    "elf": {"maximum": 0, "elements": list(affinity_elements)},
                },
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
        # The descriptor surfaces (custom descriptor, preset cards, profiles)
        # carry no persona, skill, equipment, inventory, or import-only field.
        # The draft/proposal data surfaces legitimately carry the
        # player-owned persona block (retool-concept-transient-fill D3).
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
            self.assertNotIn(forbidden, payload["custom"])
            for card in payload["presets"]:
                self.assertNotIn(forbidden, card)
            for profile in payload["custom"]["profiles"]:
                self.assertNotIn(forbidden, profile)

    @covers_requirement("webclient-character-creation-ui::creation-presentation-derives-finite-controls-from-immutable-registries")
    def test_affinity_descriptor_advertises_race_bounded_maxima_and_eight_elements(self):
        from world.lore.elements import ELEMENT_REGISTRY
        from world.rules.character_creation import max_affinity_elements

        payload = validate_creation(_valid_payload())
        affinity = payload["custom"]["affinity"]
        self.assertEqual(set(affinity), {"human", "beastfolk", "elf"})
        for race_key, entry in affinity.items():
            self.assertEqual(entry["maximum"], max_affinity_elements(race_key))
            keys = [element["key"] for element in entry["elements"]]
            self.assertEqual(set(keys), set(ELEMENT_REGISTRY))
            for element in entry["elements"]:
                self.assertIn(element["key"], ELEMENT_REGISTRY)
                self.assertTrue(element["label"])

    def test_affinity_descriptor_rejects_wrong_bounds_and_unknown_elements(self):
        payload = _valid_payload()
        affinity = payload["custom"]["affinity"]
        bad = deepcopy(affinity)
        bad["human"]["maximum"] = 99
        bad_payload = deepcopy(payload)
        bad_payload["custom"]["affinity"] = bad
        with self.assertRaises(Exception):
            validate_creation(bad_payload)
        bad = deepcopy(affinity)
        bad["human"]["elements"] = bad["human"]["elements"][:-1]
        bad_payload = deepcopy(payload)
        bad_payload["custom"]["affinity"] = bad
        with self.assertRaises(Exception):
            validate_creation(bad_payload)


def _proposal_wire(**overrides):
    """A valid base proposal wire object carrying the given transient fill."""
    proposal = {
        "revision": 2,
        "race": "human",
        "subrace": "human_commoner",
        "allocations": {
            "hp": 50, "mp": 50, "sp": 50,
            "atk_phys": 10, "agility": 10, "defense": 11,
            "magic_power": 43,
        },
        "persona": {
            "personality": "沉穩",
            "life_story": "來自邊境的小村",
            "habit": "清晨練劍",
        },
    }
    proposal.update(overrides)
    return proposal


class ProposalTransientFillValidationTests(unittest.TestCase):
    """The v3 proposal slot's five optional transient-fill keys.

    Presence-only semantics: a carried value round-trips exactly, an absent
    key stays absent (never a null-valued copy), and every bound violation or
    null is a structural rejection (bump-creation-panel-proposal-v3 D1).
    """

    def _validate(self, proposal):
        return validate_creation(_valid_payload(proposal=proposal))["proposal"]

    def _rejects(self, proposal):
        with self.assertRaises(Exception):
            self._validate(proposal)

    @covers_requirement(
        "concept-transient-fill::the-creation-panel-renders-the-transient-proposal"
    )
    def test_carried_transient_fill_keys_round_trip(self):
        fill = {
            "display_name": "莉雅",
            "age": 25,
            "apparent_age": 22,
            "background": "邊境孤女，隨商隊长大",
            "affinity_elements": ["fire", "water"],
        }
        proposal = self._validate(_proposal_wire(**fill))
        for key, value in fill.items():
            self.assertEqual(proposal[key], value)

    @covers_requirement(
        "concept-transient-fill::the-creation-panel-renders-the-transient-proposal"
    )
    def test_absent_keys_stay_absent_not_null(self):
        proposal = self._validate(_proposal_wire())
        for key in (
            "display_name",
            "age",
            "apparent_age",
            "background",
            "affinity_elements",
        ):
            self.assertNotIn(key, proposal)

    @covers_requirement(
        "concept-transient-fill::the-creation-panel-renders-the-transient-proposal"
    )
    def test_null_valued_transient_fill_keys_reject(self):
        for key in (
            "display_name",
            "age",
            "apparent_age",
            "background",
            "affinity_elements",
        ):
            with self.subTest(key=key):
                self._rejects(_proposal_wire(**{key: None}))

    def test_bound_violations_reject(self):
        cases = {
            "underage age": _proposal_wire(age=17),
            "over-bound age": _proposal_wire(age=10001),
            "boolean age": _proposal_wire(age=True),
            "underage apparent_age": _proposal_wire(apparent_age=17),
            "float age": _proposal_wire(age=25.5),
            "empty display_name": _proposal_wire(display_name=""),
            "over-long display_name": _proposal_wire(
                display_name="莉" * (MAX_PROPOSAL_NAME_CODE_POINTS + 1)
            ),
            "empty background": _proposal_wire(background=""),
            "over-long background": _proposal_wire(background="長" * 601),
            "too many elements": _proposal_wire(
                affinity_elements=list(AFFINITY_ELEMENT_KEYS) + ["fire"]
            ),
            "unknown element": _proposal_wire(affinity_elements=["wood"]),
            "duplicate element": _proposal_wire(affinity_elements=["fire", "fire"]),
            "non-list affinity": _proposal_wire(affinity_elements={"fire": 1}),
            "unknown key": _proposal_wire(eye_color="琥珀"),
        }
        for label, proposal in cases.items():
            with self.subTest(label=label):
                self._rejects(proposal)

    def test_carried_empty_affinity_list_round_trips(self):
        # The normalized elf affinity value is a carried EMPTY set; only an
        # absent (None) value may omit the key.
        proposal = self._validate(_proposal_wire(affinity_elements=[]))
        self.assertEqual(proposal["affinity_elements"], [])

    def test_whitespace_only_prose_is_non_empty_not_non_blank(self):
        # Contract pin: the transient-fill prose fields are bounded NON-EMPTY
        # (1..N code points), deliberately not NON-BLANK like the persona
        # block — whitespace-only values must keep passing in both mirrors.
        proposal = self._validate(
            _proposal_wire(display_name=" ", background="  ")
        )
        self.assertEqual(proposal["display_name"], " ")
        self.assertEqual(proposal["background"], "  ")


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
        self.assertEqual(len(payload["presets"]), 8)
        self.assertEqual(len(payload["custom"]["profiles"]), 15)
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
                subrace="human_commoner",
                allocations={
                    "hp": 50, "mp": 50, "sp": 50,
                    "atk_phys": 10, "agility": 10, "defense": 11,
                    "magic_power": 43,
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
                subrace="human_commoner",
                allocations={
                    "hp": 50, "mp": 50, "sp": 50,
                    "atk_phys": 10, "agility": 10, "defense": 11,
                    "magic_power": 43,
                },
            ),
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
        self.character.creation_draft = {"version": 2, "garbage": True}
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["draft"])
        self.assertEqual(len(payload["presets"]), 8)
        self.assertEqual(len(payload["custom"]["profiles"]), 15)
        # The whole panel remains schema-valid.
        validate_creation(payload)

    def test_semantically_broken_draft_degrades_only_the_draft_slot(self):
        # A draft that is structurally a custom draft but violates the adult
        # gate (underage) must not take the whole panel unavailable.
        self.character.creation_draft = {
            "version": 2,
            "mode": "custom",
            "stage": "custom_filled",
            "display_name": "年輕角色",
            "age": 17,
            "apparent_age": 20,
            "race": "human",
            "subrace": "human_commoner",
            "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
            "persona": None,
        }
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertIsNone(payload["draft"])
        self.assertEqual(len(payload["presets"]), 8)
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
                subrace="human_commoner",
                allocations={
                    "hp": 50, "mp": 50, "sp": 50,
                    "atk_phys": 10, "agility": 10, "defense": 11,
                    "magic_power": 43,
                },
            ),
        )
        payload = self._render()
        self.assertEqual(payload["draft"]["mode"], "custom")
        self.assertEqual(payload["draft"]["display_name"], "新角色")
        self.assertEqual(payload["draft"]["age"], 20)


    @covers_requirement("concept-transient-fill::the-creation-panel-renders-the-transient-proposal")
    def test_slotless_panel_omits_the_proposal_key(self):
        payload = self._render()
        # The key is absent entirely — never present as null.
        self.assertNotIn("proposal", payload)

    @covers_requirement("concept-transient-fill::the-creation-panel-renders-the-transient-proposal")
    def test_pending_proposal_renders_with_its_exact_shape(self):
        from web.webclient.presentation.context import ProposalSnapshot

        context = PresentationContext(
            actor=self.character,
            protocol_version=1,
            proposal=ProposalSnapshot(
                revision=3,
                race="human",
                subrace="human_commoner",
                allocations={
                    "hp": 50, "mp": 50, "sp": 50,
                    "atk_phys": 10, "agility": 10, "defense": 11,
                    "magic_power": 43,
                },
                persona={
                    "personality": "沉穩",
                    "life_story": "來自邊境的小村，靠磨劍維生",
                    "habit": "清晨練劍",
                },
            ),
        )
        payload = self.registry.render("creation", context)
        proposal = payload["proposal"]
        self.assertEqual(
            set(proposal), {"revision", "race", "subrace", "allocations", "persona"}
        )
        self.assertEqual(proposal["revision"], 3)
        self.assertEqual(proposal["persona"]["personality"], "沉穩")
        # Rendering stays read-only: no draft appeared, nothing persisted.
        self.assertIsNone(payload["draft"])
        self.assertIsNone(read_draft(self.character))

    @covers_requirement("concept-transient-fill::the-creation-panel-renders-the-transient-proposal")
    def test_snapshot_transient_fill_keys_render_and_absent_ones_omit(self):
        from web.webclient.presentation.context import ProposalSnapshot

        def snapshot(**fill):
            return PresentationContext(
                actor=self.character,
                protocol_version=1,
                proposal=ProposalSnapshot(
                    revision=4,
                    race="beastfolk",
                    subrace="catkin",
                    allocations={
                        "hp": 50, "mp": 50, "sp": 50,
                        "atk_phys": 10, "agility": 10, "defense": 11,
                        "magic_power": 43,
                    },
                    persona={
                        "personality": "好奇",
                        "life_story": "貓人少女",
                        "habit": "午後打盹",
                    },
                    **fill,
                ),
            )

        carried = self.registry.render("creation", snapshot(
            display_name="咪咪",
            age=20,
            apparent_age=18,
            background="貓婆婆收養的孤女",
            affinity_elements=("fire",),
        ))["proposal"]
        self.assertEqual(carried["display_name"], "咪咪")
        self.assertEqual(carried["age"], 20)
        self.assertEqual(carried["apparent_age"], 18)
        self.assertEqual(carried["background"], "貓婆婆收養的孤女")
        self.assertEqual(carried["affinity_elements"], ["fire"])

        absent = self.registry.render("creation", snapshot())["proposal"]
        for key in (
            "display_name",
            "age",
            "apparent_age",
            "background",
            "affinity_elements",
        ):
            self.assertNotIn(key, absent)

    def test_snapshot_affinity_is_a_copy_not_a_live_slot_reference(self):
        # The frozen snapshot must survive a later mutation of the source
        # slot: proposal_snapshot deep-copies the affinity list into a tuple.
        from types import SimpleNamespace

        from web.webclient.presentation.ingress import proposal_snapshot

        slot = {
            "owner_actor_id": "1",
            "revision": 1,
            "race": "human",
            "subrace": "human_commoner",
            "allocations": {
                "hp": 50, "mp": 50, "sp": 50,
                "atk_phys": 10, "agility": 10, "defense": 11,
                "magic_power": 43,
            },
            "persona": {
                "personality": "沉穩",
                "life_story": "來自邊境的小村",
                "habit": "清晨練劍",
            },
            "affinity_elements": ["fire"],
        }
        session = SimpleNamespace(ndb=SimpleNamespace(concept_proposal=slot))
        snapshot = proposal_snapshot(session, SimpleNamespace(pk="1"))
        self.assertIsNotNone(snapshot)
        slot["affinity_elements"].append("water")
        self.assertEqual(snapshot.as_dict()["affinity_elements"], ["fire"])

    @covers_requirement("concept-transient-fill::the-creation-panel-renders-the-transient-proposal")
    def test_worst_case_proposal_fits_the_envelope_bound(self):
        # The v3 all-ceilings proposal — three maximum-length persona fields,
        # a maximum background, a maximum display name (four-byte scalars, the
        # true UTF-8 worst case), both ages, and an eight-element affinity
        # set — stays inside the canonical envelope with room to spare.
        from web.webclient.presentation.context import ProposalSnapshot
        from web.webclient.presentation.protocol import json_byte_size

        context = PresentationContext(
            actor=self.character,
            protocol_version=1,
            proposal=ProposalSnapshot(
                revision=9,
                race="human",
                subrace="human_commoner",
                allocations={
                    "hp": 50, "mp": 50, "sp": 50,
                    "atk_phys": 10, "agility": 10, "defense": 11,
                    "magic_power": 43,
                },
                persona={
                    "personality": "😀" * 600,
                    "life_story": "😀" * 600,
                    "habit": "😀" * 600,
                },
                display_name="😀" * MAX_PROPOSAL_NAME_CODE_POINTS,
                age=10000,
                apparent_age=10000,
                background="😀" * 600,
                affinity_elements=tuple(AFFINITY_ELEMENT_KEYS),
            ),
        )
        payload = self.registry.render("creation", context)
        self.assertEqual(len(payload["proposal"]["persona"]["personality"]), 600)
        # Four-byte scalars make the maximum name a true 256-UTF-8-byte value.
        self.assertEqual(
            json_byte_size("😀" * MAX_PROPOSAL_NAME_CODE_POINTS),
            4 * MAX_PROPOSAL_NAME_CODE_POINTS + 2,
        )
        self.assertLessEqual(json_byte_size(payload), MAX_CANONICAL_JSON_BYTES)


if __name__ == "__main__":
    unittest.main()
