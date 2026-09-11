"""Behaviour tests for the sexual-resist cast wiring (sexual-resist-cast-wiring).

``ActionResolver.resolve()`` must run one ``resist_verdict()`` contest per
non-actor target of a ``resistible=True`` act before any effect handler runs,
emit the ``sexual_resist`` ``EventEntry`` contract ``_scan_sexual_coercion``
consumes, and exclude a successfully-resisting target from the act's
pleasure/counter/event effects while the actor's own effects and the cast's
costs stay unconditional (design D-4/D-5/D-7).

Every act the resolver sees is a file-local synthetic row registered through
a scoped ``skills``/``sexual_acts`` overlay — the resistible gate, the
non-resistible branch, the area act, and the costed act are all built here
from the kit's act template, never from a shipped catalogue row.
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
    SkillCategory,
    SkillDef,
    SkillKind,
    TargetSpec,
    _skill,
)
from world.tests.synthetic_data import SYNTH_ACT, SYNTH_ACT_SKILL, synthetic_registries

from ._combat_session_helpers import _race_key, open_synthetic_scope

# --- File-local synthetic act rows (kit act template, varied flags) -------

# The resistible single-target act: pleasure + duo counter + an event, all
# authored locally.
_T_ACT = "t_wire_caress"
_T_ACT_DEF = replace(
    SYNTH_ACT,
    key=_T_ACT,
    resistible=True,
    actor_counters=("duo_act_count",),
    participant_counters=("duo_act_count",),
    sexual_events=(),
)
_T_ACT_SKILL = replace(
    SYNTH_ACT_SKILL,
    key=_T_ACT,
    label="測試輕撫行為",
    description="僅存在於測試中的合成可抵抗性行為。",
    effects=[
        f"pleasure:{_T_ACT}",
        f"sexual_counter:{_T_ACT}",
    ],
)

# The non-resistible self act: a cast with no non-actor target and the
# resist flag off.
_T_SOLO = "t_wire_solo"
_T_SOLO_DEF = replace(SYNTH_ACT, key=_T_SOLO, resistible=False)
_T_SOLO_SKILL = replace(
    SYNTH_ACT_SKILL,
    key=_T_SOLO,
    label="測試自撫行為",
    description="僅存在於測試中的合成不可抵抗性行為。",
    target_spec=TargetSpec.SELF,
    effects=[f"pleasure:{_T_SOLO}", f"sexual_counter:{_T_SOLO}"],
)

# The area act: one independent contest per resolved target.
_T_AREA = "t_wire_area"
_T_AREA_DEF = replace(
    SYNTH_ACT,
    key=_T_AREA,
    resistible=True,
    actor_counters=("duo_act_count",),
    participant_counters=("duo_act_count",),
    sexual_events=(),
)
_T_AREA_SKILL = replace(
    SYNTH_ACT_SKILL,
    key=_T_AREA,
    label="測試範圍行為",
    description="僅存在於測試中的合成範圍性行為。",
    target_spec=TargetSpec.AREA,
    effects=[
        f"pleasure:{_T_AREA}",
        f"sexual_counter:{_T_AREA}",
        f"sexual_event:{_T_AREA}_event",
    ],
)

# The costed act: an explicit mp cost, resisted cast still pays it.
_T_COST = "t_wire_cost"
_T_COST_DEF = replace(
    SYNTH_ACT,
    key=_T_COST,
    resistible=True,
    actor_counters=("duo_act_count",),
    participant_counters=("duo_act_count",),
    sexual_events=(),
)
_T_COST_SKILL = replace(
    SYNTH_ACT_SKILL,
    key=_T_COST,
    label="測試收費行為",
    description="僅存在於測試中的合成收費性行為。",
    cost={"mp": 5},
    effects=[f"pleasure:{_T_COST}", f"sexual_counter:{_T_COST}"],
)

# A plain non-sexual active skill: never a contest.
_T_PLAIN = "t_wire_plain"
_T_PLAIN_SKILL = _skill(
    _T_PLAIN,
    "測試技能",
    "測試用的非性愛主動技能。",
    SkillKind.ACTIVE,
    TargetSpec.SELF,
    usable_out_of_combat=True,
    effects=["self_buff_apply:focus"],
    category=SkillCategory.ENHANCEMENT,
)

_ALL_SKILLS = {
    _T_ACT_SKILL.key: _T_ACT_SKILL,
    _T_SOLO_SKILL.key: _T_SOLO_SKILL,
    _T_AREA_SKILL.key: _T_AREA_SKILL,
    _T_COST_SKILL.key: _T_COST_SKILL,
    _T_PLAIN_SKILL.key: _T_PLAIN_SKILL,
}
_ALL_ACTS = {
    _T_ACT_DEF.key: _T_ACT_DEF,
    _T_SOLO_DEF.key: _T_SOLO_DEF,
    _T_AREA_DEF.key: _T_AREA_DEF,
    _T_COST_DEF.key: _T_COST_DEF,
}


def _scope_extra(skills: dict, acts: dict) -> dict:
    return {"skills": skills, "sexual_acts": acts}


class ResistCastWiringBase(EvenniaTest):
    """Shared fixture: a caster, one humanoid target, and a companion NPC."""

    def setUp(self):
        super().setUp()
        register_catalog()
        # setUp builds the participants against the scoped race row, so the
        # catalogue scope opens here (the kit's class decorator covers only
        # test* methods).
        open_synthetic_scope(
            self, "skills", "elements", "races", "subraces", "static_tiers"
        )
        self.actor = create_object(
            PlayerCharacter, key="resist caster", location=self.room1
        )
        self.actor.race = _race_key()
        self.actor.apply_race_baseline()
        # The synthetic catalogue is empty except for the file-local rows, so
        # the caster must own exactly the acts the suite casts.
        self.actor.db.skills = {"active": list(_ALL_SKILLS), "passive": []}
        self.target = create_object(
            PlayerCharacter, key="resist target", location=self.room1
        )
        self.target.race = _race_key()
        self.target.apply_race_baseline()

    def _catalogue(self, skills: dict[str, SkillDef], acts: dict):
        """Open a nested scope whose catalogues carry the passed rows.

        Used as a plain ``with``: the outer setUp scope keeps the fixture
        scoped for construction; this one adds the act sidecar catalogue and
        narrows the skill catalogue to the file-local rows for the cast.
        """
        return synthetic_registries(
            "skills",
            "sexual_acts",
            "elements",
            "races",
            "subraces",
            "static_tiers",
            extra=_scope_extra(skills, acts),
        )

    def _npc(self, key="resist npc", affinity: int | None = None):
        npc = create_object(NPC, key=key, location=self.room1)
        npc.race = _race_key()
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

        with self._catalogue(_ALL_SKILLS, _ALL_ACTS), patch(
            "world.rules.sexual_resist.resist_verdict",
            wraps=resist_verdict,
        ) as spy, patch("world.rules.action.roll_d100", return_value=100):
            result = self._cast(_T_ACT, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(spy.call_count, 1)
        actor, resister = spy.call_args.args[:2]
        self.assertIs(actor, self.actor)
        self.assertIs(resister, self.target)

    @covers_requirement("sexual-resist-cast-wiring::casting-a-resistible-act-resolves-one-resist-contest-per-non-actor-target-before-its-effects-apply")
    def test_non_resistible_sexual_act_never_rolls(self):
        from world.rules.sexual_resist import resist_verdict

        with self._catalogue(_ALL_SKILLS, _ALL_ACTS), patch(
            "world.rules.sexual_resist.resist_verdict"
        ) as spy:
            result = self._cast(_T_SOLO, [])
        self.assertEqual(result.outcome, "success")
        spy.assert_not_called()

    @covers_requirement("sexual-resist-cast-wiring::casting-a-resistible-act-resolves-one-resist-contest-per-non-actor-target-before-its-effects-apply")
    def test_non_sexual_skill_never_rolls(self):
        from world.rules.sexual_resist import resist_verdict

        self.actor.db.skills = {
            "active": [_T_PLAIN],
            "passive": [],
        }
        with self._catalogue(_ALL_SKILLS, _ALL_ACTS), patch(
            "world.rules.sexual_resist.resist_verdict"
        ) as spy:
            result = self._cast(_T_PLAIN, [])
        self.assertEqual(result.outcome, "success")
        spy.assert_not_called()

    @covers_requirement("sexual-resist-cast-wiring::a-resistible-area-target-act-resolves-one-independent-contest-per-resolved-target")
    def test_area_act_rolls_one_independent_contest_per_target(self):
        second = create_object(
            PlayerCharacter, key="resist target two", location=self.room1
        )
        second.race = _race_key()
        second.apply_race_baseline()
        from world.rules.sexual_resist import resist_verdict

        with self._catalogue(_ALL_SKILLS, _ALL_ACTS), patch(
            "world.rules.sexual_resist.resist_verdict",
            wraps=resist_verdict,
        ) as spy, patch(
            "world.rules.action.roll_d100",
            side_effect=[1, 100],
        ):
            result = self._cast(_T_AREA, [self.target, second])
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
        resist_entries = [
            entry
            for entry in result.event_log.entries
            if entry.kind == "sexual_resist"
        ]
        self.assertEqual(len(resist_entries), 2)

    @covers_requirement("sexual-resist-cast-wiring::a-resistible-area-target-act-resolves-one-independent-contest-per-resolved-target")
    def test_area_act_event_effect_follows_the_withheld_branch(self):
        # Each target's event effects ride its OWN contest outcome: the
        # rulebook rule keyed to the act's event fires only for the target
        # that did not resist.
        from world.rules import sexual_transitions
        from world.rules.rulebook.schema import Rule

        rule = Rule(
            id="t_area_event_rule",
            when={"event": f"{_T_AREA}_event"},
            then={"field": "experience_types", "add": "t_area_experience"},
        )
        second = self._npc("area second")
        with self._catalogue(_ALL_SKILLS, _ALL_ACTS), patch.object(
            sexual_transitions, "_RULES", [rule]
        ), patch("world.rules.action.roll_d100", side_effect=[1, 100]):
            result = self._cast(_T_AREA, [self.target, second])
        self.assertEqual(result.outcome, "success")
        self.assertIn("t_area_experience", self.target.sexual.experience_types)
        self.assertNotIn("t_area_experience", second.sexual.experience_types)

class ResistEffectWithholdingTests(ResistCastWiringBase):
    """A resisted target receives none of the act's effects; a complied one does."""

    @covers_requirement("sexual-resist-cast-wiring::a-successfully-resisting-target-receives-none-of-the-act-s-pleasure-counter-or-sexual-event-effects")
    def test_resisted_target_keeps_pleasure_and_participant_counter(self):
        before = self._pleasure(self.target)
        with self._catalogue(_ALL_SKILLS, _ALL_ACTS), patch(
            "world.rules.action.roll_d100", return_value=100
        ):
            result = self._cast(_T_ACT, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self._pleasure(self.target), before)
        self.assertEqual(self.target.sexual.duo_act_count, 0)
        # The actor's own counter credit is never gated (design D-5).
        self.assertEqual(self.actor.sexual.duo_act_count, 1)

    @covers_requirement("sexual-resist-cast-wiring::a-successfully-resisting-target-receives-none-of-the-act-s-pleasure-counter-or-sexual-event-effects")
    def test_complied_target_receives_effects_as_before(self):
        expected = compute_pleasure_gain(
            self.target, None, _T_ACT_DEF.base_pleasure, 1.0, 2
        )
        with self._catalogue(_ALL_SKILLS, _ALL_ACTS), patch(
            "world.rules.action.roll_d100", return_value=1
        ):
            result = self._cast(_T_ACT, [self.target])
        self.assertEqual(result.outcome, "success")
        self.assertEqual(self.target.sexual.duo_act_count, 1)
        self.assertEqual(self._pleasure(self.target), expected)
        self.assertEqual(self.actor.sexual.duo_act_count, 1)

    @covers_requirement("sexual-resist-cast-wiring::the-actor-s-own-effects-and-the-cast-s-resource-time-and-practice-cost-are-never-gated-by-a-target-s-resist-outcome")
    def test_actor_own_pleasure_share_applied_in_both_branches(self):
        # A fully-resisted cast leaves the actor alone in the participant set
        # (count 1); a complied cast counts two (design D-7's crowd note).
        resisted_actor_gain = compute_pleasure_gain(
            self.actor, None, _T_ACT_DEF.base_pleasure, _T_ACT_DEF.actor_pleasure_ratio, 1
        )
        complied_actor_gain = compute_pleasure_gain(
            self.actor, None, _T_ACT_DEF.base_pleasure, _T_ACT_DEF.actor_pleasure_ratio, 2
        )
        actor_before = self._pleasure(self.actor)
        with self._catalogue(_ALL_SKILLS, _ALL_ACTS):
            with patch("world.rules.action.roll_d100", return_value=100):
                self._cast(_T_ACT, [self.target])
            after_resisted = self._pleasure(self.actor)
            self.assertEqual(after_resisted - actor_before, resisted_actor_gain)
            self.assertEqual(self.actor.sexual.duo_act_count, 1)

            second = create_object(
                PlayerCharacter, key="resist target two", location=self.room1
            )
            second.race = _race_key()
            second.apply_race_baseline()
            with patch("world.rules.action.roll_d100", return_value=1):
                self._cast(_T_ACT, [second])
            self.assertEqual(
                self._pleasure(self.actor) - after_resisted, complied_actor_gain
            )
            self.assertEqual(self.actor.sexual.duo_act_count, 2)

    @covers_requirement("sexual-resist-cast-wiring::the-actor-s-own-effects-and-the-cast-s-resource-time-and-practice-cost-are-never-gated-by-a-target-s-resist-outcome")
    def test_fully_resisted_cast_still_deducts_resource_cost(self):
        mp_before = self.actor.traits.mp.current
        with self._catalogue(_ALL_SKILLS, _ALL_ACTS), patch(
            "world.rules.action.roll_d100", return_value=100
        ):
            result = self._cast(_T_COST, [self.target])
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
        with self._catalogue(_ALL_SKILLS, _ALL_ACTS), patch(
            "world.rules.action.roll_d100", return_value=42
        ):
            result = self._cast(_T_ACT, [self.target])
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
        with self._catalogue(_ALL_SKILLS, _ALL_ACTS), patch(
            "world.rules.action.roll_d100", return_value=100
        ):
            result = self._cast(_T_ACT, [self.target])
        (entry,) = self._resist_entries(result)
        self.assertTrue(entry.data["resisted"])
        self.assertFalse(entry.data["auto_comply"])
        self.assertEqual(entry.data["roll"], 100)

    @covers_requirement("sexual-resist-cast-wiring::every-resist-contest-emits-a-sexual-resist-eventlog-entry-matching-the-sexual-resist-turn-cost-contract")
    def test_auto_complied_contest_logs_none_roll(self):
        npc = self._npc(affinity=90)
        with self._catalogue(_ALL_SKILLS, _ALL_ACTS):
            result = self._cast(_T_ACT, [npc])
        (entry,) = self._resist_entries(result)
        self.assertEqual(entry.target, str(npc.key))
        self.assertIs(entry.data["roll"], None)
        self.assertTrue(entry.data["auto_comply"])
        self.assertFalse(entry.data["resisted"])
        # An auto-complied target is not excluded from the act's effects.
        self.assertGreater(self._pleasure(npc), 0)
