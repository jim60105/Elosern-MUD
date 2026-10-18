"""Companion-initiated field combat (``companion-field-combat-opening``).

A companion's field cast at a co-located living monster opens the commander's
encounter through the same initiation path the commander uses: the session,
its active-session check, its room and its rollback snapshots belong to the
resolved commander, while the caster's selection is the opening draft entry,
the caster acts first, no command time is charged, and the caster's cost and
practice are accounted once when that entry resolves in the round. A forged,
absent, knocked-out or stale caster is refused before any session, resource,
roll or clock access. The possessed and the commanded caster take the same
path, and a possessed player keeps operating the commander's session.

Data-independent: every skill, race and monster is a synthetic kit row.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from commands.combat import CmdCombatCommand
from commands.action import CmdCast
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.rules.action import RejectReason
from world.rules.clock import read_world_clock
from world.rules.combat_initiation import (
    initiate_field_combat,
    preview_field_opening,
)
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    CombatSessionError,
    SessionReason,
    get_required_combat_actors,
    read_session,
    reconstruct_battlefield,
    session_owner,
    submit_player_action,
)
from world.rules.dialogue import open_or_refresh_dialogue
from world.rules.field_cast import cast_as_member
from world.rules.party import join_party
from world.rules.party_scope import (
    REASON_MEMBER_CANNOT_ACT,
    REASON_MEMBER_NOT_PRESENT,
    REASON_NOT_PARTY_MEMBER,
    PartyScopeError,
)
from world.rules.possession import enter_possession
from world.rules.progression import SKILL_PRACTICE_XP_PER_USE, reset_practice_dedupe
from world.rules.skip_safety import _BATTLEFIELDS
from world.skills.registry import SkillCategory, SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_RACES, SYNTH_SKILLS, make_skill

from ._combat_session_helpers import (
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from .combat_fixtures import BattlefieldIsolation, grant_lineage

# A synthetic single-target spell with a bare per-use practice factor: MP 20
# with cost 12 ends at 8, and the element-free row keeps the award the
# constant itself (no affinity scaling), so an exact value proves one award.
_SPELL = make_skill(
    "t_opening_ember",
    label="同伴開場燼火",
    description="以無聲燼火揭開戰鬥的合成法術。",
    kind=SkillKind.ACTIVE,
    target_spec=TargetSpec.SINGLE,
    cost={"mp": 12},
    usable_out_of_combat=True,
    element=None,
    effects=["heal:single"],
    category=SkillCategory.ENHANCEMENT,
)
_SPELL_COST_MP = 12
_CAST = _SPELL.key
_AREA = SYNTH_SEAM_AREA_SKILL.key
_EXTRA = {
    "skills": {
        **synth_innate_overlay()["skills"],
        _SPELL.key: _SPELL,
        SYNTH_SEAM_AREA_SKILL.key: SYNTH_SEAM_AREA_SKILL,
    }
}


class _CompanionOpeningCase(BattlefieldIsolation, EvenniaTest):
    """A co-located commander, two companions, an outsider and a monster."""

    def setUp(self):
        reset_practice_dedupe()
        open_synthetic_scope(
            self,
            "skills",
            "elements",
            "sexual_acts",
            "races",
            "subraces",
            "static_tiers",
            extra=_EXTRA,
        )
        super().setUp()
        self.room = create_object(Room, key="opening meadow")
        self.elsewhere = create_object(Room, key="opening elsewhere")
        self.commander = self.char1
        self.commander.location = self.room
        self.commander.race = _race_key()
        self.commander.apply_race_baseline()
        self.commander.traits.hp.base = 500
        self.commander.traits.hp.current = 500
        self.commander.traits.mp.base = 50
        self.commander.traits.mp.current = 50
        self.aila = self._companion("艾拉")
        self.kahn = self._companion("卡恩")
        grant_lineage(self.aila, [_CAST, _AREA])
        for entity in (self.commander, self.aila, self.kahn):
            self._freeze_regen(entity)
        self.wolf = _monster("opening wolf", hp=4000, atk=1)
        self.wolf.location = self.room

    def _freeze_regen(self, entity):
        """Keep the fixture arithmetic independent of the clock's regen stage."""
        for gauge_key in ("hp", "mp", "sp"):
            gauge = getattr(entity.traits, gauge_key, None)
            if gauge is not None:
                gauge.rate = 0

    def _companion(self, key, *, hp=100):
        npc = create_object(NPC, key=key, location=self.room, home=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        npc.traits.hp.base = hp
        npc.traits.hp.current = hp
        npc.traits.mp.base = 20
        npc.traits.mp.current = 20
        npc.traits.magic_power.base = 30
        join_party(npc, self.commander)
        return npc

    def _outsider(self, key="路人"):
        npc = create_object(NPC, key=key, location=self.room)
        npc.race = _race_key()
        npc.apply_race_baseline()
        return npc

    def _expected_practice(self):
        multiplier = SYNTH_RACES[self.aila.race].learning_multiplier
        return SKILL_PRACTICE_XP_PER_USE * multiplier

    def _durable_rolls(self):
        """A round that neither misses nor flees, for deterministic arithmetic."""
        return (
            patch("world.rules.combat.battlefield.roll_d100", return_value=50),
            patch("world.rules.combat.damage.roll_d100", return_value=50),
            patch("world.rules.combat.rounds.roll_d100", return_value=50),
        )


class CompanionOpeningTests(_CompanionOpeningCase):
    """The companion's cast opens the commander's encounter."""

    @covers_requirement(
        "companion-field-actions::a-field-cast-names-its-caster-explicitly"
    )
    @covers_requirement(
        "field-combat-initiation::a-skill-aimed-at-a-co-located-hostile-monster-from-exploration-always-initiates-combat"
    )
    @covers_requirement(
        "companion-field-actions::a-companion-s-field-cast-may-open-combat-under-the-commander-s-session"
    )
    @covers_requirement(
        "field-combat-initiation::a-companion-initiator-opens-the-commander-s-encounter"
    )
    def test_a_commanded_companion_opens_the_commander_s_encounter(self):
        mp_before = self.aila.traits.mp.current
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            outcome = cast_as_member(
                self.commander, int(self.aila.pk), _CAST, targets=[self.wolf]
            )
        self.assertEqual(outcome.route, "initiation")
        self.assertEqual(outcome.combat_result["outcome"], "draft")
        record = read_session(self.commander)
        self.assertIsNotNone(record)
        # The session is the commander's alone: the caster carries no copy.
        self.assertIsNone(read_session(self.aila))
        self.assertEqual(
            record.player_ids,
            (int(self.commander.pk), int(self.aila.pk), int(self.kahn.pk)),
        )
        self.assertEqual(record.enemy_ids, (int(self.wolf.pk),))
        self.assertEqual(record.room_id, int(self.room.pk))
        self.assertEqual(record.opening_first_actor, str(self.aila.key))
        self.assertEqual(
            record.draft_entries[int(self.aila.pk)]["payload"]["skill_key"], _CAST
        )
        self.assertEqual(record.rounds_elapsed, 0)
        # The seed charges nothing yet: no command time, no caster cost.
        self.assertEqual(read_world_clock().tick, 0)
        self.assertEqual(self.aila.traits.mp.current, mp_before)
        self.assertFalse(self.aila.db.skill_proficiency)
        self.assertEqual(self.wolf.traits.hp.current, self.wolf.traits.hp.base)

    @covers_requirement(
        "companion-field-actions::a-field-cast-names-its-caster-explicitly"
    )
    @covers_requirement(
        "companion-field-actions::a-companion-s-field-cast-may-open-combat-under-the-commander-s-session"
    )
    @covers_requirement(
        "field-combat-initiation::a-companion-initiator-opens-the-commander-s-encounter"
    )
    def test_a_possessed_companion_opens_the_commander_s_encounter(self):
        enter_possession(self.commander, self.aila)
        self.assertIs(self.session.puppet, self.aila)
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            result = initiate_field_combat(self.aila, _CAST, self.wolf)
        self.assertEqual(result["outcome"], "draft")
        record = read_session(self.commander)
        self.assertIsNotNone(record)
        self.assertIsNone(read_session(self.aila))
        self.assertEqual(
            record.draft_entries[int(self.aila.pk)]["payload"]["skill_key"], _CAST
        )
        # The seeded caster is already confirmed, so the commander and the
        # other companion are the members still to choose.
        battlefield = reconstruct_battlefield(self.commander, record)
        required = set(get_required_combat_actors(record, battlefield))
        self.assertEqual(
            required - set(record.draft_entries),
            {int(self.commander.pk), int(self.kahn.pk)},
        )

    @covers_requirement(
        "companion-field-actions::a-field-cast-names-its-caster-explicitly"
    )
    @covers_requirement(
        "companion-field-actions::a-companion-s-field-cast-may-open-combat-under-the-commander-s-session"
    )
    def test_the_caster_pays_once_when_its_entry_resolves(self):
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            initiate_field_combat(
                self.aila, _CAST, self.wolf, commander=self.commander
            )
        # Independent arithmetic: MP 20 with cost 12 is still 20 until the
        # draft completes, and the element-free row awards the bare constant.
        self.assertEqual(self.aila.traits.mp.current, 20)
        self.assertFalse(self.aila.db.skill_proficiency)
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            submit_player_action(self.commander, BASIC_ATTACK_KEY, [self.wolf])
            submit_player_action(
                self.commander,
                BASIC_ATTACK_KEY,
                [self.wolf],
                commanded_actor=self.kahn,
            )
        self.assertEqual(self.aila.traits.mp.current, 20 - _SPELL_COST_MP)
        self.assertEqual(
            self.aila.db.skill_proficiency, {_CAST: self._expected_practice()}
        )
        self.assertEqual(read_session(self.commander).rounds_elapsed, 1)

    @covers_requirement(
        "field-combat-initiation::a-committed-field-initiation-emits-one-boundary-event"
    )
    @covers_requirement(
        "field-combat-initiation::a-companion-initiator-opens-the-commander-s-encounter"
    )
    def test_the_boundary_event_names_the_commander_and_the_caster(self):
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with (
            battlefield_roll,
            damage_roll,
            rounds_roll,
            patch("world.rules.combat_initiation.log_info") as info,
            self.captureOnCommitCallbacks(execute=True),
        ):
            initiate_field_combat(
                self.aila, _CAST, self.wolf, commander=self.commander
            )
        events = [
            call
            for call in info.call_args_list
            if call.args and call.args[0] == "field_combat_initiated"
        ]
        self.assertEqual(len(events), 1)
        context = events[0][1]["context"]
        self.assertEqual(context["char"], str(self.commander.pk))
        self.assertEqual(context["caster"], str(self.aila.pk))
        self.assertEqual(context["room"], str(self.room.pk))
        self.assertEqual(context["skill"], _CAST)
        self.assertEqual(context["enemy_count"], 1)
        self.assertEqual(context["opening"], "draft")

    @covers_requirement(
        "field-combat-initiation::a-companion-initiator-opens-the-commander-s-encounter"
    )
    def test_an_area_opening_engages_only_living_room_monsters(self):
        second = _monster("opening second wolf", hp=4000, atk=1)
        second.location = self.room
        dead = _monster("opening dead wolf", hp=1, atk=1)
        dead.location = self.room
        dead.traits.hp.current = 0
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            initiate_field_combat(
                self.aila, _AREA, self.wolf, commander=self.commander
            )
        record = read_session(self.commander)
        living = tuple(sorted((int(self.wolf.pk), int(second.pk))))
        self.assertEqual(record.enemy_ids, living)
        self.assertEqual(
            record.draft_entries[int(self.aila.pk)]["payload"]["targets_or_shorthand"],
            list(living),
        )

    @covers_requirement(
        "field-combat-initiation::a-companion-initiator-opens-the-commander-s-encounter"
    )
    def test_a_second_opening_cannot_replace_the_commander_s_session(self):
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            initiate_field_combat(
                self.aila, _CAST, self.wolf, commander=self.commander
            )
        before = read_session(self.commander)
        with self.assertRaises(CombatSessionError) as caught:
            initiate_field_combat(
                self.aila, _CAST, self.wolf, commander=self.commander
            )
        self.assertEqual(caught.exception.args[0], SessionReason.ALREADY_IN_COMBAT)
        after = read_session(self.commander)
        self.assertEqual(after.session_id, before.session_id)
        self.assertEqual(after.draft_version, before.draft_version)
        self.assertEqual(after.draft_entries, before.draft_entries)


class CompanionOpeningRefusalTests(_CompanionOpeningCase):
    """A caster that authority refuses never reaches the world."""

    @covers_requirement(
        "companion-field-actions::unfit-casters-are-refused-with-stable-reasons"
    )
    @covers_requirement(
        "companion-field-actions::a-companion-s-field-cast-may-open-combat-under-the-commander-s-session"
    )
    def test_a_forged_caster_is_refused_before_any_session_or_clock_access(self):
        outsider = self._outsider()
        with (
            patch("world.rules.combat_initiation.read_world_clock") as read_clock,
            patch("world.rules.clock.get_world_clock") as get_clock,
        ):
            with self.assertRaises(PartyScopeError) as caught:
                initiate_field_combat(
                    outsider, _CAST, self.wolf, commander=self.commander
                )
            self.assertEqual(caught.exception.reason, REASON_NOT_PARTY_MEMBER)
            with self.assertRaises(PartyScopeError) as caught:
                # Without explicit commander context the caster itself must
                # resolve to a commander, and a non-party NPC never does.
                initiate_field_combat(outsider, _CAST, self.wolf)
            self.assertEqual(caught.exception.reason, REASON_NOT_PARTY_MEMBER)
        read_clock.assert_not_called()
        get_clock.assert_not_called()
        self.assertIsNone(read_session(self.commander))
        self.assertIsNone(read_session(outsider))
        self.assertEqual(self.aila.traits.mp.current, 20)

    @covers_requirement(
        "companion-field-actions::unfit-casters-are-refused-with-stable-reasons"
    )
    @covers_requirement(
        "companion-field-actions::a-companion-s-field-cast-may-open-combat-under-the-commander-s-session"
    )
    def test_an_absent_caster_is_refused_before_any_session(self):
        self.aila.location = self.elsewhere
        with self.assertRaises(PartyScopeError) as caught:
            cast_as_member(
                self.commander, int(self.aila.pk), _CAST, targets=[self.wolf]
            )
        self.assertEqual(caught.exception.reason, REASON_MEMBER_NOT_PRESENT)
        with self.assertRaises(PartyScopeError) as caught:
            initiate_field_combat(
                self.aila, _CAST, self.wolf, commander=self.commander
            )
        self.assertEqual(caught.exception.reason, REASON_MEMBER_NOT_PRESENT)
        self.assertIsNone(read_session(self.commander))
        self.assertEqual(self.aila.traits.mp.current, 20)

    @covers_requirement(
        "companion-field-actions::unfit-casters-are-refused-with-stable-reasons"
    )
    def test_a_knocked_out_caster_is_refused_before_any_session(self):
        self.aila.traits.hp.current = 1
        with self.assertRaises(PartyScopeError) as caught:
            cast_as_member(
                self.commander, int(self.aila.pk), _CAST, targets=[self.wolf]
            )
        self.assertEqual(caught.exception.reason, REASON_MEMBER_CANNOT_ACT)
        with self.assertRaises(PartyScopeError) as caught:
            initiate_field_combat(
                self.aila, _CAST, self.wolf, commander=self.commander
            )
        self.assertEqual(caught.exception.reason, REASON_MEMBER_CANNOT_ACT)
        self.assertIsNone(read_session(self.commander))
        self.assertEqual(self.aila.traits.mp.current, 20)

    @covers_requirement(
        "field-combat-initiation::a-companion-initiator-opens-the-commander-s-encounter"
    )
    def test_an_injected_failure_restores_both_dialogue_surfaces(self):
        commander_host = self._outsider("開場對話者")
        caster_host = self._outsider("同伴對話者")
        open_or_refresh_dialogue(self.commander, commander_host, "問候")
        open_or_refresh_dialogue(self.aila, caster_host, "問候")
        commander_dialogue = dict(self.commander.db.dialogue_session)
        caster_dialogue = dict(self.aila.db.dialogue_session)
        with (
            patch(
                "world.rules.combat_initiation.submit_opening_action",
                side_effect=RuntimeError("injected opening failure"),
            ),
            patch.dict(_BATTLEFIELDS, {}, clear=True),
            self.assertRaises(RuntimeError),
        ):
            initiate_field_combat(
                self.aila, _CAST, self.wolf, commander=self.commander
            )
        self.assertIsNone(read_session(self.commander))
        self.assertIsNone(read_session(self.aila))
        self.assertEqual(
            dict(self.commander.db.dialogue_session), commander_dialogue
        )
        self.assertEqual(dict(self.aila.db.dialogue_session), caster_dialogue)
        self.assertEqual(self.aila.traits.mp.current, 20)
        self.assertFalse(self.aila.db.skill_proficiency)
        self.assertEqual(read_world_clock().tick, 0)
        self.assertEqual(_BATTLEFIELDS, {})


class CompanionOpeningPreviewTests(_CompanionOpeningCase):
    """A companion's preview offers exactly what the initiation accepts."""

    def test_preview_accepts_what_the_initiation_accepts(self):
        preview = preview_field_opening(
            self.aila, _CAST, self.wolf, commander=self.commander
        )
        self.assertTrue(preview.enabled)
        self.assertEqual(preview.targets, (self.wolf,))
        self.assertIsNone(preview.party_reason)
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            result = initiate_field_combat(
                self.aila, _CAST, self.wolf, commander=self.commander
            )
        self.assertNotEqual(result["outcome"], "rejected")

    def test_preview_disables_what_the_initiation_rejects(self):
        self.aila.traits.mp.current = 0
        preview = preview_field_opening(
            self.aila, _CAST, self.wolf, commander=self.commander
        )
        self.assertFalse(preview.enabled)
        self.assertEqual(preview.reason, RejectReason.INSUFFICIENT_RESOURCE)
        result = initiate_field_combat(
            self.aila, _CAST, self.wolf, commander=self.commander
        )
        self.assertEqual(result["outcome"], "rejected")
        self.assertEqual(result["reason"], RejectReason.INSUFFICIENT_RESOURCE)
        self.assertIsNone(read_session(self.commander))

    def test_preview_reports_a_party_refusal_without_raising(self):
        outsider = self._outsider()
        preview = preview_field_opening(
            outsider, _CAST, self.wolf, commander=self.commander
        )
        self.assertFalse(preview.enabled)
        self.assertIsNone(preview.reason)
        self.assertEqual(preview.party_reason, REASON_NOT_PARTY_MEMBER)
        self.aila.location = self.elsewhere
        preview = preview_field_opening(
            self.aila, _CAST, self.wolf, commander=self.commander
        )
        self.assertFalse(preview.enabled)
        self.assertEqual(preview.party_reason, REASON_MEMBER_NOT_PRESENT)


class PossessedOpeningCommandTests(_CompanionOpeningCase):
    """The possessed player keeps operating the commander's session."""

    @covers_requirement(
        "companion-field-actions::a-companion-s-field-cast-may-open-combat-under-the-commander-s-session"
    )
    def test_the_possessed_puppet_reads_its_commander_s_session(self):
        enter_possession(self.commander, self.aila)
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            initiate_field_combat(self.aila, _CAST, self.wolf)
        self.assertIs(session_owner(self.aila), self.commander)
        self.assertIs(session_owner(self.commander), self.commander)
        # The remaining members confirm through the puppet's own commands.
        for actor_token in ("a1", "a3"):
            command = CmdCombatCommand()
            command.caller = self.aila
            command.args = f"{actor_token} skill {BASIC_ATTACK_KEY}=e1"
            battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
            with battlefield_roll, damage_roll, rounds_roll:
                command.func()
        record = read_session(self.commander)
        self.assertIsNotNone(record)
        self.assertEqual(record.rounds_elapsed, 1)
        self.assertEqual(self.aila.traits.mp.current, 20 - _SPELL_COST_MP)

    def test_an_ordinary_possessed_cast_stays_the_puppet_s_own_entry(self):
        enter_possession(self.commander, self.aila)
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            initiate_field_combat(self.aila, _CAST, self.wolf)
        command = CmdCast()
        command.caller = self.aila
        command.args = f"{BASIC_ATTACK_KEY}=e1"
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            command.func()
        record = read_session(self.commander)
        # The puppet replaces its own entry; the commander never selects.
        self.assertEqual(
            record.draft_entries[int(self.aila.pk)]["payload"]["skill_key"],
            BASIC_ATTACK_KEY,
        )
        self.assertNotIn(int(self.commander.pk), record.draft_entries)

    def test_the_possessed_puppet_keeps_its_member_selection(self):
        from types import SimpleNamespace

        from web.webclient.presentation.party_actor_selection import (
            PartyActorSelection,
            party_actor_selection_snapshot,
        )

        enter_possession(self.commander, self.aila)
        battlefield_roll, damage_roll, rounds_roll = self._durable_rolls()
        with battlefield_roll, damage_roll, rounds_roll:
            initiate_field_combat(self.aila, _CAST, self.wolf)
        record = read_session(self.commander)
        # The puppet owns the presentation selection; the combat session it is
        # validated against belongs to the commander it operates.
        self.session.ndb.elosern_coordinator = SimpleNamespace(epoch="epoch-1")
        self.session.ndb.party_actor_selection = PartyActorSelection(
            int(self.aila.pk),
            "epoch-1",
            record.session_id,
            record.round_revision,
            int(self.kahn.pk),
        )
        self.assertEqual(
            party_actor_selection_snapshot(self.session, self.aila),
            int(self.kahn.pk),
        )
        self.assertIsNone(party_actor_selection_snapshot(self.session, self.commander))
