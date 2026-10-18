"""Character panel schema tests: byte-envelope, label/value bounds, and intimate-field validation."""
from tools.spec_traceability import covers_requirement
import unittest
from web.webclient.presentation.character import MAX_ACTIVE_ROWS, MAX_CATEGORY_GROUPS, MAX_CONDITION_ROWS, MAX_DISPLAYED_ROWS, MAX_EQUIPMENT_ROWS, MAX_FULL_TITLE_CODE_POINTS, MAX_LABEL_CODE_POINTS, MAX_MODIFIER_KEYS, MAX_PASSIVE_ROWS, MAX_SELECTED_LINEAGE_ROWS, MAX_TRAIT_ROWS, CharacterPanelError, validate_character
from web.webclient.presentation.protocol import MAX_CANONICAL_JSON_BYTES, ProtocolValidationError, json_byte_size
from ._support import _active_row, _skill_categories, _trait, _valid_panel


class CharacterSchemaTests(unittest.TestCase):

    def test_maximal_payload_fits_the_envelope(self):
        # Every section is present with its row count at its cap, and every
        # active row carries its growth facts plus the registry detail; the
        # selected skill carries both eight-edge lineage lists and the full
        # ladder. Text uses long labels rather than the per-field maximum: the
        # pre-existing D10 contract bounds the envelope by serialized size (a
        # simultaneous maximum of 32 traits x 16 layers x 128-code-point names
        # cannot conform at all), so this fixture pins the v9 additions at full
        # row counts.
        label = "很長的屬性名稱" * 2
        traits = [
            _trait(
                key=f"trait_{i}",
                label=label,
                current=1000,
                effective=1000,
                max=None if i % 2 else 1000,
            )
            for i in range(MAX_TRAIT_ROWS)
        ]
        conditions = [
            {
                "code": f"condition_{i}",
                "label": label,
                "severity": "beneficial",
                "remaining_seconds": 30,
                "modifiers": {
                    f"modifier_{m}": -10 for m in range(MAX_MODIFIER_KEYS)
                },
                "source": "狀態",
            }
            for i in range(MAX_CONDITION_ROWS)
        ]
        actives = [
            {
                "category": f"cat_{c}",
                "label": label,
                "groups": [
                    {
                        "group": f"group_{c}",
                        "label": label,
                        "skills": [
                            _active_row(
                                f"active_{i}",
                                label=label,
                                level=9,
                                xp_into_level=49,
                                xp_to_next_level=1,
                                cost={"mp": 12, "sp": 3},
                                target_spec="single",
                                usable_out_of_combat=True,
                            )
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
                "label": label,
                "groups": [
                    {
                        "group": None,
                        "label": None,
                        "skills": [
                            {"key": f"passive_{i}", "label": label}
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
                "display_name": label,
                "adjustment": "",
            }
            for i in range(MAX_EQUIPMENT_ROWS)
        ]
        displayed = [
            {"key": f"stat_{i}", "label": label, "value": 1000}
            for i in range(MAX_DISPLAYED_ROWS)
        ]
        payload = _valid_panel(
            traits=traits,
            conditions=conditions,
            actives=actives,
            passives=passives,
            equipment=equipment,
            full_title="長" * MAX_FULL_TITLE_CODE_POINTS,
            selected_skill={
                "key": "active_0",
                "lineage": {
                    "prerequisites": [
                        {
                            "key": f"parent_{i}",
                            "label": "長" * (MAX_LABEL_CODE_POINTS // 2),
                            "level": 1,
                        }
                        for i in range(MAX_SELECTED_LINEAGE_ROWS)
                    ],
                    "next": [
                        {
                            "key": f"child_{i}",
                            "label": "長" * (MAX_LABEL_CODE_POINTS // 2),
                            "min_level": 1,
                        }
                        for i in range(MAX_SELECTED_LINEAGE_ROWS)
                    ],
                },
                "freeform_ladder": [
                    {"scale": 0.25, "label": "1/4", "mp_cost": 3},
                    {"scale": 0.5, "label": "1/2", "mp_cost": 6},
                    {"scale": 1, "label": "1", "mp_cost": 11},
                    {"scale": 2, "label": "2", "unlock_level": 6},
                    {"scale": 4, "label": "4", "unlock_level": 10},
                ],
            },
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


    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-8-panel")
    def test_maximal_condition_rows_fit_the_envelope(self):
        # The newly added section's own maximal legal payload (32 rows, a
        # 128-code-point label, 16 modifier pairs and a 32-code-point source)
        # must still serialize inside the canonical byte bound.
        conditions = [
            {
                "code": f"condition_{index}",
                "label": "很長的狀態名稱" * 8,
                "severity": "warning",
                "remaining_seconds": 9999,
                "modifiers": {
                    f"modifier_{key}": "-10%" for key in range(MAX_MODIFIER_KEYS)
                },
                "source": "裝備、狀態",
            }
            for index in range(MAX_CONDITION_ROWS)
        ]
        normalized = validate_character(_valid_panel(conditions=conditions))
        self.assertEqual(len(normalized["conditions"]), MAX_CONDITION_ROWS)
        self.assertLessEqual(json_byte_size(normalized), MAX_CANONICAL_JSON_BYTES)


    def test_persona_and_intimate_are_not_part_of_the_v8_shape(self):
        for field, value in (
            ("persona", {"background": None}),
            ("intimate", None),
        ):
            with self.subTest(field=field):
                with self.assertRaises(ProtocolValidationError):
                    validate_character(_valid_panel(**{field: value}))


    def test_flattened_row_count_bound_applies_not_the_category_group_count(self):
        # The bound applies to the flattened row total across every category
        # and sub-group: a payload with few category groups but more than
        # MAX_*_ROWS flattened rows must be rejected (design D-6).
        for field in ("actives", "passives"):
            with self.subTest(field=field):
                bound = MAX_ACTIVE_ROWS if field == "actives" else MAX_PASSIVE_ROWS
                row = _active_row if field == "actives" else None
                payload = _valid_panel(
                    **{
                        field: _skill_categories(
                            [f"skill_{i}" for i in range(bound + 1)], row=row
                        )
                    }
                )
                with self.assertRaises(CharacterPanelError):
                    validate_character(payload)
                payload = _valid_panel(
                    **{
                        field: [
                            *_skill_categories(
                                [f"skill_{i}" for i in range(bound // 2)], row=row
                            ),
                            *_skill_categories(
                                [f"skill_{i}" for i in range(bound // 2)],
                                category="enhancement",
                                label="強化",
                                row=row,
                            ),
                        ]
                    }
                )
                validate_character(payload)


    @covers_requirement("webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel")
    def test_actives_boundary_admits_96_rows_and_rejects_97(self):
        # The flattened actives bound admits exactly MAX_ACTIVE_ROWS rows
        # spread across the eight category groups and rejects one more, while
        # an equally-shaped over-bound passives payload still fails under its
        # own unchanged MAX_PASSIVE_ROWS bound (design D6).
        def actives(total):
            return [
                {
                    "category": f"cat_{c}",
                    "label": "分類",
                    "groups": [
                        {
                            "group": None,
                            "label": None,
                            "skills": [
                                _active_row(f"active_{i}", label="主動技能")
                                for i in range(c, total, MAX_CATEGORY_GROUPS)
                            ],
                        }
                    ],
                }
                for c in range(MAX_CATEGORY_GROUPS)
            ]

        at_bound = _valid_panel(actives=actives(MAX_ACTIVE_ROWS))
        self.assertEqual(
            sum(
                len(group["skills"])
                for category in at_bound["actives"]
                for group in category["groups"]
            ),
            MAX_ACTIVE_ROWS,
        )
        validate_character(at_bound)
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(actives=actives(MAX_ACTIVE_ROWS + 1))
            )
        with self.assertRaises(CharacterPanelError):
            validate_character(
                _valid_panel(
                    passives=_skill_categories(
                        [f"passive_{i}" for i in range(MAX_PASSIVE_ROWS + 1)],
                        category="enhancement",
                        label="強化",
                    )
                )
            )


    def test_every_real_category_plus_the_unknown_fallback_fits_the_bound(self):
        # The category-group bound must leave room for the synthetic fallback:
        # an entity owning skills in all seven SkillCategory members plus one
        # unregistered key serializes eight category groups and must stay valid.
        categories = [
            "elemental_magic",
            "martial_arts",
            "enhancement",
            "divine_mystery",
            "utility",
            "sexual_act",
            "holy_rite",
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
                                _active_row(f"a{i}", label=wide)
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
