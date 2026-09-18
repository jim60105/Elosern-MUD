"""Behavior-contract tests for the total conferral revocation primitive.

Synthetic-only: the revoke cast row, the multiplier passive, the grant
sources, and every key are invented (kit ``t_*`` convention), so no
assertion binds a shipped-content data contract. The suite covers the
payload-free ``revoke_grants`` effect parse, the buff-layer clear of every
``conferred_growth_rate`` instance, the deterministic-core primitive, the
cast path through the registered handler, and commit rollback restoring
both the ``skill_grants`` and the buff store byte-equal.
"""

from copy import deepcopy
import unittest

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
    _commit,
)
from world.rules.buffs import (
    apply_buff,
    clear_conferred_growth_rates,
    entity_active_buffs,
    grant_conferred_growth_rate,
    growth_rate_multiplier,
)
from world.rules.skill_effects import (
    record_conferred_grant,
    revoke_conferred_grants,
)
from world.rules.targeting import RoomActionContext
from world.skills.effects import RevokeGrantsEffect, parse_effect
from world.skills.handler import ConferredSkillGrant
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import make_skill, synthetic_registries
from ._combat_session_helpers import synth_innate_overlay

# The revoke cast row: one bare registered prefix, no payload, no policy.
_REVOKE = make_skill(
    "t_sovereign_retraction",
    label="權能收回",
    description="收回目標身上一切授予的合成神術。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    effects=["revoke_grants"],
    category=SkillCategory.DIVINE_MYSTERY,
)
# One continuously-valued passive: the fold test needs a stored multiplier
# the grant consumer resolves at a fractional scale.
_PULSE = make_skill(
    "t_celestial_pulse",
    label="天脈鼓動",
    description="強化三項戰鬥屬性的合成被動。",
    kind=SkillKind.PASSIVE,
    effects=[
        f"stat_multiply:{trait}:2.0"
        for trait in ("atk_phys", "agility", "defense")
    ],
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
                for row in (_REVOKE, _PULSE)
            }
        }
    },
)

#: The unrelated buff every "leaves other buffs alone" assertion carries.
_UNRELATED_BUFF = "focus"


class RevokeEffectParseTests(unittest.TestCase):
    """The bare prefix parses into the marker dataclass; payloads fail closed."""

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-"
        "into-a-typed-dataclass"
    )
    def test_bare_revoke_prefix_parses_into_the_marker_dataclass(self):
        self.assertEqual(parse_effect("revoke_grants"), RevokeGrantsEffect())

    @covers_requirement(
        "skill-effect-model::parse-effect-classifies-every-declared-prefix-"
        "into-a-typed-dataclass"
    )
    def test_any_revoke_payload_fails_at_parse(self):
        for effect in ("revoke_grants:all", "revoke_grants:", "revoke_grants:a:b"):
            with self.subTest(effect=effect):
                with self.assertRaises(ValueError):
                    parse_effect(effect)


@_SCOPE
class ClearConferredGrowthRatesTests(EvenniaTest):
    """The buff-layer clear removes every source's instance, and only those."""

    def _entity(self, key="target"):
        entity = create_object(PlayerCharacter, key=key)
        entity.race = "t_duskmari"
        entity.apply_race_baseline()
        entity.location = self.room1
        entity.db.skills = {"active": [], "passive": []}
        return entity

    def test_clear_with_nothing_conferred_returns_zero_and_writes_nothing(self):
        entity = self._entity()
        self.assertEqual(clear_conferred_growth_rates(entity), 0)
        self.assertEqual(entity_active_buffs(entity), set())

    def test_clear_removes_both_sources_growth_rates_and_keeps_unrelated_buff(self):
        entity = self._entity()
        grant_conferred_growth_rate(entity, "t_src_a", 0.5)
        grant_conferred_growth_rate(entity, "t_src_b", 0.25)
        apply_buff(entity, _UNRELATED_BUFF)
        self.assertEqual(
            growth_rate_multiplier(entity),
            0.5 * 0.25,
        )
        removed = clear_conferred_growth_rates(entity)
        self.assertEqual(removed, 2)
        self.assertEqual(entity_active_buffs(entity), {_UNRELATED_BUFF})
        self.assertEqual(growth_rate_multiplier(entity), 1.0)
        self.assertFalse(
            any(
                key.startswith("conferred_growth_rate")
                for key in entity.buffs.all
            )
        )
        self.assertIn(_UNRELATED_BUFF, entity.buffs.all)


@_SCOPE
class RevocationPrimitiveTests(EvenniaTest):
    """The deterministic-core primitive clears both halves of the vocabulary."""

    def _entity(self, key="target", *, passive=()):
        entity = create_object(PlayerCharacter, key=key)
        entity.race = "t_duskmari"
        entity.apply_race_baseline()
        entity.location = self.room1
        entity.db.skills = {"active": [], "passive": list(passive)}
        return entity

    @covers_requirement(
        "skill-handler::effective-value-is-the-sole-resolution-time-"
        "multiplier-application-point-and-never-writes-to-entity-traits"
    )
    def test_revocation_clears_both_halves_and_leaves_owned_skills_and_unrelated_buffs(self):
        entity = self._entity(passive=[_PULSE.key])
        entity.traits.atk_phys.base = 60
        # Two different sources conferring the same skill both count, so the
        # pre-state folds the owned passive and both full-strength grants.
        record_conferred_grant(entity, "t_src_a", _PULSE.key, 1.0)
        record_conferred_grant(entity, "t_src_b", _PULSE.key, 1.0)
        grant_conferred_growth_rate(entity, "t_src_a", 0.5)
        grant_conferred_growth_rate(entity, "t_src_b", 0.25)
        apply_buff(entity, _UNRELATED_BUFF)
        owned_multiplier = _PULSE.parsed_effects[0].multiplier
        granted_multiplier = owned_multiplier * 1.0
        self.assertEqual(
            entity.skills.effective_value("atk_phys"),
            round(60 * owned_multiplier * granted_multiplier * granted_multiplier),
        )
        self.assertEqual(growth_rate_multiplier(entity), 0.5 * 0.25)

        revoke_conferred_grants(entity)

        self.assertEqual(entity.skills.conferred_grants(), [])
        self.assertEqual(entity_active_buffs(entity), {_UNRELATED_BUFF})
        self.assertEqual(growth_rate_multiplier(entity), 1.0)
        # The target's OWN passive still folds into the effective value; the
        # granted share no longer does.
        self.assertEqual(
            entity.skills.effective_value("atk_phys"),
            round(60 * owned_multiplier),
        )
        self.assertEqual(entity.traits.atk_phys.base, 60)

    def test_revocation_on_a_target_with_nothing_conferred_is_a_clean_no_op(self):
        entity = self._entity()
        revoke_conferred_grants(entity)
        self.assertEqual(entity.skills.conferred_grants(), [])
        self.assertFalse(entity.attributes.has("skill_grants"))
        self.assertEqual(growth_rate_multiplier(entity), 1.0)
        self.assertEqual(entity_active_buffs(entity), set())


@_SCOPE
class RevocationCastPathTests(EvenniaTest):
    """The resolver-level cast path strips grants and growth-rate buffs."""

    def _entity(self, key, *, active=(), passive=(), grants=()):
        entity = create_object(PlayerCharacter, key=key)
        entity.race = "t_duskmari"
        entity.apply_race_baseline()
        entity.location = self.room1
        entity.db.skills = {"active": list(active), "passive": list(passive)}
        entity.db.skill_grants = list(grants)
        return entity

    @covers_requirement(
        "action-resolution-pipeline::the-effect-resolution-registry-is-open-"
        "prefix-keyed-and-every-handler-declares-its"
    )
    @covers_requirement(
        "effect-context-validation::effect-handlers-declare-their-required-"
        "event-context"
    )
    def test_revoke_cast_strips_grants_and_growth_rate_buffs(self):
        caster = self._entity("revoker", active=[_REVOKE.key])
        target = self._entity(
            "cursed",
            grants=[
                ConferredSkillGrant("t_src_a", _PULSE.key, 1.0),
                ConferredSkillGrant("t_src_b", _PULSE.key, 0.5),
            ],
        )
        grant_conferred_growth_rate(target, "t_src_a", 0.5)
        grant_conferred_growth_rate(target, "t_src_b", 0.25)
        apply_buff(target, _UNRELATED_BUFF)
        self.assertEqual(len(target.skills.conferred_grants()), 2)
        self.assertEqual(growth_rate_multiplier(target), 0.5 * 0.25)

        result = ActionResolver.resolve(
            ActionRequest(
                caster,
                _REVOKE.key,
                [target],
                RoomActionContext(caster.location, {}),
            )
        )
        self.assertEqual(result.outcome, "success")
        # The staged revocation narrated one target-scoped entry through the
        # registered ``grants_revoked`` template (the resolver also stages the
        # universal skill-practice line every cast narrates).
        revoke_entries = [
            entry
            for entry in result.event_log.entries
            if entry.kind == "grants_revoked"
        ]
        self.assertEqual(len(revoke_entries), 1)
        entry = revoke_entries[0]
        self.assertEqual(entry.kind, "grants_revoked")
        self.assertEqual(entry.actor, str(caster.key))
        self.assertEqual(entry.target, str(target.key))
        self.assertIn("收回", entry.text_template)
        self.assertEqual(target.skills.conferred_grants(), [])
        self.assertEqual(growth_rate_multiplier(target), 1.0)
        self.assertEqual(entity_active_buffs(target), {_UNRELATED_BUFF})
        self.assertIn(_UNRELATED_BUFF, target.buffs.all)
        self.assertFalse(
            any(
                key.startswith("conferred_growth_rate")
                for key in target.buffs.all
            )
        )


@_SCOPE
class RevocationRollbackTests(EvenniaTest):
    """A failed commit restores both stores byte-equal."""

    def _entity(self, key="rollback"):
        entity = create_object(PlayerCharacter, key=key)
        entity.race = "t_duskmari"
        entity.apply_race_baseline()
        entity.location = self.room1
        entity.db.skills = {"active": [], "passive": []}
        return entity

    @covers_requirement(
        "action-resolution-pipeline::resolution-is-atomic-a-failure-at-any-"
        "step-leaves-zero-state-mutated"
    )
    def test_failed_commit_restores_skill_grants_and_buff_store_byte_equal(self):
        target = self._entity()
        target.db.skill_grants = [
            ConferredSkillGrant("t_src_a", _PULSE.key, 1.0),
            ConferredSkillGrant("t_src_b", _PULSE.key, 0.5),
        ]
        grant_conferred_growth_rate(target, "t_src_a", 0.5)
        grant_conferred_growth_rate(target, "t_src_b", 0.25)
        apply_buff(target, _UNRELATED_BUFF)
        before_grants = list(target.db.skill_grants)
        before_buffs = deepcopy(target.db.buffs)
        self.assertTrue(before_grants)
        self.assertNotEqual(growth_rate_multiplier(target), 1.0)

        def _failing_apply() -> None:
            # Fails only when the revocation really committed before this
            # later effect: a no-op revocation would make the whole commit
            # succeed, and the test would fail instead of passing vacuously.
            if (
                not target.skills.conferred_grants()
                and growth_rate_multiplier(target) == 1.0
            ):
                raise RuntimeError("simulated post-revocation commit failure")

        effects = [
            PendingEffect(
                target,
                "grants_revoked|rollback",
                frozenset({"skill_grants", "buffs"}),
                lambda: revoke_conferred_grants(target),
            ),
            PendingEffect(
                target,
                "later|boom",
                frozenset({"traits"}),
                _failing_apply,
            ),
        ]
        with self.assertRaises(CommitFailed) as caught:
            _commit(effects, char="tester", action="test_skill")
        self.assertIs(caught.exception.reason, RejectReason.COMMIT_FAILED)
        self.assertEqual(list(target.db.skill_grants), before_grants)
        self.assertEqual(target.db.buffs, before_buffs)