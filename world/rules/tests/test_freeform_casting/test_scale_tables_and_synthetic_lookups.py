"""Slice of ``test_freeform_casting``: the shipped scale tables and the
synthetic mastery/skill lookups they drive.
"""
from tools.spec_traceability import covers_requirement
from dataclasses import replace
from unittest.mock import patch
import unittest
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from world.lore.elements import Element
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.action_preview import preview_skill, revalidate_submission
from world.rules.clock import WorldClock
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
)
from world.rules.combat_session import engage, submit_player_action
from world.rules.player_messages import rejection_message
from world.rules.progression import (
    FREEFORM_CAST_SCALES,
    FREEFORM_SCALE_LADDER,
    FREEFORM_SCALE_VALUES,
    _load_freeform_cast_scales,
    freeform_mastery_entitled,
    freeform_scale_entries_for,
    freeform_scales_for,
    scale_for_label,
    scale_label_for,
    scaled_magnitude,
    scaled_mp_cost,
)
from world.skills.cost_tiers import is_freeform_eligible
from world.skills.handler import ConferredSkillGrant
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS
from .._combat_session_helpers import (
    _monster_tier_key,
    _race_key,
    _behaviour_archetype_key,
    open_synthetic_scope,
)
from ..combat_fixtures import BattlefieldIsolation, grant_lineage


from ._support import (
    _T_CAST,
    _T_FOCUS_MP,
    _T_MIXED,
    _T_PHOENIX,
    _T_SP_SPELL,
    _T_STORM,
    _T_TIDE,
    _T_VEIL,
    _granted_mastery_only,
    _mastery_key,
    _mastery_row,
    _open_scope,
    _owned,
    _player,
)


class FreeformScaleTableTests(unittest.TestCase):
    """The closed scale table is fixed and load-validated (freeform-casting)."""

    @covers_requirement("freeform-casting::the-freeform-scale-table-is-a-fixed-load-validated-closed-set")
    def test_canonical_table_loads_ascending_with_labels(self):
        self.assertEqual(
            FREEFORM_CAST_SCALES,
            (
                (0.25, "1/4"),
                (0.5, "1/2"),
                (1.0, "1"),
                (2.0, "2"),
                (4.0, "4"),
            ),
        )
        self.assertEqual(FREEFORM_SCALE_VALUES, (0.25, 0.5, 1.0, 2.0, 4.0))
        self.assertEqual(scale_label_for(2.0), "2")
        self.assertEqual(scale_label_for(3.0), None)
        self.assertEqual(scale_for_label("1/2"), 0.5)
        self.assertEqual(scale_for_label("3"), None)

    @covers_requirement("freeform-casting::the-freeform-scale-table-is-a-fixed-load-validated-closed-set")
    def test_deviant_tables_are_rejected_at_load(self):
        base = [
            {"scale": 0.25, "label": "1/4"},
            {"scale": 0.5, "label": "1/2"},
            {"scale": 1.0, "label": "1"},
            {"scale": 2.0, "label": "2"},
            {"scale": 4.0, "label": "4"},
        ]
        cases = {
            "missing 1.0": base[:2] + base[3:],
            "duplicate scale": base[:2] + [{"scale": 0.5, "label": "x"}] + base[2:],
            "unsorted": [base[1], base[0], *base[2:]],
            "non-finite scale": [{"scale": float("nan"), "label": "nan"}, *base[1:]],
            "non-positive scale": [{"scale": -1.0, "label": "-1"}, *base[1:]],
            "empty label": [{"scale": 0.25, "label": "  "}, *base[1:]],
            "duplicate label": base[:2] + [{"scale": 0.75, "label": "1/2"}] + base[2:],
            "count other than five": base[:4],
            "non-object entry": [0.25, *base[1:]],
            "extra key": [{"scale": 0.25, "label": "1/4", "extra": 1}, *base[1:]],
            "non-canonical scale value": [
                {"scale": 0.75, "label": "3/4"},
                *base[1:],
            ],
            "swapped label pairing": [
                {"scale": 0.25, "label": "4"},
                {"scale": 0.5, "label": "1/2"},
                {"scale": 1.0, "label": "1"},
                {"scale": 2.0, "label": "2"},
                {"scale": 4.0, "label": "1/4"},
            ],
        }
        for name, table in cases.items():
            with self.subTest(case=name):
                with self.assertRaises(ValueError):
                    _load_freeform_cast_scales({"freeform_cast_scales": table})
        with self.assertRaises(ValueError):
            _load_freeform_cast_scales({})


class ScaledCostAndMagnitudeTests(unittest.TestCase):
    """Deterministic round-half-away-from-zero helpers (freeform-casting)."""

    @covers_requirement("freeform-casting::scaled-costs-and-magnitudes-use-deterministic-round-half-away-from-zero")
    def test_half_scale_of_an_even_cost_is_exact(self):
        self.assertEqual(scaled_mp_cost(14, 0.5), 7)
        self.assertEqual(scaled_magnitude(10, 0.5), 5)

    @covers_requirement("freeform-casting::scaled-costs-and-magnitudes-use-deterministic-round-half-away-from-zero")
    def test_fractional_results_round_half_away_from_zero(self):
        self.assertEqual(scaled_mp_cost(11, 0.5), 6)
        self.assertEqual(scaled_magnitude(5, 0.5), 3)
        self.assertEqual(scaled_mp_cost(150, 0.25), 38)
        self.assertEqual(scaled_mp_cost(11, 0.5), scaled_mp_cost(11, 0.5))

    @covers_requirement("freeform-casting::scaled-costs-and-magnitudes-use-deterministic-round-half-away-from-zero")
    def test_scaled_mp_cost_never_falls_below_one(self):
        self.assertEqual(scaled_mp_cost(1, 0.25), 1)
        self.assertEqual(scaled_mp_cost(2, 0.25), 1)
        self.assertEqual(scaled_mp_cost(1, 0.5), 1)

    @covers_requirement("freeform-casting::scaled-costs-and-magnitudes-use-deterministic-round-half-away-from-zero")
    def test_whole_scales_are_exact_and_invalid_inputs_raise(self):
        self.assertEqual(scaled_mp_cost(26, 2.0), 52)
        for base, scale in (
            (0, 1.0),
            (-1, 1.0),
            (1, 0.0),
            (1, -2.0),
            (1, float("nan")),
            (1, float("inf")),
            (True, 1.0),
            (1, True),
        ):
            with self.subTest(base=base, scale=scale):
                with self.assertRaises(ValueError):
                    scaled_mp_cost(base, scale)
                with self.assertRaises(ValueError):
                    scaled_magnitude(base, scale)


class FreeformEligibilityTests(unittest.TestCase):
    """is_freeform_eligible is a pure skill-shape predicate.

    Pure: the predicate never reads entity state or the registry, so the
    fixtures are file-local synthetic rows mirroring each shape class.
    """

    @covers_requirement("freeform-casting::is-freeform-eligible-is-a-pure-skill-shape-predicate")
    def test_pure_damage_and_heal_spells_are_eligible(self):
        for row in (
            _T_CAST,  # ACTIVE elemental single-target damage
            _T_STORM,  # same shape, heavier cost
            _T_TIDE,  # pure AREA heal
            _T_PHOENIX,  # damage + self-heal (all scalable prefixes)
        ):
            with self.subTest(skill=row.key):
                self.assertTrue(is_freeform_eligible(row))

    @covers_requirement("freeform-casting::is-freeform-eligible-is-a-pure-skill-shape-predicate")
    def test_buff_status_mixed_and_non_spell_skills_are_ineligible(self):
        for row in (
            _T_VEIL,  # self-buff only
            _T_MIXED,  # damage + buff mix
            _T_FOCUS_MP,  # non-elemental self-buff
            _T_SP_SPELL,  # elemental but no mp cost
            SYNTH_SKILLS["t_steady_stride"],  # PASSIVE
            _mastery_row(),  # PASSIVE mastery
        ):
            with self.subTest(skill=row.key):
                self.assertFalse(is_freeform_eligible(row))

    @covers_requirement("freeform-casting::is-freeform-eligible-is-a-pure-skill-shape-predicate")
    def test_effect_less_elemental_skill_is_ineligible(self):
        skill = replace(_T_CAST, key="t_hollow_spark", effects=[])
        self.assertFalse(is_freeform_eligible(skill))


class FreeformScalesForTests(EvenniaTestCase):
    """Mastery entitlement plus the cast skill's own proficiency ladder."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.entity = _player()
        self.entity.db.skills = {"active": [], "passive": []}

    @covers_requirement("element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells")
    def test_ladder_follows_the_cast_skill_own_proficiency(self):
        grant_lineage(
            self.entity,
            [_T_CAST.key],
            [_mastery_key()],
            rungs={_T_CAST.key: len(FREEFORM_SCALE_VALUES) * 2},
        )
        # Full ladder at the top rung (the synthetic skill carries no
        # consuming prerequisite edges, so its derived tip cap is the global
        # proficiency cap).
        self.assertEqual(freeform_scales_for(self.entity, _T_CAST), FREEFORM_SCALE_VALUES)
        for level, expected in (
            (0, (0.25,)),
            (1, (0.25, 0.5)),
            (3, (0.25, 0.5, 1.0)),
            (6, (0.25, 0.5, 1.0, 2.0)),
        ):
            with self.subTest(level=level):
                self.entity.db.skill_proficiency = {_T_CAST.key: float(level) * 50.0}
                self.assertEqual(
                    freeform_scales_for(self.entity, _T_CAST),
                    tuple(
                        scale
                        for scale, min_level in FREEFORM_SCALE_LADDER
                        if min_level <= level
                    ),
                )

    @covers_requirement("element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells")
    def test_sibling_proficiency_never_raises_the_set(self):
        self.entity.db.skills = _owned(_T_CAST, _T_STORM, _mastery_row())
        self.entity.db.skill_proficiency = {_T_CAST.key: 500.0}
        self.assertEqual(freeform_scales_for(self.entity, _T_STORM), (0.25,))

    @covers_requirement("element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells")
    def test_entity_without_mastery_receives_an_empty_set(self):
        self.entity.traits.magic_power.base = 100
        self.entity.db.skills = _owned(_T_CAST)
        self.assertEqual(freeform_scales_for(self.entity, _T_CAST), ())
        _granted_mastery_only(self.entity)
        self.assertEqual(freeform_scales_for(self.entity, _T_CAST), ())

    @covers_requirement("element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells")
    def test_unknown_element_fails_closed(self):
        self.entity.db.skills = {"active": [], "passive": [_mastery_key()]}
        with self.assertRaises(ValueError):
            freeform_mastery_entitled(self.entity, "not_an_element")


class FreeformScaleEntriesForTests(EvenniaTestCase):
    """The relocated ``freeform_scale_entries_for`` behaves as the old combat-view helper did."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.entity = _player()
        self.entity.db.skills = {"active": [], "passive": []}

    @covers_requirement(
        "element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells"
    )
    def test_mastery_holder_receives_the_full_entry_set(self):
        grant_lineage(
            self.entity,
            [_T_CAST.key],
            [_mastery_key()],
            rungs={_T_CAST.key: len(FREEFORM_SCALE_VALUES) * 2},
        )
        base_mp = int(_T_CAST.cost["mp"])
        self.assertEqual(
            freeform_scale_entries_for(self.entity, _T_CAST),
            tuple(
                (scale, label, scaled_mp_cost(base_mp, scale))
                for scale, label in FREEFORM_CAST_SCALES
            ),
        )

    @covers_requirement(
        "element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells"
    )
    def test_without_mastery_the_entry_set_is_empty(self):
        self.entity.db.skills = _owned(_T_CAST)
        self.assertEqual(freeform_scale_entries_for(self.entity, _T_CAST), ())

    @covers_requirement(
        "element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells"
    )
    def test_ineligible_skill_yields_an_empty_set(self):
        self.entity.db.skills = _owned(_mastery_row())
        self.assertEqual(freeform_scale_entries_for(self.entity, _mastery_row()), ())

    @covers_requirement(
        "element-mastery::mastery-ownership-entitles-freeform-scaling-of-the-element-s-eligible-spells"
    )
    def test_entry_mp_costs_match_the_shared_rounding_helper(self):
        self.entity.db.skills = _owned(_T_CAST, _mastery_row())
        entries = freeform_scale_entries_for(self.entity, _T_CAST)
        base_mp = int(_T_CAST.cost["mp"])
        self.assertEqual(
            [c for _, _, c in entries],
            [scaled_mp_cost(base_mp, s) for s, _, _ in entries],
        )
