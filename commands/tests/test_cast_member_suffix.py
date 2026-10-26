"""The ``由 <成員>`` caster suffix on the text ``cast`` command.

Out of combat the suffix casts with the named member exactly as the rule-level
``cast_as_member`` does (the member's MP, SELF binding, practice award and the
commander's six-second time cost); during an active session it saves that
member's skill command through the same actor-command facade
``combat command <actor-token> skill ...`` uses, without casting or advancing
time.

The ``companion-field-actions`` requirement this module establishes is
annotated with its canonical ID on the substantive tests below.

Data-independent: every skill, race, buff and monster is a synthetic kit row.
"""

from tools.spec_traceability import covers_requirement
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest

from commands.action import CmdCast
from commands.combat import CmdCombatCommand
from typeclasses.npcs import NPC
from world.rules.action import DEFAULT_CAST_SECONDS, RejectReason
from world.rules.buffs import entity_active_buffs
from world.rules.clock import WorldClock
from world.rules.combat_session import engage, read_session
from world.rules.field_cast import FieldCastOutcome
from world.rules.party import join_party
from world.rules.player_messages import rejection_message
from world.rules.progression import SKILL_PRACTICE_XP_PER_USE, reset_practice_dedupe
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import make_skill

from world.rules.tests._combat_session_helpers import (
    _monster,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage

_HEAL = make_skill(
    "t_companion_heal",
    label="同伴癒合",
    description="以暖流癒合同伴傷口的合成法術。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={"mp": 8},
    usable_out_of_combat=True,
    element=None,
    effects=["heal:single"],
    category=SkillCategory.ENHANCEMENT,
)
_SELF = make_skill(
    "t_companion_veil",
    label="同伴苔幕",
    description="替自己覆上苔屑霧幕的合成法術。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SELF,
    cost={"mp": 13},
    usable_out_of_combat=True,
    element=None,
    effects=["self_buff_apply:t_moss_veil"],
    category=SkillCategory.ENHANCEMENT,
)
_BUFF_KEY = "t_moss_veil"
_EXTRA = {
    "skills": {
        **synth_innate_overlay()["skills"],
        _HEAL.key: _HEAL,
        _SELF.key: _SELF,
    }
}


class CastMemberSuffixTests(
    BattlefieldIsolation, EvenniaCommandTestMixin, EvenniaTest
):
    """A commander, two companions and an owned settlement clock."""

    def setUp(self):
        reset_practice_dedupe()
        open_synthetic_scope(
            self,
            "skills",
            "buffs",
            "elements",
            "sexual_acts",
            "races",
            "subraces",
            "static_tiers",
            extra=_EXTRA,
        )
        super().setUp()
        self.char1.race = _race_key()
        self.char1.apply_race_baseline()
        self.char1.location = self.room1
        self.char1.traits.hp.base = 100
        self.char1.traits.hp.current = 10
        self.char1.traits.mp.current = self.char1.traits.mp.max
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")
        grant_lineage(self.aila, [_HEAL.key, _SELF.key])
        for entity in (self.char1, self.aila, self.kahn):
            self._freeze_regen(entity)
        self.clock = WorldClock()

    def _freeze_regen(self, entity):
        """Keep the fixture arithmetic independent of the clock's regen stage."""
        for gauge_key in ("hp", "mp", "sp"):
            gauge = getattr(entity.traits, gauge_key, None)
            if gauge is not None:
                gauge.rate = 0

    def _companion(self, key, *, hp=100):
        npc = create_object(NPC, key=key, location=self.room1, home=self.room1)
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.traits.hp.base = hp
        npc.traits.hp.current = hp
        npc.traits.mp.base = 20
        npc.traits.mp.current = 20
        npc.traits.magic_power.base = 30
        join_party(npc, self.char1)
        return npc

    def _run(self, command, args, expected=None):
        with patch(
            "world.rules.cast_settlement.read_world_clock",
            return_value=self.clock,
        ), patch(
            "world.rules.cast_settlement.get_world_clock",
            return_value=self.clock,
        ):
            return self.call(command, args, expected)

    @covers_requirement(
        "companion-field-actions::the-text-cast-command-accepts-a-caster-suffix"
    )
    def test_out_of_combat_suffix_casts_as_the_member(self):
        self._run(CmdCast(), f"{_HEAL.key}={self.char1.key} 由 艾拉")
        # The member pays, the commander is healed, and the member accrues the
        # practice award; the commander's own proficiency stays untouched.
        self.assertEqual(self.aila.traits.mp.current, 12)
        self.assertEqual(int(self.char1.traits.hp.current), 40)
        self.assertEqual(
            self.aila.db.skill_proficiency, {_HEAL.key: SKILL_PRACTICE_XP_PER_USE}
        )
        self.assertFalse(self.char1.db.skill_proficiency)
        self.assertEqual(self.clock.tick, DEFAULT_CAST_SECONDS)

    @covers_requirement(
        "companion-field-actions::the-text-cast-command-accepts-a-caster-suffix"
    )
    def test_in_combat_suffix_saves_the_member_skill_command(self):
        monster = _monster("suffix goblin", hp=500)
        monster.location = self.room1
        engage(self.char1, monster)
        self._run(CmdCombatCommand(), f"a2 skill {_HEAL.key}=e1")
        expected = read_session(self.char1).draft_entries[self.aila.pk]
        self._run(CmdCast(), f"{_HEAL.key}=e1 由 艾拉")
        record = read_session(self.char1)
        self.assertEqual(record.draft_entries[self.aila.pk], expected)
        self.assertEqual(record.rounds_elapsed, 0)
        self.assertEqual(self.clock.tick, 0)

    def test_an_unknown_member_token_is_refused(self):
        self._run(CmdCast(), f"{_HEAL.key} 由 路人", "對方不是你的隊伍成員。")
        self.assertEqual(self.aila.traits.mp.current, 20)
        self.assertEqual(self.clock.tick, 0)

    def test_a_knocked_out_member_is_refused(self):
        self.kahn.traits.hp.current = 1
        self._run(CmdCast(), f"{_HEAL.key} 由 卡恩", "對方目前無法行動。")
        self.assertEqual(self.clock.tick, 0)

    def test_a_companion_monster_target_opens_the_commander_s_encounter(self):
        wolf = _monster("suffix wolf", hp=2000, atk=1)
        wolf.location = self.room1
        self._run(CmdCast(), f"{_HEAL.key}={wolf.key} 由 艾拉")
        # The suffix's monster target opens the commander's encounter with
        # 艾拉's selection as its opening entry; nothing is spent or advanced
        # before the remaining members choose.
        record = read_session(self.char1)
        self.assertIsNotNone(record)
        self.assertIsNone(read_session(self.aila))
        self.assertEqual(record.opening_first_actor, str(self.aila.key))
        self.assertEqual(
            record.draft_entries[int(self.aila.pk)]["payload"]["skill_key"],
            _HEAL.key,
        )
        self.assertEqual(self.aila.traits.mp.current, 20)
        self.assertEqual(self.clock.tick, 0)

    def test_a_missing_member_token_falls_through_to_the_ordinary_parse(self):
        self._run(
            CmdCast(),
            f"{_HEAL.key} 由",
            rejection_message(RejectReason.UNKNOWN_SKILL),
        )
        self.assertEqual(self.aila.traits.mp.current, 20)
        self.assertEqual(self.clock.tick, 0)

    def test_a_bare_trailing_token_never_selects_a_caster(self):
        self._run(CmdCast(), f"{_HEAL.key}={self.char1.key} 由")
        self.assertEqual(self.aila.traits.mp.current, 20)
        self.assertEqual(int(self.char1.traits.hp.current), 10)
        self.assertEqual(self.clock.tick, 0)

    def test_the_final_suffix_wins_over_a_target_name_containing_you(self):
        target = create_object(NPC, key="莉瑟 由 月光", location=self.room1)
        target.race = _race_key()
        target.apply_race_baseline()
        target.traits.hp.base = 100
        target.traits.hp.current = 10
        self._run(CmdCast(), f"{_HEAL.key}=莉瑟 由 月光 由 艾拉")
        self.assertEqual(int(target.traits.hp.current), 40)
        self.assertEqual(self.aila.traits.mp.current, 12)

    def test_a_scale_token_is_forwarded_to_the_rule(self):
        outcome = FieldCastOutcome(
            "rejected", reason=RejectReason.UNKNOWN_SKILL, detail=_HEAL.key
        )
        with patch(
            "commands.action.cast_as_member", return_value=outcome
        ) as cast:
            self._run(CmdCast(), f"{_HEAL.key}@1/2={self.char1.key} 由 艾拉")
        cast.assert_called_once()
        args, kwargs = cast.call_args
        self.assertEqual(args[0], self.char1)
        self.assertEqual(args[1], self.aila.pk)
        self.assertEqual(args[2], _HEAL.key)
        self.assertEqual(kwargs["targets"], [self.char1])
        self.assertEqual(kwargs["scale"], 0.5)

    def test_a_multiword_member_name_resolves(self):
        moonlight = self._companion("艾拉 月光")
        grant_lineage(moonlight, [_SELF.key])
        self._freeze_regen(moonlight)
        self._run(CmdCast(), f"{_SELF.key} 由 艾拉 月光")
        self.assertIn(_BUFF_KEY, entity_active_buffs(moonlight))
        self.assertEqual(moonlight.traits.mp.current, 7)
        self.assertEqual(self.clock.tick, DEFAULT_CAST_SECONDS)

    def test_an_in_session_flee_suffix_keeps_the_actor_command_path(self):
        monster = _monster("suffix flee goblin", hp=500)
        monster.location = self.room1
        engage(self.char1, monster)
        self._run(
            CmdCast(),
            "flee 由 艾拉",
            "個別逃跑已經取消，整隊的行動需要明確確認。",
        )
        record = read_session(self.char1)
        self.assertEqual(record.draft_entries, {})
        self.assertEqual(record.rounds_elapsed, 0)
        self.assertEqual(self.clock.tick, 0)
