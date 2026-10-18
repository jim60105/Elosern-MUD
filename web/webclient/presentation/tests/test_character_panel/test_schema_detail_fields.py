"""Character panel schema tests: v9 growth facts and registry-backed row detail."""
import unittest
from tools.spec_traceability import covers_requirement
from web.webclient.presentation.character import MAX_ACTIVE_ROWS, validate_character
from web.webclient.presentation.protocol import MAX_CANONICAL_JSON_BYTES, ProtocolValidationError, json_byte_size
from ._support import (
    T_EMBER,
    _active_row,
    _flattened_keys,
    _skill_categories,
    _skill_categories_enriched,
    _valid_panel,
)

_GROWTH_FIELDS = (
    "level",
    "xp_into_level",
    "xp_to_next_level",
    "capped",
    "fresh",
    "booked",
)


class CharacterSchemaTests(unittest.TestCase):

    @covers_requirement("webclient-exploration-menu::character-active-skill-rows-carry-compact-growth-facts")
    def test_active_row_with_registry_backed_detail_fields_validates(self):
        fixture_cost = {"mp": 12}
        normalized = validate_character(
            _valid_panel(actives=_skill_categories_enriched([T_EMBER], cost=fixture_cost))
        )
        row = normalized["actives"][0]["groups"][0]["skills"][0]
        self.assertEqual(row["cost"], fixture_cost)
        self.assertEqual(row["target_spec"], "single")
        self.assertIs(row["usable_out_of_combat"], True)
        self.assertEqual(row["level"], 1)
        self.assertEqual(row["xp_into_level"], 10)
        self.assertEqual(row["xp_to_next_level"], 40)
        self.assertIs(row["capped"], False)
        self.assertIs(row["fresh"], False)
        self.assertIs(row["booked"], False)
        self.assertNotIn("freeform_scales", row)

    @covers_requirement("webclient-exploration-menu::character-active-skill-rows-carry-compact-growth-facts")
    def test_every_growth_fact_is_required(self):
        for field in _GROWTH_FIELDS:
            with self.subTest(field=field):
                row = _active_row(T_EMBER)
                del row[field]
                payload = _valid_panel(actives=_skill_categories([T_EMBER], row=lambda key: row))
                with self.assertRaises(ProtocolValidationError):
                    validate_character(payload)

    @covers_requirement("webclient-exploration-menu::character-active-skill-rows-carry-compact-growth-facts")
    def test_growth_facts_are_typed_and_bounded(self):
        for field, bad in (
            ("level", -1),
            ("level", 1.5),
            ("level", True),
            ("xp_into_level", -1),
            ("xp_into_level", "10"),
            ("xp_to_next_level", -1),
            ("xp_to_next_level", float("nan")),
            ("capped", 0),
            ("fresh", "yes"),
            ("booked", None),
        ):
            with self.subTest(field=field, bad=bad):
                row = _active_row(T_EMBER, **{field: bad})
                payload = _valid_panel(actives=_skill_categories([T_EMBER], row=lambda key: row))
                with self.assertRaises(ProtocolValidationError):
                    validate_character(payload)

    @covers_requirement("webclient-exploration-menu::character-active-skill-rows-carry-compact-growth-facts")
    def test_a_capped_row_reports_zero_xp_to_the_next_level(self):
        row = _active_row(T_EMBER, level=10, xp_into_level=0, xp_to_next_level=0, capped=True)
        normalized = validate_character(
            _valid_panel(actives=_skill_categories([T_EMBER], row=lambda key: row))
        )
        self.assertIs(normalized["actives"][0]["groups"][0]["skills"][0]["capped"], True)
        contradictory = _active_row(
            T_EMBER, level=10, xp_into_level=0, xp_to_next_level=40, capped=True
        )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    actives=_skill_categories([T_EMBER], row=lambda key: contradictory)
                )
            )

    def test_active_row_detail_fields_are_omittable(self):
        normalized = validate_character(
            _valid_panel(actives=_skill_categories([T_EMBER], row=_active_row))
        )
        row = normalized["actives"][0]["groups"][0]["skills"][0]
        self.assertEqual(set(row), {"key", "label", *_GROWTH_FIELDS})

    @covers_requirement("webclient-exploration-menu::character-active-skill-rows-carry-compact-growth-facts")
    def test_freeform_scales_are_rejected_on_a_row(self):
        # v9 moves the ladder to selected_skill: a row carrying the v8 field
        # fails the exact-field contract instead of being silently ignored.
        row = _active_row(T_EMBER, cost={"mp": 12})
        row["freeform_scales"] = [{"scale": 1, "label": "1", "mp_cost": 12}]
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(actives=_skill_categories([T_EMBER], row=lambda key: row))
            )

    def test_active_row_rejects_malformed_detail_fields(self):
        payload = _valid_panel(actives=_skill_categories([T_EMBER], row=_active_row))
        payload["actives"][0]["groups"][0]["skills"][0]["shorthands"] = ["all"]
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)
        payload = _valid_panel(actives=_skill_categories([T_EMBER], row=_active_row))
        payload["actives"][0]["groups"][0]["skills"][0]["target_spec"] = "wild"
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)
        payload = _valid_panel(actives=_skill_categories([T_EMBER], row=_active_row))
        payload["actives"][0]["groups"][0]["skills"][0]["usable_out_of_combat"] = "yes"
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)

    def test_explicit_null_detail_fields_are_rejected(self):
        # The JS mirror rejects present-but-null optional fields; Python must
        # agree (schema parity, fix-webclient-skillbook-descriptor-data).
        for null_field in ("cost", "target_spec", "usable_out_of_combat"):
            with self.subTest(null_field=null_field):
                row = _active_row(T_EMBER, **{null_field: None})
                with self.assertRaises(ProtocolValidationError):
                    validate_character(
                        _valid_panel(
                            actives=_skill_categories([T_EMBER], row=lambda key: row)
                        )
                    )

    def test_worst_case_active_rows_with_detail_fields_fit_the_envelope(self):
        # Every one of the MAX_ACTIVE_ROWS active rows carries the six growth
        # facts plus cost, target_spec and usable_out_of_combat.
        actives = _skill_categories_enriched(
            [f"active_{i}" for i in range(MAX_ACTIVE_ROWS)], cost={"mp": 12}
        )
        payload = _valid_panel(actives=actives)
        normalized = validate_character(payload)
        self.assertLessEqual(json_byte_size(normalized), MAX_CANONICAL_JSON_BYTES)
        self.assertEqual(_flattened_keys(normalized["actives"]), _flattened_keys(actives))


if __name__ == "__main__":
    unittest.main()
