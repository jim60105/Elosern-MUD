"""Character panel schema tests: registry-backed active-row detail-field validation."""
import unittest
from web.webclient.presentation.character import MAX_ACTIVE_ROWS, validate_character
from web.webclient.presentation.protocol import MAX_CANONICAL_JSON_BYTES, ProtocolValidationError, json_byte_size
from ._support import T_EMBER, _flattened_keys, _skill_categories, _skill_categories_enriched, _valid_panel


class CharacterSchemaTests(unittest.TestCase):

    def test_active_row_with_registry_backed_detail_fields_validates(self):
        fixture_cost = {"mp": 12}
        normalized = validate_character(
            _valid_panel(actives=_skill_categories_enriched([T_EMBER], cost=fixture_cost))
        )
        row = normalized["actives"][0]["groups"][0]["skills"][0]
        self.assertEqual(row["cost"], fixture_cost)
        self.assertEqual(row["target_spec"], "single")
        self.assertIs(row["usable_out_of_combat"], True)
        self.assertEqual(len(row["freeform_scales"]), 5)


    def test_active_row_detail_fields_are_omittable(self):
        normalized = validate_character(_valid_panel(actives=_skill_categories([T_EMBER])))
        row = normalized["actives"][0]["groups"][0]["skills"][0]
        self.assertEqual(set(row), {"key", "label"})


    def test_active_row_rejects_malformed_detail_fields(self):
        payload = _valid_panel(actives=_skill_categories([T_EMBER]))
        payload["actives"][0]["groups"][0]["skills"][0]["shorthands"] = ["all"]
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)
        payload = _valid_panel(actives=_skill_categories([T_EMBER]))
        payload["actives"][0]["groups"][0]["skills"][0]["target_spec"] = "wild"
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)
        payload = _valid_panel(actives=_skill_categories([T_EMBER]))
        payload["actives"][0]["groups"][0]["skills"][0]["usable_out_of_combat"] = "yes"
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)


    def test_freeform_scales_without_an_mp_cost_fails_closed(self):
        # The empty cost object (the free form) and a zero mp cost both fail
        # closed when freeform_scales is present.
        for mp_value in (None, 0):
            with self.subTest(mp_value=mp_value):
                payload = _valid_panel(actives=_skill_categories_enriched([T_EMBER], cost={"mp": 12}))
                cost = {} if mp_value is None else {"mp": mp_value}
                payload["actives"][0]["groups"][0]["skills"][0]["cost"] = cost
                with self.assertRaises(ProtocolValidationError):
                    validate_character(payload)


    def test_explicit_null_detail_fields_are_rejected(self):
        # The JS mirror rejects present-but-null optional fields; Python must
        # agree (schema parity, fix-webclient-skillbook-descriptor-data).
        for null_field in ("cost", "target_spec", "usable_out_of_combat"):
            with self.subTest(null_field=null_field):
                candidate = _valid_panel(actives=_skill_categories([T_EMBER]))
                candidate["actives"][0]["groups"][0]["skills"][0][null_field] = None
                with self.assertRaises(ProtocolValidationError):
                    validate_character(candidate)
        # A null freeform_scales is accepted and the field is omitted.
        t_cost = {"mp": 12}
        normalized = validate_character(
            _valid_panel(actives=_skill_categories_enriched([T_EMBER], cost=t_cost))
        )
        row = normalized["actives"][0]["groups"][0]["skills"][0]
        self.assertEqual(
            row["freeform_scales"],
            _skill_categories_enriched([T_EMBER], cost=t_cost)[0]["groups"][0][
                "skills"
            ][0]["freeform_scales"],
        )
        null_scales = _valid_panel(
            actives=_skill_categories_enriched([T_EMBER], cost=t_cost)
        )
        null_scales["actives"][0]["groups"][0]["skills"][0]["freeform_scales"] = None
        normalized = validate_character(null_scales)
        self.assertNotIn("freeform_scales", normalized["actives"][0]["groups"][0]["skills"][0])


    def test_worst_case_active_rows_with_detail_fields_fit_the_envelope(self):
        # Every one of the 32 active rows carries cost + target_spec +
        # usable_out_of_combat + the full five-entry freeform_scales set.
        actives = _skill_categories_enriched(
            [f"active_{i}" for i in range(MAX_ACTIVE_ROWS)], cost={"mp": 12}
        )
        payload = _valid_panel(actives=actives)
        normalized = validate_character(payload)
        self.assertLessEqual(json_byte_size(normalized), MAX_CANONICAL_JSON_BYTES)
        self.assertEqual(_flattened_keys(normalized["actives"]), _flattened_keys(actives))


if __name__ == "__main__":
    unittest.main()
