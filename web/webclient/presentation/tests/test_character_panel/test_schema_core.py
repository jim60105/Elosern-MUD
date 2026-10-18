"""Character panel schema tests: core shape, version, trait/layer, and disguise rejections."""
from tools.spec_traceability import covers_requirement
import unittest
from web.webclient.presentation.character import (
    CHARACTER_SCHEMA_VERSION,
    MAX_CONDITION_ROWS,
    MAX_LAYERS_PER_STAT,
    MAX_MODIFIER_KEYS,
    CharacterPanelError,
    validate_character,
)
from web.webclient.presentation.protocol import MAX_SAFE_INTEGER, ProtocolValidationError
from ._support import _condition_row, _equipment_row, _layer, _trait, _valid_panel


class CharacterSchemaTests(unittest.TestCase):

    def test_valid_panel_passes(self):
        normalized = validate_character(_valid_panel())
        self.assertEqual(normalized["schema_version"], CHARACTER_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["kind"], "character")


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_condition_rows_are_exact_and_bounded(self):
        # A buff row and an indefinite rule row round-trip verbatim, including
        # the rulebook's authored percentage-string adjustment.
        rows = [
            _condition_row(
                code="t_buff",
                label="合成增益",
                severity="beneficial",
                remaining_seconds=30,
                modifiers={},
                source="狀態",
            ),
            _condition_row(
                code="t_rule",
                label="合成警告",
                severity="warning",
                remaining_seconds=None,
                modifiers={"agility": "-10%", "defense": -2},
                source="裝備",
            ),
        ]
        normalized = validate_character(_valid_panel(conditions=rows))
        self.assertEqual(normalized["conditions"], rows)
        # Each row carries exactly its six fields; unknown and missing keys
        # reject, as does an unknown severity or a negative remaining time.
        for bad in (
            {**_condition_row(), "extra": 1},
            {key: value for key, value in _condition_row().items() if key != "source"},
            _condition_row(severity="buff"),
            _condition_row(remaining_seconds=-1),
            _condition_row(remaining_seconds=MAX_SAFE_INTEGER + 1),
            _condition_row(source="altar"),
            _condition_row(source=""),
            _condition_row(modifiers={"defense": True}),
            _condition_row(modifiers={"defense": "  "}),
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ProtocolValidationError):
                    validate_character(_valid_panel(conditions=[bad]))
        # The row count and the modifier-key count are bounded.
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(
                    conditions=[_condition_row() for _ in range(MAX_CONDITION_ROWS + 1)]
                )
            )
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(
                    conditions=[
                        _condition_row(
                            modifiers={
                                f"key_{index}": 1
                                for index in range(MAX_MODIFIER_KEYS + 1)
                            }
                        )
                    ]
                )
            )


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_member_id_is_a_positive_safe_integer(self):
        for bad in (0, -1, True, 1.5, "7", None):
            with self.subTest(bad=bad):
                with self.assertRaises(ProtocolValidationError):
                    validate_character(_valid_panel(member_id=bad))


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_version_four_payloads_reject_everywhere(self):
        # The transitional v4 tolerance is closed (render-equipment-
        # breakdown-webclient): a v4 payload rejects on the version gate,
        # and a v4 trait row smuggled under version 5 rejects on the exact
        # breakdown-shape rules.
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(schema_version=4))
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    traits=[{"key": "hp", "label": "生命", "current": 10, "max": 10}]
                )
            )


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_v5_trait_layer_validation_is_exact(self):
        normalized = validate_character(
            _valid_panel(traits=[_trait(layers=[_layer()])])
        )
        self.assertEqual(normalized["traits"][0]["layers"], [_layer()])
        for bad in (
            _layer(source="innate"),
            _layer(kind="percent"),
            _layer(amount=0),
            _layer(amount="15"),
            _layer(amount=float("nan")),
            _layer(amount=float("inf")),
            _layer(amount=True),
            _layer(name=" "),
            {k: v for k, v in _layer().items() if k != "kind"},
            {**_layer(), "extra": 1},
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ProtocolValidationError):
                    validate_character(_valid_panel(traits=[_trait(layers=[bad])]))
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(
                    traits=[
                        _trait(layers=[_layer() for _ in range(MAX_LAYERS_PER_STAT + 1)])
                    ]
                )
            )
        # Fractional scaled-grant amounts ride as floats; negative signed too.
        normalized = validate_character(
            _valid_panel(
                traits=[
                    _trait(
                        key="defense",
                        label="防禦",
                        base=5,
                        current=7.5,
                        max=None,
                        effective=7.5,
                        layers=[_layer(kind="flat", amount=-2.5, source="condition", name="劇毒")],
                    )
                ]
            )
        )
        self.assertEqual(normalized["traits"][0]["layers"][0]["amount"], -2.5)
        # The defining row contract: statics expose effective through
        # current; gauges carry effective == max. Contradictions reject.
        for contradiction in (
            _trait(key="atk_phys", label="攻擊", base=10, current=10, max=None, effective=15),
            _trait(key="hp", base=100, current=40, max=115, effective=100),
        ):
            with self.subTest(row=contradiction["key"]):
                with self.assertRaises(ProtocolValidationError):
                    validate_character(_valid_panel(traits=[contradiction]))


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_v5_equipment_rows_require_the_adjustment_summary(self):
        normalized = validate_character(
            _valid_panel(equipment=[_equipment_row(adjustment="攻擊 −2｜防禦 ＋8")])
        )
        self.assertEqual(
            normalized["equipment"][0]["adjustment"], "攻擊 −2｜防禦 ＋8"
        )
        row = _equipment_row()
        del row["adjustment"]
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(equipment=[row]))
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(equipment=[_equipment_row(adjustment=None)]))


    def test_rejects_unknown_and_missing_fields(self):
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(bogus=1))
        payload = _valid_panel()
        del payload["wallet"]
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)
        payload = _valid_panel()
        del payload["actives"]
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)


    def test_trait_max_consistency(self):
        # Gauge row {current: 0, max: 0, effective: 0} validates
        normalized = validate_character(
            _valid_panel(traits=[_trait(current=0, max=0, effective=0)])
        )
        self.assertEqual(normalized["traits"][0]["max"], 0)
        self.assertEqual(normalized["traits"][0]["current"], 0)
        self.assertEqual(normalized["traits"][0]["effective"], 0)

        # {current: 3, max: 0} still rejects
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(traits=[_trait(current=3, max=0, effective=0)])
            )

        # effective != max still rejects
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(traits=[_trait(current=0, max=0, effective=1)])
            )

        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(traits=[_trait(current=11, max=10)])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(traits=[_trait(key="hp"), _trait(key="hp")])
            )


    def test_disguise_requires_empty_displayed_when_inactive(self):
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    disguise={
                        "active": False,
                        "description": "",
                        "displayed": [{"key": "atk_phys", "label": "攻擊", "value": 12}],
                    }
                )
            )


    def test_active_disguise_requires_description(self):
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    disguise={
                        "active": True,
                        "description": "  ",
                        "displayed": [],
                    }
                )
            )


if __name__ == "__main__":
    unittest.main()
