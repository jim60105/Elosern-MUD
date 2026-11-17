"""Creation panel validation tests: descriptor bounds, preset cards, and profile budgets."""
from tools.spec_traceability import covers_requirement
from copy import deepcopy
import unittest
from unittest.mock import patch
from web.webclient.presentation.creation import AGE_MAXIMUM, AGE_MINIMUM, APPARENT_AGE_MAXIMUM, APPARENT_AGE_MINIMUM, CREATION_SCHEMA_VERSION, CreationPanelError, MAX_BACKGROUND_CODE_POINTS, MAX_DESCRIPTION_CODE_POINTS, MAX_DISPLAY_NAME_CODE_POINTS, MAX_EMPHASIS_CODE_POINTS, MAX_EXPLANATION_CODE_POINTS, MAX_LABEL_CODE_POINTS, MAX_NAME_LENGTH, MAX_PRESET_KEY_CODE_POINTS, MAX_PRESETS, MAX_PROFILES, MAX_RACES, MAX_RACE_KEY_CODE_POINTS, MAX_SILHOUETTES, MAX_SPECIALTY_CODE_POINTS, MAX_SUBRACES, MAX_SUBRACE_KEY_CODE_POINTS, MIN_NAME_LENGTH, validate_creation
from world.art.gallery_fallback import band_key_for
from world.lore.sex import SEX_VALUES
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)
from world.rules.character_creation import resolve_starting_profile
from world.rules.creation_wizard import ALLOCATABLE_AXES
from world.tests.synthetic_data import SYNTH_PRESETS
from ._support import _open_t_creation_scope, _set_presets_count, _shipped_race_affinity, _t_profile_pairs, _valid_payload


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


    def test_valid_realistic_payload_round_trips(self):
        payload = _valid_payload()
        validated = validate_creation(payload)
        self.assertEqual(validated["schema_version"], CREATION_SCHEMA_VERSION)
        self.assertTrue(validated["available"])
        self.assertEqual(validated["kind"], "creation")
        self.assertIsNone(validated["draft"])
        self.assertEqual(len(validated["presets"]), len(SYNTH_PRESETS))
        self.assertEqual(
            [card["key"] for card in validated["presets"]],
            list(SYNTH_PRESETS),
        )


    @covers_requirement("webclient-character-creation-ui::creation-presentation-derives-finite-controls-from-immutable-registries")
    def test_deterministic_preset_and_profile_ordering(self):
        payload = validate_creation(_valid_payload())
        self.assertEqual(
            [card["key"] for card in payload["presets"]],
            list(SYNTH_PRESETS),
        )
        profile_keys = [(p["race"], p["subrace"]) for p in payload["custom"]["profiles"]]
        self.assertEqual(profile_keys, _t_profile_pairs())
        self.assertEqual(
            [axis["axis"] for axis in payload["custom"]["profiles"][0]["axes"]],
            list(ALLOCATABLE_AXES),
        )


    def test_schema_version_kind_and_availability_discriminators(self):
        for mutate, label in (
            (lambda p: p.update(schema_version=1), "schema_version"),
            (lambda p: p.update(schema_version=2), "legacy schema_version 2"),
            # v3 is the pre-sex version; the exact gate must reject it on both
            # ends (namegen-creation-ui "A stale schema version is rejected").
            (lambda p: p.update(schema_version=3), "legacy schema_version 3"),
            (lambda p: p.update(schema_version=5), "legacy schema_version 5"),
            # v6 is the pre-artwork version: the exact gate rejects it on both
            # ends (creation-panel-artwork "A stale schema version is rejected").
            (lambda p: p.update(schema_version=6), "legacy schema_version 6"),
            (lambda p: p.update(available=False), "available"),
            (lambda p: p.update(kind="services"), "kind"),
        ):
            with self.subTest(label=label):
                payload = _valid_payload()
                mutate(payload)
                with self.assertRaises(CreationPanelError):
                    validate_creation(payload)


    @covers_requirement("webclient-character-creation-ui::creation-presentation-derives-finite-controls-from-immutable-registries")
    def test_custom_descriptor_ships_server_labelled_sex_options(self):
        payload = validate_creation(_valid_payload())
        self.assertEqual(payload["schema_version"], 7)
        self.assertEqual(
            payload["custom"]["sex"],
            [
                {"key": "female", "label": "女性"},
                {"key": "male", "label": "男性"},
                {"key": "other", "label": "其他"},
            ],
        )


    def test_sex_descriptor_mirrors_the_vocabulary_exactly(self):
        base = _valid_payload()
        with self.subTest("missing"):
            bad = deepcopy(base)
            del bad["custom"]["sex"]
            with self.assertRaises(Exception):
                validate_creation(bad)
        with self.subTest("reordered"):
            bad = deepcopy(base)
            bad["custom"]["sex"].reverse()
            with self.assertRaises(Exception):
                validate_creation(bad)
        with self.subTest("fabricated member"):
            bad = deepcopy(base)
            bad["custom"]["sex"][0] = {"key": "dwarf", "label": "女性"}
            with self.assertRaises(Exception):
                validate_creation(bad)
        with self.subTest("extra field on option"):
            bad = deepcopy(base)
            bad["custom"]["sex"][0]["default"] = True
            with self.assertRaises(Exception):
                validate_creation(bad)
        with self.subTest("empty vocabulary"):
            bad = deepcopy(base)
            bad["custom"]["sex"] = []
            with self.assertRaises(Exception):
                validate_creation(bad)
        with self.subTest("label over bound"):
            bad = deepcopy(base)
            bad["custom"]["sex"][0]["label"] = "x" * (MAX_LABEL_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(bad)


    def test_preset_card_bounds(self):
        with self.assertRaises(Exception):
            validate_creation(_valid_payload(presets=_set_presets_count(MAX_PRESETS + 1)))
        base = _valid_payload()
        base["presets"] = base["presets"][:1]
        card = base["presets"][0]
        original = dict(card)
        with self.subTest("key"):
            card["key"] = "x" * (MAX_PRESET_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))
        card["key"] = original["key"]
        with self.subTest("display_name"):
            card["display_name"] = "x" * (MAX_DISPLAY_NAME_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))
        card["display_name"] = original["display_name"]
        with self.subTest("race"):
            card["race"] = "x" * (MAX_RACE_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))
        card["race"] = original["race"]
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


    @covers_requirement("webclient-character-creation-ui::creation-race-display-names-travel-with-opaque-keys")
    def test_preset_card_race_must_exist_in_custom_races(self):
        payload = _valid_payload()
        payload["presets"][0]["race"] = "unknown_race"
        with self.assertRaises(CreationPanelError):
            validate_creation(payload)

    @covers_requirement("webclient-character-creation-ui::creation-race-display-names-travel-with-opaque-keys")
    def test_race_option_display_name_zh_validation(self):
        payload = _valid_payload()
        with self.subTest("missing display_name_zh"):
            bad = deepcopy(payload)
            del bad["custom"]["races"][0]["display_name_zh"]
            with self.assertRaises(Exception):
                validate_creation(bad)
        with self.subTest("blank display_name_zh"):
            bad = deepcopy(payload)
            bad["custom"]["races"][0]["display_name_zh"] = "   "
            with self.assertRaises(Exception):
                validate_creation(bad)
        with self.subTest("overlong display_name_zh"):
            bad = deepcopy(payload)
            bad["custom"]["races"][0]["display_name_zh"] = "x" * (MAX_DISPLAY_NAME_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(bad)

    def test_preset_card_empty_prose_and_subrace_bound_are_rejected(self):
        base = _valid_payload()
        base["presets"] = base["presets"][:1]
        card = base["presets"][0]
        original = dict(card)
        for field in ("display_name", "race_description", "emphasis", "background"):
            with self.subTest(field=field):
                card[field] = "   "
                with self.assertRaises(Exception):
                    validate_creation(deepcopy(base))
        card["display_name"] = original["display_name"]
        card["race_description"] = "描述"
        card["emphasis"] = "配點"
        card["background"] = "背景"
        with self.subTest("subrace bound"):
            card["subrace"] = "x" * (MAX_SUBRACE_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(base))


    def test_name_and_age_bounds_are_exact(self):
        for mutate, label in (
            (lambda c: c["name"].update(min_length=0), "min_length"),
            (lambda c: c["name"].update(max_length=81), "max_length"),
            (lambda c: c["age"].update(age_minimum=1), "age_minimum"),
            (lambda c: c["age"].update(age_maximum=10001), "age_maximum"),
            (lambda c: c["age"].update(apparent_age_minimum=1), "apparent_age_minimum"),
            (lambda c: c["age"].update(apparent_age_maximum=10001), "apparent_age_maximum"),
        ):
            with self.subTest(label=label):
                payload = _valid_payload()
                mutate(payload["custom"])
                with self.assertRaises(Exception):
                    validate_creation(payload)
        payload = _valid_payload()
        self.assertEqual(payload["custom"]["name"]["min_length"], MIN_NAME_LENGTH)
        self.assertEqual(payload["custom"]["name"]["max_length"], MAX_NAME_LENGTH)
        self.assertEqual(payload["custom"]["age"]["age_minimum"], AGE_MINIMUM)
        self.assertEqual(payload["custom"]["age"]["age_maximum"], AGE_MAXIMUM)
        self.assertEqual(
            payload["custom"]["age"]["apparent_age_minimum"], APPARENT_AGE_MINIMUM
        )
        self.assertEqual(
            payload["custom"]["age"]["apparent_age_maximum"], APPARENT_AGE_MAXIMUM
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
        original = dict(race)
        subrace_key = next(iter(payload["custom"]["subraces"]))
        with self.subTest("key"):
            race["key"] = "x" * (MAX_RACE_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        race["key"] = original["key"]
        with self.subTest("description"):
            race["description"] = "x" * (MAX_DESCRIPTION_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        race["description"] = "描述"
        with self.subTest("subraces-not-list"):
            race["subraces"] = "t_not-a-list"
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        race["subraces"] = [subrace_key, "x" * (MAX_SUBRACE_KEY_CODE_POINTS + 1)]
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
        entry = payload["custom"]["subraces"][next(iter(payload["custom"]["subraces"]))]
        original = dict(entry)
        with self.subTest("display_name_zh"):
            entry["display_name_zh"] = "x" * (MAX_SPECIALTY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        entry["display_name_zh"] = original["display_name_zh"]
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
        original = dict(profile)
        with self.subTest("race"):
            profile["race"] = "x" * (MAX_RACE_KEY_CODE_POINTS + 1)
            with self.assertRaises(Exception):
                validate_creation(deepcopy(payload))
        profile["race"] = original["race"]
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


    def test_preset_cards_carry_a_canonical_alpha_only_artwork_descriptor(self):
        payload = validate_creation(_valid_payload())
        for card in payload["presets"]:
            artwork = card["artwork"]
            self.assertEqual(
                artwork["subject_id"], f"creation:preset:{card['key']}"
            )
            self.assertIsNone(artwork["generation_subject"])
            self.assertIsNone(artwork["generation_state"])
            self.assertEqual(artwork["retention_sources"], [])
            self.assertEqual(artwork["terminal"]["kind"], "alpha_mask")
            self.assertEqual(artwork["attempts"], [])
            self.assertEqual(
                set(artwork),
                {
                    "subject_id",
                    "revision",
                    "generation_subject",
                    "generation_state",
                    "attempts",
                    "terminal",
                    "retention_sources",
                },
            )


    def test_preset_artwork_rejects_every_malformed_case(self):
        def official_attempt(url="/art/official/abc", origin="official"):
            return {
                "type": "image",
                "source_id": "portrait.official:preset/x",
                "rank": 50,
                "resource": {
                    "resource_id": "preset/x/hero.png",
                    "version": "a" * 64,
                    "url": url,
                    "origin": origin,
                    "geometry": {
                        "image_size": None,
                        "face_rect": {"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2},
                        "stage": None,
                        "aspect_ratio": "3:4",
                    },
                },
            }

        def fault_attempt():
            return {
                "type": "fault",
                "source_id": "portrait.official:preset/x",
                "rank": 50,
                "reason": "source_unavailable",
            }

        base = _valid_payload()

        def mutated(mutate):
            payload = deepcopy(base)
            mutate(payload)
            return payload

        cases = [
            ("missing artwork", lambda p: p["presets"][0].pop("artwork")),
            ("null artwork", lambda p: p["presets"][0].update(artwork=None)),
            (
                "non same-origin attempt URL",
                lambda p: p["presets"][0]["artwork"]["attempts"].append(
                    official_attempt(url="https://example.invalid/art/x.png")
                ),
            ),
            (
                "non-official attempt origin",
                lambda p: p["presets"][0]["artwork"]["attempts"].append(
                    official_attempt(url="/art/x.png", origin="runtime")
                ),
            ),
            (
                "fault attempt",
                lambda p: p["presets"][0]["artwork"]["attempts"].append(
                    fault_attempt()
                ),
            ),
            (
                "two image attempts",
                lambda p: p["presets"][0]["artwork"]["attempts"].extend(
                    [official_attempt(), official_attempt()]
                ),
            ),
            (
                "claimed generation",
                lambda p: p["presets"][0]["artwork"].update(
                    generation_subject="portrait:character:1",
                    generation_state="pending",
                ),
            ),
            (
                "retention",
                lambda p: p["presets"][0]["artwork"].update(
                    retention_sources=[
                        {"source_id": "portrait.official:x", "token": "a" * 64}
                    ]
                ),
            ),
            (
                "missing terminal",
                lambda p: p["presets"][0]["artwork"].update(terminal=None),
            ),
            (
                "terminal wrong route",
                lambda p: p["presets"][0]["artwork"]["terminal"]["resource"].update(
                    origin="runtime", url="/art/runtime/x.png"
                ),
            ),
            (
                "wrong subject id",
                lambda p: p["presets"][0]["artwork"].update(
                    subject_id="creation:preset:another"
                ),
            ),
        ]
        for label, mutate in cases:
            with self.subTest(label=label):
                with self.assertRaises(ProtocolValidationError):
                    validate_creation(mutated(mutate))


    def test_silhouette_table_covers_every_advertised_sex_exactly(self):
        payload = validate_creation(_valid_payload())
        table = payload["custom"]["silhouettes"]
        sexes = [option["key"] for option in payload["custom"]["sex"]]
        self.assertEqual(
            [entry["sex"] for entry in table],
            [sex for sex in sexes for _ in range(3)],
        )
        for sex in sexes:
            entries = [entry for entry in table if entry["sex"] == sex]
            self.assertEqual(entries[0]["apparent_age_minimum"], APPARENT_AGE_MINIMUM)
            self.assertEqual(entries[-1]["apparent_age_maximum"], APPARENT_AGE_MAXIMUM)
            for previous, current in zip(entries, entries[1:]):
                self.assertEqual(
                    current["apparent_age_minimum"],
                    previous["apparent_age_maximum"] + 1,
                )
            for entry in entries:
                expected_key = band_key_for(
                    "portrait:character:1",
                    sex,
                    entry["apparent_age_minimum"],
                )
                self.assertEqual(
                    expected_key,
                    band_key_for(
                        "portrait:character:1",
                        sex,
                        entry["apparent_age_maximum"],
                    ),
                    "a silhouette interval must not straddle a band boundary",
                )
                artwork = entry["artwork"]
                self.assertEqual(artwork["attempts"], [])
                self.assertEqual(artwork["retention_sources"], [])
                self.assertIsNone(artwork["generation_subject"])
                self.assertIsNone(artwork["generation_state"])
                self.assertEqual(artwork["terminal"]["kind"], "alpha_mask")
                self.assertEqual(
                    artwork["terminal"]["source_id"],
                    f"portrait.alpha:{expected_key}",
                )

    def test_the_silhouette_bound_covers_the_advertised_sex_vocabulary(self):
        # Three non-empty bands per advertised sex is the builder's partition;
        # a future vocabulary growth must move the bound rather than emit a
        # table its own validator rejects.
        self.assertLessEqual(len(SEX_VALUES) * 3, MAX_SILHOUETTES)


    def test_silhouette_table_rejects_every_malformed_case(self):
        base = _valid_payload()

        def mutated(mutate):
            payload = deepcopy(base)
            mutate(payload["custom"]["silhouettes"])
            return payload

        def first(table):
            return table[0]

        cases = [
            ("empty table", lambda t: t.clear()),
            ("over-bound table", lambda t: t.extend(deepcopy(t))),
            ("unknown sex", lambda t: first(t).update(sex="dwarf")),
            ("noninteger endpoint", lambda t: first(t).update(apparent_age_minimum=1.5)),
            ("boolean endpoint", lambda t: first(t).update(apparent_age_minimum=True)),
            (
                "reversed interval",
                lambda t: first(t).update(apparent_age_minimum=500, apparent_age_maximum=100),
            ),
            ("out-of-range endpoint", lambda t: first(t).update(apparent_age_minimum=-1)),
            ("gap", lambda t: first(t).update(apparent_age_maximum=11)),
            ("overlap", lambda t: first(t).update(apparent_age_maximum=13)),
            ("extra entry field", lambda t: first(t).update(extra=True)),
            (
                "missing advertised sex",
                lambda t: t.__setitem__(
                    slice(None), [entry for entry in t if entry["sex"] != "male"]
                ),
            ),
            (
                "terminal removed",
                lambda t: first(t)["artwork"].update(terminal=None),
            ),
            (
                "terminal wrong route",
                lambda t: first(t)["artwork"]["terminal"]["resource"].update(
                    origin="runtime", url="/art/runtime/x.png"
                ),
            ),
            (
                "attempt present",
                lambda t: first(t)["artwork"]["attempts"].append(
                    {
                        "type": "fault",
                        "source_id": "portrait.official:preset/x",
                        "rank": 50,
                        "reason": "source_unavailable",
                    }
                ),
            ),
            (
                "subject id mismatch",
                lambda t: first(t)["artwork"].update(
                    subject_id="creation:silhouette:1:male:0:12"
                ),
            ),
            (
                "retention present",
                lambda t: first(t)["artwork"].update(
                    retention_sources=[
                        {"source_id": "portrait.alpha:woman", "token": "a" * 64}
                    ]
                ),
            ),
        ]
        for label, mutate in cases:
            with self.subTest(label=label):
                with self.assertRaises(ProtocolValidationError):
                    validate_creation(mutated(mutate))

    def test_a_full_descriptor_payload_fits_the_envelope(self):
        # Descriptor additions must not push a structurally full panel past the
        # canonical byte gate: the bound stays as it was and a realistic
        # maximum-count panel with every preview descriptor still fits.
        payload = _valid_payload()
        card = payload["presets"][0]
        payload["presets"] = [deepcopy(card) for _ in range(MAX_PRESETS)]
        validated = validate_creation(payload)
        self.assertEqual(len(validated["presets"]), MAX_PRESETS)
        self.assertEqual(len(validated["custom"]["silhouettes"]), 9)
        for entry in validated["presets"]:
            self.assertEqual(
                entry["artwork"]["subject_id"], f"creation:preset:{entry['key']}"
            )
        self.assertLessEqual(json_byte_size(validated), MAX_CANONICAL_JSON_BYTES)


if __name__ == "__main__":
    unittest.main()
