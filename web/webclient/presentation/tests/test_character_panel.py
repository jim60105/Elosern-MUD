"""Exact ``character`` schema, presenter, and parity tests.

Covers the D10 shared bounds, the version-3 payload validation (category-
grouped ``actives``/``passives``), true-vs-disguised values, the empty
displayed list when undisguised, read-only guarantees, and the
status-vs-character parity proving both panels share the same canonical trait
source.
Version 5 (expose-stat-breakdown-read-model) adds the breakdown trait rows
(``base``/``effective``/``layers``) and the equipment ``adjustment`` summary;
render-equipment-breakdown-webclient closed the transitional tolerance
window: version 5 is the only accepted schema version, and v4 payloads
reject.
"""

from tools.spec_traceability import covers_requirement

import unittest
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage

from typeclasses.characters import PlayerCharacter
from web.webclient.presentation.character import (
    CHARACTER_SCHEMA_VERSION,
    MAX_ACTIVE_ROWS,
    MAX_CATEGORY_GROUPS,
    MAX_DISPLAYED_ROWS,
    MAX_EQUIPMENT_ROWS,
    MAX_KEY_CODE_POINTS,
    MAX_LABEL_CODE_POINTS,
    MAX_LAYERS_PER_STAT,
    MAX_PASSIVE_ROWS,
    MAX_SLOT_CODE_POINTS,
    MAX_TRAIT_ROWS,
    CharacterPanelError,
    validate_character,
)
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.protocol import (
    MAX_CANONICAL_JSON_BYTES,
    ProtocolValidationError,
    json_byte_size,
)
from web.webclient.presentation.registry import build_production_registry
from world.rules.clock import get_world_clock
from world.rules.guild import register_adventurer
from world.rules.status_query import StatusQueryError
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY

# ``flee`` is injected into ``SKILL_REGISTRY`` at import time by
# ``world.rules.disengage``, so the presenter tests import it explicitly to
# keep the innate skills in scope.
import world.rules.disengage  # noqa: F401  (registers flee)


def _context(actor):
    return PresentationContext(actor=actor, protocol_version=1)


def _trait(**overrides):
    value = {
        "key": "hp",
        "label": "生命",
        "base": 10,
        "current": 10,
        "max": 10,
        "effective": 10,
        "layers": [],
    }
    value.update(overrides)
    return value


def _layer(**overrides):
    value = {"source": "equipment", "name": "騎士全套板甲", "kind": "flat", "amount": 15}
    value.update(overrides)
    return value


def _equipment_row(**overrides):
    value = {
        "slot": "weapon_main",
        "item_key": "plain_sword",
        "display_name": "鐵劍",
        "adjustment": "",
    }
    value.update(overrides)
    return value


def _skill_categories(keys, category="elemental_magic", label="元素魔法"):
    """One minimal valid category group carrying the given keys as rows."""
    return [
        {
            "category": category,
            "label": label,
            "groups": [
                {
                    "group": None,
                    "label": None,
                    "skills": [{"key": key, "label": key} for key in keys],
                }
            ],
        }
    ]


def _flattened_keys(category_groups):
    """The ordered skill keys across every category and sub-group."""
    return [
        row["key"]
        for category in category_groups
        for group in category["groups"]
        for row in group["skills"]
    ]


def _skill_categories_enriched(keys, category="elemental_magic", label="元素魔法", group="fire", group_label="火"):
    """One valid category group carrying registry-backed detail on every row."""
    scales = [
        {"scale": 0.25, "label": "1/4", "mp_cost": 4},
        {"scale": 0.5, "label": "1/2", "mp_cost": 7},
        {"scale": 1, "label": "1", "mp_cost": 14},
        {"scale": 2, "label": "2", "mp_cost": 28},
        {"scale": 4, "label": "4", "mp_cost": 56},
    ]
    return [
        {
            "category": category,
            "label": label,
            "groups": [
                {
                    "group": group,
                    "label": group_label,
                    "skills": [
                        {
                            "key": key,
                            "label": key,
                            "cost": {"mp": 14},
                            "target_spec": "single",
                            "usable_out_of_combat": True,
                            "freeform_scales": scales,
                        }
                        for key in keys
                    ],
                }
            ],
        }
    ]


def _valid_panel(**overrides):
    value = {
        "schema_version": CHARACTER_SCHEMA_VERSION,
        "available": True,
        "kind": "character",
        "traits": [_trait(), _trait(key="atk_phys", label="攻擊", base=5, current=5, max=None, effective=5)],
        "actives": _skill_categories(["fire_ball"]),
        "passives": _skill_categories(
            ["defense_instinct"], category="enhancement", label="強化"
        ),
        "equipment": [_equipment_row()],
        "disguise": {
            "active": False,
            "description": "",
            "displayed": [],
        },
        "guild": {"rank": None, "merit": 0},
        "wallet": 100,
        "persona": {"background": None},
        "intimate": None,
    }
    value.update(overrides)
    return value


class CharacterSchemaTests(unittest.TestCase):
    def test_valid_panel_passes(self):
        normalized = validate_character(_valid_panel())
        self.assertEqual(normalized["schema_version"], CHARACTER_SCHEMA_VERSION)
        self.assertTrue(normalized["available"])
        self.assertEqual(normalized["kind"], "character")

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-5-panel")
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

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-5-panel")
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
                        layers=[_layer(kind="flat", amount=-2.5, source="condition", name="剧毒")],
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

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-5-panel")
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
            validate_character(_valid_panel(schema_version=6))
        with self.assertRaises(CharacterPanelError):
            validate_character(_valid_panel(schema_version="4"))
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

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-5-panel")
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

    @covers_requirement(
        "webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel"
    )
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
        # an entity owning skills in all eight SkillCategory members plus one
        # unregistered key serializes nine category groups and must stay valid.
        categories = [
            "elemental_magic",
            "martial_arts",
            "enhancement",
            "innate_gift",
            "movement",
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
                            "group": "fire",
                            "label": "火",
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

    def test_active_row_with_registry_backed_detail_fields_validates(self):
        normalized = validate_character(_valid_panel(actives=_skill_categories_enriched(["fire_ball"])))
        row = normalized["actives"][0]["groups"][0]["skills"][0]
        self.assertEqual(row["cost"], {"mp": 14})
        self.assertEqual(row["target_spec"], "single")
        self.assertIs(row["usable_out_of_combat"], True)
        self.assertEqual(len(row["freeform_scales"]), 5)

    def test_active_row_detail_fields_are_omittable(self):
        normalized = validate_character(_valid_panel(actives=_skill_categories(["fire_ball"])))
        row = normalized["actives"][0]["groups"][0]["skills"][0]
        self.assertEqual(set(row), {"key", "label"})

    def test_active_row_rejects_malformed_detail_fields(self):
        payload = _valid_panel(actives=_skill_categories(["fire_ball"]))
        payload["actives"][0]["groups"][0]["skills"][0]["shorthands"] = ["all"]
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)
        payload = _valid_panel(actives=_skill_categories(["fire_ball"]))
        payload["actives"][0]["groups"][0]["skills"][0]["target_spec"] = "wild"
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)
        payload = _valid_panel(actives=_skill_categories(["fire_ball"]))
        payload["actives"][0]["groups"][0]["skills"][0]["usable_out_of_combat"] = "yes"
        with self.assertRaises(ProtocolValidationError):
            validate_character(payload)

    def test_freeform_scales_without_an_mp_cost_fails_closed(self):
        # The empty cost object (the free form) and a zero mp cost both fail
        # closed when freeform_scales is present.
        for mp_value in (None, 0):
            with self.subTest(mp_value=mp_value):
                payload = _valid_panel(actives=_skill_categories_enriched(["fire_ball"]))
                cost = {} if mp_value is None else {"mp": mp_value}
                payload["actives"][0]["groups"][0]["skills"][0]["cost"] = cost
                with self.assertRaises(ProtocolValidationError):
                    validate_character(payload)

    def test_explicit_null_detail_fields_are_rejected(self):
        # The JS mirror rejects present-but-null optional fields; Python must
        # agree (schema parity, fix-webclient-skillbook-descriptor-data).
        for null_field in ("cost", "target_spec", "usable_out_of_combat"):
            with self.subTest(null_field=null_field):
                candidate = _valid_panel(actives=_skill_categories(["fire_ball"]))
                candidate["actives"][0]["groups"][0]["skills"][0][null_field] = None
                with self.assertRaises(ProtocolValidationError):
                    validate_character(candidate)
        # A null freeform_scales is accepted and the field is omitted.
        normalized = validate_character(
            _valid_panel(actives=_skill_categories_enriched(["fire_ball"]))
        )
        row = normalized["actives"][0]["groups"][0]["skills"][0]
        self.assertEqual(
            row["freeform_scales"],
            [
                {"scale": 0.25, "label": "1/4", "mp_cost": 4},
                {"scale": 0.5, "label": "1/2", "mp_cost": 7},
                {"scale": 1, "label": "1", "mp_cost": 14},
                {"scale": 2, "label": "2", "mp_cost": 28},
                {"scale": 4, "label": "4", "mp_cost": 56},
            ],
        )
        null_scales = _valid_panel(actives=_skill_categories_enriched(["fire_ball"]))
        null_scales["actives"][0]["groups"][0]["skills"][0]["freeform_scales"] = None
        normalized = validate_character(null_scales)
        self.assertNotIn("freeform_scales", normalized["actives"][0]["groups"][0]["skills"][0])

    def test_worst_case_active_rows_with_detail_fields_fit_the_envelope(self):
        # Every one of the 32 active rows carries cost + target_spec +
        # usable_out_of_combat + the full five-entry freeform_scales set.
        actives = _skill_categories_enriched([f"active_{i}" for i in range(MAX_ACTIVE_ROWS)])
        payload = _valid_panel(actives=actives)
        normalized = validate_character(payload)
        self.assertLessEqual(json_byte_size(normalized), MAX_CANONICAL_JSON_BYTES)
        self.assertEqual(_flattened_keys(normalized["actives"]), _flattened_keys(actives))


class CharacterPresenterTests(BattlefieldIsolation, EvenniaTest):
    def setUp(self):
        super().setUp()
        # Register the quest catalog in this class's own setup: the affinity
        # rulebook load (reached through guild registration) resolves
        # ``introductory_hunt`` from the definition registry, so this class
        # must not depend on an earlier test to have registered it.
        from world.quests.catalog import register_catalog

        register_catalog()
        get_world_clock()
        self.player = create_object(PlayerCharacter, key="角色狀態測試")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.db.wallet = 500
        grant_lineage(self.player, ["fire_ball"], ["defense_instinct"])
        self.player.db.equipment = {
            "weapon_main": "plain_sword",
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        self.player.save()

    def _registry(self):
        return build_production_registry()

    def _render(self):
        return self._registry().render("character", _context(self.player))

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-5-panel")
    def test_character_renders_true_values_without_mutation(self):
        before_traits = dict(self.player.attributes.get("traits", category="traits"))
        before_wallet = self.player.db.wallet
        before_equipment = self.player.db.equipment
        payload = self._render()
        self.assertTrue(payload["available"])
        self.assertEqual(payload["kind"], "character")
        self.assertEqual(payload["schema_version"], CHARACTER_SCHEMA_VERSION)
        hp = next(row for row in payload["traits"] if row["key"] == "hp")
        self.assertEqual(hp["max"], self.player.traits.hp.max)
        self.assertEqual(hp["current"], self.player.traits.hp.current)
        self.assertEqual(hp["effective"], self.player.traits.hp.max)
        self.assertEqual(hp["base"], before_traits["hp"].get("base"))
        self.assertEqual(hp["layers"], [])
        atk = next(row for row in payload["traits"] if row["key"] == "atk_phys")
        # v5: the plain_sword's +2 flat rides as a named equipment layer and
        # the total-display current equals the authoritative effective.
        from world.rules.combat import _adjusted_attack

        self.assertEqual(atk["base"], self.player.traits.atk_phys.base)
        self.assertEqual(atk["effective"], _adjusted_attack(self.player, "atk_phys"))
        self.assertEqual(atk["current"], atk["effective"])
        self.assertIsNone(atk["max"])
        self.assertEqual([layer["source"] for layer in atk["layers"]], ["equipment"])
        self.assertEqual(
            _flattened_keys(payload["actives"]),
            [
                "fire_ball",
                # The lineage closure owns fire_arrow alongside fire_ball.
                "fire_arrow",
                "basic_attack",
                "flee",
                *sorted(
                    key
                    for key, act in SEXUAL_ACT_REGISTRY.items()
                    if not act.unlock
                ),
            ],
        )
        self.assertEqual(
            _flattened_keys(payload["passives"]),
            ["defense_instinct"],
        )
        self.assertEqual(payload["equipment"][0]["slot"], "weapon_main")
        self.assertEqual(payload["wallet"], 500)
        # Byte-for-byte unchanged canonical state.
        self.assertEqual(
            dict(self.player.attributes.get("traits", category="traits")),
            before_traits,
        )
        self.assertEqual(self.player.db.wallet, before_wallet)
        self.assertEqual(self.player.db.equipment, before_equipment)

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-5-panel")
    @covers_requirement(
        "webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-5-panel",
        "webclient-exploration-menu::character-panel-skills-are-grouped-by-category-with-the-same-ordering-rule-as-the-combat-panel",
    )
    def test_innate_active_skills_are_visible_for_the_first_time(self):
        self.player.db.skills = {"active": [], "passive": []}
        payload = self._render()
        # Category order follows SkillCategory declaration order, so
        # martial_arts (basic_attack) precedes movement (flee); the
        # unconditionally-owned acts follow as the sexual_act category.
        self.assertEqual(
            _flattened_keys(payload["actives"]),
            [
                "basic_attack",
                "flee",
                *sorted(
                    key
                    for key, act in SEXUAL_ACT_REGISTRY.items()
                    if not act.unlock
                ),
            ],
        )
        martial = next(
            category for category in payload["actives"]
            if category["category"] == "martial_arts"
        )
        self.assertEqual(
            [row["key"] for group in martial["groups"] for row in group["skills"]],
            ["basic_attack"],
        )
        movement = next(
            category for category in payload["actives"]
            if category["category"] == "movement"
        )
        self.assertEqual(
            [row["key"] for group in movement["groups"] for row in group["skills"]],
            ["flee"],
        )

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-5-panel")
    def test_expanded_state_shows_true_values_and_an_honest_disguise(self):
        self.player.db.disguised_stats = {"atk_phys": 12, "agility": 10}
        payload = self._render()
        self.assertTrue(payload["disguise"]["active"])
        self.assertTrue(payload["disguise"]["description"].strip())
        displayed = {row["key"]: row["value"] for row in payload["disguise"]["displayed"]}
        self.assertEqual(displayed, {"atk_phys": 12, "agility": 10})
        atk = next(row for row in payload["traits"] if row["key"] == "atk_phys")
        # True values: the literal base is never the disguised value, and the
        # total-display current tracks the true effective, not 12.
        self.assertEqual(atk["base"], self.player.traits.atk_phys.base)
        self.assertNotEqual(atk["base"], 12)
        self.assertNotEqual(atk["current"], 12)
        self.assertEqual(atk["current"], atk["effective"])

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-5-panel")
    def test_undisguised_actor_has_empty_displayed_list(self):
        payload = self._render()
        self.assertFalse(payload["disguise"]["active"])
        self.assertEqual(payload["disguise"]["displayed"], [])
        self.assertTrue(payload["traits"])

    def test_guild_rank_and_merit_are_reported(self):
        from typeclasses.components import GuildStaff
        from typeclasses.npcs import NPC
        from world.rules.surfaces import write_counter_trait

        self.player.location = self.room1
        staff = create_object(NPC, key="公會職員", location=self.room1)
        staff.components.add(
            GuildStaff.create(staff, service_id="staff", branch_key="guild_branch_altoria")
        )
        register_adventurer(self.player, staff=staff)
        write_counter_trait(self.player, "guild_merit", 60)
        payload = self._render()
        self.assertEqual(payload["guild"]["rank"], "F")
        self.assertEqual(payload["guild"]["merit"], 60)

    @covers_requirement("webclient-exploration-menu::the-character-panel-is-an-exact-read-only-version-5-panel")
    def test_status_character_parity_on_shared_values(self):
        status = self._registry().render("status", _context(self.player))
        character = self._render()
        self.assertTrue(status["available"])
        for key in ("hp", "mp", "sp"):
            gauge = status["resources"][key]
            row = next(row for row in character["traits"] if row["key"] == key)
            self.assertEqual(row["current"], gauge["current"])
            self.assertEqual(row["max"], gauge["maximum"])
        self.assertEqual(
            character["disguise"]["active"], status["disguise_active"]
        )

    def test_combat_mode_renders_unavailable_form(self):
        from typeclasses.monsters import Monster

        monster = create_object(Monster, key="哥布林", location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        from world.rules.combat_session import engage

        self.player.location = self.room1
        engage(self.player, monster)
        payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("traits", payload)

    def test_unknown_item_and_skill_degrade_to_their_keys(self):
        self.player.db.equipment = {
            "weapon_main": "no_such_item",
            "weapon_off": None,
            "armor": None,
            "accessories": [],
        }
        self.player.db.skills = {"active": [], "passive": ["no_such_skill"]}
        payload = self._render()
        row = next(r for r in payload["equipment"] if r["slot"] == "weapon_main")
        self.assertEqual(row["display_name"], "no_such_item")
        self.assertEqual(_flattened_keys(payload["passives"]), ["no_such_skill"])
        fallback = next(
            category for category in payload["passives"]
            if category["category"] == "unknown"
        )
        self.assertEqual(fallback["label"], "未知技能")
        self.assertEqual(fallback["groups"][0]["skills"][0]["label"], "no_such_skill")
        self.assertNotIn(
            "no_such_skill",
            _flattened_keys(payload["actives"]),
            "an unknown passive key must not leak into the actives listing",
        )

    def test_read_model_failure_renders_unavailable(self):
        with patch(
            "web.webclient.presentation.character.build_character_read_model",
            side_effect=StatusQueryError("broken"),
        ):
            payload = self._render()
        self.assertFalse(payload["available"])
        self.assertNotIn("traits", payload)

    @covers_requirement(
        "webclient-component-showcase::the-status-character-and-skill-surfaces-present-truthful-non-color-only-state"
    )
    def test_active_skill_rows_are_enriched_by_the_registry(self):
        payload = self._render()
        row = next(
            r
            for c in payload["actives"]
            for g in c["groups"]
            for r in g["skills"]
            if r["key"] == "fire_ball"
        )
        self.assertEqual(row["cost"], {"mp": 14})
        self.assertEqual(row["target_spec"], "single")
        self.assertIs(row["usable_out_of_combat"], False)
        self.assertNotIn("freeform_scales", row)
        # Passive rows stay bare {key, label}.
        for c in payload["passives"]:
            for g in c["groups"]:
                for r in g["skills"]:
                    self.assertEqual(set(r), {"key", "label"})

    @covers_requirement(
        "webclient-component-showcase::the-status-character-and-skill-surfaces-present-truthful-non-color-only-state"
    )
    def test_freeform_scales_populated_for_mastery_holder(self):
        # fire_ball's derived tip cap is Lv.3 (its consuming edges), so the
        # ladder can never unlock above the 1.0 rung for it (use-driven-
        # skill-lineage D6: a ceiling is the max consuming edge).
        grant_lineage(
            self.player,
            ["fire_ball"],
            ["defense_instinct", "fire_mastery"],
            rungs={"fire_ball": 3},
        )
        payload = self._render()
        row = next(
            r
            for c in payload["actives"]
            for g in c["groups"]
            for r in g["skills"]
            if r["key"] == "fire_ball"
        )
        # Ladder rungs available at the Lv.3 ceiling: 0.25/0.5/1.0.
        self.assertEqual(
            [entry["mp_cost"] for entry in row["freeform_scales"]],
            [4, 7, 14],
        )

    @covers_requirement(
        "webclient-component-showcase::the-status-character-and-skill-surfaces-present-truthful-non-color-only-state"
    )
    def test_unregistered_active_key_stays_bare_in_presenter(self):
        self.player.db.skills = {"active": ["no_such_skill"], "passive": []}
        payload = self._render()
        fallback = next(c for c in payload["actives"] if c["category"] == "unknown")
        self.assertEqual(
            fallback["groups"][0]["skills"][0],
            {"key": "no_such_skill", "label": "no_such_skill"},
        )


if __name__ == "__main__":
    unittest.main()
