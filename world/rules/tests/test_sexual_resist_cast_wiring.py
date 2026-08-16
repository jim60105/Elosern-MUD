"""Behaviour tests for the sexual-resist cast wiring (sexual-resist-cast-wiring).

``ActionResolver.resolve()`` must run one ``resist_verdict()`` contest per
non-actor target of a ``resistible=True`` act before any effect handler runs,
emit the ``sexual_resist`` ``EventEntry`` contract ``_scan_sexual_coercion``
consumes, and exclude a successfully-resisting target from the act's
pleasure/counter/event effects while the actor's own effects and the cast's
costs stay unconditional (design D-4/D-5/D-7).
"""

from tools.spec_traceability import covers_requirement

from dataclasses import replace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.npcs import NPC
from world.quests.catalog import register_catalog
from world.rules.action import ActionRequest, ActionResolver
from world.rules.affinity import AffinitySource, apply_affinity_change
from world.rules.sexual_act_effects import compute_pleasure_gain
from world.rules.targeting import RoomActionContext
from world.skills.registry import (
    SKILL_REGISTRY,
    SkillCategory,
    SkillKind,
    TargetSpec,
    _skill,
)
from world.skills.sexual_acts import SEXUAL_ACT_REGISTRY
from world.skills.sexual_acts._builder import _act_family


class ResistCastWiringBase(EvenniaTest):
    """Shared fixture: a caster, one humanoid target, and a companion NPC."""

    def setUp(self):
        super().setUp()
        register_catalog()
        self.actor = create_object(
            PlayerCharacter, key="resist caster", location=self.room1
        )
        self.actor.race = "human"
        self.actor.apply_race_baseline()
        self.actor.db.skills = {"active": [], "passive": []}
        self.target = create_object(
            PlayerCharacter, key="resist target", location=self.room1
        )
        self.target.race = "human"
        self.target.apply_race_baseline()

    def _npc(self, key="resist npc", affinity: int | None = None):
        npc = create_object(NPC, key=key, location=self.room1)
        npc.race = "human"
        npc.apply_race_baseline()
        if affinity is not None:
            apply_affinity_change(
                npc, self.actor, AffinitySource.QUEST_COMPLETION, affinity
            )
        return npc

    def _cast(self, act_key, targets, event_context=None):
        return ActionResolver.resolve(
            ActionRequest(
                self.actor,
                act_key,
                targets,
                RoomActionContext(self.room1, event_context),
            )
        )

    def _pleasure(self, entity):
        return entity.sexual.pleasure.base


class ResistGateTests(ResistCastWiringBase):
    """One contest per non-actor target; actor and non-acts are skipped."""

    @covers_requirement("sexual-resist-cast-wiring::casting-a-resistible-act-resolves-one-resist-contest-per-non-actor-target-before-its-effects-apply")
    def test_resistible_single_act_rolls_exactly_one_contest(self):
        from world.rules.sexual_resist import resist_verdict

        with patch(
            "world.rules.sexual_resist.resist_verdict",
            wraps=resist_verdict,
        ) as spy, patch("world.rules.action.roll_d100", return_value=100):
            result = self._cast("combat_tease", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(spy.call_count, 1)
        actor, resister = spy.call_args.args[:2]
        self.assertIs(actor, self.actor)
        self.assertIs(resister, self.target)

    @covers_requirement("sexual-resist-cast-wiring::casting-a-resistible-act-resolves-one-resist-contest-per-non-actor-target-before-its-effects-apply")
    def test_non_resistible_sexual_act_never_rolls(self):
        from world.rules.sexual_resist import resist_verdict

        with patch("world.rules.sexual_resist.resist_verdict") as spy:
            result = self._cast("solo_self_touch", [])
        self.assertEqual(result.outcome, "success")
        spy.assert_not_called()

    @covers_requirement("sexual-resist-cast-wiring::casting-a-resistible-act-resolves-one-resist-contest-per-non-actor-target-before-its-effects-apply")
    def test_non_sexual_skill_never_rolls(self):
        from world.rules.sexual_resist import resist_verdict

        skill = _skill(
            "test_plain_skill",
            "測試技能",
            "測試用的非性愛主動技能。",
            SkillKind.ACTIVE,
            TargetSpec.SELF,
            usable_out_of_combat=True,
            effects=["self_buff_apply:focus"],
            category=SkillCategory.ENHANCEMENT,
        )
        self.actor.db.skills = {
            "active": ["test_plain_skill"],
            "passive": [],
        }
        with patch.dict(SKILL_REGISTRY, {skill.key: skill}), patch(
            "world.rules.sexual_resist.resist_verdict"
        ) as spy:
            result = self._cast("test_plain_skill", [])
        self.assertEqual(result.outcome, "success")
        spy.assert_not_called()

    @covers_requirement("sexual-resist-cast-wiring::a-resistible-area-target-act-resolves-one-independent-contest-per-resolved-target")
    def test_area_act_rolls_one_independent_contest_per_target(self):
        (skill, act), = _act_family(
            "關係",
            (
                "test_area_resist",
                "測試範圍行為",
                "僅存在於測試中的合成範圍性行為。",
                TargetSpec.AREA,
                {},
                10,
                "腰腹",
                "腰腹",
                0.5,
                ("duo_act_count",),
                ("duo_act_count",),
                ("masturbation_climax",),
                True,
            ),
        )
        second = create_object(
            PlayerCharacter, key="resist target two", location=self.room1
        )
        second.race = "human"
        second.apply_race_baseline()
        from world.rules.sexual_resist import resist_verdict

        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ), patch(
            "world.rules.sexual_resist.resist_verdict",
            wraps=resist_verdict,
        ) as spy, patch(
            "world.rules.action.roll_d100",
            side_effect=[1, 100],
        ):
            result = self._cast("test_area_resist", [self.target, second])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(spy.call_count, 2)
        resisters = [call.args[1] for call in spy.call_args_list]
        self.assertEqual(resisters, [self.target, second])
        # Target two resisted; the first target and the actor keep effects.
        self.assertEqual(self.target.sexual.duo_act_count, 1)
        self.assertEqual(second.sexual.duo_act_count, 0)
        self.assertEqual(self.actor.sexual.duo_act_count, 1)
        self.assertGreater(self._pleasure(self.target), 0)
        self.assertEqual(self._pleasure(second), 0)
        self.assertGreater(self._pleasure(self.actor), 0)
        # The act's sexual_event fired only for the complying target.
        self.assertIn("自慰", self.target.sexual.experience_types)
        self.assertNotIn("自慰", second.sexual.experience_types)
        resist_entries = [
            entry
            for entry in result.event_log.entries
            if entry.kind == "sexual_resist"
        ]
        self.assertEqual(len(resist_entries), 2)


class ResistEffectWithholdingTests(ResistCastWiringBase):
    """A resisted target receives none of the act's effects; a complied one does."""

    @covers_requirement("sexual-resist-cast-wiring::a-successfully-resisting-target-receives-none-of-the-act-s-pleasure-counter-or-sexual-event-effects")
    def test_resisted_target_keeps_pleasure_and_participant_counter(self):
        before = self._pleasure(self.target)
        with patch("world.rules.action.roll_d100", return_value=100):
            result = self._cast("partner_caress", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self._pleasure(self.target), before)
        self.assertEqual(self.target.sexual.duo_act_count, 0)
        # The actor's own counter credit is never gated (design D-5).
        self.assertEqual(self.actor.sexual.duo_act_count, 1)

    @covers_requirement("sexual-resist-cast-wiring::a-successfully-resisting-target-receives-none-of-the-act-s-pleasure-counter-or-sexual-event-effects")
    def test_complied_target_receives_effects_as_before(self):
        expected = compute_pleasure_gain(
            self.target, "腰腹", 10, 1.0, 2
        )
        with patch("world.rules.action.roll_d100", return_value=1):
            result = self._cast("partner_caress", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.duo_act_count, 1)
        self.assertEqual(self._pleasure(self.target), expected)
        self.assertEqual(self.actor.sexual.duo_act_count, 1)

    @covers_requirement("sexual-resist-cast-wiring::the-actor-s-own-effects-and-the-cast-s-resource-time-and-practice-cost-are-never-gated-by-a-target-s-resist-outcome")
    def test_actor_own_pleasure_share_applied_in_both_branches(self):
        # A fully-resisted cast leaves the actor alone in the participant set
        # (count 1); a complied cast counts two (design D-7's crowd note).
        resisted_actor_gain = compute_pleasure_gain(
            self.actor, "腰腹", 7, 0.4, 1
        )
        complied_actor_gain = compute_pleasure_gain(
            self.actor, "腰腹", 7, 0.4, 2
        )
        actor_before = self._pleasure(self.actor)
        with patch("world.rules.action.roll_d100", return_value=100):
            self._cast("combat_tease", [self.target])
        after_resisted = self._pleasure(self.actor)
        self.assertEqual(after_resisted - actor_before, resisted_actor_gain)
        self.assertEqual(self.actor.sexual.hostile_act_count, 1)

        second = create_object(
            PlayerCharacter, key="resist target two", location=self.room1
        )
        second.race = "human"
        second.apply_race_baseline()
        with patch("world.rules.action.roll_d100", return_value=1):
            self._cast("combat_tease", [second])
        self.assertEqual(self._pleasure(self.actor) - after_resisted, complied_actor_gain)
        self.assertEqual(self.actor.sexual.hostile_act_count, 2)

    @covers_requirement("sexual-resist-cast-wiring::the-actor-s-own-effects-and-the-cast-s-resource-time-and-practice-cost-are-never-gated-by-a-target-s-resist-outcome")
    def test_fully_resisted_cast_still_deducts_resource_cost(self):
        (skill, act), = _act_family(
            "關係",
            (
                "test_cost_resist",
                "測試收費行為",
                "僅存在於測試中的合成收費性行為。",
                TargetSpec.SINGLE,
                {},
                10,
                "腰腹",
                "腰腹",
                0.5,
                ("duo_act_count",),
                (),
                (),
                True,
            ),
        )
        skill = replace(skill, cost={"mp": 5})
        mp_before = self.actor.traits.mp.current
        with patch.dict(SEXUAL_ACT_REGISTRY, {act.key: act}), patch.dict(
            SKILL_REGISTRY, {skill.key: skill}
        ), patch("world.rules.action.roll_d100", return_value=100):
            result = self._cast("test_cost_resist", [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.actor.traits.mp.current, mp_before - 5)
        self.assertEqual(self.actor.sexual.duo_act_count, 1)
        self.assertEqual(self.target.sexual.duo_act_count, 0)
        # Time cost and practice XP are also unconditional on resist outcome.
        self.assertIsInstance(result.time_cost_seconds, int)
        self.assertGreaterEqual(result.time_cost_seconds, 0)
        self.assertIn(
            "skill_practice",
            [entry.kind for entry in result.event_log.entries],
        )


class ResistEventLogTests(ResistCastWiringBase):
    """The emitted EventEntry matches the sexual-resist-turn-cost contract."""

    def _resist_entries(self, result):
        return [
            entry
            for entry in result.event_log.entries
            if entry.kind == "sexual_resist"
        ]

    @covers_requirement("sexual-resist-cast-wiring::every-resist-contest-emits-a-sexual-resist-eventlog-entry-matching-the-sexual-resist-turn-cost-contract")
    def test_rolled_contest_logs_exactly_one_entry_with_numeric_roll(self):
        with patch("world.rules.action.roll_d100", return_value=42):
            result = self._cast("combat_tease", [self.target])
        entries = self._resist_entries(result)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry.target, str(self.target.key))
        self.assertEqual(entry.actor, str(self.actor.key))
        self.assertEqual(
            entry.data,
            {"resisted": False, "auto_comply": False, "roll": 42},
        )
        self.assertEqual(
            set(entry.data), {"resisted", "auto_comply", "roll"}
        )

    @covers_requirement("sexual-resist-cast-wiring::every-resist-contest-emits-a-sexual-resist-eventlog-entry-matching-the-sexual-resist-turn-cost-contract")
    def test_resisted_verdict_logs_resisted_true(self):
        with patch("world.rules.action.roll_d100", return_value=100):
            result = self._cast("combat_tease", [self.target])
        (entry,) = self._resist_entries(result)
        self.assertTrue(entry.data["resisted"])
        self.assertFalse(entry.data["auto_comply"])
        self.assertEqual(entry.data["roll"], 100)

    @covers_requirement("sexual-resist-cast-wiring::every-resist-contest-emits-a-sexual-resist-eventlog-entry-matching-the-sexual-resist-turn-cost-contract")
    def test_auto_complied_contest_logs_none_roll(self):
        npc = self._npc(affinity=90)
        result = self._cast("combat_tease", [npc])
        (entry,) = self._resist_entries(result)
        self.assertEqual(entry.target, str(npc.key))
        self.assertIs(entry.data["roll"], None)
        self.assertTrue(entry.data["auto_comply"])
        self.assertFalse(entry.data["resisted"])
        # An auto-complied target is not excluded from the act's effects.
        self.assertGreater(self._pleasure(npc), 0)
