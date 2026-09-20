"""Character panel schema tests: byte-envelope, label/value bounds, and intimate-field validation."""
from tools.spec_traceability import covers_requirement
import unittest
from web.webclient.presentation.character import MAX_ACTIVE_ROWS, MAX_CATEGORY_GROUPS, MAX_DISPLAYED_ROWS, MAX_EQUIPMENT_ROWS, MAX_LABEL_CODE_POINTS, MAX_PASSIVE_ROWS, MAX_TRAIT_ROWS, CharacterPanelError, validate_character
from web.webclient.presentation.protocol import MAX_CANONICAL_JSON_BYTES, ProtocolValidationError, json_byte_size
from ._support import _skill_categories, _trait, _valid_panel


class CharacterSchemaTests(unittest.TestCase):

    def test_worst_case_legal_payload_fits_the_envelope(self):
        traits = [
            _trait(
                key=f"trait_{i}",
                label="很長的屬性名稱" * 3,
                current=1000,
                effective=1000,
                max=None if i % 2 else 1000,
            )
            for i in range(MAX_TRAIT_ROWS)
        ]
        actives = [
            {
                "category": f"cat_{c}",
                "label": "很長的主動技能分類" * 3,
                "groups": [
                    {
                        "group": f"group_{c}",
                        "label": "很長的子分類名稱" * 3,
                        "skills": [
                            {"key": f"active_{i}", "label": "很長的主動技能名稱" * 3}
                            for i in range(c, MAX_ACTIVE_ROWS, MAX_CATEGORY_GROUPS)
                        ],
                    }
                ],
            }
            for c in range(MAX_CATEGORY_GROUPS)
        ]
        passives = [
            {
                "category": f"cat_{c}",
                "label": "很長的被動技能分類" * 3,
                "groups": [
                    {
                        "group": None,
                        "label": None,
                        "skills": [
                            {"key": f"passive_{i}", "label": "很長的主動技能名稱" * 3}
                            for i in range(c, MAX_PASSIVE_ROWS, MAX_CATEGORY_GROUPS)
                        ],
                    }
                ],
            }
            for c in range(MAX_CATEGORY_GROUPS)
        ]
        equipment = [
            {
                "slot": "weapon_main",
                "item_key": f"item_{i}",
                "display_name": "很長的裝備名稱" * 3,
                "adjustment": "",
            }
            for i in range(MAX_EQUIPMENT_ROWS)
        ]
        displayed = [
            {"key": f"stat_{i}", "label": "很長的顯示數值名稱" * 3, "value": 1000}
            for i in range(MAX_DISPLAYED_ROWS)
        ]
        payload = _valid_panel(
            traits=traits,
            actives=actives,
            passives=passives,
            equipment=equipment,
            disguise={
                "active": True,
                "description": "偽裝中的描述文字" * 10,
                "displayed": displayed,
            },
        )
        normalized = validate_character(payload)
        size = json_byte_size(normalized)
        self.assertLessEqual(size, MAX_CANONICAL_JSON_BYTES)


    def test_rejects_blank_labels_and_over_bound_values(self):
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(traits=[_trait(label="  ")]))
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(passives=[_skill_categories(["x"], category="x" * 65)])
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    passives=[
                        {
                            "category": "enhancement",
                            "label": "強化",
                            "groups": [
                                {"group": "g", "label": None, "skills": []}
                            ],
                        }
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    passives=[
                        {
                            "category": "enhancement",
                            "label": "強化",
                            "groups": [
                                {"group": None, "label": None, "skills": [{"key": "x", "label": "  "}]}
                            ],
                        }
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    passives=[
                        {
                            "category": "enhancement",
                            "label": "強化",
                            "groups": [],
                        }
                    ]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    equipment=[{"slot": " ", "item_key": "x", "display_name": "劍"}]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    equipment=[{"slot": "w", "item_key": "x", "display_name": "  "}]
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    disguise={
                        "active": True,
                        "description": "偽裝中",
                        "displayed": [{"key": "k", "label": "  ", "value": 1}],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(
                _valid_panel(
                    disguise={
                        "active": True,
                        "description": "偽裝中",
                        "displayed": [
                            {"key": f"k{i}", "label": "數值", "value": i}
                            for i in range(MAX_DISPLAYED_ROWS + 1)
                        ],
                    }
                )
            )
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(guild={"rank": " ", "merit": 0}))
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(traits=[_trait(key="x" * 65)]))


    def test_rejects_wrong_version_kind_and_row_counts(self):
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(schema_version=1))
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(schema_version=2))
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(schema_version=3))
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(schema_version="4"))
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(schema_version=5))
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(available=False))
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(kind="services"))
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(traits=[_trait() for _ in range(MAX_TRAIT_ROWS + 1)])
            )
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(
                    actives=[
                        {
                            "category": f"cat_{i}",
                            "label": "分類",
                            "groups": [{"group": None, "label": None, "skills": []}],
                        }
                        for i in range(MAX_CATEGORY_GROUPS + 1)
                    ]
                )
            )
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(
                    equipment=[
                        {"slot": "w", "item_key": "x", "display_name": "劍"}
                        for _ in range(MAX_EQUIPMENT_ROWS + 1)
                    ]
                )
            )


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-7-panel")
    def test_intimate_field_validation(self):
        # ``intimate: None`` is valid — the section is omitted when the actor has
        # no sexual-state record.
        normalized = validate_character(_valid_panel())
        self.assertIsNone(normalized["intimate"])

        # A populated intimate section is validated against its fixed vocabulary.
        intimate = {
            "arousal": "中等",
            "wetness": "微濕",
            "shame": "輕微",
            "exposure": "低",
            "climax_phase": "未達",
            "climax_today": 2,
        }
        normalized = validate_character(_valid_panel(intimate=intimate))
        self.assertEqual(normalized["intimate"], intimate)

        # Unknown fields are rejected.
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(intimate={**intimate, "bogus": 1}))

        # Missing fields are rejected.
        partial = dict(intimate)
        del partial["climax_phase"]
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(intimate=partial))

        # A level word that is not a member of the fixed vocabulary is rejected.
        bad = dict(intimate)
        bad["arousal"] = "很高"
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(intimate=bad))

        # Non-string level fields are rejected.
        bad = dict(intimate)
        bad["wetness"] = 1
        with self.assertRaises(ProtocolValidationError):
            validate_character(_valid_panel(intimate=bad))

        # ``climax_today`` must be a non-negative integer.
        for value in (True, -1, "2"):
            bad = dict(intimate)
            bad["climax_today"] = value
            with self.assertRaises(ProtocolValidationError):
                validate_character(_valid_panel(intimate=bad))


    def test_flattened_row_count_bound_applies_not_the_category_group_count(self):
        # The bound applies to the flattened row total across every category
        # and sub-group: a payload with few category groups but more than
        # MAX_*_ROWS flattened rows must be rejected (design D-6).
        for field in ("actives", "passives"):
            with self.subTest(field=field):
                bound = MAX_ACTIVE_ROWS if field == "actives" else MAX_PASSIVE_ROWS
                payload = _valid_panel(
                    **{
                        field: _skill_categories(
                            [f"skill_{i}" for i in range(bound + 1)]
                        )
                    }
                )
                with self.assertRaises(CharacterPanelError):
                    validate_character(payload)
                payload = _valid_panel(
                    **{
                        field: [
                            *_skill_categories([f"skill_{i}" for i in range(bound // 2)]),
                            *_skill_categories(
                                [f"skill_{i}" for i in range(bound // 2)],
                                category="enhancement",
                                label="強化",
                            ),
                        ]
                    }
                )
                validate_character(payload)


    def test_every_real_category_plus_the_unknown_fallback_fits_the_bound(self):
        # The category-group bound must leave room for the synthetic fallback:
        # an entity owning skills in all six SkillCategory members plus one
        # unregistered key serializes seven category groups and must stay valid.
        categories = [
            "elemental_magic",
            "martial_arts",
            "enhancement",
            "divine_mystery",
            "utility",
            "sexual_act",
        ]
        groups = []
        for category in categories:
            groups.extend(
                _skill_categories(
                    [f"skill_{category}"], category=category, label="分類"
                )
            )
        groups.extend(_skill_categories(["no_such_skill"], category="unknown"))
        payload = _valid_panel(passives=groups)
        normalized = validate_character(payload)
        self.assertEqual(
            len(normalized["passives"]), MAX_CATEGORY_GROUPS
        )


    def test_over_limit_envelope_fails_closed(self):
        wide = "😀" * MAX_LABEL_CODE_POINTS
        payload = _valid_panel(
            traits=[_trait(key=f"t{i}", label=wide) for i in range(MAX_TRAIT_ROWS)],
            actives=[
                {
                    "category": "elemental_magic",
                    "label": "元素魔法",
                    "groups": [
                        {
                            "group": "t_合成",
                            "label": "合成分組",
                            "skills": [
                                {"key": f"a{i}", "label": wide}
                                for i in range(MAX_ACTIVE_ROWS)
                            ],
                        }
                    ],
                }
            ],
            passives=[
                {
                    "category": "enhancement",
                    "label": "強化",
                    "groups": [
                        {
                            "group": None,
                            "label": None,
                            "skills": [
                                {"key": f"p{i}", "label": wide}
                                for i in range(MAX_PASSIVE_ROWS)
                            ],
                        }
                    ],
                }
            ],
            equipment=[
                {
                    "slot": "weapon_main",
                    "item_key": f"i{i}",
                    "display_name": wide,
                    "adjustment": "",
                }
                for i in range(MAX_EQUIPMENT_ROWS)
            ],
            disguise={
                "active": True,
                "description": wide,
                "displayed": [
                    {"key": f"d{i}", "label": wide, "value": 1}
                    for i in range(MAX_DISPLAYED_ROWS)
                ],
            },
        )
        with self.assertRaises(CharacterPanelError):
            validate_character(payload)


if __name__ == "__main__":
    unittest.main()
