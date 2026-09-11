"""Tests for the action resolver's sexual-transition bridge.

The carrier is a file-local synthetic skill whose sole effect carries the
participant-scoped ``sexual_event:`` prefix under an invented event name, and
the transition table is patched to one file-local rule keyed to that name.
Together they prove the bridge end to end — the resolver hands the effect's
event name to ``apply_event``, and a matching rule's delta mutates the
actor's pleasure gauge — without a shipped skill row or a shipped rulebook
row.
"""

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from world.rules.action import ActionRequest, ActionResolver
from world.rules.rulebook.schema import Rule
from world.rules.targeting import RoomActionContext
from world.skills.registry import TargetSpec

from ._combat_session_helpers import _race_key, open_synthetic_scope
from world.tests.synthetic_data import make_skill

_T_SELF_ARM = "t_self_arm"
_T_EVENT = "t_self_arm_stimulus"

# A self-target skill whose sole effect arms the sexual-transition bridge.
_T_SELF_ARM_SKILL = make_skill(
    _T_SELF_ARM,
    label="測試自觸技能",
    description="僅供測試的合成技能，唯一效果為帶自造事件名的性愛事件前綴。",
    effects=[f"sexual_event:{_T_EVENT}"],
    target_spec=TargetSpec.SELF,
)

# One file-local bridge rule: the invented event name moves pleasure by a
# fixed +2, so the asserted gain is authored here, never read from shipped
# balance data.
_T_BRIDGE_RULES = [
    Rule(
        id="t_bridge_rule",
        when={"event": _T_EVENT},
        then={"field": "pleasure", "delta": "+2"},
    )
]


class _FixedRng:
    @staticmethod
    def randint(lower, upper):
        return lower


class SexualEventSelfArmingTests(EvenniaTestCase):
    def setUp(self):
        super().setUp()
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "races",
            "subraces",
            "static_tiers",
            extra={"skills": {_T_SELF_ARM: _T_SELF_ARM_SKILL}},
        )
        self.actor = create_object(PlayerCharacter, key="sexual-caster")
        self.actor.race = _race_key()
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [_T_SELF_ARM], "passive": []}

    def test_landed_transition_module_resolves_and_mutates(self):
        from world.rules import sexual_transitions

        before = self.actor.sexual.pleasure.value
        with patch.object(sexual_transitions, "_RULES", _T_BRIDGE_RULES):
            result = ActionResolver.resolve(
                ActionRequest(
                    self.actor,
                    _T_SELF_ARM,
                    [],
                    RoomActionContext(
                        self.actor.location,
                        {"sexual": {"rng": _FixedRng()}},
                    ),
                )
            )
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.sexual.pleasure.value, before + 2)
