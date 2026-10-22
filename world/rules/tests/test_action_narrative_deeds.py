"""Behavior tests for settled skill and adult action narrative evidence and milestones.

OpenSpec change: record-action-adult-recent-deeds
Specs: openspec/specs/narrative-events/spec.md
Design: docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md §5, §5.1, §5.2, §6, §10
"""

from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from world.lore.sexual_vocab import BODY_PARTS
from world.narrative.events import get_committed_award_results
from world.narrative.models import NarrativeEvent
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.clock import AdvanceSource, WorldClock, get_world_clock
from world.quests.catalog import register_catalog
from world.rules.combat import Battlefield, _stored_hp
from world.rules.combat.rounds import _end_of_round_upkeep
from world.rules.targeting import RoomActionContext
from world.rules.titles import award_automatic_title, read_title_state
from world.rules.titles.awards import AutomaticTitleAward
from world.rules.titles.state import _FIXED_KIND
from world.skills.effects import EffectPolicy
from world.skills.registry import SkillCategory, SkillDef, SkillKind, TargetSpec
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY, SexualActDef
from world.tests.synthetic_data import make_skill


_T_HEAL_SKILL = make_skill(
    "t_synth_heal_deed",
    element="light",
    effects=("heal:single",),
    effect_policies=(EffectPolicy(coefficient=1.0),),
)

_T_RESISTIBLE_ADULT_ACT = SexualActDef(
    key="t_synth_resistible_adult_act",
    unlock={},
    base_pleasure=10,
    actor_part=BODY_PARTS[0],
    target_part=BODY_PARTS[0],
    actor_pleasure_ratio=0.5,
    actor_counters=("duo_act_count",),
    participant_counters=("duo_act_count",),
    sexual_events=(),
    resistible=True,
)

_T_RESISTIBLE_ADULT_SKILL = make_skill(
    key="t_synth_resistible_adult_act",
    label="t_可抵抗行為",
    description="t_合成可抵抗性愛行為",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    category=SkillCategory.SEXUAL_ACT,
    usable_out_of_combat=True,
    effects=[
        f"pleasure:{_T_RESISTIBLE_ADULT_ACT.key}",
        f"sexual_counter:{_T_RESISTIBLE_ADULT_ACT.key}",
    ],
)

_T_PENETRATION_ACT = SexualActDef(
    key="t_synth_penetration_act",
    unlock={},
    base_pleasure=15,
    actor_part=BODY_PARTS[0],
    target_part=BODY_PARTS[0],
    actor_pleasure_ratio=0.8,
    actor_counters=("duo_act_count",),
    participant_counters=("duo_act_count",),
    sexual_events=("first_vaginal_penetration",),
    resistible=False,
)

_T_PENETRATION_SKILL = make_skill(
    key="t_synth_penetration_act",
    label="t_初次結合行為",
    description="t_合成破處與經驗解鎖性愛行為",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    category=SkillCategory.SEXUAL_ACT,
    usable_out_of_combat=True,
    effects=[
        f"pleasure:{_T_PENETRATION_ACT.key}",
        f"sexual_counter:{_T_PENETRATION_ACT.key}",
        "sexual_event:first_vaginal_penetration",
    ],
)


class ActionNarrativeDeedsTests(EvenniaTestCase):
    """Behavior tests validating narrative deeds for skill use, adult actions, and milestones."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="deeds_room")
        self.actor = create_object(PlayerCharacter, key="ActorChar", location=self.room)
        self.target = create_object(PlayerCharacter, key="TargetChar", location=self.room)
        self.bystander = create_object(PlayerCharacter, key="BystanderPeer", location=self.room)
        for entity in (self.actor, self.target, self.bystander):
            entity.race = "human"
            entity.apply_race_baseline()
        self.actor.traits.hp.current = 100
        self.target.traits.hp.current = 50
        self.actor.traits.mp.current = 100
        self.context = RoomActionContext(self.room)

    def _grant_skills(self, entity, *skill_keys):
        entity.db.skills = {"active": list(skill_keys), "passive": []}

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_synthetic_heal_records_skill_use_without_rescue_claim(self):
        """Scenario: Concrete skill effects & untouched recipient control.

        WHEN a skill heals a recipient without protection evidence
        THEN the record states actual actor, recipient and effect without a rescue claim,
        AND an untouched co-located party member is NOT attributed a participation role.
        """
        self._grant_skills(self.actor, _T_HEAL_SKILL.key)
        request = ActionRequest(self.actor, _T_HEAL_SKILL.key, [self.target], self.context)

        with patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_HEAL_SKILL.key: _T_HEAL_SKILL}):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        self.assertGreater(self.target.traits.hp.current, 50)

        # Locate the recorded narrative event
        events = NarrativeEvent.objects.filter(event_type="skill_use")
        self.assertEqual(events.count(), 1)
        event = events.first()

        self.assertEqual(event.content["skill_key"], _T_HEAL_SKILL.key)
        self.assertEqual(event.content["actor"]["id"], str(self.actor.pk))
        self.assertEqual(event.content["actor"]["name"], self.actor.key)
        self.assertEqual(event.content["actor"]["role"], "actor")

        # Actual recipient is self.target
        self.assertEqual(len(event.content["recipients"]), 1)
        recipient = event.content["recipients"][0]
        self.assertEqual(recipient["id"], str(self.target.pk))
        self.assertEqual(recipient["name"], self.target.key)
        self.assertEqual(recipient["role"], "recipient")

        # Untouched bystander is NOT in recipients or participants
        self.assertNotIn(str(self.bystander.pk), event.participants)
        self.assertNotIn(self.bystander.key, [r["name"] for r in event.content["recipients"]])

        # Inviolable claim limits: no rescue or protection claim
        self.assertFalse(event.content["claim_limits"]["rescue_claimed"])
        self.assertFalse(event.content["claim_limits"]["protection_claimed"])

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results",
        "narrative-events::adult-evidence-does-not-invent-consent-or-public-standing",
    )
    def test_hostile_resisted_adult_act_retains_meaning_and_roles(self):
        """Scenario: Adult outcome retains meaning & resistance remains resistance.

        WHEN an adult action settles structured transition, counter and resistance results
        THEN the record retains the established act, roles and actual outcomes without
        reversing resistance or inferring willingness or consent.
        """
        self._grant_skills(self.actor, _T_RESISTIBLE_ADULT_SKILL.key)
        request = ActionRequest(
            self.actor, _T_RESISTIBLE_ADULT_SKILL.key, [self.target], self.context
        )

        with (
            patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_RESISTIBLE_ADULT_SKILL.key: _T_RESISTIBLE_ADULT_SKILL}),
            patch.dict(SEXUAL_ACT_REGISTRY, {_T_RESISTIBLE_ADULT_ACT.key: _T_RESISTIBLE_ADULT_ACT}),
            patch("world.rules.action.gates.roll_d100", return_value=100),  # Resisted successfully
        ):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")

        events = NarrativeEvent.objects.filter(event_type="adult_action")
        self.assertEqual(events.count(), 1)
        event = events.first()

        self.assertEqual(event.content["act_key"], _T_RESISTIBLE_ADULT_SKILL.key)
        self.assertEqual(event.content["actor"]["id"], str(self.actor.pk))
        self.assertEqual(event.content["actor"]["role"], "actor")

        self.assertEqual(len(event.content["recipients"]), 1)
        recipient = event.content["recipients"][0]
        self.assertEqual(recipient["id"], str(self.target.pk))
        self.assertEqual(recipient["role"], "recipient")

        # Resistance results are preserved and not inverted
        resistances = event.content["outcomes"]["resistance"]
        self.assertTrue(len(resistances) >= 1)
        self.assertTrue(any(r["resisted"] is True for r in resistances))

        # Inviolable consent and relationship bounds: resistance is NOT willingness
        self.assertFalse(event.content["privacy"]["consent_inferred"])
        self.assertFalse(event.content["privacy"]["willingness_inferred"])
        self.assertFalse(event.content["privacy"]["relationship_inferred"])

        # Untouched peer excluded from adult participation
        self.assertNotIn(str(self.bystander.pk), event.participants)

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_untouched_recipient_is_excluded_from_participants(self):
        """Scenario: Untouched recipient is excluded.

        WHEN a nearby party member receives no action or effect
        THEN the member is not attributed an adult participation role.
        """
        # Move bystander into room
        self.assertEqual(self.bystander.location, self.room)
        self._grant_skills(self.actor, _T_HEAL_SKILL.key)
        request = ActionRequest(self.actor, _T_HEAL_SKILL.key, [self.target], self.context)

        with patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_HEAL_SKILL.key: _T_HEAL_SKILL}):
            ActionResolver.resolve(request)

        event = NarrativeEvent.objects.filter(event_type="skill_use").first()
        self.assertIsNotNone(event)
        self.assertIn(str(self.actor.pk), event.participants)
        self.assertIn(str(self.target.pk), event.participants)
        self.assertNotIn(str(self.bystander.pk), event.participants)

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_action_rollback_and_replay_atomicity(self):
        """Scenario: Action rollback and replay.

        WHEN a source fails after deed/title writes, then later commits and replays
        THEN the failed transaction leaves no effects or evidence and the replay
        retains one committed occurrence and its original award results.
        """
        source_id = "occurrence:atomic_action_test:1"
        self._grant_skills(self.actor, _T_HEAL_SKILL.key)
        request = ActionRequest(
            self.actor, _T_HEAL_SKILL.key, [self.target], self.context, source_id=source_id
        )

        initial_target_hp = self.target.traits.hp.current

        # Simulate failure after deed/title write inside atomic block
        with self.assertRaises(RuntimeError):
            with transaction.atomic():
                with patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_HEAL_SKILL.key: _T_HEAL_SKILL}):
                    result = ActionResolver.resolve(request)
                    self.assertEqual(result.outcome, "success")
                    raise RuntimeError("Simulated database failure before outer commit")

        # Database rows rolled back completely
        self.assertFalse(NarrativeEvent.objects.filter(source_id=source_id).exists())

        # Later, commits successfully
        with transaction.atomic():
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_HEAL_SKILL.key: _T_HEAL_SKILL}):
                res1 = ActionResolver.resolve(request)
        self.assertEqual(res1.outcome, "success")
        self.assertEqual(NarrativeEvent.objects.filter(source_id=source_id).count(), 1)

        # Replay same occurrence with same source identity
        with transaction.atomic():
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_HEAL_SKILL.key: _T_HEAL_SKILL}):
                res2 = ActionResolver.resolve(request)
        self.assertEqual(res2.outcome, "success")
        # Exactly one occurrence remains, not duplicated
        self.assertEqual(NarrativeEvent.objects.filter(source_id=source_id).count(), 1)

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions"
    )
    def test_new_adult_threshold_is_recorded_once_and_replay_is_inert(self):
        """Scenario: New threshold is recorded once.

        WHEN a synthetic adult threshold is crossed and its settlement is replayed
        THEN one milestone records the actual crossing with the action provenance.
        """
        self.assertTrue(self.target.sexual.virgin)
        self.assertNotIn("陰道性交", self.target.sexual.experience_types)

        source_id = "occurrence:adult_milestone_test:1"
        self._grant_skills(self.actor, _T_PENETRATION_SKILL.key)
        request = ActionRequest(
            self.actor, _T_PENETRATION_SKILL.key, [self.target], self.context, source_id=source_id
        )

        with (
            patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_PENETRATION_SKILL.key: _T_PENETRATION_SKILL}),
            patch.dict(SEXUAL_ACT_REGISTRY, {_T_PENETRATION_ACT.key: _T_PENETRATION_ACT}),
        ):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        self.assertFalse(self.target.sexual.virgin)
        self.assertIn("陰道性交", self.target.sexual.experience_types)

        # Milestones recorded for virginity loss and newly acquired experience
        milestones = NarrativeEvent.objects.filter(event_type="adult_milestone")
        self.assertTrue(milestones.count() >= 1)

        exp_ms = milestones.filter(
            content__milestone_kind="experience_type",
            content__identifier="陰道性交",
            content__entity_id=str(self.target.pk),
        ).first()
        self.assertIsNotNone(exp_ms)
        self.assertEqual(exp_ms.content["action_source_id"], source_id)
        self.assertEqual(exp_ms.content["entity_id"], str(self.target.pk))

        count_before = NarrativeEvent.objects.filter(event_type="adult_milestone").count()

        # Replay the same action occurrence: replay must be inert
        with (
            patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_PENETRATION_SKILL.key: _T_PENETRATION_SKILL}),
            patch.dict(SEXUAL_ACT_REGISTRY, {_T_PENETRATION_ACT.key: _T_PENETRATION_ACT}),
        ):
            ActionResolver.resolve(request)

        count_after = NarrativeEvent.objects.filter(event_type="adult_milestone").count()
        self.assertEqual(count_before, count_after)

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions"
    )
    def test_old_lifetime_state_creates_no_recent_milestone(self):
        """Scenario: Old lifetime state has no recency.

        WHEN an existing counter or experience set is merely read or reconstructed
        THEN no recent milestone is created.
        """
        # Pre-seed existing experience and counters
        self.target.sexual.add_experience_type("陰道性交")
        self.target.sexual.virgin = False
        initial_milestone_count = NarrativeEvent.objects.filter(event_type="adult_milestone").count()

        # Re-read sexual handler without settlement
        _ = self.target.sexual.experience_types
        _ = self.target.sexual.virgin
        _ = self.target.sexual.climax_count

        self.assertEqual(
            NarrativeEvent.objects.filter(event_type="adult_milestone").count(),
            initial_milestone_count,
        )

        # Execute an action that does not cross any new threshold
        self._grant_skills(self.actor, _T_HEAL_SKILL.key)
        request = ActionRequest(self.actor, _T_HEAL_SKILL.key, [self.target], self.context)
        with patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_HEAL_SKILL.key: _T_HEAL_SKILL}):
            ActionResolver.resolve(request)

        # Pre-existing lifetime state must NOT create new milestones
        self.assertEqual(
            NarrativeEvent.objects.filter(event_type="adult_milestone").count(),
            initial_milestone_count,
        )

    @covers_requirement(
        "narrative-events::adult-evidence-does-not-invent-consent-or-public-standing"
    )
    def test_private_experience_stays_personal_without_public_notoriety(self):
        """Scenario: Private experience stays personal.

        WHEN a player has accessible private personal experience
        THEN it can support personal nomination without a public recognition claim
        or title-display policy change.
        """
        # Remove bystander from room to make it private between actor and target
        self.bystander.location = None

        self._grant_skills(self.actor, _T_RESISTIBLE_ADULT_SKILL.key)
        request = ActionRequest(
            self.actor, _T_RESISTIBLE_ADULT_SKILL.key, [self.target], self.context
        )

        with (
            patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_RESISTIBLE_ADULT_SKILL.key: _T_RESISTIBLE_ADULT_SKILL}),
            patch.dict(SEXUAL_ACT_REGISTRY, {_T_RESISTIBLE_ADULT_ACT.key: _T_RESISTIBLE_ADULT_ACT}),
            patch("world.rules.action.gates.roll_d100", return_value=100),
        ):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        event = NarrativeEvent.objects.filter(event_type="adult_action").first()
        self.assertIsNotNone(event)

        # Private experience without external audience
        self.assertEqual(event.visibility, "private")
        self.assertTrue(event.content["privacy"]["private_experience"])
        self.assertFalse(event.content["privacy"]["public_notoriety"])

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_ordinary_skill_and_adult_records_create_no_immediate_nomination_trigger(self):
        """Ordinary skill-use and adult-action records never create immediate nomination triggers."""
        self._grant_skills(self.actor, _T_HEAL_SKILL.key)
        request = ActionRequest(self.actor, _T_HEAL_SKILL.key, [self.target], self.context)

        with patch("server.title_nomination_service.schedule_epithet_nomination") as trigger_mock:
            with patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_HEAL_SKILL.key: _T_HEAL_SKILL}):
                result = ActionResolver.resolve(request)
            self.assertEqual(result.outcome, "success")
            trigger_mock.assert_not_called()

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions"
    )
    def test_clock_advance_climax_milestone(self):
        """Non-resolver climax settlement during clock advance records milestones."""
        self.target.sexual.climax_phase.value = "進行中"
        self.assertEqual(self.target.sexual.climax_count, 0)

        clock = WorldClock(tick=1000)
        clock.advance(1800, AdvanceSource.COMMAND, (self.target,))

        milestones = NarrativeEvent.objects.filter(
            event_type="adult_milestone",
            content__entity_id=str(self.target.pk),
            content__identifier="first_climax",
        )
        self.assertEqual(milestones.count(), 1)
        ms = milestones.first()
        self.assertIn("clock:climax:", ms.source_id)

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions"
    )
    def test_combat_upkeep_climax_milestone(self):
        """Non-resolver climax settlement during combat round upkeep records milestones."""
        self.target.sexual.climax_phase.value = "進行中"
        self.assertEqual(self.target.sexual.climax_count, 0)

        battlefield = Battlefield(
            {"party": frozenset({str(self.target.key)}), "foes": frozenset()},
            {str(self.target.key): self.target},
        )
        battlefield.session_id = "test_sess_upkeep"
        battlefield.round_number = 2

        _end_of_round_upkeep(battlefield)

        milestones = NarrativeEvent.objects.filter(
            event_type="adult_milestone",
            content__entity_id=str(self.target.pk),
            content__identifier="first_climax",
        )
        self.assertEqual(milestones.count(), 1)
        ms = milestones.first()
        self.assertIn("combat:test_sess_upkeep:round:2:upkeep:climax:", ms.source_id)

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_area_skill_targeting_and_duplicate_keys(self):
        """AREA targeting with entities sharing display keys retains distinct durable PK attribution."""
        target2 = create_object(PlayerCharacter, key="TargetChar", location=self.room)
        target2.race = "human"
        target2.apply_race_baseline()
        target2.traits.hp.current = 60

        area_heal_skill = make_skill(
            "t_synth_area_heal",
            element="light",
            target_spec=TargetSpec.AREA,
            effects=("heal:area",),
            effect_policies=(EffectPolicy(coefficient=1.0),),
        )

        self._grant_skills(self.actor, area_heal_skill.key)
        request = ActionRequest(self.actor, area_heal_skill.key, [self.target, target2], self.context)

        with patch.dict("world.skills.registry.SKILL_REGISTRY", {area_heal_skill.key: area_heal_skill}):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        event = NarrativeEvent.objects.filter(event_type="skill_use", content__skill_key=area_heal_skill.key).first()
        self.assertIsNotNone(event)

        recipient_ids = {r["id"] for r in event.content["recipients"]}
        self.assertIn(str(self.target.pk), recipient_ids)
        self.assertIn(str(target2.pk), recipient_ids)
        self.assertEqual(len(event.content["recipients"]), 2)

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_action_title_awards_finalized_in_narrative_event(self):
        """Automatic title awards from the occurrence are finalized into award_results."""
        source_id = "occurrence:title_award_action:1"
        self._grant_skills(self.actor, _T_HEAL_SKILL.key)
        request = ActionRequest(self.actor, _T_HEAL_SKILL.key, [self.target], self.context, source_id=source_id)

        synth_award = AutomaticTitleAward(
            source_id=source_id,
            recipient_id=str(self.actor.pk),
            kind=_FIXED_KIND,
            title_id="t_synth_action_title",
            granted_tick=100,
            display_name="合成事蹟稱號",
        )

        from world.rules.action import PendingEffect
        def fake_planner(req, log):
            return [PendingEffect(self.actor, "title_granted|t_synth", frozenset(), lambda: None, title_awards=[synth_award])]

        with (
            patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_HEAL_SKILL.key: _T_HEAL_SKILL}),
            patch.dict("world.rules.action.contracts._EVENT_EFFECT_PLANNERS", {"fake_title": fake_planner}),
        ):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")
        self.assertEqual(result.title_awards, (synth_award,))
        event = NarrativeEvent.objects.filter(source_id=source_id).first()
        self.assertIsNotNone(event)
        self.assertEqual(len(event.content.get("award_results", [])), 1)
        self.assertEqual(event.content["award_results"][0]["title_id"], "t_synth_action_title")
