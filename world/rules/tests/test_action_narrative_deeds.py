"""Behavior tests for settled skill and adult action narrative evidence and milestones.

OpenSpec change: record-action-adult-recent-deeds
Specs: openspec/specs/narrative-events/spec.md
Design: docs/superpowers/specs/2026-10-22-epithet-recent-deeds-design.md §5, §5.1, §5.2, §6, §10
"""

import json
import unittest
from unittest.mock import patch

from django.db import transaction
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.items import ItemUseMechanics
from world.lore.sexual_vocab import BODY_PARTS
from world.narrative.events import get_committed_award_results
from world.narrative.models import NarrativeEvent
from world.narrative.recent_deeds import select_authorized_recent_deeds
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.buffs import (
    BUFF_DEFINITIONS,
    BuffDefinition,
    apply_buff,
    entity_active_buffs,
)
from world.rules.clock import AdvanceSource, WorldClock, get_world_clock
from world.quests.catalog import register_catalog
from world.rules.combat import (
    Battlefield,
    COMBAT_YAML,
    CombatProvenance,
    _stored_hp,
    combat_provenance,
)
from world.rules.combat.rounds import _end_of_round_upkeep
from world.rules.combat_session import engage, forfeit, read_session
from world.rules.defeat_aftermath import DEFEAT_AFTERMATH_RULEBOOK
from world.rules.item_effects import (
    GaugeAdjustEffect,
    ItemEffectProfile,
    ItemStat,
    ItemTargetScope,
)
from world.rules.items import use_item
from world.rules.tests._combat_session_helpers import open_synthetic_scope
from world.rules.rulebook.schema import Rule
from world.rules.state_reactions import STATE_REACTION_RULES
from world.rules.targeting import RoomActionContext
from world.rules.titles import award_automatic_title, read_title_state
from world.rules.titles.awards import AutomaticTitleAward
from world.rules.titles.ballot import read_pending_ballot
from world.rules.titles.state import _FIXED_KIND
from world.skills.effects import EffectPolicy
from world.skills.registry import SkillCategory, SkillDef, SkillKind, TargetSpec
from world.skills.sexual_acts import SexualActDef
from world.tests.synthetic_data import make_item, make_skill


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
            patch.dict("world.skills.sexual_acts.SEXUAL_ACT_REGISTRY", {_T_RESISTIBLE_ADULT_ACT.key: _T_RESISTIBLE_ADULT_ACT}),
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
            patch.dict("world.skills.sexual_acts.SEXUAL_ACT_REGISTRY", {_T_PENETRATION_ACT.key: _T_PENETRATION_ACT}),
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
            patch.dict("world.skills.sexual_acts.SEXUAL_ACT_REGISTRY", {_T_PENETRATION_ACT.key: _T_PENETRATION_ACT}),
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
            patch.dict("world.skills.sexual_acts.SEXUAL_ACT_REGISTRY", {_T_RESISTIBLE_ADULT_ACT.key: _T_RESISTIBLE_ADULT_ACT}),
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
        # Optional battlefield attributes are not an identity source: the
        # occurrence provenance is. Attaching look-alike attributes proves the
        # upkeep source ignores them.
        battlefield.session_id = "test_sess_upkeep"
        battlefield.round_number = 9

        with combat_provenance(
            CombatProvenance(
                engagement_id="hostile:1000:1",
                round_ordinal=2,
                session_id="test_sess_upkeep",
            )
        ):
            _end_of_round_upkeep(battlefield)

        milestones = NarrativeEvent.objects.filter(
            event_type="adult_milestone",
            content__entity_id=str(self.target.pk),
            content__identifier="first_climax",
        )
        self.assertEqual(milestones.count(), 1)
        ms = milestones.first()
        self.assertIn("combat:hostile:1000:1:round:2:upkeep:", ms.source_id)
        self.assertNotIn("round:9", ms.source_id)
        self.assertEqual(
            ms.content["encounter_context"]["encounter_id"], "hostile:1000:1"
        )
        self.assertEqual(ms.content["encounter_context"]["round_number"], 2)

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions",
        "narrative-events::non-resolver-adult-milestones-are-recorded-at-transition-time",
    )
    def test_buff_reaction_crossing_is_recorded_once_by_its_upkeep(self):
        """Scenario: Upkeep buff reaction crossing is retained once.

        A real damage-over-time tick's ``hp_loss`` reaction raises pleasure and
        pushes the victim from 接近 into 進行中 *before* the later state
        snapshot. That crossing belongs to this upkeep boundary and is recorded
        exactly once under (engagement, round, entity); it is not re-dated by a
        later clock read, and a later round never reuses this source.
        """
        passive = make_skill(
            "t_upkeep_feedback",
            element="light",
            kind=SkillKind.PASSIVE,
            effects=(),
        )
        self.target.db.skills = {"active": [], "passive": [passive.key]}
        self.target.traits.hp.current = 100
        reaction = Rule(
            id="t_upkeep_feedback_rule",
            when={"event": "hp_loss", "skill_qualified": passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )
        rounds_seconds = int(COMBAT_YAML["round"]["seconds"])
        dot = BuffDefinition(
            key="t_upkeep_reaction_dot",
            duration=60,
            polarity="debuff",
            tick_interval=rounds_seconds,
            stacking="refresh",
            modifiers={"rate": {"target": "hp", "delta": -10}},
        )
        battlefield = Battlefield(
            {"party": frozenset({str(self.target.key)}), "foes": frozenset()},
            {str(self.target.key): self.target},
        )
        first_round = CombatProvenance(
            engagement_id="hostile:upkeep-reaction:1",
            round_ordinal=1,
            session_id="test_sess_reaction",
        )

        with patch.dict(BUFF_DEFINITIONS, {dot.key: dot}, clear=False), patch.dict(
            "world.skills.registry.SKILL_REGISTRY", {passive.key: passive}
        ), patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction],
        ):
            apply_buff(self.target, dot.key)
            # Park the victim one step below the active phase only after the
            # debuff's own application reaction, so the tick is the crossing.
            self.target.sexual.climax_phase.value = "接近"
            self.target.sexual.pleasure.base = 60
            # A staged extension keeps settlement in the active phase, so the
            # crossing this very upkeep applied stays observable afterwards.
            self.target.sexual.stage_climax_extension()
            with patch("world.rules.combat.rounds.log_info") as info:
                with self.captureOnCommitCallbacks(execute=True):
                    with combat_provenance(first_round):
                        _end_of_round_upkeep(battlefield)

        self.assertEqual(self.target.sexual.climax_phase.level, "進行中")
        first_source = (
            f"combat:hostile:upkeep-reaction:1:round:1:upkeep:{self.target.pk}"
            f":milestone:{self.target.pk}:state_transition:climax_onset"
        )
        onset = NarrativeEvent.objects.filter(
            event_type="adult_milestone", source_id=first_source
        )
        self.assertEqual(onset.count(), 1)
        self.assertEqual(
            onset.first().content["encounter_context"]["encounter_id"],
            "hostile:upkeep-reaction:1",
        )
        boundary = [
            call.kwargs["context"]
            for call in info.call_args_list
            if call.args and call.args[0] == "combat_upkeep_milestone"
        ]
        self.assertEqual(len(boundary), 1)
        self.assertEqual(boundary[0]["engagement"], "hostile:upkeep-reaction:1")
        self.assertEqual(boundary[0]["round"], 1)
        self.assertEqual(boundary[0]["entity"], str(self.target.pk))
        self.assertGreaterEqual(boundary[0]["milestones"], 1)

        # A later clock read re-reads the already-recorded state: the crossing
        # is not dated again (a genuinely new later transition may still be).
        with patch.dict(BUFF_DEFINITIONS, {dot.key: dot}, clear=False), patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction],
        ):
            WorldClock(tick=get_world_clock().tick).advance(
                6, AdvanceSource.COMMAND, (self.target,)
            )
        self.assertEqual(
            NarrativeEvent.objects.filter(
                event_type="adult_milestone",
                source_id=first_source,
            ).count(),
            1,
        )

        # Later rounds own distinct sources: the round discriminator is part
        # of the identity (pinned for both rounds by the provenance suite).
        self.assertIn(":round:1:upkeep:", first_source)
        self.assertEqual(
            len(
                {
                    event.source_id
                    for event in NarrativeEvent.objects.filter(
                        event_type="adult_milestone"
                    )
                }
            ),
            NarrativeEvent.objects.filter(event_type="adult_milestone").count(),
        )

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions",
        "narrative-events::non-resolver-adult-milestones-are-recorded-at-transition-time",
    )
    def test_buff_onset_settled_in_the_same_boundary_is_retained(self):
        """An onset erased by the same boundary's settlement is still recorded."""
        passive = make_skill(
            "t_upkeep_feedback_settled",
            element="light",
            kind=SkillKind.PASSIVE,
            effects=(),
        )
        self.target.db.skills = {"active": [], "passive": [passive.key]}
        # A previous climax exists, so ``first_climax`` cannot stand in for
        # the onset this boundary is responsible for.
        self.target.sexual.record_climax_count()
        reaction = Rule(
            id="t_upkeep_feedback_settled_rule",
            when={"event": "hp_loss", "skill_qualified": passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )
        dot = BuffDefinition(
            key="t_upkeep_settled_dot",
            duration=60,
            polarity="debuff",
            tick_interval=int(COMBAT_YAML["round"]["seconds"]),
            stacking="refresh",
            modifiers={"rate": {"target": "hp", "delta": -10}},
        )
        battlefield = Battlefield(
            {"party": frozenset({str(self.target.key)}), "foes": frozenset()},
            {str(self.target.key): self.target},
        )
        provenance = CombatProvenance(
            engagement_id="hostile:upkeep-settled:1",
            round_ordinal=1,
            session_id="test_sess_settled",
        )
        with patch.dict(BUFF_DEFINITIONS, {dot.key: dot}, clear=False), patch.dict(
            "world.skills.registry.SKILL_REGISTRY", {passive.key: passive}
        ), patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction],
        ):
            apply_buff(self.target, dot.key)
            self.target.sexual.climax_phase.value = "接近"
            self.target.sexual.pleasure.base = 60
            with combat_provenance(provenance):
                _end_of_round_upkeep(battlefield)

        self.assertEqual(self.target.sexual.climax_phase.level, "餘韻")
        self.assertEqual(self.target.sexual.climax_count, 2)
        upkeep_source = (
            f"combat:hostile:upkeep-settled:1:round:1:upkeep:{self.target.pk}"
        )
        milestone = NarrativeEvent.objects.get(
            event_type="adult_milestone",
            content__action_source_id=upkeep_source,
            content__identifier="climax_onset",
        )
        self.assertTrue(milestone.source_id.startswith(upkeep_source))

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
        # Verify distinct per-effect target_id attribution
        effect_target_ids = {eff.get("target_id") for eff in event.content["effects"]}
        self.assertIn(str(self.target.pk), effect_target_ids)
        self.assertIn(str(target2.pk), effect_target_ids)

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

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_combat_slot_provenance_preserves_title_award_provenance(self):
        """A combat action's round/slot provenance establishes exact source_id parity with its awards."""
        self._grant_skills(self.actor, _T_HEAL_SKILL.key)
        combat_ctx = RoomActionContext(self.room)
        combat_ctx.battlefield = Battlefield(
            {"party": frozenset({str(self.actor.key), str(self.target.key)}), "foes": frozenset()},
            {str(self.actor.key): self.actor, str(self.target.key): self.target},
        )
        # Look-alike optional attributes must never become the identity: the
        # occurrence provenance is the only source.
        combat_ctx.battlefield.session_id = "sess_not_authoritative"
        combat_ctx.battlefield.round_number = 7

        request = ActionRequest(self.actor, _T_HEAL_SKILL.key, [self.target], combat_ctx)
        provenance = CombatProvenance(
            engagement_id="hostile:42:1",
            round_ordinal=3,
            slot_ordinal=2,
            session_id="sess_combat_prov",
        )

        expected_source_id = (
            f"action:combat:hostile:42:1:r3:s2:{self.actor.pk}:{_T_HEAL_SKILL.key}"
        )

        synth_award = AutomaticTitleAward(
            source_id=expected_source_id,
            recipient_id=str(self.actor.pk),
            kind=_FIXED_KIND,
            title_id="t_combat_title",
            granted_tick=100,
            display_name="戰鬥稱號",
        )

        from world.rules.action import PendingEffect
        def fake_planner(req, log):
            # Planner must observe the identical request.source_id
            self.assertEqual(req.source_id, expected_source_id)
            return [PendingEffect(self.actor, "title_granted|t_combat", frozenset(), lambda: None, title_awards=[synth_award])]

        with (
            patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_HEAL_SKILL.key: _T_HEAL_SKILL}),
            patch.dict("world.rules.action.contracts._EVENT_EFFECT_PLANNERS", {"fake_combat_title": fake_planner}),
            combat_provenance(provenance),
        ):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success", f"Failed with {result.reason}: {result.detail}")
        self.assertEqual(result.title_awards[0].source_id, expected_source_id)
        event = NarrativeEvent.objects.filter(source_id=expected_source_id).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.content["action_source_id"], expected_source_id)
        self.assertEqual(event.content["award_results"][0]["source_id"], expected_source_id)
        self.assertEqual(
            event.content["encounter_context"],
            {
                "encounter_id": "hostile:42:1",
                "session_id": "sess_combat_prov",
                "round_number": 3,
                "slot_ordinal": 2,
            },
        )

    @covers_requirement(
        "narrative-events::adult-evidence-does-not-invent-consent-or-public-standing",
        "narrative-events::adult-milestones-record-newly-crossed-transitions",
    )
    def test_room_occupancy_does_not_promote_private_milestones_to_public(self):
        """Room occupancy by third-party living entities keeps personal milestones strictly private."""
        # Bystander is in room
        self.assertEqual(self.bystander.location, self.room)

        self._grant_skills(self.actor, _T_PENETRATION_SKILL.key)
        request = ActionRequest(
            self.actor, _T_PENETRATION_SKILL.key, [self.target], self.context
        )

        with (
            patch.dict("world.skills.registry.SKILL_REGISTRY", {_T_PENETRATION_SKILL.key: _T_PENETRATION_SKILL}),
            patch.dict("world.skills.sexual_acts.SEXUAL_ACT_REGISTRY", {_T_PENETRATION_ACT.key: _T_PENETRATION_ACT}),
        ):
            result = ActionResolver.resolve(request)

        self.assertEqual(result.outcome, "success")

        # While the action itself was observed by bystander:
        action_event = NarrativeEvent.objects.filter(event_type="adult_action").first()
        self.assertIsNotNone(action_event)
        self.assertEqual(action_event.visibility, "public")

        # BUT individual adult_milestone records remain strictly private to their subject!
        milestones = NarrativeEvent.objects.filter(event_type="adult_milestone")
        self.assertTrue(milestones.count() >= 1)
        for ms in milestones:
            self.assertEqual(ms.visibility, "private")
            self.assertTrue(ms.content["privacy"]["private_experience"])


# A single file-local buff mount so the buff families have a real registered row.
_T_DEED_WARD = BuffDefinition(
    key="t_deed_ward",
    duration=60,
    tick_interval=None,
    stacking="refresh",
    modifiers={},
    polarity="buff",
)

_T_BUFF_SKILL = make_skill(
    key="t_synth_buff_deed",
    element=None,
    target_spec=TargetSpec.SINGLE,
    effects=["buff_apply:t_deed_ward"],
    effect_policies=(EffectPolicy(1.0),),
)

_T_SELF_BUFF_SKILL = make_skill(
    key="t_synth_self_buff_deed",
    element=None,
    target_spec=TargetSpec.SELF,
    effects=["self_buff_apply:t_deed_ward"],
    effect_policies=(EffectPolicy(1.0),),
)

_T_CLEANSE_SKILL = make_skill(
    key="t_synth_cleanse_deed",
    element="light",
    target_spec=TargetSpec.SINGLE,
    effects=["cleanse:status"],
    effect_policies=(EffectPolicy(1.0),),
)

# Two cleanse components in one occurrence: the second removes nothing.
_T_DOUBLE_CLEANSE_SKILL = make_skill(
    key="t_synth_double_cleanse_deed",
    element="light",
    target_spec=TargetSpec.SINGLE,
    effects=["cleanse:status", "cleanse:status"],
    effect_policies=(EffectPolicy(1.0), EffectPolicy(1.0)),
)

# Two heals in one occurrence: only the remaining HP gap can be restored.
_T_DOUBLE_HEAL_SKILL = make_skill(
    key="t_synth_double_heal_deed",
    element="light",
    target_spec=TargetSpec.SINGLE,
    effects=["heal:single", "heal:single"],
    effect_policies=(EffectPolicy(1.0), EffectPolicy(1.0)),
)

# A restore whose requested amount exceeds a nearly full gauge.
_T_RESTORE_SKILL = make_skill(
    key="t_synth_restore_deed",
    element="light",
    target_spec=TargetSpec.SINGLE,
    effects=["gauge_transfer:mp:restore:fixed:40"],
    effect_policies=(EffectPolicy(1.0),),
)

# A high-pleasure self act: its staged gain exceeds any remaining gauge room, so
# the committed amount and the requested magnitude differ observably.
_T_FLOOD_ACT = SexualActDef(
    key="t_synth_flood_act",
    unlock={},
    base_pleasure=80,
    actor_part=BODY_PARTS[0],
    target_part=BODY_PARTS[0],
    actor_pleasure_ratio=0.5,
    actor_counters=("duo_act_count",),
    participant_counters=("duo_act_count",),
    sexual_events=(),
    resistible=False,
)

_T_FLOOD_SKILL = make_skill(
    key="t_synth_flood_act",
    label="t_溢滿行為",
    description="t_合成高快感性愛行為",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    category=SkillCategory.SEXUAL_ACT,
    usable_out_of_combat=True,
    effects=[f"pleasure:{_T_FLOOD_ACT.key}", f"sexual_counter:{_T_FLOOD_ACT.key}"],
)

# A self act whose settled sexual event is an own-state transition.
_T_SELF_ACT = SexualActDef(
    key="t_synth_self_deed_act",
    unlock={},
    base_pleasure=5,
    actor_part=BODY_PARTS[0],
    target_part=BODY_PARTS[0],
    actor_pleasure_ratio=1.0,
    actor_counters=("duo_act_count",),
    participant_counters=("duo_act_count",),
    sexual_events=(),
    resistible=False,
)

_T_SELF_ACT_SKILL = make_skill(
    key="t_synth_self_deed_act",
    label="t_自身性愛行為",
    description="t_合成自身性愛行為",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SELF,
    category=SkillCategory.SEXUAL_ACT,
    usable_out_of_combat=True,
    effects=[
        f"pleasure:{_T_SELF_ACT.key}",
        f"sexual_counter:{_T_SELF_ACT.key}",
        "sexual_event:stimulus_applied",
    ],
)


class SettledEffectVocabularyTests(EvenniaTestCase):
    """Committed effect vocabulary, committed amounts and legal absent rolls."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="effect_deeds_room")
        self.actor = create_object(PlayerCharacter, key="EffectActor", location=self.room)
        self.target = create_object(PlayerCharacter, key="EffectTarget", location=self.room)
        self.bystander = create_object(PlayerCharacter, key="EffectBystander", location=self.room)
        for entity in (self.actor, self.target, self.bystander):
            entity.race = "human"
            entity.apply_race_baseline()
        self.actor.traits.hp.current = 100
        self.target.traits.hp.current = 50
        self.actor.traits.mp.current = 100
        self.context = RoomActionContext(self.room)
        buff_patch = patch.dict(
            "world.rules.buffs.BUFF_DEFINITIONS",
            {_T_DEED_WARD.key: _T_DEED_WARD},
            clear=False,
        )
        buff_patch.start()
        self.addCleanup(buff_patch.stop)

    def _cast(self, skill, targets, *, source_id=None, acts=None):
        self.actor.db.skills = {"active": [skill.key], "passive": []}
        request = ActionRequest(
            self.actor, skill.key, targets, self.context, source_id=source_id
        )
        act_patch = patch.dict(
            "world.skills.sexual_acts.SEXUAL_ACT_REGISTRY",
            acts or {},
            clear=False,
        )
        with (
            patch.dict("world.skills.registry.SKILL_REGISTRY", {skill.key: skill}),
            act_patch,
        ):
            return ActionResolver.resolve(request)

    def _action_evidence(self):
        events = list(NarrativeEvent.objects.filter(event_type__in=["skill_use", "adult_action"]))
        self.assertEqual(len(events), 1)
        return events[0]

    def _effect_rows(self, content):
        """Return the committed effect rows of one evidence record."""
        if "outcomes" in content:
            return content["outcomes"]["effects"]
        return content["effects"]

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_committed_pleasure_gain_keeps_actor_recipient_and_result(self):
        """Scenario: Production effect vocabulary survives persistence.

        WHEN a settled adult act applies pleasure gain
        THEN its committed effect states the actual actor, recipient and result.
        """
        with patch("world.rules.action.gates.roll_d100", return_value=1):
            result = self._cast(
                _T_RESISTIBLE_ADULT_SKILL,
                [self.target],
                acts={_T_RESISTIBLE_ADULT_ACT.key: _T_RESISTIBLE_ADULT_ACT},
            )
        self.assertEqual(result.outcome, "success", f"{result.reason}: {result.detail}")

        content = self._action_evidence().content
        rows = [row for row in self._effect_rows(content) if row["kind"] == "pleasure_gain"]
        recipient_rows = [row for row in rows if row["target_id"] == str(self.target.pk)]
        self.assertEqual(len(recipient_rows), 1)
        row = recipient_rows[0]
        self.assertEqual(row["actor_id"], str(self.actor.pk))
        self.assertEqual(row["target_name"], self.target.key)
        self.assertGreater(row["result"]["amount"], 0)
        self.assertEqual(
            set(row["result"]), {"amount"}
        )

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_committed_target_buff_keeps_actor_recipient_and_result(self):
        """Scenario: Production effect vocabulary survives persistence.

        WHEN a settled skill applies a target buff
        THEN the committed effect states actor, recipient and the applied buff.
        """
        result = self._cast(_T_BUFF_SKILL, [self.target])
        self.assertEqual(result.outcome, "success", f"{result.reason}: {result.detail}")

        rows = [row for row in self._effect_rows(self._action_evidence().content)
                if row["kind"] == "buff_applied"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["actor_id"], str(self.actor.pk))
        self.assertEqual(rows[0]["target_id"], str(self.target.pk))
        self.assertEqual(rows[0]["target_name"], self.target.key)
        self.assertEqual(rows[0]["result"], {"buff_key": _T_DEED_WARD.key})

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_committed_self_buff_keeps_actor_and_result(self):
        """Scenario: Production effect vocabulary survives persistence.

        WHEN a settled skill applies a self buff
        THEN the committed effect states the actor as its own recipient and result.
        """
        result = self._cast(_T_SELF_BUFF_SKILL, [])
        self.assertEqual(result.outcome, "success", f"{result.reason}: {result.detail}")

        rows = [row for row in self._effect_rows(self._action_evidence().content)
                if row["kind"] == "self_buff_applied"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["actor_id"], str(self.actor.pk))
        self.assertEqual(rows[0]["target_id"], str(self.actor.pk))
        self.assertEqual(rows[0]["result"], {"buff_key": _T_DEED_WARD.key})

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_committed_cleanse_keeps_actor_recipient_and_result(self):
        """Scenario: Production effect vocabulary survives persistence.

        WHEN a settled skill cleanses a recipient's debuffs
        THEN the committed effect states actor, recipient and the removal count.
        """
        apply_buff(self.target, "poisoned")
        result = self._cast(_T_CLEANSE_SKILL, [self.target])
        self.assertEqual(result.outcome, "success", f"{result.reason}: {result.detail}")

        rows = [row for row in self._effect_rows(self._action_evidence().content)
                if row["kind"] == "buffs_cleansed"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["actor_id"], str(self.actor.pk))
        self.assertEqual(rows[0]["target_id"], str(self.target.pk))
        self.assertEqual(rows[0]["result"], {"count": 1})

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_clamped_gain_states_the_committed_amount(self):
        """Scenario: Actual bounded effect remains actual.

        WHEN an effect requests more pleasure than the recipient can receive
        THEN the deed states the committed amount, not the requested magnitude,
        AND a non-participant keeps an unchanged gauge and no effect row.
        """
        self.target.sexual.pleasure.base = 95
        bystander_pleasure = self.bystander.sexual.pleasure.value

        result = self._cast(
            _T_FLOOD_SKILL,
            [self.target],
            acts={_T_FLOOD_ACT.key: _T_FLOOD_ACT},
        )
        self.assertEqual(result.outcome, "success", f"{result.reason}: {result.detail}")
        self.assertEqual(self.target.sexual.pleasure.value, 100)

        requested = [
            entry.data["amount"]
            for entry in result.event_log.entries
            if entry.kind == "pleasure_gain" and entry.target == self.target.key
        ]
        self.assertEqual(len(requested), 1)
        self.assertGreater(requested[0], 5)

        rows = [row for row in self._effect_rows(self._action_evidence().content)
                if row["kind"] == "pleasure_gain"]
        recipient_rows = [row for row in rows if row["target_id"] == str(self.target.pk)]
        self.assertEqual(len(recipient_rows), 1)
        self.assertEqual(recipient_rows[0]["result"]["amount"], 5)
        self.assertNotIn(
            str(self.bystander.pk),
            [row["target_id"] for row in rows],
        )
        self.assertEqual(self.bystander.sexual.pleasure.value, bystander_pleasure)

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_clamped_gauge_restore_states_the_committed_amount(self):
        """Scenario: Actual bounded effect remains actual.

        WHEN a restore requests more of a resource than the recipient can hold
        THEN the deed states the committed restoration, not the requested one.
        """
        self.target.traits.mp.current = 95
        result = self._cast(_T_RESTORE_SKILL, [self.target])
        self.assertEqual(result.outcome, "success", f"{result.reason}: {result.detail}")
        staged = [
            entry.data["amount"]
            for entry in result.event_log.entries
            if entry.kind == "gauge_transfer" and entry.target == self.target.key
        ]
        self.assertEqual(len(staged), 1)
        self.assertGreater(staged[0], 5)
        self.assertEqual(self.target.traits.mp.current, 100)

        rows = [row for row in self._effect_rows(self._action_evidence().content)
                if row["kind"] == "gauge_transfer"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target_id"], str(self.target.pk))
        self.assertEqual(
            rows[0]["result"], {"gauge": "mp", "direction": "restore", "amount": 5}
        )

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_each_heal_states_the_hp_it_actually_restored(self):
        """Scenario: Actual bounded effect remains actual.

        WHEN one occurrence stages two heals for a recipient with room for only
        the first
        THEN each staged component states the HP its own application restored.
        """
        maximum = int(self.target.traits.hp.max)
        self.target.traits.hp.current = maximum - 2

        result = self._cast(_T_DOUBLE_HEAL_SKILL, [self.target])
        self.assertEqual(result.outcome, "success", f"{result.reason}: {result.detail}")
        self.assertEqual(int(self.target.traits.hp.value), maximum)

        # Both components stage the same clamped restoration against the same
        # pre-settlement gap, so only the first can commit HP. Each record
        # states what its own application restored, never the staged request.
        staged = {
            entry.data["amount"]
            for entry in result.event_log.entries
            if entry.kind == "heal" and entry.target == self.target.key
        }
        self.assertEqual(staged, {2})

        rows = [row for row in self._effect_rows(self._action_evidence().content)
                if row["kind"] == "heal"]
        self.assertEqual(len(rows), 2)
        amounts = [row["result"]["amount"] for row in rows]
        self.assertEqual(amounts, [2, 0])

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_snapshot_read_creates_no_buff_storage(self):
        """Scenario: Action rollback and replay (read-only snapshot).

        WHEN a pre-settlement snapshot is taken for a buff-free entity
        THEN the snapshot creates no buff storage to roll back.
        """
        import world.narrative.action_adapters as adapter_module

        fresh = create_object(PlayerCharacter, key="EffectFresh", location=self.room)
        fresh.race = "human"
        fresh.apply_race_baseline()
        self.assertFalse(fresh.attributes.has("buffs"))

        snapshot = adapter_module.capture_milestone_snapshot(fresh)
        self.assertIsNotNone(snapshot)
        self.assertEqual(snapshot.gauges.buff_keys, frozenset())
        self.assertFalse(fresh.attributes.has("buffs"))

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_repeated_cleanse_states_the_committed_removal_count(self):
        """Scenario: Actual bounded effect remains actual.

        WHEN one occurrence stages two cleanses but only one debuff is present
        THEN the deed states the committed removal count once for the recipient.
        """
        apply_buff(self.target, "poisoned")

        result = self._cast(_T_DOUBLE_CLEANSE_SKILL, [self.target])
        self.assertEqual(result.outcome, "success", f"{result.reason}: {result.detail}")
        self.assertEqual(entity_active_buffs(self.target), set())

        rows = [row for row in self._effect_rows(self._action_evidence().content)
                if row["kind"] == "buffs_cleansed"]
        # Each cleanse component states the removals its own application made:
        # the second finds nothing left and can never repeat the first's count.
        self.assertEqual([row["target_id"] for row in rows], [str(self.target.pk)] * 2)
        self.assertEqual(
            [row["result"]["count"] for row in rows], [1, 0]
        )

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_committed_log_form_states_the_same_settled_results(self):
        """Scenario: Production effect vocabulary survives persistence.

        WHEN the committed event log is the only input form
        THEN repeated bounded results collapse to one committed record per
        recipient and the other families state the same values as the staged form.
        """
        import world.narrative.action_adapters as adapter_module
        from world.rules.event_log import EventEntry, EventLog

        self.target.sexual.pleasure.base = 95
        snapshot = adapter_module.capture_milestone_snapshot(self.target)
        self.target.sexual.pleasure.base = 100
        log = EventLog(
            actor=str(self.actor.pk),
            skill_key=_T_RESISTIBLE_ADULT_SKILL.key,
            targets=(self.target.key,),
            entries=(
                EventEntry(
                    kind="pleasure_gain",
                    actor=str(self.actor.pk),
                    target=self.target.key,
                    data={"amount": 40},
                    text_template="{done}",
                ),
                EventEntry(
                    kind="pleasure_gain",
                    actor=str(self.actor.pk),
                    target=self.target.key,
                    data={"amount": 10},
                    text_template="{done}",
                ),
                EventEntry(
                    kind="sexual_counter",
                    actor=str(self.actor.pk),
                    target=self.target.key,
                    data={"counter": "duo_act_count"},
                    text_template="{done}",
                ),
                EventEntry(
                    kind="sexual_resist",
                    actor=str(self.actor.pk),
                    target=self.target.key,
                    data={"resisted": False, "auto_comply": True, "roll": None},
                    text_template="{done}",
                ),
            ),
            time_cost_seconds=0,
        )
        request = ActionRequest(
            self.actor,
            _T_RESISTIBLE_ADULT_SKILL.key,
            [self.target],
            self.context,
            source_id="occurrence:entry_form:1",
        )
        with (
            patch.dict(
                "world.skills.registry.SKILL_REGISTRY",
                {_T_RESISTIBLE_ADULT_SKILL.key: _T_RESISTIBLE_ADULT_SKILL},
            ),
            patch.dict(
                "world.skills.sexual_acts.SEXUAL_ACT_REGISTRY",
                {_T_RESISTIBLE_ADULT_ACT.key: _T_RESISTIBLE_ADULT_ACT},
            ),
        ):
            adapter_module.record_action_settlement_evidence(
                request,
                log,
                (),
                {id(self.target): snapshot},
                tick=7,
                delivered_targets=[self.target],
            )

        event = NarrativeEvent.objects.filter(
            source_id="occurrence:entry_form:1"
        ).first()
        self.assertIsNotNone(event)
        rows = [
            row
            for row in event.content["outcomes"]["effects"]
            if row["kind"] == "pleasure_gain"
        ]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["target_id"], str(self.target.pk))
        self.assertEqual(rows[0]["result"], {"amount": 5})
        self.assertEqual(
            event.content["outcomes"]["counters"],
            [
                {
                    "target_id": str(self.target.pk),
                    "target_name": self.target.key,
                    "counter": "duo_act_count",
                }
            ],
        )
        self.assertEqual(len(event.content["outcomes"]["resistance"]), 1)

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_shared_display_key_never_joins_a_committed_log_recipient(self):
        """Scenario: Untouched recipient is excluded.

        WHEN two requested targets share a display key and the committed log
        names that key
        THEN neither untouched target is attributed a recipient role.
        """
        import world.narrative.action_adapters as adapter_module
        from world.rules.event_log import EventEntry, EventLog

        twin = create_object(PlayerCharacter, key="EffectTarget", location=self.room)
        twin.race = "human"
        twin.apply_race_baseline()
        log = EventLog(
            actor=str(self.actor.pk),
            skill_key=_T_HEAL_SKILL.key,
            targets=(self.target.key, twin.key),
            entries=(
                EventEntry(
                    kind="heal",
                    actor=str(self.actor.pk),
                    target=self.target.key,
                    data={"amount": 3},
                    text_template="{done}",
                ),
            ),
            time_cost_seconds=0,
        )
        request = ActionRequest(
            self.actor,
            _T_HEAL_SKILL.key,
            [self.target, twin],
            self.context,
            source_id="occurrence:entry_twin:1",
        )
        with patch.dict(
            "world.skills.registry.SKILL_REGISTRY",
            {_T_HEAL_SKILL.key: _T_HEAL_SKILL},
        ):
            with self.assertRaises(ValueError):
                adapter_module.record_action_settlement_evidence(
                    request, log, (), {}, tick=7
                )

        self.assertFalse(
            NarrativeEvent.objects.filter(source_id="occurrence:entry_twin:1").exists()
        )

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_actor_named_key_never_joins_a_committed_log_recipient(self):
        """Scenario: Untouched recipient is excluded.

        WHEN the acting entity and one submitted target share a display key
        THEN an entry naming that key (the actor's own self-effect) is not
        evidence that the untouched target took part.
        """
        import world.narrative.action_adapters as adapter_module
        from world.rules.event_log import EventEntry, EventLog

        self.actor.key = "EffectTarget"
        log = EventLog(
            actor=str(self.actor.pk),
            skill_key=_T_SELF_BUFF_SKILL.key,
            targets=(self.target.key,),
            entries=(
                EventEntry(
                    kind="self_buff_applied",
                    actor=str(self.actor.pk),
                    target=self.actor.key,
                    data={"buff_key": _T_DEED_WARD.key},
                    text_template="{done}",
                ),
            ),
            time_cost_seconds=0,
        )
        request = ActionRequest(
            self.actor,
            _T_SELF_BUFF_SKILL.key,
            [self.target],
            self.context,
            source_id="occurrence:entry_actor_key:1",
        )
        with patch.dict(
            "world.skills.registry.SKILL_REGISTRY",
            {_T_SELF_BUFF_SKILL.key: _T_SELF_BUFF_SKILL},
        ):
            adapter_module.record_action_settlement_evidence(
                request, log, (), {}, tick=7
            )

        event = NarrativeEvent.objects.filter(
            source_id="occurrence:entry_actor_key:1"
        ).first()
        self.assertIsNotNone(event)
        self.assertEqual(event.content["recipients"], [])
        self.assertEqual(event.participants, [str(self.actor.pk)])
        self.assertEqual(
            [row["target_id"] for row in event.content["effects"]],
            [str(self.actor.pk)],
        )

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_repeated_gains_are_stated_once_as_the_committed_change(self):
        """Scenario: Actual bounded effect remains actual.

        WHEN one occurrence applies several pleasure gains to the same recipient
        THEN the deed states one committed change for that recipient instead of
        repeating the same observed delta for each staged component.
        """
        repeated = make_skill(
            key="t_synth_repeated_pleasure_deed",
            label="t_重複快感行為",
            description="t_合成重複快感性愛行為",
            kind=SkillKind.ACTIVE,
            target_spec=TargetSpec.SINGLE,
            category=SkillCategory.SEXUAL_ACT,
            usable_out_of_combat=True,
            effects=[
                f"pleasure:{_T_FLOOD_ACT.key}",
                f"pleasure:{_T_FLOOD_ACT.key}",
                f"sexual_counter:{_T_FLOOD_ACT.key}",
            ],
        )
        self.target.sexual.pleasure.base = 0

        result = self._cast(
            repeated,
            [self.target],
            acts={_T_FLOOD_ACT.key: _T_FLOOD_ACT},
        )
        self.assertEqual(result.outcome, "success", f"{result.reason}: {result.detail}")

        staged = sum(
            entry.data["amount"]
            for entry in result.event_log.entries
            if entry.kind == "pleasure_gain" and entry.target == self.target.key
        )
        committed = self.target.sexual.pleasure.value
        self.assertGreater(staged, 0)
        self.assertEqual(committed, min(100, staged))

        rows = [
            row
            for row in self._effect_rows(self._action_evidence().content)
            if row["kind"] == "pleasure_gain"
            and row["target_id"] == str(self.target.pk)
        ]
        # Each staged component states what its own application committed; the
        # shared gauge can only absorb the total, so the amounts sum to the
        # observed committed change and never repeat it.
        self.assertEqual(len(rows), 2)
        self.assertEqual(sum(row["result"]["amount"] for row in rows), committed)

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_auto_complied_adult_action_commits_evidence_the_feed_renders(self):
        """Scenarios: Auto-compliance has no resistance roll; producer-to-renderer.

        WHEN a legal resistible act auto-complies and its authoritative verdict
        has no roll
        THEN the action commits, its evidence keeps the actual verdict, and the
        rendered deed feed reads that committed evidence.
        """
        npc = create_object(NPC, key="AutoComplyNpc", location=self.room)
        npc.race = "human"
        npc.apply_race_baseline()
        apply_affinity_change(
            npc, self.actor, AffinitySource.QUEST_COMPLETION, 90
        )

        result = self._cast(
            _T_RESISTIBLE_ADULT_SKILL,
            [npc],
            source_id="occurrence:auto_comply:1",
            acts={_T_RESISTIBLE_ADULT_ACT.key: _T_RESISTIBLE_ADULT_ACT},
        )
        self.assertEqual(result.outcome, "success", f"{result.reason}: {result.detail}")

        event = NarrativeEvent.objects.filter(
            source_id="occurrence:auto_comply:1"
        ).first()
        self.assertIsNotNone(event)
        verdicts = event.content["outcomes"]["resistance"]
        self.assertEqual(len(verdicts), 1)
        self.assertIs(verdicts[0]["resisted"], False)
        self.assertIs(verdicts[0]["auto_comply"], True)
        self.assertIsNone(verdicts[0]["roll"])

        feed = select_authorized_recent_deeds(self.actor, frozen_tick=event.tick)
        self.assertIn("occurrence:auto_comply:1", feed.source_ids)
        rendered = json.loads(feed.rendered_json)
        group = next(
            group for group in rendered["recent_deeds"]
            if "occurrence:auto_comply:1" in group["source_ids"]
        )
        self.assertEqual(group["count"], 1)
        self.assertEqual(
            group["facts"]["outcomes"]["resistance"][0]["resisted"], False
        )
        self.assertEqual(
            set(group["facts"]["outcomes"]["resistance"][0]),
            {"target_id", "target_name", "resisted"},
        )
        self.assertNotIn('"roll":', feed.rendered_json)

    @covers_requirement(
        "narrative-events::narrative-facts-commit-atomically-with-covered-gameplay"
    )
    def test_failure_after_the_evidence_write_rolls_back_everything(self):
        """Scenario: Action rollback and replay.

        WHEN a source fails after its evidence write but before the action commit
        THEN the action, its effects, gauges and evidence roll back together and
        no nomination is admitted.
        """
        import world.narrative.action_adapters as adapter_module

        real_record = adapter_module.record_action_settlement_evidence
        observed: dict[str, int] = {}

        def failing_record(*args, **kwargs):
            real_record(*args, **kwargs)
            observed["evidence"] = NarrativeEvent.objects.filter(
                source_id="occurrence:rollback:1"
            ).count()
            raise RuntimeError("injected failure after the evidence write")

        target_hp = self.target.traits.hp.current
        actor_mp = self.actor.traits.mp.current
        with (
            patch.object(
                adapter_module,
                "record_action_settlement_evidence",
                failing_record,
            ),
            patch(
                "server.title_nomination_service.schedule_epithet_nomination"
            ) as nomination,
        ):
            result = self._cast(
                _T_HEAL_SKILL,
                [self.target],
                source_id="occurrence:rollback:1",
            )

        nomination.assert_not_called()
        self.assertEqual(observed["evidence"], 1)
        self.assertEqual(result.outcome, "rejected")
        self.assertFalse(
            NarrativeEvent.objects.filter(source_id="occurrence:rollback:1").exists()
        )
        self.assertEqual(self.target.traits.hp.current, target_hp)
        self.assertEqual(self.actor.traits.mp.current, actor_mp)
        self.assertEqual(read_pending_ballot(self.actor), ())

    @covers_requirement(
        "title-system::nomination-prompts-contain-authorized-structured-deeds-and-advisory-identity"
    )
    def test_structured_adult_results_survive_prompt_construction(self):
        """Scenario: Adult outcome survives construction.

        WHEN real adult and skill settlements commit through storage
        THEN their structured results survive prompt construction and the counts
        represent committed occurrences only.
        """
        self._cast(
            _T_SELF_ACT_SKILL,
            [],
            source_id="occurrence:1:self",
            acts={_T_SELF_ACT.key: _T_SELF_ACT},
        )
        self._cast(
            _T_SELF_ACT_SKILL,
            [],
            source_id="occurrence:2:self",
            acts={_T_SELF_ACT.key: _T_SELF_ACT},
        )
        self._cast(
            _T_RESISTIBLE_ADULT_SKILL,
            [self.target],
            source_id="occurrence:3:resist",
            acts={_T_RESISTIBLE_ADULT_ACT.key: _T_RESISTIBLE_ADULT_ACT},
        )
        self._cast(_T_HEAL_SKILL, [self.target], source_id="occurrence:4:heal")
        self._cast(_T_HEAL_SKILL, [self.target], source_id="occurrence:5:heal")
        # A replay of an already committed occurrence adds no second occurrence.
        self._cast(_T_HEAL_SKILL, [self.target], source_id="occurrence:4:heal")

        from server.title_nomination_service import _build_context

        tick = NarrativeEvent.objects.order_by("-tick").first().tick
        context = _build_context(self.actor, frozen_tick=tick)
        payload = json.loads(context.recent_deeds_json)
        groups = payload["recent_deeds"]

        adult_groups = [
            group for group in groups
            if group["facts"].get("act_key") == _T_SELF_ACT_SKILL.key
        ]
        self.assertEqual(len(adult_groups), 1)
        adult_group = adult_groups[0]
        self.assertEqual(adult_group["count"], 2)
        outcomes = adult_group["facts"]["outcomes"]
        self.assertEqual(
            [row["event"] for row in outcomes["transitions"]], ["stimulus_applied"]
        )
        self.assertTrue(outcomes["counters"])
        self.assertTrue(outcomes["effects"])
        self.assertEqual(outcomes["transitions"][0]["target_id"], str(self.actor.pk))
        self.assertIn("occurrence:1:self", adult_group["source_ids"])
        self.assertIn("occurrence:2:self", adult_group["source_ids"])

        resist_groups = [
            group for group in groups
            if group["facts"].get("act_key") == _T_RESISTIBLE_ADULT_SKILL.key
        ]
        self.assertEqual(len(resist_groups), 1)
        self.assertTrue(resist_groups[0]["facts"]["outcomes"]["resistance"])

        skill_groups = [
            group for group in groups
            if group["facts"].get("skill_key") == _T_HEAL_SKILL.key
        ]
        self.assertEqual(len(skill_groups), 1)
        self.assertEqual(skill_groups[0]["count"], 2)
        self.assertIn("occurrence:4:heal", context.supplied_source_ids)
        self.assertIn("occurrence:5:heal", context.supplied_source_ids)


class SettledResultNormalizationTests(unittest.TestCase):
    """Both accepted input forms converge on one committed-result vocabulary."""

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_pending_and_entry_forms_state_identical_effects(self):
        """Scenario: Production effect vocabulary survives persistence.

        WHEN the staged pending description and the committed event payload
        state the same effect
        THEN both forms yield the identical committed result.
        """
        import world.narrative.action_adapters as adapter_module

        cases = {
            "damage": (("7", "1", "12"), {"amount": 12}, {"amount": 12, "hit": True}),
            "heal": (("9",), {"amount": 9}, {"amount": 9}),
            "self_heal": (("9",), {"amount": 9}, {"amount": 9}),
            "pleasure_gain": (("4",), {"amount": 4}, {"amount": 4}),
            "buff_applied": (("focus",), {"buff_key": "focus"}, {"buff_key": "focus"}),
            "self_buff_applied": (
                ("focus",),
                {"buff_key": "focus"},
                {"buff_key": "focus"},
            ),
            "buffs_cleansed": (("2",), {"count": 2}, {"count": 2}),
            "gauge_transfer": (
                ("mp", "drain", "5"),
                {"gauge": "mp", "direction": "drain", "amount": 5},
                {"gauge": "mp", "direction": "drain", "amount": 5},
            ),
        }
        for kind, (values, entry_data, expected) in cases.items():
            with self.subTest(kind=kind):
                from_values = adapter_module._settled_result_from_values(
                    kind, values, source="equivalence"
                )
                from_entry = adapter_module._settled_result_from_entry(
                    kind, entry_data, source="equivalence"
                )
                self.assertEqual(from_values, expected)
                self.assertEqual(from_entry, expected)

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_uncommitted_and_malformed_results_fail_closed(self):
        """Scenario: Production effect vocabulary survives persistence.

        WHEN a staged damage misses, or required evidence is malformed
        THEN a miss states no committed effect and malformed evidence raises
        instead of becoming an empty or invented result.
        """
        import world.narrative.action_adapters as adapter_module

        self.assertIsNone(
            adapter_module._settled_result_from_values(
                "damage", ("7", "0", "12"), source="miss"
            )
        )
        with self.assertRaises(ValueError):
            adapter_module._settled_result_from_values(
                "pleasure_gain", ("not-an-int",), source="malformed"
            )
        with self.assertRaises(ValueError):
            adapter_module._settled_result_from_entry(
                "pleasure_gain", {}, source="missing-amount"
            )
        with self.assertRaises(ValueError):
            adapter_module._settled_result_from_entry(
                "buff_applied", {"buff_key": 7}, source="not-text"
            )
        with self.assertRaises(ValueError):
            adapter_module._settled_result_from_values(
                "title_granted", ("t_synth",), source="unadmitted"
            )

        # An absent roll is a normal result; a verdict with no outcome at all,
        # or one that is not a two-flag verdict, fails its source transaction.
        self.assertEqual(
            adapter_module._pending_resistance_values(
                ("0", "1", "none"), source="absented"
            ),
            (False, True, None),
        )
        self.assertEqual(
            adapter_module._entry_resistance_values(
                {"resisted": False, "auto_comply": True, "roll": None},
                source="absented",
            ),
            (False, True, None),
        )
        for malformed in (
            {},
            {"resisted": False},
            {"resisted": False, "auto_comply": True},
            {"resisted": 0, "auto_comply": 1, "roll": None},
            {"resisted": False, "auto_comply": True, "roll": "7"},
        ):
            with self.subTest(resistance=malformed):
                with self.assertRaises(ValueError):
                    adapter_module._entry_resistance_values(
                        malformed, source="malformed"
                    )
        for malformed_values in (("0", "1"), ("0", "1", "bogus"), ("2", "0", "7")):
            with self.subTest(resistance=malformed_values):
                with self.assertRaises(ValueError):
                    adapter_module._pending_resistance_values(
                        malformed_values, source="malformed"
                    )

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_shared_display_keys_never_resolve_to_a_guessed_recipient(self):
        """Scenario: Untouched recipient is excluded.

        WHEN two candidates share one display key, or a committed entry names an
        unknown target
        THEN identity resolution refuses rather than attributing a recipient.
        """
        import types

        import world.narrative.action_adapters as adapter_module

        first = types.SimpleNamespace(pk=1, key="Twin")
        second = types.SimpleNamespace(pk=2, key="Twin")
        self.assertEqual(adapter_module._unique_key_index([first, second]), {})

        entry = types.SimpleNamespace(target="Twin")
        with self.assertRaises(ValueError):
            adapter_module._entry_target(
                entry,
                "damage",
                adapter_module._unique_key_index([first, second]),
                "3",
                "Actor",
                source="ambiguous",
            )
        with self.assertRaises(ValueError):
            adapter_module._entry_target(
                entry,
                "damage",
                {},
                "3",
                "Actor",
                source="unknown",
            )


class SettledEffectVocabularyDocumentationTests(unittest.TestCase):
    """The documented settled-result vocabulary is the adapter's own table."""

    @covers_requirement(
        "narrative-events::settled-skill-and-adult-actions-retain-deterministic-roles-and-results"
    )
    def test_documented_vocabulary_matches_the_adapter(self):
        """Scenario: Production effect vocabulary survives persistence.

        WHEN the narrative evidence contract documents its accepted results
        THEN the document names exactly the kinds and result fields the adapter
        accepts, so producer and consumer vocabulary cannot drift.
        """
        import world.narrative.action_adapters as adapter_module

        documentation = adapter_module.__doc__ or ""
        marker = "Accepted settled-effect results:"
        self.assertIn(marker, documentation)

        documented: dict[str, tuple[str, ...]] = {}
        for line in documentation.split(marker, 1)[1].splitlines():
            entry = line.strip()
            if not entry:
                if documented:
                    break
                continue
            self.assertTrue(entry.startswith("- "), entry)
            kind, _, fields = entry[2:].partition(": ")
            documented[kind] = tuple(
                field.strip() for field in fields.split(",") if field.strip()
            )

        declared = {
            kind: tuple(field for field, _ in fields)
            for kind, fields in adapter_module._SETTLED_EFFECT_RESULTS.items()
        }
        self.assertEqual(documented, declared)


class TransitionTimeMilestoneSelectionTests(EvenniaTestCase):
    """Each owner's transition-time milestone reaches selection exactly once.

    Spec: ``narrative-events`` — non-resolver adult milestones are recorded at
    transition time under their own operation/encounter identity and are not
    dated again by a later clock read; existing balance values are unchanged.
    """

    def setUp(self):
        super().setUp()
        register_catalog()
        self.room = create_object(Room, key="milestone selection room")
        self.player = create_object(
            PlayerCharacter, key="MilestonePlayer", location=self.room
        )
        self.ally = create_object(
            PlayerCharacter, key="MilestoneAlly", location=self.room
        )
        for entity in (self.player, self.ally):
            entity.race = "human"
            entity.apply_race_baseline()
            entity.traits.hp.current = 100
        self.item_key = "t_selection_bliss"
        open_synthetic_scope(
            self,
            "items",
            extra={
                "items": {
                    self.item_key: make_item(
                        self.item_key,
                        display_name_zh="合成快感藥",
                        price_table_key="t_mossmeals",
                        use_mechanics=ItemUseMechanics(
                            consumable=True, combat_allowed=True
                        ),
                    )
                },
                "item_effect_profiles": {
                    self.item_key: ItemEffectProfile(
                        effects=(
                            GaugeAdjustEffect(
                                stat=ItemStat.PLEASURE,
                                amount=20,
                                scope=ItemTargetScope.ALL_ALLIES,
                            ),
                        )
                    )
                },
            },
        )

    def _selection(self, entity):
        return select_authorized_recent_deeds(
            entity, frozen_tick=int(get_world_clock().tick)
        )

    def _assert_cited_once(self, selection, source_id: str) -> None:
        self.assertIn(source_id, selection.source_ids)
        self.assertEqual(selection.source_ids.count(source_id), 1)
        # ``source_ids`` is deduplicated; the factual groups are the citation.
        hits = [g for g in selection.groups if source_id in g.source_ids]
        self.assertEqual(len(hits), 1)
        self.assertEqual(
            sum(group.source_ids.count(source_id) for group in selection.groups), 1
        )

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions"
    )
    def test_upkeep_crossing_reaches_selection_once_with_declared_balance(self):
        """Scenario: a real upkeep crossing is cited once by its own source."""
        passive = make_skill(
            "t_selection_feedback",
            element="light",
            kind=SkillKind.PASSIVE,
            effects=(),
        )
        self.player.db.skills = {"active": [], "passive": [passive.key]}
        reaction = Rule(
            id="t_selection_feedback_rule",
            when={"event": "hp_loss", "skill_qualified": passive.key},
            then={"pleasure_gain": {"max_hp_coefficient": 140}},
        )
        seconds = int(COMBAT_YAML["round"]["seconds"])
        dot = BuffDefinition(
            key="t_selection_dot",
            duration=60,
            polarity="debuff",
            tick_interval=seconds,
            stacking="refresh",
            modifiers={"rate": {"target": "hp", "delta": -10}},
        )
        battlefield = Battlefield(
            {"party": frozenset({str(self.player.key)}), "foes": frozenset()},
            {str(self.player.key): self.player},
        )
        provenance = CombatProvenance(
            engagement_id="hostile:selection:1",
            round_ordinal=1,
            session_id="selection_session",
        )
        max_hp = int(self.player.traits.hp.max)
        with patch.dict(BUFF_DEFINITIONS, {dot.key: dot}, clear=False), patch.dict(
            "world.skills.registry.SKILL_REGISTRY", {passive.key: passive}
        ), patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction],
        ):
            apply_buff(self.player, dot.key)
            self.player.sexual.climax_phase.value = "接近"
            self.player.sexual.pleasure.base = 60
            self.player.sexual.stage_climax_extension()
            hp_before = int(self.player.traits.hp.current)
            pleasure_before = int(self.player.sexual.pleasure.base)
            with patch(
                "server.title_nomination_service.schedule_epithet_nomination"
            ) as trigger:
                with combat_provenance(provenance):
                    _end_of_round_upkeep(battlefield)
            trigger.assert_not_called()

        hp_loss = hp_before - int(self.player.traits.hp.current)
        self.assertEqual(hp_loss, -dot.modifiers["rate"]["delta"])
        self.assertEqual(
            int(self.player.sexual.pleasure.base) - pleasure_before,
            (140 * hp_loss) // max_hp,
        )
        upkeep_source = (
            f"combat:hostile:selection:1:round:1:upkeep:{self.player.pk}"
        )
        milestone = NarrativeEvent.objects.get(
            event_type="adult_milestone",
            content__action_source_id=upkeep_source,
            content__identifier="climax_onset",
        )
        self.assertTrue(milestone.source_id.startswith(upkeep_source))
        selection = self._selection(self.player)
        self._assert_cited_once(selection, milestone.source_id)

        # A later clock read never dates this crossing again, under this or
        # any other source.
        onsets_before = NarrativeEvent.objects.filter(
            event_type="adult_milestone",
            content__entity_id=str(self.player.pk),
            content__identifier="climax_onset",
        ).count()
        with patch.dict(BUFF_DEFINITIONS, {dot.key: dot}, clear=False), patch(
            "world.rules.state_reactions.STATE_REACTION_RULES",
            STATE_REACTION_RULES + [reaction],
        ):
            WorldClock(tick=int(get_world_clock().tick)).advance(
                seconds, AdvanceSource.COMMAND, (self.player,)
            )
        self.assertEqual(
            NarrativeEvent.objects.filter(
                event_type="adult_milestone",
                content__entity_id=str(self.player.pk),
                content__identifier="climax_onset",
            ).count(),
            onsets_before,
        )
        self.assertEqual(
            NarrativeEvent.objects.filter(
                event_type="adult_milestone", source_id=milestone.source_id
            ).count(),
            1,
        )

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions"
    )
    def test_accepted_item_crossing_reaches_selection_once_with_declared_balance(self):
        """Scenario: an accepted item use's recipients are cited once each."""
        from world.rules.items import ItemUseRequest, resolve_item_use

        for entity in (self.player, self.ally):
            entity.sexual.climax_phase.value = "接近"
            entity.sexual.pleasure.base = 40
        self.player.db.inventory = [self.item_key]
        with patch(
            "server.title_nomination_service.schedule_epithet_nomination"
        ) as trigger:
            result = resolve_item_use(
                ItemUseRequest(self.player, self.item_key),
                in_combat=False,
                context=RoomActionContext(self.room),
            )
        trigger.assert_not_called()
        self.assertEqual(result.outcome, "success")
        for entity in (self.player, self.ally):
            self.assertEqual(int(entity.sexual.pleasure.base), 60)

        milestones = list(
            NarrativeEvent.objects.filter(
                event_type="adult_milestone", content__identifier="climax_onset"
            )
        )
        self.assertEqual(len(milestones), 2)
        (operation_id,) = {m.content["action_source_id"] for m in milestones}
        self.assertTrue(operation_id.startswith("item:accept:"))
        player_milestone = next(
            m for m in milestones if m.content["entity_id"] == str(self.player.pk)
        )
        ally_milestone = next(
            m for m in milestones if m.content["entity_id"] == str(self.ally.pk)
        )
        player_selection = self._selection(self.player)
        self._assert_cited_once(player_selection, player_milestone.source_id)
        # The ally's private milestone is never disclosed to the player.
        self.assertNotIn(ally_milestone.source_id, player_selection.source_ids)
        self._assert_cited_once(self._selection(self.ally), ally_milestone.source_id)

    @covers_requirement(
        "narrative-events::adult-milestones-record-newly-crossed-transitions"
    )
    def test_defeat_attempt_crossing_reaches_selection_once_with_declared_balance(self):
        """Scenario: a defeat aftermath attempt is cited once by its own source."""
        import world.rules.defeat_aftermath.violation as violation_module

        monster = create_object(Monster, key="哥布林", location=self.room)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        monster.traits.hp.base = 100
        monster.traits.hp.current = 100
        monster.traits.atk_phys.base = 10
        row = DEFEAT_AFTERMATH_RULEBOOK.violation.rows[str(monster.key)]
        self.player.traits.agility.base = 10
        self.player.traits.atk_phys.base = 10
        monster.sexual.pleasure.base = 13
        for _ in range(4):
            self.player.sexual.record_hostile_act()
        pleasure_before = int(self.player.sexual.pleasure.base)
        hostile_before = self.player.sexual.hostile_act_count
        engage(self.player, monster)
        record = read_session(self.player)
        with patch.object(
            violation_module, "derived_roll", return_value=1
        ), patch(
            "server.title_nomination_service.schedule_epithet_nomination"
        ) as trigger:
            forfeit(self.player)
        trigger.assert_not_called()

        attempt_source = (
            f"defeat:{record.engagement_id}:{monster.pk}"
            f":attempt:0:victim:{self.player.pk}"
        )
        action = NarrativeEvent.objects.get(
            event_type="adult_action", source_id=attempt_source
        )
        self.assertFalse(action.content["outcomes"]["resistance"][0]["resisted"])
        unlocks = [
            NarrativeEvent.objects.get(
                event_type="adult_milestone", source_id=summary["source_id"]
            )
            for summary in action.content["milestones"]
            if summary["milestone_kind"] == "act_unlock"
        ]
        self.assertTrue(unlocks)
        # Both attempts landed through the shipped formula, so the declared
        # landed deltas and counter credits are exactly what applied.
        self.assertEqual(
            int(self.player.sexual.pleasure.base) - pleasure_before,
            2 * row.landed.victim_pleasure,
        )
        self.assertEqual(self.player.sexual.hostile_act_count, hostile_before + 2)
        selection = self._selection(self.player)
        self._assert_cited_once(selection, action.source_id)
        for unlock in unlocks:
            self._assert_cited_once(selection, unlock.source_id)
