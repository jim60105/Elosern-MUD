"""Freeform casting (element-mastery-freeform-casting) tests.

Covers the closed scale table, deterministic scaling helpers, eligibility
predicate, mastery entitlement query, the resolver's step-1 freeform gate,
scaled resource deduction and magnitudes, preview scaling, the combat-session
facade threading, and the text ``cast`` command scale token.

Synthetic-data migration (test-data-independence): every fixture is a kit
skill row (``t_*`` keys on the kit's borrowed element) or a runtime-derived
element-mastery row, and the expected deductions are computed from the shared
rounding authority (``scaled_mp_cost``) or plain fixture arithmetic — never
pinned to shipped row values.
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

from ._combat_session_helpers import (
    _monster_tier_key,
    _race_key,
    _behaviour_archetype_key,
    open_synthetic_scope,
)
from .combat_fixtures import BattlefieldIsolation, grant_lineage

# --- synthetic fixtures -----------------------------------------------------

_T_CAST = SYNTH_SKILLS["t_ember_burst"]  # ACTIVE elemental mp-12 damage spell
_T_ELEMENT = _T_CAST.element.key


def _mastery_key() -> str:
    """The element-mastery passive key the production entitlement derives.

    ``progression.freeform_mastery_entitled`` hardcodes ``f"{element}_mastery"``
    — a production vocabulary (the ``synth_innate_overlay`` precedent), so the
    row is built under the runtime-derived key and the test never names a
    shipped mastery identifier.
    """
    return f"{_T_ELEMENT}_mastery"


def _mastery_row():
    return replace(
        SYNTH_SKILLS["t_steady_stride"],
        key=_mastery_key(),
        label="合成元素精通",
        description="對該元素達到最高造詣的合成被動。",
        effects=["passive_trait:element_mastery"],
        category=SkillCategory.ELEMENTAL_MAGIC,
        group=_T_ELEMENT,
    )


# Expensive sibling on the same element: the high-deduction fixture.
_T_STORM = replace(
    _T_CAST,
    key="t_ember_cascade",
    label="燼焰傾瀑",
    description="連貫的燼焰一波接一波地淹沒目標。",
    cost={"mp": 30},
)
# Beyond-affordable fixture: its ×4 rung exceeds the unaffordable-cast budget.
_T_TYRANT = replace(
    _T_CAST,
    key="t_ember_tyrant",
    label="燼界暴君",
    description="牽動整個燼界的超重合成的法術。",
    cost={"mp": 60},
)
# Pure AREA heal spell: the healing-ceiling / dead-target fixture.
_T_TIDE = replace(
    _T_CAST,
    key="t_tide_mercy",
    label="潮恩",
    description="以暖流覆蓋所有仍可救治的傷者。",
    target_spec=TargetSpec.AREA,
    effects=["heal:area"],
)
# Damage + self-heal mix on a heavy mp cost: the multi-quantity scaling mix.
_T_PHOENIX = replace(
    _T_CAST,
    key="t_ember_phoenix",
    label="燼生鳳翔",
    description="焚燬對手並從餘燼中重塑自身。",
    cost={"mp": 150},
    effects=[f"damage:{_T_ELEMENT}:magic", "self_heal"],
)
# Shape-ineligible spell (damage + buff mix): the gate's ineligible-active case.
_T_MIXED = replace(
    _T_CAST,
    key="t_ember_flurry",
    label="燼屑亂舞",
    description="灼熱燼屑纏身而舞。",
    effects=[f"damage:{_T_ELEMENT}:magic", "buff_apply:t_moss_veil"],
)
# Non-elemental mp-cost skill: the gate's crash-safety case.
_T_FOCUS_MP = replace(
    SYNTH_SKILLS["t_cinder_cleave"],
    key="t_still_mind",
    label="靜心",
    description="凝聚意識的無屬性修練。",
    cost={"mp": 5},
    effects=["self_buff_apply:t_moss_veil"],
)
# SP-only elemental: the no-mp-cost rejection case.
_T_SP_SPELL = replace(
    _T_CAST,
    key="t_ash_fang",
    label="燼牙",
    description="以體力驱动的銳利燼牙。",
    cost={"sp": 12},
)
# Buff-only movement-style self skill: the out-of-combat ineligible case.
_T_VEIL = replace(
    SYNTH_SKILLS["t_moss_veil"],
    key="t_glow_veil",
    label="光燼幕",
    description="召出覆蓋燼屑的防護霧幕。",
    usable_out_of_combat=True,
)
# Out-of-combat-usable shapes for the text-command seam: the room context
# refuses damaging casts (out-of-combat-damage-gate), so the command tests
# cast scalable NON-damage shapes; the scale-token mechanics under test
# (cost scaling, clock advance) are shape-independent.
_T_OOC_HEAL = replace(
    _T_TIDE,
    key="t_ember_soothe",
    label="燼慰",
    description="以微燼暖流安撫傷口。",
    usable_out_of_combat=True,
)
_T_OOC_CAST = replace(
    _T_CAST,
    key="t_ember_gale",
    label="燼風",
    description="吹拂灼熱燼風。",
    usable_out_of_combat=True,
)
# A second-element spell (the kit's own element row): the cross-element gate
# case. The Element instance bypasses pre-patch string resolution while the
# patched registry knows the key.
_T_GLOW = replace(
    _T_CAST,
    key="t_glow_spire",
    label="光沼尖刺",
    description="自光沼抽出一根尖刺貫穿目標。",
    element=Element("t_glowmire", "光沼", "Synthetic element."),
    group="t_glowmire",
    effects=["damage:t_glowmire:magic"],
)

_EXTRA_SKILLS = {
    _T_STORM.key: _T_STORM,
    _T_TYRANT.key: _T_TYRANT,
    _T_TIDE.key: _T_TIDE,
    _T_PHOENIX.key: _T_PHOENIX,
    _T_MIXED.key: _T_MIXED,
    _T_FOCUS_MP.key: _T_FOCUS_MP,
    _T_SP_SPELL.key: _T_SP_SPELL,
    _T_VEIL.key: _T_VEIL,
    _T_OOC_HEAL.key: _T_OOC_HEAL,
    _T_OOC_CAST.key: _T_OOC_CAST,
    _T_GLOW.key: _T_GLOW,
    _mastery_row().key: _mastery_row(),
}


def _open_scope(test):
    open_synthetic_scope(
        test,
        "skills",
        "elements",
        "buffs",
        "sexual_acts",
        "races",
        "subraces",
        "static_tiers",
        extra={"skills": dict(_EXTRA_SKILLS)},
    )


def _player(key="freeform caster"):
    player = create_object(PlayerCharacter, key=key)
    player.race = _race_key()
    player.apply_race_baseline()
    player.traits.magic_power.base = 30
    return player


def _monster(key="freeform wolf"):
    monster = create_object(Monster, key=key)
    monster.threat_tier = _monster_tier_key()
    monster.behaviour_tree = _behaviour_archetype_key()
    monster.apply_monster_tier("floor")
    return monster


def _granted_mastery_only(player: PlayerCharacter) -> None:
    player.db.skill_grants = [ConferredSkillGrant("source", _mastery_key(), 1.0)]


def _owned(*rows) -> dict[str, list[str]]:
    """A ``db.skills`` payload carrying the given rows in active/passive order."""
    return {
        "active": [row.key for row in rows if row.kind is SkillKind.ACTIVE],
        "passive": [row.key for row in rows if row.kind is SkillKind.PASSIVE],
    }


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


class FreeformResolverGateTests(EvenniaTestCase):
    """The resolver gates scaled casts at the ownership step."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.actor = _player()
        self.target = create_object(PlayerCharacter, key="freeform target")
        self.target.race = _race_key()
        self.target.apply_race_baseline()
        self.actor.traits.mp.base = 500
        self.actor.traits.mp.current = 500
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"freeform target"}),
            },
            {"freeform caster": self.actor, "freeform target": self.target},
        )
        self.context = BattlefieldActionContext(self.field)

    def _request(self, skill_key, scale):
        return ActionRequest(
            self.actor,
            skill_key,
            [self.target],
            self.context,
            scale=scale,
        )

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_mastery_holder_can_scale_an_eligible_spell(self):
        grant_lineage(
            self.actor, [_T_CAST.key], [_mastery_key()], rungs={_T_CAST.key: 6}
        )
        result = ActionResolver.preflight(self._request(_T_CAST.key, 2.0))
        self.assertEqual(result.outcome, "success")
        self.assertNotEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_scaling_without_mastery_is_rejected(self):
        self.actor.db.skills = _owned(_T_CAST)
        result = ActionResolver.preflight(self._request(_T_CAST.key, 2.0))
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_mastery_entitles_scaling_of_that_element_only(self):
        grant_lineage(
            self.actor,
            [_T_CAST.key, _T_GLOW.key],
            [_mastery_key()],
            rungs={_T_CAST.key: 6},
        )
        glow = ActionResolver.preflight(self._request(_T_GLOW.key, 2.0))
        self.assertEqual(glow.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        wind = ActionResolver.preflight(self._request(_T_CAST.key, 2.0))
        self.assertEqual(wind.outcome, "success")

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_scaling_an_ineligible_spell_is_rejected_even_with_mastery(self):
        self.actor.db.skills = _owned(_T_MIXED, _mastery_row())
        result = ActionResolver.preflight(self._request(_T_MIXED.key, 2.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_non_elemental_mp_skill_never_crashes_the_gate(self):
        self.actor.db.skills = _owned(_T_FOCUS_MP)
        result = ActionResolver.preflight(self._request(_T_FOCUS_MP.key, 2.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_sp_only_elemental_skill_is_not_scalable(self):
        self.actor.db.skills = _owned(_T_SP_SPELL, _mastery_row())
        self.actor.traits.sp.current = 500
        result = ActionResolver.preflight(self._request(_T_SP_SPELL.key, 2.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        sp_before = self.actor.traits.sp.value
        ActionResolver.resolve(self._request(_T_SP_SPELL.key, 2.0))
        self.assertEqual(self.actor.traits.sp.value, sp_before)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_non_member_scale_is_rejected(self):
        self.actor.db.skills = _owned(_T_CAST, _mastery_row())
        result = ActionResolver.preflight(self._request(_T_CAST.key, 3.0))
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)

    @covers_requirement("freeform-casting::the-resolver-gates-scaled-casts-at-the-ownership-step")
    def test_scale_one_is_always_permitted(self):
        grant_lineage(
            self.actor,
            [_T_FOCUS_MP.key, _T_MIXED.key, _T_VEIL.key],
            [_mastery_key()],
        )
        for key in (_T_FOCUS_MP.key, _T_MIXED.key, _T_VEIL.key):
            with self.subTest(skill=key):
                result = ActionResolver.preflight(self._request(key, 1.0))
                self.assertNotEqual(
                    result.reason,
                    RejectReason.SCALED_CAST_FORBIDDEN,
                )


class ActionRequestScaleContractTests(EvenniaTestCase):
    """ActionRequest carries an optional scale modifier and a new rejection category."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.actor = _player()
        self.target = create_object(PlayerCharacter, key="scale contract target")
        self.target.race = _race_key()
        self.target.apply_race_baseline()
        grant_lineage(
            self.actor, [_T_CAST.key], [_mastery_key()], rungs={_T_CAST.key: 1}
        )
        self.actor.traits.mp.base = 500
        self.actor.traits.mp.current = 500
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"scale contract target"}),
            },
            {"freeform caster": self.actor, "scale contract target": self.target},
        )
        self.context = BattlefieldActionContext(self.field)

    @covers_requirement("action-resolution-pipeline::actionrequest-carries-an-optional-scale-modifier-and-a-new-rejection-category")
    def test_existing_requests_default_to_scale_one(self):
        request = ActionRequest(
            self.actor,
            _T_CAST.key,
            [self.target],
            self.context,
        )
        self.assertEqual(request.scale, 1.0)
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        spend = next(
            entry
            for entry in result.event_log.entries
            if entry.kind == "resource_spend"
        )
        self.assertEqual(
            spend.data["amount"], scaled_mp_cost(int(_T_CAST.cost["mp"]), 1.0)
        )

    @covers_requirement("action-resolution-pipeline::actionrequest-carries-an-optional-scale-modifier-and-a-new-rejection-category")
    def test_scale_reaches_the_resource_steps_and_the_handlers(self):
        self.target.traits.defense.base = 0
        self.target.traits.hp.base = 200
        self.target.traits.hp.current = 200
        self.actor.traits.magic_power.base = 6
        request = ActionRequest(
            self.actor,
            _T_CAST.key,
            [self.target],
            self.context,
            scale=0.5,
        )
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        spend = next(
            entry
            for entry in result.event_log.entries
            if entry.kind == "resource_spend"
        )
        # Step 2 and step 6 compare and deduct the same scaled amount.
        self.assertEqual(
            spend.data["amount"], scaled_mp_cost(int(_T_CAST.cost["mp"]), 0.5)
        )
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        # magic_power 6 → unscaled critical 12 → half scale 6.
        self.assertEqual(damage_entry.data["amount"], 6)

    @covers_requirement("action-resolution-pipeline::actionrequest-carries-an-optional-scale-modifier-and-a-new-rejection-category")
    def test_the_rejection_category_is_available(self):
        self.actor.db.skills = _owned(_T_CAST)
        request = ActionRequest(
            self.actor,
            _T_CAST.key,
            [self.target],
            self.context,
            scale=2.0,
        )
        result = ActionResolver.preflight(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        self.assertIsNone(result.event_log)
        self.assertIsNone(result.time_cost_seconds)


class FreeformScaledResolutionTests(EvenniaTestCase, BattlefieldIsolation):
    """A scaled cast deducts scaled MP and applies scaled magnitudes."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.actor = _player()
        self.monster = _monster("freeform wolf")
        self.actor.traits.mp.base = 1000
        self.actor.traits.mp.current = 1000
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"freeform wolf"}),
            },
            {"freeform caster": self.actor, "freeform wolf": self.monster},
        )
        self.context = BattlefieldActionContext(self.field)
        grant_lineage(
            self.actor,
            [_T_CAST.key, _T_STORM.key, _T_PHOENIX.key],
            [_mastery_key()],
            rungs={
                _T_CAST.key: 6,
                _T_STORM.key: 6,
                _T_PHOENIX.key: 6,
            },
        )

    def _request(self, skill_key, targets, scale):
        return ActionRequest(
            self.actor,
            skill_key,
            targets,
            self.context,
            scale=scale,
        )

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_half_scale_cast_deducts_half_mp_and_deals_half_damage(self):
        # magic_power 6 gives an unscaled critical of round(6 * 2.0) = 12
        # against zero defense; half scale stages 6.
        self.actor.traits.magic_power.base = 6
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        mp_before = self.actor.traits.mp.value
        hp_before = self.monster.traits.hp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request(_T_CAST.key, [self.monster], 0.5)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.actor.traits.mp.value,
            mp_before - scaled_mp_cost(int(_T_CAST.cost["mp"]), 0.5),
        )
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        self.assertEqual(damage_entry.data["amount"], 6)
        self.assertEqual(self.monster.traits.hp.value, hp_before - 6)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_double_scale_cast_deducts_double_mp(self):
        mp_before = self.actor.traits.mp.value
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = ActionResolver.resolve(
                self._request(_T_STORM.key, [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.actor.traits.mp.value,
            mp_before - scaled_mp_cost(int(_T_STORM.cost["mp"]), 2.0),
        )

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_unaffordable_scaled_cost_rejects_without_any_effect(self):
        grant_lineage(
            self.actor,
            [_T_TYRANT.key],
            [_mastery_key()],
            rungs={_T_TYRANT.key: 10},
        )
        self.actor.traits.mp.base = 200
        self.actor.traits.mp.current = 200
        hp_before = self.monster.traits.hp.value
        # The fixture budget sits strictly under the ×4 rung of the heavy row.
        self.assertLess(200, scaled_mp_cost(int(_T_TYRANT.cost["mp"]), 4.0))
        result = ActionResolver.resolve(
            self._request(_T_TYRANT.key, [self.monster], 4.0)
        )
        self.assertEqual(result.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(self.actor.traits.mp.value, 200)
        self.assertEqual(self.monster.traits.hp.value, hp_before)
        self.assertIsNone(result.event_log)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_scaled_damage_obeys_the_floor(self):
        # magic_power 2 → base critical 4 → quarter scale 1 (the floor), never 0.
        self.actor.traits.magic_power.base = 2
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request(_T_CAST.key, [self.monster], 0.25)
            )
        self.assertEqual(result.outcome, "success")
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        self.assertEqual(damage_entry.data["amount"], 1)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_scaled_lethal_hit_emits_exactly_one_defeat(self):
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 5
        self.monster.traits.hp.current = 5
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request(_T_CAST.key, [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        defeated = [
            entry
            for entry in result.event_log.entries
            if entry.kind == "target_defeated"
        ]
        self.assertEqual(len(defeated), 1)
        self.assertLessEqual(self.monster.traits.hp.value, 0)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_scaled_healing_respects_the_maximum_and_knockout_rules(self):
        grant_lineage(
            self.actor, [_T_TIDE.key], [_mastery_key()],
            rungs={_T_TIDE.key: 6},
        )
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 150
        # magic_power 30 → base heal 30 → double scale 60, capped by the gap 50.
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = ActionResolver.resolve(
                self._request(_T_TIDE.key, [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        heal_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "heal"
        )
        self.assertEqual(heal_entry.data["amount"], 50)
        self.assertEqual(self.monster.traits.hp.value, 200)
        # A zero-HP entity is never revived: targeting drops the dead
        # candidate, so the scaled heal applies no restoration.
        self.monster.traits.hp.current = 0
        self.actor.traits.mp.current = 1000
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = ActionResolver.resolve(
                self._request(_T_TIDE.key, [self.monster], 2.0)
            )
        self.assertEqual(result.reason, RejectReason.NO_VALID_TARGETS_IN_AREA)
        self.assertEqual(self.monster.traits.hp.value, 0)

    @covers_requirement("freeform-casting::a-scaled-cast-deducts-scaled-mp-and-applies-scaled-magnitudes-atomically")
    def test_damage_self_heal_spell_scales_damage_self_heal_and_mp_together(self):
        self.actor.traits.hp.base = 100
        self.actor.traits.hp.current = 40
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        mp_before = self.actor.traits.mp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = ActionResolver.resolve(
                self._request(_T_PHOENIX.key, [self.monster], 2.0)
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(
            self.actor.traits.mp.value,
            mp_before - scaled_mp_cost(int(_T_PHOENIX.cost["mp"]), 2.0),
        )
        damage_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "damage"
        )
        # magic_power 30 → base critical 60 → double scale 120.
        self.assertEqual(damage_entry.data["amount"], 120)
        self.assertEqual(self.monster.traits.hp.value, 80)
        heal_entry = next(
            entry for entry in result.event_log.entries if entry.kind == "self_heal"
        )
        # base heal 30 → double scale 60, capped by the gap to maximum.
        self.assertEqual(heal_entry.data["amount"], 60)
        self.assertEqual(self.actor.traits.hp.value, 100)


class FreeformPreviewTests(EvenniaTestCase):
    """Preview and the combat facade accept and revalidate scale."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.actor = _player()
        self.target = create_object(PlayerCharacter, key="preview target")
        self.target.race = _race_key()
        self.target.apply_race_baseline()
        grant_lineage(
            self.actor,
            [_T_CAST.key],
            [_mastery_key()],
            rungs={_T_CAST.key: len(FREEFORM_SCALE_VALUES) * 2},
        )
        self.field = Battlefield(
            {
                "party": frozenset({"freeform caster"}),
                "foes": frozenset({"preview target"}),
            },
            {"freeform caster": self.actor, "preview target": self.target},
        )
        self.context = BattlefieldActionContext(self.field)

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_preview_reports_scaled_resource_availability(self):
        top_cost = scaled_mp_cost(int(_T_CAST.cost["mp"]), 4.0)
        self.actor.traits.mp.current = top_cost
        preview = preview_skill(
            self.actor,
            _T_CAST.key,
            self.context,
            [self.target],
            scale=4.0,
        )
        self.assertTrue(preview.enabled)
        self.actor.traits.mp.current = top_cost - 1
        preview = preview_skill(
            self.actor,
            _T_CAST.key,
            self.context,
            [self.target],
            scale=4.0,
        )
        self.assertFalse(preview.enabled)
        self.assertEqual(preview.reason, RejectReason.INSUFFICIENT_RESOURCE)
        self.assertEqual(preview.detail, "mp")

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_preview_applies_the_freeform_gate(self):
        self.actor.db.skills = _owned(_T_CAST)
        preview = preview_skill(
            self.actor,
            _T_CAST.key,
            self.context,
            [self.target],
            scale=2.0,
        )
        self.assertFalse(preview.enabled)
        self.assertEqual(preview.reason, RejectReason.SCALED_CAST_FORBIDDEN)
        preview = revalidate_submission(
            self.actor,
            _T_CAST.key,
            self.context,
            [self.target],
            scale=2.0,
        )
        self.assertEqual(preview.reason, RejectReason.SCALED_CAST_FORBIDDEN)


class FreeformSessionFacadeTests(EvenniaTest, BattlefieldIsolation):
    """The facade resolves a scaled combat cast and rejects tampered scales."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.actor = _player("freeform session")
        grant_lineage(
            self.actor, [_T_CAST.key], [_mastery_key()], rungs={_T_CAST.key: 6}
        )
        self.actor.traits.mp.base = 1000
        self.actor.traits.mp.current = 1000
        self.monster = _monster("session wolf")
        self.monster.traits.defense.base = 0
        self.monster.traits.hp.base = 200
        self.monster.traits.hp.current = 200
        self.actor.move_to(self.room1)
        self.monster.move_to(self.room1)

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_facade_resolves_a_scaled_combat_cast(self):
        engage(self.actor, self.monster)
        mp_before = self.actor.traits.mp.value
        with patch("world.rules.combat.roll_d100", return_value=100):
            result = submit_player_action(
                self.actor, _T_CAST.key, [self.monster], scale=2.0
            )
        self.assertEqual(result["outcome"], "round")
        self.assertEqual(
            self.actor.traits.mp.value,
            mp_before - scaled_mp_cost(int(_T_CAST.cost["mp"]), 2.0),
        )
        self.assertLess(self.monster.traits.hp.value, 200)

    @covers_requirement("freeform-casting::preview-and-the-combat-facade-accept-and-revalidate-scale")
    def test_facade_rejects_a_tampered_scale_before_initiative(self):
        engage(self.actor, self.monster)
        mp_before = self.actor.traits.mp.value
        hp_before = self.monster.traits.hp.value
        record_before = self.actor.db.active_combat
        result = submit_player_action(
            self.actor, _T_CAST.key, [self.monster], scale=3.0
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.SCALED_CAST_FORBIDDEN)
        self.assertEqual(self.actor.traits.mp.value, mp_before)
        self.assertEqual(self.monster.traits.hp.value, hp_before)
        self.assertEqual(self.actor.db.active_combat, record_before)


class FreeformTextCommandTests(EvenniaCommandTestMixin, EvenniaTest):
    """The text cast command accepts a scale token."""

    def setUp(self):
        _open_scope(self)
        super().setUp()

    def _setup_caster(self, *, mastery: bool) -> None:
        self.char1.race = _race_key()
        self.char1.apply_race_baseline()
        self.char1.traits.magic_power.base = 30
        grant_lineage(
            self.char1,
            [_T_OOC_HEAL.key, _T_VEIL.key],
            [_mastery_key()] if mastery else [],
            rungs={_T_OOC_HEAL.key: len(FREEFORM_SCALE_VALUES) * 2}
            if mastery
            else None,
        )
        self.char1.traits.mp.base = 500
        self.char1.traits.mp.current = 500
        self.char1.move_to(self.room1)

    def _setup_target(self) -> None:
        target = create_object(PlayerCharacter, key="glow target")
        target.race = _race_key()
        target.apply_race_baseline()
        target.move_to(self.room1)

    def _clock(self):
        clock = WorldClock()
        return patch(
            "world.rules.cast_settlement.read_world_clock", return_value=clock
        ), patch(
            "world.rules.cast_settlement.get_world_clock", return_value=clock
        ), clock

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_scaled_out_of_combat_cast_deducts_scaled_mp_and_advances_time(self):
        from commands.action import CmdCast

        # The synthetic row itself declares out-of-combat usability (no
        # shipped-registry mutation needed); the heal shape keeps the room
        # cast clear of the sanctioned damaging-action gate
        # (out-of-combat-damage-gate) while the scale-token mechanics under
        # test (cost scaling, clock advance) stay shape-independent.
        self._setup_caster(mastery=True)
        self._setup_target()
        read_patch, get_patch, clock = self._clock()
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_HEAL.key}@1/2=glow target",
                f"{self.char1.key} 對 glow target 恢復了",
            )
        half_end = self.char1.traits.mp.value
        # The ordinary command-time charge applies per cast.
        self.assertEqual(clock.tick, 6)
        # Reset the gauge (and its regen remainder) so the second cast
        # accrues the same regen; the exact scaled deduction is then the
        # differential between the two command casts.
        self.char1.traits.mp.current = 500
        self.char1.traits.mp.regen_remainder = 0.0
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_HEAL.key}@1=glow target",
                f"{self.char1.key} 對 glow target 恢復了",
            )
        one_end = self.char1.traits.mp.value
        self.assertEqual(clock.tick, 12)
        base_mp = int(_T_OOC_HEAL.cost["mp"])
        # The 1/2 rung deducts exactly one half-scale's worth less.
        self.assertEqual(
            half_end - one_end,
            scaled_mp_cost(base_mp, 1.0) - scaled_mp_cost(base_mp, 0.5),
        )

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_invalid_scale_token_rejects_without_effect(self):
        from commands.action import CmdCast

        self._setup_caster(mastery=True)
        read_patch, get_patch, clock = self._clock()
        mp_before = self.char1.traits.mp.value
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_CAST.key}@3",
                rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
            )
        self.assertEqual(self.char1.traits.mp.value, mp_before)
        self.assertEqual(clock.tick, 0)

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_unauthorized_scale_rejects_without_effect(self):
        from commands.action import CmdCast

        # Same non-damage scalable shape as the success-path test: the
        # unauthorized-scale rejection comes from the freeform gate, and the
        # fixture must not be gated earlier by the damaging-action gate.
        self._setup_caster(mastery=False)
        read_patch, get_patch, clock = self._clock()
        mp_before = self.char1.traits.mp.value
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_HEAL.key}@2",
                rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
            )
        self.assertEqual(self.char1.traits.mp.value, mp_before)
        self.assertEqual(clock.tick, 0)

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_scale_on_an_ineligible_spell_rejects_with_the_stable_message(self):
        from commands.action import CmdCast

        self._setup_caster(mastery=True)
        read_patch, get_patch, clock = self._clock()
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_VEIL.key}@2",
                rejection_message(RejectReason.SCALED_CAST_FORBIDDEN),
            )
        self.assertEqual(clock.tick, 0)

    @covers_requirement("freeform-casting::the-text-cast-command-accepts-a-scale-token")
    def test_scale_one_stays_the_ordinary_command_path(self):
        from commands.action import CmdCast

        # Non-damage scalable shape (see the scaled-cast test above): the
        # ordinary room command path must not trip the damaging-action gate.
        self._setup_caster(mastery=True)
        self._setup_target()
        read_patch, get_patch, clock = self._clock()
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_HEAL.key}@1=glow target",
                f"{self.char1.key} 對 glow target 恢復了",
            )
        one_end = self.char1.traits.mp.value
        # Reset the gauge (and its regen remainder) so the second cast
        # accrues the same regen; the exact deduction is the differential.
        self.char1.traits.mp.current = 500
        self.char1.traits.mp.regen_remainder = 0.0
        with read_patch, get_patch:
            self.call(
                CmdCast(),
                f"{_T_OOC_HEAL.key}@2=glow target",
                f"{self.char1.key} 對 glow target 恢復了",
            )
        two_end = self.char1.traits.mp.value
        self.assertEqual(clock.tick, 12)
        base_mp = int(_T_OOC_HEAL.cost["mp"])
        # The ×2 rung deducts exactly one double-scale's worth more.
        self.assertEqual(
            one_end - two_end,
            scaled_mp_cost(base_mp, 2.0) - scaled_mp_cost(base_mp, 1.0),
        )
