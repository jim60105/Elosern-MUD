"""Explicit-caster field casting for a present party member.

Covers ``world/rules/field_cast.py::cast_as_member``: the acting-purpose member
boundary, the unchanged field routing with the member as actor (costs, SELF
binding, practice award, time cost), the present-party settlement scope, the
stable refusals, and the companion monster opening the commander's encounter
(``companion-field-combat-opening``).

The ``companion-field-actions`` requirements this module establishes are
annotated with their canonical IDs on the substantive tests below.

Data-independent: every skill, race, buff and monster is a synthetic kit row.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.action import DEFAULT_CAST_SECONDS, RejectReason
from world.rules.buffs import entity_active_buffs
from world.rules.clock import AdvanceSource, WorldClock
from world.rules.combat_session import read_session
from world.rules.fatigue import (
    SleepPosture,
    read_fatigue_state,
    write_fatigue_state,
)
from world.rules.field_cast import cast_as_member
from world.rules.party import join_party
from world.rules.party_scope import (
    REASON_MEMBER_ASLEEP,
    REASON_MEMBER_CANNOT_ACT,
    REASON_MEMBER_NOT_PRESENT,
    REASON_NOT_PARTY_MEMBER,
    PartyScopeError,
    present_party_scope,
    resolve_commander,
)
from world.rules.progression import SKILL_PRACTICE_XP_PER_USE, reset_practice_dedupe
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_RACES, make_skill

from ._combat_session_helpers import (
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from .combat_fixtures import BattlefieldIsolation, grant_lineage

# A synthetic heal with the independent expected arithmetic: MP 20 with cost 8
# ends at 12, and magic power 30 with the rulebook's 1.0 heal multiplier
# restores exactly 30 HP. Element ``None`` keeps the practice factor free of
# affinity scaling, so the award is the bare per-use constant.
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
# The kit buff row the self-buff names; the scope carries it under "buffs".
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


class _CompanionCastCase(BattlefieldIsolation, EvenniaTestCase):
    """A co-located commander, two companions, an outsider and a clock."""

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
        self.room = create_object(Room, key="companion cast meadow")
        self.elsewhere = create_object(Room, key="companion cast elsewhere")
        self.commander = _player("companion cast commander")
        self.commander.location = self.room
        self.commander.traits.hp.base = 100
        self.commander.traits.hp.current = 10
        self.commander.traits.mp.current = self.commander.traits.mp.max
        self.aila = self._companion("艾拉", magic_power=30)
        self.kahn = self._companion("卡恩", magic_power=30)
        grant_lineage(self.aila, [_HEAL.key, _SELF.key])
        for entity in (self.commander, self.aila, self.kahn):
            self._freeze_regen(entity)
        self.clock = WorldClock()

    def _freeze_regen(self, entity):
        """Keep the fixture arithmetic independent of the clock's regen stage.

        The advance still settles the party (asserted through the scope spy);
        disabling the per-second rates only keeps the cost and heal amounts
        exact, as the change's independent expected numbers require.
        """
        for gauge_key in ("hp", "mp", "sp"):
            gauge = getattr(entity.traits, gauge_key, None)
            if gauge is not None:
                gauge.rate = 0

    def _companion(self, key, *, hp=100, magic_power=30):
        npc = create_object(NPC, key=key, location=self.room, home=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.traits.hp.base = hp
        npc.traits.hp.current = hp
        npc.traits.mp.base = 20
        npc.traits.mp.current = 20
        npc.traits.magic_power.base = magic_power
        join_party(npc, self.commander)
        return npc

    def _outsider(self, key="路人"):
        npc = create_object(NPC, key=key, location=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        return npc

    def _wolf(self, key="companion cast wolf"):
        wolf = _monster(key, hp=2000, atk=1)
        wolf.location = self.room
        return wolf

    def _settle(self):
        """Patch the settlement clock so the test owns the tick."""
        return (
            patch(
                "world.rules.cast_settlement.read_world_clock",
                return_value=self.clock,
            ),
            patch(
                "world.rules.cast_settlement.get_world_clock",
                return_value=self.clock,
            ),
        )

    def _cast(self, member, skill_key, **kwargs):
        read_clock, get_clock = self._settle()
        with read_clock, get_clock:
            return cast_as_member(
                self.commander, int(member.pk), skill_key, **kwargs
            )

    def _expected_practice(self):
        multiplier = SYNTH_RACES[self.aila.race].learning_multiplier
        return SKILL_PRACTICE_XP_PER_USE * multiplier


class CompanionCastRuleTests(_CompanionCastCase):
    """The wrapper routes with the member as actor and settles the party once."""

    @covers_requirement(
        "party-time-settlement::field-cast-and-item-use-advances-settle-the-present-party",
        "companion-field-actions::a-field-cast-names-its-caster-explicitly",
        "companion-field-actions::companion-field-casts-cost-the-commander-s-time-and-settle-the-party",
    )
    def test_companion_heal_charges_the_companion_and_heals_the_commander(self):
        commander_mp = self.commander.traits.mp.current
        with patch.object(
            self.clock, "advance", wraps=self.clock.advance
        ) as advance:
            outcome = self._cast(self.aila, _HEAL.key, targets=[self.commander])
        self.assertEqual(outcome.route, "settlement")
        self.assertEqual(outcome.settlement.result.outcome, "success")
        self.assertEqual(
            outcome.settlement.result.time_cost_seconds, DEFAULT_CAST_SECONDS
        )
        # Independent arithmetic: MP 20 - cost 8 = 12; magic power 30 with
        # the rulebook's 1.0 heal multiplier restores exactly 30 HP.
        self.assertEqual(self.aila.traits.mp.current, 12)
        self.assertEqual(self.commander.traits.mp.current, commander_mp)
        self.assertEqual(int(self.commander.traits.hp.current), 40)
        self.assertEqual(
            self.aila.db.skill_proficiency, {_HEAL.key: self._expected_practice()}
        )
        self.assertFalse(self.commander.db.skill_proficiency)
        advance.assert_called_once()
        seconds, source, scope = advance.call_args.args
        self.assertEqual(seconds, DEFAULT_CAST_SECONDS)
        self.assertEqual(source, AdvanceSource.COMMAND)
        self.assertEqual(scope, (self.commander, self.aila, self.kahn))
        self.assertEqual(self.clock.tick, DEFAULT_CAST_SECONDS)

    @covers_requirement(
        "companion-field-actions::a-field-cast-names-its-caster-explicitly"
    )
    def test_self_buff_binds_to_the_caster(self):
        outcome = self._cast(self.aila, _SELF.key)
        self.assertEqual(outcome.settlement.result.outcome, "success")
        self.assertIn(_BUFF_KEY, entity_active_buffs(self.aila))
        self.assertNotIn(_BUFF_KEY, entity_active_buffs(self.commander))
        self.assertEqual(self.aila.traits.mp.current, 7)

    @covers_requirement(
        "companion-field-actions::companion-field-casts-cost-the-commander-s-"
        "time-and-settle-the-party"
    )
    def test_a_depleted_caster_completes_the_full_action_then_collapses(self):
        write_fatigue_state(self.aila, 12, SleepPosture.AWAKE)
        outcome = self._cast(self.aila, _HEAL.key, targets=[self.commander])
        # Full effects, costs and six seconds commit before the collapse; no
        # part of the interval becomes retrospective sleep recovery.
        self.assertEqual(outcome.settlement.result.outcome, "success")
        self.assertEqual(outcome.settlement.result.time_cost_seconds, 6)
        self.assertEqual(self.aila.traits.mp.current, 12)
        self.assertEqual(int(self.commander.traits.hp.current), 40)
        self.assertEqual(self.clock.tick, 6)
        state = read_fatigue_state(self.aila)
        self.assertEqual(state.reserve_units, 0)
        self.assertIs(state.posture, SleepPosture.FORCED)

    @covers_requirement(
        "companion-field-actions::companion-field-casts-cost-the-commander-s-"
        "time-and-settle-the-party"
    )
    def test_only_the_unselected_depleted_companion_collapses(self):
        write_fatigue_state(self.kahn, 12, SleepPosture.AWAKE)
        outcome = self._cast(self.aila, _HEAL.key, targets=[self.commander])
        self.assertEqual(outcome.settlement.result.outcome, "success")
        self.assertEqual(self.clock.tick, 6)
        self.assertIs(
            read_fatigue_state(self.kahn).posture, SleepPosture.FORCED
        )
        self.assertIs(
            read_fatigue_state(self.commander).posture, SleepPosture.AWAKE
        )
        self.assertIs(
            read_fatigue_state(self.aila).posture, SleepPosture.AWAKE
        )
        # The forced-sleep projection carries the status notice; control did
        # not move away from the commander.
        self.assertIn(
            "fatigue_forced_sleep", entity_active_buffs(self.kahn)
        )
        # Control never moved: no combat session opened and the companion
        # stayed in place.
        self.assertIsNone(read_session(self.commander))
        self.assertIs(self.kahn.location, self.room)

    @covers_requirement(
        "party-member-authority::acting-purposes-exclude-knocked-out-members",
        "companion-field-actions::unfit-casters-are-refused-with-stable-reasons",
    )
    def test_a_knocked_out_caster_is_refused(self):
        self.kahn.traits.hp.current = 1
        with self.assertRaises(PartyScopeError) as caught:
            self._cast(self.kahn, _HEAL.key, targets=[self.commander])
        self.assertEqual(caught.exception.reason, REASON_MEMBER_CANNOT_ACT)
        self.assertEqual(self.kahn.traits.mp.current, 20)
        self.assertEqual(int(self.commander.traits.hp.current), 10)
        self.assertEqual(self.clock.tick, 0)
        self.assertIsNone(read_session(self.commander))

    @covers_requirement(
        "party-member-authority::sleep-blocks-acting-purposes-without-removing-authenticated-authority"
    )
    def test_a_sleeping_caster_is_refused_with_zero_effects_and_time(self):
        write_fatigue_state(self.kahn, 0, SleepPosture.FORCED)
        with self.assertRaises(PartyScopeError) as caught:
            self._cast(self.kahn, _HEAL.key, targets=[self.commander])
        self.assertEqual(caught.exception.reason, REASON_MEMBER_ASLEEP)
        self.assertEqual(self.kahn.traits.mp.current, 20)
        self.assertEqual(int(self.commander.traits.hp.current), 10)
        self.assertEqual(self.clock.tick, 0)
        self.assertIsNone(read_session(self.commander))

    @covers_requirement(
        "party-member-authority::member-presence-is-checked-against-the-commander-s-room",
        "companion-field-actions::unfit-casters-are-refused-with-stable-reasons",
    )
    def test_an_absent_caster_is_refused(self):
        self.aila.location = self.elsewhere
        with self.assertRaises(PartyScopeError) as caught:
            self._cast(self.aila, _HEAL.key, targets=[self.commander])
        self.assertEqual(caught.exception.reason, REASON_MEMBER_NOT_PRESENT)
        self.assertEqual(self.clock.tick, 0)

    @covers_requirement(
        "party-member-authority::a-named-member-is-re-derived-and-never-substituted",
        "companion-field-actions::unfit-casters-are-refused-with-stable-reasons",
    )
    def test_a_non_member_caster_is_refused(self):
        outsider = self._outsider()
        with self.assertRaises(PartyScopeError) as caught:
            self._cast(outsider, _HEAL.key, targets=[self.commander])
        self.assertEqual(caught.exception.reason, REASON_NOT_PARTY_MEMBER)
        self.assertEqual(self.clock.tick, 0)

    @covers_requirement(
        "party-member-authority::a-named-member-is-re-derived-and-never-substituted"
    )
    def test_a_forged_caster_identity_is_refused_before_any_session(self):
        read_clock, get_clock = self._settle()
        with read_clock, get_clock, self.assertRaises(PartyScopeError) as caught:
            cast_as_member(
                self.commander, 999_999, _HEAL.key, targets=[self.commander]
            )
        self.assertEqual(caught.exception.reason, REASON_NOT_PARTY_MEMBER)
        self.assertEqual(self.clock.tick, 0)
        self.assertIsNone(read_session(self.commander))

    @covers_requirement(
        "companion-field-actions::a-field-cast-names-its-caster-explicitly"
    )
    def test_an_unowned_skill_is_refused_with_the_existing_reason(self):
        outcome = self._cast(self.kahn, _HEAL.key, targets=[self.commander])
        self.assertEqual(outcome.route, "settlement")
        self.assertEqual(outcome.settlement.result.outcome, "rejected")
        self.assertEqual(
            outcome.settlement.result.reason, RejectReason.UNKNOWN_SKILL
        )
        self.assertEqual(self.kahn.traits.mp.current, 20)
        self.assertEqual(int(self.commander.traits.hp.current), 10)
        self.assertEqual(self.clock.tick, 0)

    @covers_requirement(
        "companion-field-actions::unfit-casters-are-refused-with-stable-reasons"
    )
    def test_an_existing_action_gate_returns_its_own_reason(self):
        grant_lineage(self.kahn, [_HEAL.key])
        self.kahn.traits.mp.current = 0
        outcome = self._cast(self.kahn, _HEAL.key, targets=[self.commander])
        self.assertEqual(outcome.route, "settlement")
        self.assertEqual(outcome.settlement.result.outcome, "rejected")
        self.assertEqual(
            outcome.settlement.result.reason, RejectReason.INSUFFICIENT_RESOURCE
        )
        self.assertEqual(self.kahn.traits.mp.current, 0)
        self.assertEqual(int(self.commander.traits.hp.current), 10)
        self.assertFalse(self.kahn.db.skill_proficiency)
        self.assertEqual(self.clock.tick, 0)

    def test_a_companion_monster_target_opens_the_commander_s_encounter(self):
        wolf = self._wolf()
        aila_mp = self.aila.traits.mp.current
        outcome = self._cast(self.aila, _HEAL.key, targets=[wolf])
        # The member's cast is the opening selection of the commander's
        # encounter, so the session lives on the commander alone and nothing
        # is spent or rolled before the remaining members choose.
        self.assertEqual(outcome.route, "initiation")
        self.assertEqual(outcome.combat_result["outcome"], "draft")
        record = read_session(self.commander)
        self.assertIsNotNone(record)
        self.assertIsNone(read_session(self.aila))
        self.assertEqual(record.opening_first_actor, str(self.aila.key))
        self.assertEqual(
            record.draft_entries[int(self.aila.pk)]["payload"]["skill_key"],
            _HEAL.key,
        )
        self.assertEqual(self.aila.traits.mp.current, aila_mp)
        self.assertEqual(int(wolf.traits.hp.current), 2000)
        self.assertEqual(self.clock.tick, 0)


class PresentPartyScopeForCompanionTests(_CompanionCastCase):
    """The settlement-scope extension keeps commander authority strict."""

    @covers_requirement(
        "party-member-authority::the-present-party-scope-is-ordered-and-room-bound"
    )
    def test_a_bound_companion_resolves_the_commanders_present_party(self):
        self.assertEqual(
            present_party_scope(self.aila),
            (self.commander, self.aila, self.kahn),
        )
        with self.assertRaises(PartyScopeError) as caught:
            resolve_commander(self.aila)
        self.assertEqual(caught.exception.reason, REASON_NOT_PARTY_MEMBER)

    def test_a_stale_possession_flag_still_rejects(self):
        self.aila.db.possessed_by = self.commander.pk
        with self.assertRaises(PartyScopeError) as caught:
            present_party_scope(self.aila)
        self.assertEqual(caught.exception.reason, REASON_NOT_PARTY_MEMBER)

    def test_a_one_sided_binding_is_rejected(self):
        self.aila.db.party_member = None
        with self.assertRaises(PartyScopeError) as caught:
            present_party_scope(self.aila)
        self.assertEqual(caught.exception.reason, REASON_NOT_PARTY_MEMBER)
