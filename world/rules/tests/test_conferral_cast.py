"""Behavior-contract tests for the data-driven conferral cast path.

Synthetic-only: the caster rows, the conferrable passives, the gate-type
row, and the no-continuous-effect row are all invented skills, so no
assertion binds a shipped-content data contract. The suite covers the
replace-by-key store, the direct-ownership precondition, the derived set
at the declared per-occurrence coefficient, the empty-set rejection in
preview and resolution, and commit rollback of the grant surface.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from tools.spec_traceability import covers_requirement
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
    RejectedAction,
    _commit,
)
from world.rules.action_preview import preview_skill
from world.rules.skill_effects import (
    record_conferred_grant,
    validate_source_owns_skill,
)
from world.rules.targeting import RoomActionContext
from world.skills.effects import EffectPolicy
from world.skills.handler import ConferredSkillGrant
from world.skills.registry import SkillCategory, SkillDef, SkillKind, TargetSpec
from world.tests.synthetic_data import make_skill, synthetic_registries
from ._combat_session_helpers import synth_innate_overlay

# The caster row: one registered conferral prefix at a declared scale.
_DUSK_CONFER = make_skill(
    "t_duskward_confer",
    label="暮授術",
    description="將自身技能片段授予他人的合成法術。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    effects=["confer_skill_partial"],
    effect_policies=(EffectPolicy(coefficient=0.25),),
    category=SkillCategory.DIVINE_MYSTERY,
)
# The growth-rate twin: the same data-derived scale rule.
_MENTORS_RITE = make_skill(
    "t_mentors_rite",
    label="師徒之約",
    description="將自身的成長節奏授予目標的合成儀式。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    effects=["confer_growth_rate"],
    effect_policies=(EffectPolicy(coefficient=1.5),),
    category=SkillCategory.DIVINE_MYSTERY,
)
# Two continuously-valued passives: a stat multiplier and a rule-table row —
# exactly the shapes the grant consumers resolve fractionally.
_MIGHTY_PULSE = make_skill(
    "t_mighty_pulse",
    label="巨力脈動",
    description="強化三項戰鬥屬性的合成被動。",
    kind=SkillKind.PASSIVE,
    effects=[
        f"stat_multiply:{trait}:2.0"
        for trait in ("atk_phys", "agility", "defense")
    ],
)
_DEFENSE_INSTINCT = make_skill(
    "t_defense_instinct",
    label="防護直覺",
    description="連結規則表的合成被動。",
    kind=SkillKind.PASSIVE,
    effects=["passive_buff:t_defense_instinct"],
)
# The gate-type row and a no-continuous-effect row: both must be skipped by
# the derived set, never staged as grants.
_MIRROR_VEIL = make_skill(
    "t_mirror_veil",
    label="鏡幕偽裝",
    description="以鏡光扭曲自身外貌的合成偽裝法術。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SELF,
    effects=["set_disguise"],
)
_DAMAGE_ONLY = make_skill(
    "t_spark_jab",
    label="火花刺",
    description="只有傷害、無法按比例授予的合成技能。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    effects=["damage:t_dummy:physical"],
)

_SCOPE = synthetic_registries(
    "races",
    "skills",
    "elements",
    # The owned-key set derives unlocked act keys from the scoped sexual-act
    # catalogue; without this scope the shipped acts would leak in as keys
    # unknown to the synthetic skill registry and slip past the shape gate.
    "sexual_acts",
    extra={
        "skills": {
            **synth_innate_overlay()["skills"],
            **{
                row.key: row
                for row in (
                    _DUSK_CONFER,
                    _MENTORS_RITE,
                    _MIGHTY_PULSE,
                    _DEFENSE_INSTINCT,
                    _MIRROR_VEIL,
                    _DAMAGE_ONLY,
                )
            }
        }
    },
)


def _make_policy_skill(
    key: str, label: str, effects, policy, category: SkillCategory
) -> SkillDef:
    """One active synthetic row carrying an explicit effect policy."""
    return SkillDef(
        key=key,
        label=label,
        description="測試用：效果政策聲明。",
        kind=SkillKind.ACTIVE,
        target_spec=TargetSpec.SINGLE,
        element=None,
        cost={},
        usable_out_of_combat=True,
        effects=effects,
        effect_policies=policy,
        category=category,
    )


@_SCOPE
class ConferralStoreSemanticsTests(EvenniaTest):
    """The write primitive, the ownership gate, and the read-side fold."""

    def _entity(self, key="grantee"):
        entity = create_object(PlayerCharacter, key=key)
        entity.race = "t_duskmari"
        entity.apply_race_baseline()
        entity.location = self.room1
        entity.db.skills = {"active": [], "passive": []}
        return entity

    @covers_requirement(
        "skill-handler::effective-value-is-the-sole-resolution-time-"
        "multiplier-application-point-and-never-writes-to-entity-traits"
    )
    def test_repeated_conferral_from_one_source_replaces_the_grant(self):
        entity = self._entity()
        entity.traits.atk_phys.base = 60
        record_conferred_grant(entity, "t_source", _MIGHTY_PULSE.key, 0.1)
        record_conferred_grant(entity, "t_source", _MIGHTY_PULSE.key, 0.25)
        grants = entity.skills.conferred_grants()
        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0].scale, 0.25)
        multiplier = _MIGHTY_PULSE.parsed_effects[0].multiplier
        # The refreshed grant is folded exactly once.
        self.assertEqual(
            entity.skills.effective_value("atk_phys"),
            round(60 * multiplier * 0.25),
        )

    @covers_requirement(
        "skill-handler::effective-value-is-the-sole-resolution-time-"
        "multiplier-application-point-and-never-writes-to-entity-traits"
    )
    def test_two_sources_conferring_the_same_skill_both_count(self):
        entity = self._entity()
        entity.traits.atk_phys.base = 60
        record_conferred_grant(entity, "t_first", _MIGHTY_PULSE.key, 0.5)
        record_conferred_grant(entity, "t_second", _MIGHTY_PULSE.key, 0.25)
        grants = entity.skills.conferred_grants()
        self.assertEqual(
            [(g.source_key, g.skill_key) for g in grants],
            [
                ("t_first", _MIGHTY_PULSE.key),
                ("t_second", _MIGHTY_PULSE.key),
            ],
        )
        multiplier = _MIGHTY_PULSE.parsed_effects[0].multiplier
        self.assertEqual(
            entity.skills.effective_value("atk_phys"),
            round(60 * multiplier * 0.5 * multiplier * 0.25),
        )

    def test_replacing_one_pair_preserves_the_relative_order(self):
        entity = self._entity()
        record_conferred_grant(entity, "t_first", _MIGHTY_PULSE.key, 0.5)
        record_conferred_grant(entity, "t_second", _DEFENSE_INSTINCT.key, 0.5)
        record_conferred_grant(entity, "t_first", _MIGHTY_PULSE.key, 0.25)
        self.assertEqual(
            [
                (g.source_key, g.skill_key, g.scale)
                for g in entity.skills.conferred_grants()
            ],
            [
                ("t_first", _MIGHTY_PULSE.key, 0.25),
                ("t_second", _DEFENSE_INSTINCT.key, 0.5),
            ],
        )

    def test_unowned_skill_is_rejected_and_writes_nothing(self):
        entity = self._entity()
        with self.assertRaises(RejectedAction) as raised:
            validate_source_owns_skill(entity, _MIGHTY_PULSE.key)
        self.assertIs(
            raised.exception.reason, RejectReason.EFFECT_RESOLUTION_FAILED
        )
        self.assertEqual(entity.skills.conferred_grants(), [])

    def test_directly_owned_skill_passes_the_ownership_gate(self):
        entity = self._entity()
        entity.db.skills = {"active": [], "passive": [_MIGHTY_PULSE.key]}
        validate_source_owns_skill(entity, _MIGHTY_PULSE.key)

    def test_conferral_policy_accepts_a_non_identity_coefficient(self):
        skill = _make_policy_skill(
            "t_policy_confer",
            "政策授予",
            ["confer_skill_partial"],
            (EffectPolicy(coefficient=0.25),),
            SkillCategory.DIVINE_MYSTERY,
        )
        self.assertEqual(skill.effect_policies[0].coefficient, 0.25)

    def test_prefix_outside_the_allow_list_still_rejects_a_coefficient(self):
        with self.assertRaisesRegex(ValueError, "coefficient"):
            _make_policy_skill(
                "t_policy_buff",
                "政策增益",
                ["buff_apply:focus"],
                (EffectPolicy(coefficient=0.5),),
                SkillCategory.ENHANCEMENT,
            )


@_SCOPE
class ConferralCastPathTests(EvenniaTest):
    """The resolver-level cast path: derived set and data-driven scale."""

    def _caster(
        self, key, *, passive=(), grants=(), confer=_DUSK_CONFER
    ):
        caster = create_object(PlayerCharacter, key=key)
        caster.race = "t_duskmari"
        caster.apply_race_baseline()
        caster.location = self.room1
        caster.db.skills = {"active": [confer.key], "passive": list(passive)}
        caster.db.skill_grants = list(grants)
        return caster

    def _cast(self, caster, target, skill=None, event_context=None):
        skill = skill or _DUSK_CONFER
        return ActionResolver.resolve(
            ActionRequest(
                caster,
                skill.key,
                [target],
                RoomActionContext(caster.location, event_context or {}),
            )
        )

    @covers_requirement(
        "effect-context-validation::effect-handlers-declare-their-required-"
        "event-context"
    )
    def test_cast_without_context_writes_one_grant_per_conferrable_owned_skill(self):
        caster = self._caster(
            "conferrer",
            passive=[
                _MIGHTY_PULSE.key,
                _DEFENSE_INSTINCT.key,
                _MIRROR_VEIL.key,
                _DAMAGE_ONLY.key,
            ],
        )
        target = self._caster("receiver")
        result = self._cast(caster, target)
        self.assertEqual(result.outcome, "success")
        grants = target.skills.conferred_grants()
        self.assertEqual(
            [(g.source_key, g.skill_key, g.scale) for g in grants],
            [
                ("conferrer", _MIGHTY_PULSE.key, 0.25),
                ("conferrer", _DEFENSE_INSTINCT.key, 0.25),
            ],
        )

    def test_caller_supplied_confer_scale_is_ignored(self):
        caster = self._caster("scale-ignored", passive=[_MIGHTY_PULSE.key])
        target = self._caster("receiver")
        result = self._cast(
            caster, target, event_context={"confer_scale": 0.9}
        )
        self.assertEqual(result.outcome, "success")
        grants = target.skills.conferred_grants()
        self.assertEqual(len(grants), 1)
        self.assertEqual(grants[0].scale, 0.25)

    def test_caster_with_nothing_conferrable_is_rejected(self):
        caster = self._caster("empty-caster", passive=[_MIRROR_VEIL.key])
        target = self._caster("receiver")
        result = self._cast(caster, target)
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
        self.assertEqual(target.skills.conferred_grants(), [])

    def test_a_conferred_grant_cannot_be_conferred_onward(self):
        lender = self._caster("lender", passive=[_MIGHTY_PULSE.key])
        holder = self._caster(
            "holder",
            grants=[ConferredSkillGrant("lender", _MIGHTY_PULSE.key, 0.25)],
        )
        third = self._caster("third")
        result = self._cast(holder, third)
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
        self.assertEqual(third.skills.conferred_grants(), [])

    def test_repeated_cast_from_one_source_keeps_one_grant_per_pair(self):
        caster = self._caster("repeat", passive=[_MIGHTY_PULSE.key])
        target = self._caster("receiver")
        for _ in range(2):
            result = self._cast(caster, target)
            self.assertEqual(result.outcome, "success")
        grants = target.skills.conferred_grants()
        self.assertEqual(
            [(g.skill_key, g.scale) for g in grants],
            [(_MIGHTY_PULSE.key, 0.25)],
        )

    def test_growth_rate_cast_reads_the_declared_scale(self):
        caster = self._caster("mentor", confer=_MENTORS_RITE)
        target = self._caster("t_protege")
        result = self._cast(caster, target, skill=_MENTORS_RITE)
        self.assertEqual(result.outcome, "success")
        buff = target.buffs.all[f"conferred_growth_rate:{caster.key}"]
        self.assertEqual((buff.source_key, buff.scale), (caster.key, 1.5))

    def test_growth_rate_ignores_a_caller_supplied_scale(self):
        caster = self._caster("mentor", confer=_MENTORS_RITE)
        target = self._caster("t_protege")
        result = self._cast(
            caster,
            target,
            skill=_MENTORS_RITE,
            event_context={"confer_scale": 0.9},
        )
        self.assertEqual(result.outcome, "success")
        buff = target.buffs.all[f"conferred_growth_rate:{caster.key}"]
        self.assertEqual(buff.scale, 1.5)


@_SCOPE
class ConferralPreviewAndRollbackTests(EvenniaTest):
    """Preview parity for the empty event context and the empty derived set."""

    def _caster(self, key, *, passive=()):
        caster = create_object(PlayerCharacter, key=key)
        caster.race = "t_duskmari"
        caster.apply_race_baseline()
        caster.location = self.room1
        caster.db.skills = {"active": [_DUSK_CONFER.key], "passive": list(passive)}
        return caster

    @covers_requirement(
        "effect-context-validation::effect-handlers-declare-their-required-"
        "event-context"
    )
    def test_preview_reports_no_missing_context_for_a_conferral_skill(self):
        caster = self._caster("preview", passive=[_MIGHTY_PULSE.key])
        target = self._caster("target")
        context = RoomActionContext(caster.location, {})
        preview = preview_skill(caster, _DUSK_CONFER.key, context, [target])
        self.assertTrue(preview.enabled)
        self.assertIsNone(preview.reason)
        preflight = ActionResolver.preflight(
            ActionRequest(caster, _DUSK_CONFER.key, [target], context)
        )
        self.assertEqual(preflight.outcome, "success")

    def test_preview_rejects_an_empty_derived_set_like_resolution(self):
        caster = self._caster("preview-empty", passive=[_MIRROR_VEIL.key])
        target = self._caster("target")
        context = RoomActionContext(caster.location, {})
        preview = preview_skill(caster, _DUSK_CONFER.key, context, [target])
        self.assertFalse(preview.enabled)
        self.assertIs(preview.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
        preflight = ActionResolver.preflight(
            ActionRequest(caster, _DUSK_CONFER.key, [target], context)
        )
        self.assertEqual(preflight.outcome, "rejected")
        self.assertIs(preflight.reason, RejectReason.EFFECT_RESOLUTION_FAILED)

    def test_combat_submission_with_an_empty_derived_set_rejects_before_initiative(self):
        from unittest.mock import patch

        from typeclasses.monsters import Monster
        from world.rules.clock import WorldClock
        from world.rules.combat_session import (
            engage,
            read_session,
            submit_player_action,
        )

        caster = self._caster("combat-empty", passive=[_MIRROR_VEIL.key])
        monster = create_object(Monster, key="sparring dummy")
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.location = self.room1
        engage(caster, monster)
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            result = submit_player_action(
                caster, _DUSK_CONFER.key, [monster]
            )
        self.assertEqual(result["outcome"], "rejected")
        self.assertIs(
            result["reason"], RejectReason.EFFECT_RESOLUTION_FAILED
        )
        self.assertEqual(read_session(caster).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)

    def test_failed_commit_restores_skill_grants_byte_equal(self):
        target = self._caster("rollback")
        target.db.skill_grants = [
            ConferredSkillGrant("t_old", "t_steady_stride", 0.5)
        ]
        before = list(target.db.skill_grants)

        def _failing_apply() -> None:
            raise RuntimeError("simulated commit failure")

        # The multi-grant derived-set shape: two staged grants followed by a
        # later effect whose apply fails after the grants already committed.
        effects = [
            PendingEffect(
                target,
                f"skill_granted|rollback|{skill_key}|0.25",
                frozenset({"skill_grants"}),
                lambda skill_key=skill_key: record_conferred_grant(
                    target, "t_source", skill_key, 0.25
                ),
            )
            for skill_key in (_MIGHTY_PULSE.key, _DEFENSE_INSTINCT.key)
        ]
        effects.append(
            PendingEffect(
                target,
                "later|boom",
                frozenset({"traits"}),
                _failing_apply,
            )
        )
        with self.assertRaises(CommitFailed) as caught:
            _commit(effects, char="tester", action="test_skill")
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(list(target.db.skill_grants), before)