"""End-to-end tests for the conferral write seam.

Runs on synthetic rows: a caster carrying the registered conferral effect
prefix, a fractional-conferable passive grant target, and a gate-type
(disguise) row that must be refused — the validator's structural class-based
gate, not a maintained key list, is what the rejection proves.
"""

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.targeting import RoomActionContext
from world.skills.registry import SkillKind, TargetSpec
from world.tests.synthetic_data import make_skill, synthetic_registries

# The caster row carries the registered conferral effect prefix.
_DUSK_CONFER = make_skill(
    "t_duskward_confer",
    label="暮授術",
    description="將自身技能片段授予他人的合成法術。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SELF,
    effects=["confer_skill_partial"],
)
# The grant target: a continuous-valued (stat multiplier) passive — exactly
# what the grant consumers can resolve fractionally.
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
# The gate-type row: a binary disguise effect has no fractional meaning, so
# conferral must be rejected structurally.
_MIRROR_VEIL = make_skill(
    "t_mirror_veil",
    label="鏡幕偽裝",
    description="以鏡光扭曲自身外貌的合成偽裝法術。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SELF,
    effects=["set_disguise"],
)


@synthetic_registries(
    "races",
    "skills",
    extra={
        "skills": {
            _DUSK_CONFER.key: _DUSK_CONFER,
            _MIGHTY_PULSE.key: _MIGHTY_PULSE,
            _MIRROR_VEIL.key: _MIRROR_VEIL,
        }
    },
)
class ConferralActionTests(EvenniaTest):
    def _resolver_context(self, actor, **event_context):
        return RoomActionContext(actor.location, event_context)

    def _actor(self, key):
        actor = create_object(PlayerCharacter, key=key)
        actor.race = "t_duskmari"
        actor.apply_race_baseline()
        actor.db.skills = {"active": [_DUSK_CONFER.key], "passive": []}
        return actor

    def test_conferral_commits_through_action_resolver(self):
        actor = self._actor("source")
        result = ActionResolver.resolve(
            ActionRequest(
                actor,
                _DUSK_CONFER.key,
                [actor],
                self._resolver_context(
                    actor,
                    confer_skill_key=_MIGHTY_PULSE.key,
                    confer_scale=0.1,
                ),
            )
        )
        self.assertEqual(result.outcome, "success")
        grant = actor.db.skill_grants[0]
        self.assertEqual(grant.source_key, "source")
        self.assertEqual(grant.skill_key, _MIGHTY_PULSE.key)
        self.assertEqual(grant.scale, 0.1)
        self.assertEqual(
            set(type(grant).__dataclass_fields__),
            {"source_key", "skill_key", "scale"},
        )

    def test_gate_type_conferral_is_rejected_at_resolution_time(self):
        actor = self._actor("gate source")
        result = ActionResolver.resolve(
            ActionRequest(
                actor,
                _DUSK_CONFER.key,
                [actor],
                self._resolver_context(
                    actor,
                    confer_skill_key=_MIRROR_VEIL.key,
                    confer_scale=0.5,
                ),
            )
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.EFFECT_RESOLUTION_FAILED)
        self.assertEqual(actor.db.skill_grants or [], [])

    def test_preflight_rejects_missing_confer_scale(self):
        actor = self._actor("preflight source")
        result = ActionResolver.preflight(
            ActionRequest(
                actor,
                _DUSK_CONFER.key,
                [actor],
                self._resolver_context(actor, confer_skill_key=_MIGHTY_PULSE.key),
            )
        )
        self.assertEqual(result.outcome, "rejected")
        self.assertIs(result.reason, RejectReason.MISSING_EFFECT_CONTEXT)
