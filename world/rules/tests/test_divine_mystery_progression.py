"""Behavior-contract tests for the divine-mystery catalog's progression shape.

Synthetic-only compositions (the test-data-independence pattern): the
conferral ladder, the ally-audience party conferral, the three-parent
capstone gate and the chain-root usability case are all invented rows
built from the kit's ``make_skill`` factory or standalone definitions, so
no assertion binds or restates a shipped-content data contract. The
behaviors established here are the contracts the catalog's shipped rows
declare through their data: a later rung of a conferral chain strictly
out-values an earlier one, an ALLIES-audience conferral reaches every ally
in the resolved audience, a multi-parent node waits for its last parent,
and a chain root needs no prerequisite edge.
"""

import unittest
from types import SimpleNamespace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter

from tools.spec_traceability import covers_requirement

from world.rules.action import ActionRequest, ActionResolver
from world.rules.progression import (
    SKILL_PROFICIENCY_XP_PER_LEVEL,
    can_use_skill,
)
from world.rules.targeting import RoomActionContext
from world.skills.effects import EffectAudience, EffectPolicy
from world.skills.registry import (
    SkillCategory,
    SkillDef,
    SkillKind,
    SkillPrerequisite,
    TargetSpec,
    validate_prerequisite_graph,
)
from world.tests.synthetic_data import make_skill, synthetic_registries

from ._combat_session_helpers import (
    live_skill_registry,
    synth_innate_overlay,
)

# ---------------------------------------------------------------------------
# Synthetic conferral ladder: two rungs of the same conferral chain, at the
# authored scales a node declares through its EffectPolicy coefficient.
# ---------------------------------------------------------------------------

_RUNG_EARLY = make_skill(
    "t_rite_early",
    label="暮授初章",
    description="將自身技能片段按低比例授予目標的合成儀式。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    effects=["confer_skill_partial"],
    effect_policies=(EffectPolicy(coefficient=0.1),),
    category=SkillCategory.DIVINE_MYSTERY,
)
_RUNG_LATE = make_skill(
    "t_rite_late",
    label="暮授終章",
    description="將自身技能片段按更高比例授予目標的合成儀式。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    effects=["confer_skill_partial"],
    effect_policies=(EffectPolicy(coefficient=0.25),),
    category=SkillCategory.DIVINE_MYSTERY,
)

# ---------------------------------------------------------------------------
# Ally-audience conferral rows: the AREA + EffectAudience.ALLIES pair the
# shipped party nodes declare (the wind 神速領域 shape).
# ---------------------------------------------------------------------------

_PARTY_CONFER = make_skill(
    "t_shared_rite",
    label="共授之儀",
    description="將同一批技能片段一次覆蓋全隊的合成儀式。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.AREA,
    cost={},
    usable_out_of_combat=True,
    effects=["confer_skill_partial"],
    effect_policies=(
        EffectPolicy(coefficient=0.1, audience=EffectAudience.ALLIES),
    ),
    category=SkillCategory.DIVINE_MYSTERY,
)
_PARTY_GROWTH = make_skill(
    "t_shared_creed",
    label="共學之誓",
    description="將同一學習節奏借給全隊的合成誓言。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.AREA,
    cost={},
    usable_out_of_combat=True,
    effects=["confer_growth_rate"],
    effect_policies=(
        EffectPolicy(coefficient=1.5, audience=EffectAudience.ALLIES),
    ),
    category=SkillCategory.DIVINE_MYSTERY,
)

# One continuously-valued passive: the grant consumer resolves it at the
# conferred scale, so the ladder's effective-value growth is observable.
_GILDED_PULSE = make_skill(
    "t_gilded_pulse",
    label="鎏光脈動",
    description="強化攻擊屬性的合成被動。",
    kind=SkillKind.PASSIVE,
    effects=["stat_multiply:atk_phys:2.0"],
)


def _cast(actor, skill, targets):
    """One out-of-combat resolution against the room context."""
    return ActionResolver.resolve(
        ActionRequest(
            actor,
            skill.key,
            list(targets),
            RoomActionContext(actor.location, {}),
        )
    )


_SCOPE = synthetic_registries(
    "races",
    "skills",
    "elements",
    # The owned-key set derives unlocked act keys from the scoped sexual-act
    # catalogue; without this scope the shipped acts would leak in as keys
    # unknown to the synthetic skill registry.
    "sexual_acts",
    extra={
        "skills": {
            **synth_innate_overlay()["skills"],
            **{
                row.key: row
                for row in (
                    _RUNG_EARLY,
                    _RUNG_LATE,
                    _PARTY_CONFER,
                    _PARTY_GROWTH,
                    _GILDED_PULSE,
                )
            }
        }
    },
)


@_SCOPE
class ProgressionConferralLadderTests(EvenniaTest):
    """A later rung of one conferral chain out-values an earlier rung."""

    def _caster(self, key, active=(), passive=()):
        caster = create_object(PlayerCharacter, key=key)
        caster.race = "t_duskmari"
        caster.apply_race_baseline()
        caster.location = self.room1
        caster.db.skills = {"active": list(active), "passive": list(passive)}
        return caster

    def _target(self, key="t_ladder_protege"):
        target = create_object(PlayerCharacter, key=key)
        target.race = "t_duskmari"
        target.apply_race_baseline()
        target.location = self.room1
        target.db.skills = {"active": [], "passive": []}
        # A true trait to fold: the grant multiplier applies at cast scale.
        target.traits.atk_phys.base = 60
        return target

    @covers_requirement(
        "skill-handler::conferral-records-a-data-scaled-grant-of-every-skill-"
        "its-caster-owns-統御術",
        "divine-mystery::divine-mystery-progression-composes-conferral-veil-"
        "and-reveal-behavior",
    )
    def test_later_rung_confers_a_strictly_larger_effective_value(self):
        caster = self._caster(
            "t_ladder_master", active=(_RUNG_EARLY.key, _RUNG_LATE.key), passive=(_GILDED_PULSE.key,)
        )
        target = self._target()
        early = _cast(caster, _RUNG_EARLY, [target])
        self.assertEqual(early.outcome, "success")
        early_value = target.skills.effective_value("atk_phys")

        late = _cast(caster, _RUNG_LATE, [target])
        self.assertEqual(late.outcome, "success")
        late_value = target.skills.effective_value("atk_phys")

        # The later rung strictly out-values the earlier one on the same
        # target, by the data-declared scale difference.
        self.assertGreater(late_value, early_value)
        # The same (source, skill) pair replaced by the later rung's scale:
        # one grant remains, at the later node's declared coefficient.
        grants = target.skills.conferred_grants()
        self.assertEqual(len(grants), 1)
        self.assertEqual(
            grants[0].scale, _RUNG_LATE.effect_policies[0].coefficient
        )


@_SCOPE
class PartyAudienceConferralTests(EvenniaTest):
    """An ally-audience conferral reaches every ally in the audience."""

    def _member(self, key):
        member = create_object(PlayerCharacter, key=key)
        member.race = "t_duskmari"
        member.apply_race_baseline()
        member.location = self.room1
        member.db.skills = {"active": [], "passive": []}
        return member

    @covers_requirement(
        "skill-effect-model::effect-audiences-select-recipients-without-"
        "changing-skill-faction-constraints",
        "divine-mystery::divine-mystery-progression-composes-conferral-veil-"
        "and-reveal-behavior",
    )
    def test_skill_partial_conferral_reaches_every_ally_in_the_audience(self):
        caster = self._member("t_shared_master")
        caster.db.skills = {
            "active": [_PARTY_CONFER.key],
            "passive": [_GILDED_PULSE.key],
        }
        allies = [self._member(f"t_shared_ally_{index}") for index in range(3)]
        result = _cast(caster, _PARTY_CONFER, allies)
        self.assertEqual(result.outcome, "success")
        for ally in allies:
            with self.subTest(ally=ally.key):
                grants = ally.skills.conferred_grants()
                self.assertEqual(
                    [(g.source_key, g.skill_key, g.scale) for g in grants],
                    [
                        (
                            caster.key,
                            _GILDED_PULSE.key,
                            _PARTY_CONFER.effect_policies[0].coefficient,
                        )
                    ],
                )

    @covers_requirement(
        "skill-effect-model::effect-audiences-select-recipients-without-"
        "changing-skill-faction-constraints",
        "divine-mystery::divine-mystery-progression-composes-conferral-veil-"
        "and-reveal-behavior",
    )
    def test_growth_rate_conferral_reaches_every_ally_in_the_audience(self):
        caster = self._member("t_growth_master")
        caster.db.skills = {"active": [_PARTY_GROWTH.key], "passive": []}
        allies = [self._member(f"t_growth_ally_{index}") for index in range(2)]
        result = _cast(caster, _PARTY_GROWTH, allies)
        self.assertEqual(result.outcome, "success")
        for ally in allies:
            with self.subTest(ally=ally.key):
                buff = ally.buffs.all[f"conferred_growth_rate:{caster.key}"]
                self.assertIsNotNone(buff)
                self.assertEqual(
                    buff.scale, _PARTY_GROWTH.effect_policies[0].coefficient
                )


# ---------------------------------------------------------------------------
# Pure lineage-graph cases: no scope, no entity persistence. The
# injected registry is validated against the load-time caches and restored
# to the live registry (the shipped one outside any scope) when each test
# finishes, so the suites stay order-independent.
# ---------------------------------------------------------------------------


def _divine_lineage_node(
    key: str,
    label: str,
    prerequisites: tuple[SkillPrerequisite, ...] = (),
) -> SkillDef:
    """One minimal synthetic DIVINE_MYSTERY node for lineage-graph tests."""
    return SkillDef(
        key=key,
        label=label,
        description="合成神祕系譜節點。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        cost={},
        usable_out_of_combat=True,
        element=None,
        effects=["confer_skill_partial"],
        category=SkillCategory.DIVINE_MYSTERY,
        prerequisites=tuple(prerequisites),
    )


class CapstoneGateTests(unittest.TestCase):
    """The multi-parent convergence gate over a synthetic graph."""

    def setUp(self):
        self.registry = {
            "t_cap_root_a": _divine_lineage_node("t_cap_root_a", "熒授之根甲"),
            "t_cap_root_b": _divine_lineage_node("t_cap_root_b", "熒授之根乙"),
            "t_cap_root_c": _divine_lineage_node("t_cap_root_c", "熒授之根丙"),
            "t_capstone": _divine_lineage_node(
                "t_capstone",
                "熒授之冠",
                prerequisites=(
                    SkillPrerequisite("t_cap_root_a", 10),
                    SkillPrerequisite("t_cap_root_b", 10),
                    SkillPrerequisite("t_cap_root_c", 10),
                ),
            ),
        }
        validate_prerequisite_graph(self.registry)
        self.addCleanup(validate_prerequisite_graph, live_skill_registry())

    def _entity(self, proficiency):
        owned = tuple(self.registry)
        return SimpleNamespace(
            race=None,
            pk=None,
            key="stub",
            skills=SimpleNamespace(owned_keys=lambda: set(owned)),
            db=SimpleNamespace(
                skill_proficiency=dict(proficiency),
                affinity_elements=[],
                skills={"active": list(owned), "passive": []},
            ),
        )

    @covers_requirement(
        "skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-"
        "predicate",
        "divine-mystery::divine-mystery-progression-composes-conferral-veil-"
        "and-reveal-behavior",
    )
    def test_three_parent_capstone_waits_for_its_last_parent(self):
        level = SKILL_PROFICIENCY_XP_PER_LEVEL
        entity = self._entity(
            {
                "t_cap_root_a": 10 * level,
                "t_cap_root_b": 10 * level,
                "t_cap_root_c": 9 * level,
            }
        )
        self.assertFalse(can_use_skill(entity, self.registry["t_capstone"]))
        entity.db.skill_proficiency["t_cap_root_c"] = 10 * level
        self.assertTrue(can_use_skill(entity, self.registry["t_capstone"]))

    @covers_requirement(
        "skill-lineage::can-use-skill-is-the-single-shared-use-eligibility-"
        "predicate",
        "divine-mystery::divine-mystery-progression-composes-conferral-veil-"
        "and-reveal-behavior",
    )
    def test_chain_root_is_usable_with_no_prerequisite(self):
        # The root declares no edge and the entity owns no descendant: the
        # single use predicate needs nothing but ownership.
        entity = SimpleNamespace(
            race=None,
            pk=None,
            key="stub",
            skills=SimpleNamespace(owned_keys=lambda: {"t_cap_root_a"}),
            db=SimpleNamespace(
                skill_proficiency={},
                affinity_elements=[],
                skills={"active": ["t_cap_root_a"], "passive": []},
            ),
        )
        self.assertTrue(can_use_skill(entity, self.registry["t_cap_root_a"]))