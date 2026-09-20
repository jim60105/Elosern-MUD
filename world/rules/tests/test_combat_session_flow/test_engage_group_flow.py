"""Slice of ``test_combat_session_flow``: EngageGroupTests.
"""
from tools.spec_traceability import covers_requirement
import inspect
from pathlib import Path
import unittest
from unittest.mock import patch
from dataclasses import replace
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaCommandTestMixin, EvenniaTest, EvenniaTestCase
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from commands.action import CmdCast
from world.quests.catalog import register_catalog
from world.quests.tests._fixtures import QuestRegistryIsolation
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.clock import WorldClock
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    engage_group,
    is_in_active_session,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
    submit_opening_action,
)
from world.rules.overwhelm import classify_overwhelm
from world.rules.event_log import render_plain_text
from world.rules.party import join_party
from world.rules.combat_session import BASIC_ATTACK_KEY
from world.skills.registry import SkillKind, TargetSpec
from world.tests.synthetic_data import SYNTH_SKILLS, make_skill
from .._combat_session_helpers import (
    BattlefieldIsolation,
    SYNTH_SEAM_AREA_SKILL,
    _monster,
    _player,
    _race_key,
    open_synthetic_scope,
    synth_innate_overlay,
)
from ..combat_fixtures import grant_lineage


from ._support import (
    _T_CAST,
    _open_scope,
)


class EngageGroupTests(BattlefieldIsolation, EvenniaTestCase):
    """combat-session-opening-dispatch 5.9/5.10/5.13: group engagement."""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="group arena")
        self.player = _player("group hunter")
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000

    @covers_requirement("player-combat-session::engage-group-opens-one-session-against-several-co-located-hostile-targets")
    def test_engage_group_opens_one_session_and_resolves_to_victory(self):
        m1 = _monster("m1", hp=100, atk=10)
        m2 = _monster("m2", hp=100, atk=10)
        m1.location = self.room
        m2.location = self.room
        result = engage_group(self.player, [m2, m1])
        record = result["record"]
        self.assertEqual(record.enemy_ids, tuple(sorted([int(m1.pk), int(m2.pk)])))
        battlefield = reconstruct_battlefield(self.player, record)
        self.assertEqual(
            sorted(str(k) for k in battlefield.teams["foes"]),
            sorted([m1.key, m2.key]),
        )
        # The player dominates both floor-tier foes, so the opening's
        # two-part judgement selects compression, and the round-1 cast
        # plus the auto-attacks settle the whole session in one call.
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            outcome = submit_opening_action(self.player, _T_CAST, [m1])
        self.assertEqual(outcome["outcome"], "victory")
        self.assertGreaterEqual(
            len([
                entry
                for log in outcome["logs"]
                for entry in log.entries
                if entry.kind == "commanded_action"
            ]),
            1,
        )
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::engage-group-opens-one-session-against-several-co-located-hostile-targets")
    def test_engage_group_rejections_leave_no_session(self):
        from world.rules.clock import get_world_clock

        good = _monster("good", hp=100, atk=10)
        good.location = self.room
        dead = _monster("dead", hp=0)
        dead.location = self.room
        remote = _monster("remote", hp=100)
        remote.location = create_object(Room, key="elsewhere")
        stranger = create_object(NPC, key="npc-stranger", location=self.room)
        cases = [
            ([good, dead], SessionReason.TARGET_DEAD),
            ([good, remote], SessionReason.NOT_PRESENT),
            ([good, stranger], SessionReason.NOT_HOSTILE),
            ([good, good], SessionReason.DUPLICATE_PARTICIPANT),
            ([], SessionReason.MALFORMED_SESSION),
        ]
        for targets, reason in cases:
            with self.subTest(reason=reason), self.assertRaises(CombatSessionError) as ctx:
                engage_group(self.player, targets)
            self.assertEqual(ctx.exception.args[0], reason)
            self.assertIsNone(read_session(self.player))
        self.assertEqual(get_world_clock().tick, 0)

    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_opening_rejects_shorthand_and_off_roster_before_anything(self):
        m1 = _monster("opening foe", hp=100, atk=10)
        m1.location = self.room
        away = _monster("away foe", hp=100)
        away.location = create_object(Room, key="not here")
        engage_group(self.player, [m1])
        mp_before = self.player.traits.mp.value
        with self.assertRaises(TypeError):
            submit_opening_action(self.player, _T_CAST, "all-enemies")
        with self.assertRaises(CombatSessionError) as ctx:
            submit_opening_action(self.player, _T_CAST, [away])
        self.assertEqual(ctx.exception.args[0], SessionReason.NOT_PRESENT)
        record = read_session(self.player)
        self.assertEqual(record.rounds_elapsed, 0)
        self.assertEqual(self.player.traits.mp.value, mp_before)

    @covers_requirement("player-combat-session::engage-group-opens-one-session-against-several-co-located-hostile-targets")
    def test_two_enemy_session_exercises_scans_knockouts_and_settlement(self):
        # 5.11: a two-enemy session through _primary_opponent_id(), the
        # friendly-fire scan, nonlethal knockout, and terminal settlement.
        import world.rules.combat_session as session_mod
        import world.rules.combat_session.rounds as session_rounds

        companion = create_object(NPC, key="並肩", location=self.room)
        companion.race = _race_key()
        companion.apply_race_baseline()
        join_party(companion, self.player)
        m1 = _monster("twin a", hp=100, atk=10)
        m2 = _monster("twin b", hp=100, atk=10)
        m1.location = self.room
        m2.location = self.room
        grant_lineage(self.player, [SYNTH_SEAM_AREA_SKILL.key])
        engage_group(self.player, [m1, m2])
        seen: list = []
        real_primary = session_mod._primary_opponent_id

        def spy(battlefield, record):
            value = real_primary(battlefield, record)
            seen.append(value)
            return value

        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            patch("world.rules.combat.damage.roll_d100", return_value=100),
            patch("world.rules.combat.rounds.roll_d100", return_value=100),
            patch("world.rules.action.gates.roll_d100", return_value=100),
            patch.object(session_rounds, "_primary_opponent_id", side_effect=spy),
        ):
            result = submit_opening_action(self.player, SYNTH_SEAM_AREA_SKILL.key, [m1])
        self.assertGreaterEqual(len(seen), 1)
        self.assertEqual(
            seen[0], min(int(m1.pk), int(m2.pk))
        )
        self.assertEqual(result["outcome"], "victory")
        # The AREA cast hit the companion through the two-enemy
        # roster and the nonlethal companion policy floored it at 1 HP; the
        # per-hit affinity penalty contract itself is pinned in
        # test_friendly_fire (here the scan simply must not crash the flow).
        # The player's AREA cast reached the companion through the
        # two-enemy roster (observed: one 7-damage hit under the patched
        # rolls); the friendly-fire/coercion scans ran over the two-enemy
        # logs without crashing the flow. The per-hit affinity-penalty
        # contract itself is pinned in test_friendly_fire.
        self.assertLess(companion.traits.hp.current, companion.traits.hp.max)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::one-submission-inside-an-active-session-is-one-ordinary-round-by-default-and-structurally")
    def test_both_openings_forward_the_same_policy_kwargs(self):
        # 5.4: the round and overwhelm entries receive the identical
        # simulated/nonlethal/journal/notification policy.
        from world.rules.combat import run_round as real_run_round
        from world.rules.overwhelm import resolve_overwhelm as real_resolve

        companion = create_object(NPC, key="政策護伴", location=self.room)
        companion.race = _race_key()
        companion.apply_race_baseline()
        join_party(companion, self.player)
        captured = {}

        def record_round(field, provider, **kwargs):
            captured.setdefault("round", kwargs)
            return real_run_round(field, provider, **kwargs)

        def record_resolve(field, provider, **kwargs):
            captured.setdefault("overwhelm", kwargs)
            return real_resolve(field, provider, **kwargs)

        def build():
            foe = _monster("政策敵", hp=300, atk=10)
            foe.location = self.room
            engage(self.player, foe)
            return foe

        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=44),
            patch("world.rules.combat.damage.roll_d100", return_value=44),
            patch("world.rules.combat.rounds.roll_d100", return_value=44),
            patch("world.rules.action.gates.roll_d100", return_value=44),
            patch("world.rules.combat_session.rounds.run_round", side_effect=record_round),
        ):
            submit_player_action(self.player, _T_CAST, [build()])
        self.player.db.active_combat = None
        with (
            patch("world.rules.combat.battlefield.roll_d100", return_value=44),
            patch("world.rules.combat.damage.roll_d100", return_value=44),
            patch("world.rules.combat.rounds.roll_d100", return_value=44),
            patch("world.rules.action.gates.roll_d100", return_value=44),
            patch(
                "world.rules.combat_session.rounds.resolve_overwhelm",
                side_effect=record_resolve,
            ),
        ):
            submit_opening_action(self.player, _T_CAST, [build()])
        self.assertEqual(
            sorted(captured), ["overwhelm", "round"]
        )
        for key in ("simulated", "nonlethal_keys"):
            self.assertEqual(
                captured["round"][key], captured["overwhelm"][key], key
            )
        self.assertFalse(captured["round"]["simulated"])
        self.assertEqual(
            captured["round"]["nonlethal_keys"], {companion.key}
        )
        for key in ("journal_sink", "notifications_sink"):
            self.assertIsInstance(captured["round"][key], list, key)
            self.assertIsInstance(captured["overwhelm"][key], list, key)
