"""Creation panel validation tests: draft stages, byte-gate ceiling, and affinity descriptor."""
from tools.spec_traceability import covers_requirement
from copy import deepcopy
import unittest
from unittest.mock import patch
from web.webclient.presentation.creation import AFFINITY_ELEMENT_KEYS, AGE_MAXIMUM, AGE_MINIMUM, APPARENT_AGE_MAXIMUM, APPARENT_AGE_MINIMUM, CREATION_SCHEMA_VERSION, CreationPanelError, MAX_BACKGROUND_CODE_POINTS, MAX_DESCRIPTION_CODE_POINTS, MAX_DISPLAY_NAME_CODE_POINTS, MAX_EMPHASIS_CODE_POINTS, MAX_EXPLANATION_CODE_POINTS, MAX_LABEL_CODE_POINTS, MAX_NAME_LENGTH, MAX_PRESET_KEY_CODE_POINTS, MAX_PRESETS, MAX_PROFILES, MAX_RACES, MAX_RACE_KEY_CODE_POINTS, MAX_SPECIALTY_CODE_POINTS, MAX_SUBRACES, MAX_SUBRACE_KEY_CODE_POINTS, validate_creation
from web.webclient.presentation.protocol import MAX_CANONICAL_JSON_BYTES, json_byte_size
from world.rules.character_creation import max_affinity_elements
from world.rules.creation_wizard import ALLOCATABLE_AXES
from world.tests.synthetic_data import SYNTH_RACES
from ._support import _SHIPPED_AFFINITY_BOUNDS, _T_PRESET, _T_RACE, _T_SUBRACE, _open_t_creation_scope, _shipped_race_affinity, _valid_payload


class CreationPanelValidationTests(unittest.TestCase):
    """Pure payload-validation tests for every bound in D2."""


    def setUp(self):
        _open_t_creation_scope(self)
        handle = patch(
            "web.webclient.presentation.creation._validate_affinity",
            _shipped_race_affinity,
        )
        handle.start()
        self.addCleanup(handle.stop)


    def test_draft_preset_stage_shape(self):
        draft = {"mode": "preset", "stage": "preset_selected", "preset_key": _T_PRESET}
        payload = _valid_payload(draft=draft)
        validated = validate_creation(payload)
        self.assertEqual(validated["draft"]["preset_key"], _T_PRESET)
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
            "race": _T_RACE,
            "subrace": _T_SUBRACE,
            "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
            "sex": "other",
        }
        payload = _valid_payload(draft=draft)
        validated = validate_creation(payload)
        self.assertEqual(validated["draft"]["mode"], "custom")
        # The serializer always renders the required nullable persona key; a
        # draft without player persona prose ships an explicit null
        # (retool-concept-transient-fill D2/D3).
        self.assertIsNone(validated["draft"]["persona"])
        bad = deepcopy(payload)
        bad["draft"]["age"] = -1
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
            "race": _T_RACE,
            "subrace": _T_SUBRACE,
            "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
            "sex": "other",
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


    def test_draft_sex_member_round_trips(self):
        draft = {
            "mode": "custom",
            "stage": "custom_filled",
            "display_name": "新角色",
            "age": 20,
            "apparent_age": 20,
            "race": _T_RACE,
            "subrace": _T_SUBRACE,
            "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
            "persona": None,
            "sex": "male",
        }
        validated = validate_creation(_valid_payload(draft=draft))
        self.assertEqual(validated["draft"]["sex"], "male")


    def test_draft_without_or_tampered_sex_is_rejected(self):
        # The wizard normalizer only ever emits a concrete member, so a wire
        # draft with a tampered or missing sex key is a hostile DB edit; the
        # panel mirror rejects it like every other malformed draft field. The
        # serializer is exercised through a valid draft and the wire dict is
        # mutated afterwards.
        base = {
            "mode": "custom",
            "stage": "custom_filled",
            "display_name": "新角色",
            "age": 20,
            "apparent_age": 20,
            "race": _T_RACE,
            "subrace": _T_SUBRACE,
            "allocations": {axis: 0 for axis in ALLOCATABLE_AXES},
            "persona": None,
            "sex": "other",
        }
        with self.subTest("tampered member"):
            payload = _valid_payload(draft=base)
            payload["draft"]["sex"] = "nope"
            with self.assertRaises(Exception):
                validate_creation(payload)
        with self.subTest("missing key (v2 shape)"):
            payload = _valid_payload(draft=base)
            del payload["draft"]["sex"]
            with self.assertRaises(Exception):
                validate_creation(payload)


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
            "key": AFFINITY_ELEMENT_KEYS[0],
            "label": "l" * MAX_LABEL_CODE_POINTS,
        }
        affinity_elements = [
            dict(affinity_element, key=key)
            for key in AFFINITY_ELEMENT_KEYS
        ]
        payload = {
            "schema_version": CREATION_SCHEMA_VERSION,
            "available": True,
            "kind": "creation",
            "draft": None,
            "presets": [dict(card) for _ in range(MAX_PRESETS)],
            "custom": {
                "name": {"min_length": 1, "max_length": MAX_NAME_LENGTH},
                "age": {
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
                    race_key: {
                        "maximum": max_affinity_elements(race_key),
                        "elements": list(affinity_elements),
                    }
                    for race_key in SYNTH_RACES
                },
                "sex": [
                    {"key": key, "label": "x" * MAX_LABEL_CODE_POINTS}
                    for key in ("female", "male", "other")
                ],
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
        ):
            self.assertNotIn(forbidden, payload["custom"])
            for card in payload["presets"]:
                self.assertNotIn(forbidden, card)
            for profile in payload["custom"]["profiles"]:
                self.assertNotIn(forbidden, profile)


    @covers_requirement("webclient-character-creation-ui::creation-presentation-derives-finite-controls-from-immutable-registries")
    def test_affinity_descriptor_advertises_race_bounded_maxima_and_eight_elements(self):
        raw = _valid_payload()
        # The descriptor itself mirrors the patched race registry under the
        # kit scope: one entry per kit race, bounded by the bound mapping.
        descriptor = raw["custom"]["affinity"]
        self.assertEqual(set(descriptor), set(SYNTH_RACES))
        for race_key, entry in descriptor.items():
            self.assertEqual(entry["maximum"], max_affinity_elements(race_key))
            keys = [element["key"] for element in entry["elements"]]
            self.assertEqual(set(keys), set(AFFINITY_ELEMENT_KEYS))
        # The wire contract keeps the shipped trio normalization: every
        # shipped bound key plus the kit entries survive validation.
        payload = validate_creation(raw)
        affinity = payload["custom"]["affinity"]
        self.assertEqual(set(affinity), set(_SHIPPED_AFFINITY_BOUNDS) | set(SYNTH_RACES))
        for race_key, entry in affinity.items():
            self.assertEqual(entry["maximum"], max_affinity_elements(race_key))
            keys = [element["key"] for element in entry["elements"]]
            self.assertEqual(set(keys), set(AFFINITY_ELEMENT_KEYS))
            for element in entry["elements"]:
                self.assertIn(element["key"], AFFINITY_ELEMENT_KEYS)
                self.assertTrue(element["label"])


    def test_affinity_descriptor_rejects_wrong_bounds_and_unknown_elements(self):
        payload = _valid_payload()
        affinity = payload["custom"]["affinity"]
        first_race = next(iter(affinity))
        bad = deepcopy(affinity)
        bad[first_race]["maximum"] = 99
        bad_payload = deepcopy(payload)
        bad_payload["custom"]["affinity"] = bad
        with self.assertRaises(Exception):
            validate_creation(bad_payload)
        bad = deepcopy(affinity)
        bad[first_race]["elements"] = bad[first_race]["elements"][:-1]
        bad_payload = deepcopy(payload)
        bad_payload["custom"]["affinity"] = bad
        with self.assertRaises(Exception):
            validate_creation(bad_payload)


if __name__ == "__main__":
    unittest.main()
