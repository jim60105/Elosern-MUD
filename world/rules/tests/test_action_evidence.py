"""Behavior tests for recent-action evidence and conditional extra strikes (light-penance-events).

Validates bounded recent-action evidence recorded on the acting perpetrator
for committed forced interaction outcomes (resisted is False AND auto_comply is
False), exclusive 60 world second expiry boundaries, refresh-not-stack
semantics, non-mutating queries, rollback restoration, cross-path producers
(direct, NPC, combat session, cast settlement), and conditional extra
independent strikes riding DamagePolicy.repeat_when with ordered HP projection,
single defeat/knockout emissions, and nonlethal clamping.
"""

from collections.abc import Mapping
import unittest
from unittest.mock import patch

from tools.spec_traceability import covers_requirement

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.quests.catalog import register_catalog
from world.lore.sexual_vocab import BODY_PARTS
from world.rules.action import (
    ActionRequest,
    ActionResolver,
    CommitFailed,
    PendingEffect,
    RejectReason,
)
from world.rules.action_evidence import (
    ACTION_EVIDENCE_ATTR,
    EVIDENCE_KINDS,
    LIGHT_EVIDENCE_DURATION,
    action_evidence_planner,
    get_action_evidence,
    get_current_world_time,
    has_action_evidence,
    read_all_action_evidence,
    stage_action_evidence,
)
from world.rules.cast_settlement import settle_out_of_combat_cast
from world.rules.clock import WorldClock
from world.rules.combat import (
    Battlefield,
    BattlefieldActionContext,
    _stored_hp,
)
from world.rules.targeting import RoomActionContext
from world.rules.event_log import EventEntry, EventLog
from world.rules.traits import restore_gauges_to_full
from world.skills.effects import (
    DamageEffect,
    DamagePolicy,
    EffectAudience,
    EffectPolicy,
)
from world.skills.registry import SkillCategory, SkillDef, SkillKind, TargetSpec
from world.skills.sexual_acts import SexualActDef
from world.tests.synthetic_data import make_skill, synthetic_registries

from .combat_fixtures import grant_lineage


# Synthetic skills and acts for behavior testing
_T_PENANCE_BURST = make_skill(
    "t_penance_burst",
    element="fire",
    effects=("damage:fire:magic",),
    effect_policies=(
        EffectPolicy(
            coefficient=1.0,
            damage=DamagePolicy(
                repeat_when="forced_interaction",
                extra_strikes=1,
            ),
        ),
    ),
)

_T_PHYSICAL_RETRIBUTION = make_skill(
    "t_physical_retribution",
    element="fire",
    effects=("damage:fire:physical",),
    effect_policies=(
        EffectPolicy(
            coefficient=1.0,
            damage=DamagePolicy(
                repeat_when="forced_interaction",
                extra_strikes=1,
            ),
        ),
    ),
)

_T_AREA_RETRIBUTION = make_skill(
    "t_area_retribution",
    element="fire",
    target_spec=TargetSpec.AREA,
    effects=("damage:fire:magic",),
    effect_policies=(
        EffectPolicy(
            coefficient=1.0,
            audience=EffectAudience.ENEMIES,
            damage=DamagePolicy(
                repeat_when="forced_interaction",
                extra_strikes=1,
            ),
        ),
    ),
)

_T_RESISTIBLE_ACT_DEF = SexualActDef(
    key="t_synth_resistible_act",
    unlock={},
    base_pleasure=6,
    actor_part=BODY_PARTS[0],
    target_part=BODY_PARTS[0],
    actor_pleasure_ratio=0.5,
    actor_counters=(),
    participant_counters=(),
    sexual_events=(),
    resistible=True,
)

_T_RESISTIBLE_ACT_SKILL = SkillDef(
    key="t_synth_resistible_act",
    label="t_可抵抗行為",
    description="t_合成可抵抗行為",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={},
    usable_out_of_combat=True,
    element=None,
    effects=[
        "pleasure:t_synth_resistible_act",
        "sexual_counter:t_synth_resistible_act",
        "sexual_event:self_exposure",
    ],
    category=SkillCategory.SEXUAL_ACT,
    group="t_合成",
)

_EXTRA_SKILLS = {
    _T_PENANCE_BURST.key: _T_PENANCE_BURST,
    _T_PHYSICAL_RETRIBUTION.key: _T_PHYSICAL_RETRIBUTION,
    _T_AREA_RETRIBUTION.key: _T_AREA_RETRIBUTION,
    _T_RESISTIBLE_ACT_SKILL.key: _T_RESISTIBLE_ACT_SKILL,
}

_EXTRA_ACTS = {
    _T_RESISTIBLE_ACT_DEF.key: _T_RESISTIBLE_ACT_DEF,
}

_SCOPE = synthetic_registries(
    "skills",
    "sexual_acts",
    extra={"skills": _EXTRA_SKILLS, "sexual_acts": _EXTRA_ACTS},
)


class ActionEvidencePurityTests(unittest.TestCase):
    """Purity and boundary tests for action evidence storage and queries."""

    def test_uninitialized_entity_has_no_evidence(self):
        class DummyEntity:
            attributes = None

        self.assertFalse(has_action_evidence(DummyEntity(), "forced_interaction"))
        self.assertIsNone(get_action_evidence(DummyEntity(), "forced_interaction"))
        self.assertEqual(read_all_action_evidence(DummyEntity()), {})

    def test_unknown_evidence_kind_returns_false(self):
        class DummyEntity:
            attributes = {}

        self.assertFalse(has_action_evidence(DummyEntity(), "blasphemy"))
        self.assertIsNone(get_action_evidence(DummyEntity(), "blasphemy"))

    def test_malformed_attribute_fails_closed(self):
        class DummyAttributes:
            def __init__(self, val):
                self.val = val

            def get(self, key, default=None):
                return self.val

        class DummyEntity:
            def __init__(self, val):
                self.attributes = DummyAttributes(val)

        for bad in (None, [], "forced_interaction", 123, {"forced_interaction": "bad"}):
            with self.subTest(bad=bad):
                entity = DummyEntity(bad)
                self.assertFalse(has_action_evidence(entity, "forced_interaction"))
                self.assertIsNone(get_action_evidence(entity, "forced_interaction"))

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_exclusive_expiry_boundary(self):
        class DummyAttributes:
            def get(self, key, default=None):
                return {
                    "forced_interaction": {
                        "kind": "forced_interaction",
                        "actor_id": "1",
                        "recorded_at": 40,
                        "expires_at": 100,
                    }
                }

        class DummyEntity:
            attributes = DummyAttributes()

        entity = DummyEntity()
        # Active strictly before expiry
        self.assertTrue(has_action_evidence(entity, "forced_interaction", now=99))
        self.assertIsNotNone(get_action_evidence(entity, "forced_interaction", now=99))

        # Inactive exactly at expiry (exclusive boundary)
        self.assertFalse(has_action_evidence(entity, "forced_interaction", now=100))
        self.assertIsNone(get_action_evidence(entity, "forced_interaction", now=100))

        # Inactive after expiry
        self.assertFalse(has_action_evidence(entity, "forced_interaction", now=101))
        self.assertIsNone(get_action_evidence(entity, "forced_interaction", now=101))

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_queries_do_not_mutate_storage(self):
        storage = {
            "forced_interaction": {
                "kind": "forced_interaction",
                "actor_id": "1",
                "recorded_at": 40,
                "expires_at": 100,
            }
        }

        class DummyAttributes:
            def get(self, key, default=None):
                return storage

            def remove(self, key, category=None):
                raise AssertionError("storage mutated during read query")

            def add(self, key, value, category=None):
                raise AssertionError("storage mutated during read query")

        class DummyEntity:
            attributes = DummyAttributes()

        entity = DummyEntity()
        # Query when expired at now=200
        self.assertFalse(has_action_evidence(entity, "forced_interaction", now=200))
        self.assertIsNone(get_action_evidence(entity, "forced_interaction", now=200))
        # Verify storage remains unchanged
        self.assertIn("forced_interaction", storage)
        self.assertEqual(read_all_action_evidence(entity), storage)

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_refresh_monotonic_and_non_monotonic_semantics(self):
        storage = {}

        class DummyAttributes:
            def get(self, key, default=None):
                return storage.get(key, default)

            def add(self, key, value, category=None):
                storage[key] = value

        class DummyEntity:
            attributes = DummyAttributes()
            key = "actor1"
            pk = 1

        entity = DummyEntity()

        # 1. Initial stage at t=10, duration=60 -> expires at 70
        eff1 = stage_action_evidence(entity, "forced_interaction", event_time=10, duration=60)
        eff1.apply()
        self.assertEqual(storage[ACTION_EVIDENCE_ATTR]["forced_interaction"]["expires_at"], 70)

        # 2. Monotonic refresh at t=30, duration=60 -> max(70, 30+60=90) = 90
        eff2 = stage_action_evidence(entity, "forced_interaction", event_time=30, duration=60)
        eff2.apply()
        self.assertEqual(storage[ACTION_EVIDENCE_ATTR]["forced_interaction"]["expires_at"], 90)

        # 3. Non-monotonic / existing future expiry at t=20, duration=60 -> max(90, 20+60=80) = 90
        eff3 = stage_action_evidence(entity, "forced_interaction", event_time=20, duration=60)
        eff3.apply()
        self.assertEqual(storage[ACTION_EVIDENCE_ATTR]["forced_interaction"]["expires_at"], 90)

        # Verify strike count was not stacked (only single entry mapping)
        self.assertEqual(len(storage[ACTION_EVIDENCE_ATTR]), 1)
        self.assertNotIn("count", storage[ACTION_EVIDENCE_ATTR]["forced_interaction"])


class DamagePolicyValidationTests(unittest.TestCase):
    """Validation and invariant tests for DamagePolicy repeat_when extensions."""

    def test_repeat_when_with_extra_strikes_default(self):
        policy = DamagePolicy(repeat_when="forced_interaction")
        self.assertEqual(policy.repeat_when, "forced_interaction")
        self.assertEqual(policy.extra_strikes, 1)

    def test_repeat_when_unknown_kind_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(repeat_when="unknown_kind")
        self.assertIn("unknown DamagePolicy repeat_when predicate", str(ctx.exception))

    def test_repeat_when_non_string_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(repeat_when=123)
        self.assertIn("must be a string or None", str(ctx.exception))

    def test_extra_strikes_greater_than_one_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(repeat_when="forced_interaction", extra_strikes=2)
        self.assertIn("requires extra_strikes=1", str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(repeat_when="forced_interaction", extra_strikes=3)
        self.assertIn("must be in (0, 1, 2)", str(ctx.exception))

    def test_extra_strikes_zero_with_repeat_when_raises(self):
        with self.assertRaises(ValueError) as ctx:
            DamagePolicy(repeat_when="forced_interaction", extra_strikes=0)
        self.assertIn("requires extra_strikes=1", str(ctx.exception))

    def test_empty_predicate_permitted_with_repeat_when(self):
        policy = DamagePolicy(predicate=(), repeat_when="forced_interaction")
        self.assertEqual(policy.predicate, ())
        self.assertEqual(policy.repeat_when, "forced_interaction")
        self.assertEqual(policy.extra_strikes, 1)

    def test_both_predicate_and_repeat_when_valid(self):
        policy = DamagePolicy(
            predicate=("dark",),
            attack_multiplier=1.5,
            repeat_when="forced_interaction",
        )
        self.assertEqual(policy.predicate, ("dark",))
        self.assertEqual(policy.attack_multiplier, 1.5)
        self.assertEqual(policy.repeat_when, "forced_interaction")
        self.assertEqual(policy.extra_strikes, 1)


@_SCOPE
class ActionEvidenceEventLogPlannerTests(EvenniaTestCase):
    """Behavior tests for ActionResolver event-effect planning of action evidence."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.actor = create_object(PlayerCharacter, key="evid_actor")
        self.target = create_object(PlayerCharacter, key="evid_target")
        for entity in (self.actor, self.target):
            entity.race = "human"
            entity.apply_race_baseline()
            restore_gauges_to_full(entity)
            entity.db.skills = {"active": [], "passive": []}

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_qualifying_forced_outcome_marks_perpetrator_actor(self):
        """WHEN a forced outcome commits against a target, the actor qualifies, not the target."""
        event_log = EventLog(
            actor=str(self.actor.key),
            skill_key="t_synth_resistible_act",
            targets=(str(self.target.key),),
            entries=(
                EventEntry(
                    kind="sexual_resist",
                    actor=str(self.actor.key),
                    target=str(self.target.key),
                    data={"resisted": False, "auto_comply": False, "roll": 25},
                    text_template="",
                ),
            ),
            time_cost_seconds=0,
        )
        request = ActionRequest(
            self.actor,
            "t_synth_resistible_act",
            [self.target],
            BattlefieldActionContext(None, event_context={"now": 100}),
        )
        effects = action_evidence_planner(request, event_log)
        self.assertEqual(len(effects), 1)
        self.assertIs(effects[0].entity, self.actor)
        effects[0].apply()

        # Actor qualifies for the 60s window (until 100 + 60 = 160)
        self.assertTrue(has_action_evidence(self.actor, "forced_interaction", now=150))
        self.assertFalse(has_action_evidence(self.actor, "forced_interaction", now=160))

        # Target never qualifies
        self.assertFalse(has_action_evidence(self.target, "forced_interaction", now=150))

        # Event log contains no action_evidence entries (narrative text has no mechanical authority)
        self.assertFalse(any(e.kind == "action_evidence" for e in event_log.entries))

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_resisted_outcome_records_no_evidence(self):
        """WHEN the outcome is resisted, no new evidence is staged."""
        event_log = EventLog(
            actor=str(self.actor.key),
            skill_key="t_synth_resistible_act",
            targets=(str(self.target.key),),
            entries=(
                EventEntry(
                    kind="sexual_resist",
                    actor=str(self.actor.key),
                    target=str(self.target.key),
                    data={"resisted": True, "auto_comply": False, "roll": 85},
                    text_template="",
                ),
            ),
            time_cost_seconds=0,
        )
        request = ActionRequest(
            self.actor,
            "t_synth_resistible_act",
            [self.target],
            BattlefieldActionContext(None, event_context={"now": 100}),
        )
        effects = action_evidence_planner(request, event_log)
        self.assertEqual(effects, [])
        self.assertFalse(has_action_evidence(self.actor, "forced_interaction", now=100))

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_auto_comply_outcome_records_no_evidence(self):
        """WHEN the outcome is automatic compliance, no new evidence is staged."""
        event_log = EventLog(
            actor=str(self.actor.key),
            skill_key="t_synth_resistible_act",
            targets=(str(self.target.key),),
            entries=(
                EventEntry(
                    kind="sexual_resist",
                    actor=str(self.actor.key),
                    target=str(self.target.key),
                    data={"resisted": False, "auto_comply": True, "roll": None},
                    text_template="",
                ),
            ),
            time_cost_seconds=0,
        )
        request = ActionRequest(
            self.actor,
            "t_synth_resistible_act",
            [self.target],
            BattlefieldActionContext(None, event_context={"now": 100}),
        )
        effects = action_evidence_planner(request, event_log)
        self.assertEqual(effects, [])
        self.assertFalse(has_action_evidence(self.actor, "forced_interaction", now=100))

    def test_malformed_event_entry_fails_closed(self):
        """Malformed sexual_resist entry payloads do not crash the cast."""
        for bad_data in (None, "bad", 123, []):
            with self.subTest(bad_data=bad_data):
                event_log = EventLog(
                    actor=str(self.actor.key),
                    skill_key="t_synth_resistible_act",
                    targets=(str(self.target.key),),
                    entries=(
                        EventEntry(
                            kind="sexual_resist",
                            actor=str(self.actor.key),
                            target=str(self.target.key),
                            data=bad_data,
                            text_template="",
                        ),
                    ),
                    time_cost_seconds=0,
                )
                request = ActionRequest(
                    self.actor,
                    "t_synth_resistible_act",
                    [self.target],
                    BattlefieldActionContext(None, event_context={"now": 100}),
                )
                effects = action_evidence_planner(request, event_log)
                self.assertEqual(effects, [])

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_narrative_context_cannot_create_evidence(self):
        """WHEN a narrative or client context accuses a target of wrongdoing, no evidence is created."""
        event_log = EventLog(
            actor=str(self.actor.key),
            skill_key="t_synth_resistible_act",
            targets=(str(self.target.key),),
            entries=(
                EventEntry(
                    kind="narrative_accusation",
                    actor=str(self.target.key),
                    target=str(self.actor.key),
                    data={"accusation": "blasphemy", "guilty": True},
                    text_template="",
                ),
            ),
            time_cost_seconds=0,
        )
        request = ActionRequest(
            self.actor,
            "t_synth_resistible_act",
            [self.target],
            BattlefieldActionContext(None, event_context={"now": 100}),
        )
        effects = action_evidence_planner(request, event_log)
        self.assertEqual(effects, [])
        self.assertFalse(has_action_evidence(self.actor, "forced_interaction"))
        self.assertFalse(has_action_evidence(self.target, "forced_interaction"))

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_direct_resolver_cast_marks_actor(self):
        """A resistible act resolved through ActionResolver records evidence on the caster."""
        grant_lineage(self.actor, [_T_RESISTIBLE_ACT_SKILL.key])
        bf = Battlefield(
            {"party": frozenset({str(self.actor.key)}), "foes": frozenset({str(self.target.key)})},
            {str(self.actor.key): self.actor, str(self.target.key): self.target},
        )
        request = ActionRequest(
            self.actor,
            _T_RESISTIBLE_ACT_SKILL.key,
            [self.target],
            BattlefieldActionContext(bf, event_context={"now": 50}),
        )
        # Force low resist roll so target fails to resist (resisted is False, auto_comply is False)
        with patch("world.rules.action.gates.roll_d100", return_value=1):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertTrue(has_action_evidence(self.actor, "forced_interaction", now=50))
        self.assertTrue(has_action_evidence(self.actor, "forced_interaction", now=109))
        self.assertFalse(has_action_evidence(self.actor, "forced_interaction", now=110))

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_npc_perpetrator_cast_marks_npc(self):
        """An NPC perpetrator using a forced act is marked with evidence identically to a player."""
        npc = create_object(NPC, key="evid_npc")
        npc.race = "human"
        npc.apply_race_baseline()
        restore_gauges_to_full(npc)
        grant_lineage(npc, [_T_RESISTIBLE_ACT_SKILL.key])

        bf = Battlefield(
            {"party": frozenset({str(npc.key)}), "foes": frozenset({str(self.target.key)})},
            {str(npc.key): npc, str(self.target.key): self.target},
        )
        request = ActionRequest(
            npc,
            _T_RESISTIBLE_ACT_SKILL.key,
            [self.target],
            BattlefieldActionContext(bf, event_context={"now": 200}),
        )
        with patch("world.rules.action.gates.roll_d100", return_value=1):
            result = ActionResolver.resolve(request)
        self.assertEqual(result.outcome, "success")
        self.assertTrue(has_action_evidence(npc, "forced_interaction", now=200))
        self.assertTrue(has_action_evidence(npc, "forced_interaction", now=259))
        self.assertFalse(has_action_evidence(npc, "forced_interaction", now=260))

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_rollback_restores_action_evidence(self):
        """A failed commit rolls back staged action evidence to pre-action state."""
        grant_lineage(self.actor, [_T_RESISTIBLE_ACT_SKILL.key])
        bf = Battlefield(
            {"party": frozenset({str(self.actor.key)}), "foes": frozenset({str(self.target.key)})},
            {str(self.actor.key): self.actor, str(self.target.key): self.target},
        )
        request = ActionRequest(
            self.actor,
            _T_RESISTIBLE_ACT_SKILL.key,
            [self.target],
            BattlefieldActionContext(bf, event_context={"now": 50}),
        )

        def failing_apply():
            raise RuntimeError("forced commit failure")

        with patch("world.rules.action.gates.roll_d100", return_value=1), patch.dict(
            "world.rules.action.contracts._EVENT_EFFECT_PLANNERS",
            {
                "poison_planner": lambda r, l: [
                    PendingEffect(self.actor, "poison", frozenset({"action_evidence"}), failing_apply)
                ]
            },
            clear=False,
        ):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "rejected")
        # Evidence was rolled back and does not survive
        self.assertFalse(has_action_evidence(self.actor, "forced_interaction", now=50))

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_settle_out_of_combat_cast_marks_actor(self):
        """Out-of-combat cast settlement commits evidence on the caster on qualifying outcome."""
        room = create_object(Room, key="evid_room")
        self.actor.location = room
        self.target.location = room
        grant_lineage(self.actor, [_T_RESISTIBLE_ACT_SKILL.key])

        request = ActionRequest(
            self.actor,
            _T_RESISTIBLE_ACT_SKILL.key,
            [self.target],
            RoomActionContext(room, event_context={"now": 70}),
        )
        clock = WorldClock(tick=70)
        with patch("world.rules.action.gates.roll_d100", return_value=1):
            settlement = settle_out_of_combat_cast(request, clock=clock)
        self.assertEqual(settlement.result.outcome, "success")
        self.assertTrue(has_action_evidence(self.actor, "forced_interaction", now=70))
        self.assertTrue(has_action_evidence(self.actor, "forced_interaction", now=129))
        self.assertFalse(has_action_evidence(self.actor, "forced_interaction", now=130))

    @covers_requirement("recent-action-evidence::recent-evidence-is-committed-on-the-actor-and-expires-in-world-time")
    def test_settle_out_of_combat_cast_rollback_restores_evidence(self):
        """Outer settlement rollback restores pre-action evidence."""
        room = create_object(Room, key="evid_room_rb")
        self.actor.location = room
        self.target.location = room
        grant_lineage(self.actor, [_T_RESISTIBLE_ACT_SKILL.key])

        request = ActionRequest(
            self.actor,
            _T_RESISTIBLE_ACT_SKILL.key,
            [self.target],
            RoomActionContext(room, event_context={"now": 70}),
        )
        clock = WorldClock(tick=70)

        with patch("world.rules.action.gates.roll_d100", return_value=1), patch.object(
            clock, "advance", side_effect=RuntimeError("clock advance failed")
        ):
            with self.assertRaises(RuntimeError):
                settle_out_of_combat_cast(request, clock=clock)

        # Evidence did not survive outer settlement rollback
        self.assertFalse(has_action_evidence(self.actor, "forced_interaction", now=70))


@_SCOPE
class ConditionalExtraStrikeMechanicsTests(EvenniaTestCase):
    """Behavior tests for DamagePolicy extra independent strike mechanics."""

    def setUp(self):
        super().setUp()
        self.actor = create_object(PlayerCharacter, key="strike_actor")
        self.target = create_object(PlayerCharacter, key="strike_target")
        for entity in (self.actor, self.target):
            entity.race = "human"
            entity.apply_race_baseline()
            restore_gauges_to_full(entity)
            entity.db.skills = {"active": [], "passive": []}
        self.actor.traits.magic_power.base = 40
        self.actor.traits.atk_phys.base = 40
        self.target.traits.defense.base = 10
        restore_gauges_to_full(self.actor)
        restore_gauges_to_full(self.target)
        grant_lineage(
            self.actor,
            [_T_PENANCE_BURST.key, _T_PHYSICAL_RETRIBUTION.key, _T_AREA_RETRIBUTION.key],
        )

    def _battlefield(self, nonlethal: bool = False, nonlethal_keys: tuple[str, ...] = ()):
        bf = Battlefield(
            {"party": frozenset({"strike_actor"}), "foes": frozenset({"strike_target"})},
            {"strike_actor": self.actor, "strike_target": self.target},
        )
        event_ctx = {"now": 100}
        if nonlethal:
            event_ctx["nonlethal"] = True
        if nonlethal_keys:
            event_ctx["nonlethal_keys"] = nonlethal_keys
        return bf, BattlefieldActionContext(bf, event_context=event_ctx)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_first_miss_second_hit_deals_damage_and_records_both_rolls(self):
        """WHEN strike 1 misses and strike 2 hits on an eligible target, only strike 2 damages HP and both rolls are recorded."""
        # Mark target with fresh forced_interaction evidence
        eff = stage_action_evidence(self.target, "forced_interaction", event_time=80, duration=60)
        eff.apply()
        self.assertTrue(has_action_evidence(self.target, "forced_interaction", now=100))

        bf, ctx = self._battlefield()
        request = ActionRequest(
            self.actor,
            _T_PENANCE_BURST.key,
            [self.target],
            ctx,
        )

        initial_hp = _stored_hp(self.target)
        with patch("world.rules.combat.damage.roll_d100", side_effect=[1, 80]):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        roll_entries = [e for e in result.event_log.entries if e.kind == "roll"]
        damage_entries = [e for e in result.event_log.entries if e.kind == "damage"]

        # Exactly 2 rolls recorded for one paid action
        self.assertEqual(len(roll_entries), 2)
        self.assertFalse(roll_entries[0].data["hit"])
        self.assertTrue(roll_entries[1].data["hit"])

        # Exactly 1 damage entry from the second hit
        self.assertEqual(len(damage_entries), 1)
        self.assertGreater(damage_entries[0].data["amount"], 0)
        self.assertEqual(initial_hp - _stored_hp(self.target), damage_entries[0].data["amount"])

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_ineligible_target_has_only_one_strike(self):
        """WHEN recent evidence is missing or expired, only the ordinary single strike occurs."""
        # Target has no evidence
        self.assertFalse(has_action_evidence(self.target, "forced_interaction", now=100))

        bf, ctx = self._battlefield()
        request = ActionRequest(
            self.actor,
            _T_PENANCE_BURST.key,
            [self.target],
            ctx,
        )
        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        roll_entries = [e for e in result.event_log.entries if e.kind == "roll"]
        self.assertEqual(len(roll_entries), 1)

        # Now give evidence that is expired at now=100 (expires_at=90)
        eff = stage_action_evidence(self.target, "forced_interaction", event_time=20, duration=60)
        eff.apply()
        self.assertFalse(has_action_evidence(self.target, "forced_interaction", now=100))

        with patch("world.rules.combat.damage.roll_d100", return_value=50):
            result2 = ActionResolver.resolve(request)

        self.assertEqual(result2.outcome, "success")
        roll_entries2 = [e for e in result2.event_log.entries if e.kind == "roll"]
        self.assertEqual(len(roll_entries2), 1)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_ordered_hp_projection_and_single_defeat_entry(self):
        """Two strikes crossing target HP emit exactly one target_defeated entry."""
        eff = stage_action_evidence(self.target, "forced_interaction", event_time=80, duration=60)
        eff.apply()

        # Set target HP to 25 so two hits (each ~20 damage) drop it below 0
        self.target.traits.hp.base = 25
        restore_gauges_to_full(self.target)
        self.assertEqual(_stored_hp(self.target), 25)

        bf, ctx = self._battlefield()
        request = ActionRequest(
            self.actor,
            _T_PENANCE_BURST.key,
            [self.target],
            ctx,
        )
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        defeat_entries = [e for e in result.event_log.entries if e.kind == "target_defeated"]
        self.assertEqual(len(defeat_entries), 1)
        self.assertEqual(defeat_entries[0].target, str(self.target.key))

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_repeated_damage_floors_at_1_hp_with_single_knockout_in_nonlethal(self):
        """In nonlethal combat, two strikes crossing target HP floor at 1 with one knockout mark."""
        eff = stage_action_evidence(self.target, "forced_interaction", event_time=80, duration=60)
        eff.apply()

        self.target.traits.hp.base = 20
        restore_gauges_to_full(self.target)

        bf, ctx = self._battlefield(nonlethal=True, nonlethal_keys=(str(self.target.key),))
        request = ActionRequest(
            self.actor,
            _T_PENANCE_BURST.key,
            [self.target],
            ctx,
        )
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        # HP is floored at 1
        self.assertEqual(_stored_hp(self.target), 1)
        # Exactly one knockout entry
        ko_entries = [e for e in result.event_log.entries if e.kind == "target_knocked_out"]
        self.assertEqual(len(ko_entries), 1)
        self.assertEqual(ko_entries[0].target, str(self.target.key))
        # Battlefield knockout mark recorded
        self.assertIn(str(self.target.key), bf.knocked_out)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_atomic_rollback_restores_hp_and_evidence(self):
        """A failed commit after two strikes restores target HP and evidence atomically."""
        eff = stage_action_evidence(self.target, "forced_interaction", event_time=80, duration=60)
        eff.apply()
        initial_hp = _stored_hp(self.target)

        bf, ctx = self._battlefield()
        request = ActionRequest(
            self.actor,
            _T_PENANCE_BURST.key,
            [self.target],
            ctx,
        )

        def failing_apply():
            raise RuntimeError("commit explosion")

        with patch("world.rules.combat.damage.roll_d100", return_value=50), patch.dict(
            "world.rules.action.contracts._EVENT_EFFECT_PLANNERS",
            {
                "boom": lambda r, l: [
                    PendingEffect(self.target, "boom", frozenset({"traits"}), failing_apply)
                ]
            },
        ):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "rejected")
        # HP is restored
        self.assertEqual(_stored_hp(self.target), initial_hp)
        # Evidence is restored
        self.assertTrue(has_action_evidence(self.target, "forced_interaction", now=100))

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_second_synthetic_configuration_proves_policy_reuse(self):
        """A second synthetic physical skill uses the same generic repeat_when mechanism."""
        eff = stage_action_evidence(self.target, "forced_interaction", event_time=80, duration=60)
        eff.apply()

        bf, ctx = self._battlefield()
        request = ActionRequest(
            self.actor,
            _T_PHYSICAL_RETRIBUTION.key,
            [self.target],
            ctx,
        )
        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        roll_entries = [e for e in result.event_log.entries if e.kind == "roll"]
        self.assertEqual(len(roll_entries), 2)
        damage_entries = [e for e in result.event_log.entries if e.kind == "damage"]
        self.assertEqual(len(damage_entries), 2)

    @covers_requirement("skill-effect-model::a-follow-up-strike-repeats-damage-on-evidence-or-unconditionally-without-repeating-the-action")
    def test_area_mixed_eligibility_targets(self):
        """In an AREA cast, only the target carrying evidence receives the extra strike."""
        target2 = create_object(PlayerCharacter, key="target_clean")
        target2.race = "human"
        target2.apply_race_baseline()
        restore_gauges_to_full(target2)
        target2.traits.defense.base = 10

        # Only target1 carries evidence
        eff = stage_action_evidence(self.target, "forced_interaction", event_time=80, duration=60)
        eff.apply()

        bf = Battlefield(
            {
                "party": frozenset({"strike_actor"}),
                "foes": frozenset({"strike_target", "target_clean"}),
            },
            {
                "strike_actor": self.actor,
                "strike_target": self.target,
                "target_clean": target2,
            },
        )
        ctx = BattlefieldActionContext(bf, event_context={"now": 100})
        request = ActionRequest(
            self.actor,
            _T_AREA_RETRIBUTION.key,
            "all-enemies",
            ctx,
        )

        with patch("world.rules.combat.damage.roll_d100", return_value=80):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        t1_rolls = [
            e for e in result.event_log.entries
            if e.kind == "roll" and e.target == str(self.target.key)
        ]
        t2_rolls = [
            e for e in result.event_log.entries
            if e.kind == "roll" and e.target == str(target2.key)
        ]

        # Target 1 (with evidence) gets 2 rolls
        self.assertEqual(len(t1_rolls), 2)
        # Target 2 (without evidence) gets 1 roll
        self.assertEqual(len(t2_rolls), 1)
