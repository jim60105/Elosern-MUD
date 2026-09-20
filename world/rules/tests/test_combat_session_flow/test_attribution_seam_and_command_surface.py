"""Slice of ``test_combat_session_flow``: commanded-action attribution,
the round-settlement seam, and the session command surface.
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
    _T_SEAM_CASCADE,
    _open_scope,
)


class CommandedActionAttributionTests(BattlefieldIsolation, EvenniaTestCase):
    """overwhelm-log-attribution under the opening seam: the compressed log of
    a player-overwhelming session opened through ``submit_opening_action()``
    marks the player's commanded skill exactly once and keeps that attack's
    own roll line, so the marker can never be misread as a different action.
    (combat-session-opening-dispatch 5.7/5.12: compression is now reachable
    only through the opening seam, so the attribution contract is driven
    there.)"""

    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room = create_object(Room, key="attribution arena")
        self.player = _player("attribution player")
        self.player.location = self.room
        grant_lineage(self.player, [_T_CAST])
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        self.monster = _monster("attribution goblin", hp=100)
        self.monster.location = self.room

    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    @covers_requirement("player-combat-session::submit-opening-action-is-the-sole-compression-dispatcher-and-always-grants-the-player-first-strike")
    def test_compressed_opening_marks_commanded_skill_once_with_attributable_rolls(self):
        engage(self.player, self.monster)
        with patch("world.rules.combat.battlefield.roll_d100", return_value=44), patch("world.rules.combat.damage.roll_d100", return_value=44), patch("world.rules.combat.rounds.roll_d100", return_value=44):
            result = submit_opening_action(self.player, _T_CAST, [self.monster])
        self.assertEqual(result["outcome"], "victory")
        # Exactly one first-round commanded_action marker, kind skill, the
        # submitted key's label, attached to the player's own cast log.
        markers = [
            entry
            for log in result["logs"]
            for entry in log.entries
            if entry.kind == "commanded_action"
        ]
        self.assertEqual(len(markers), 1)
        self.assertEqual(markers[0].actor, str(self.player.key))
        self.assertEqual(markers[0].data, {"skill": SYNTH_SKILLS[_T_CAST].label})
        opening_logs = [
            render_plain_text(log)
            for log in result["logs"]
            if log.actor == str(self.player.key)
            and log.skill_key == _T_CAST
        ]
        self.assertEqual(len(opening_logs), 1)
        opening_lines = opening_logs[0].splitlines()
        # The marker prefixes the action's own roll line, which stays
        # immediately before the damage it describes.
        self.assertEqual(opening_lines[0], f"你施展了「{SYNTH_SKILLS[_T_CAST].label}」。")
        self.assertEqual(
            opening_lines[1],
            f"{self.player.key} 對 {self.monster.key} 的攻擊擲出了 44。",
        )
        self.assertTrue(
            opening_lines[2].startswith(
                f"{self.player.key} 對 {self.monster.key} 造成了 "
            )
        )


class RoundSettlementSeamTests(BattlefieldIsolation, EvenniaTestCase):
    """Cross-cutting regression tests for the shared round seam (task 3.2).

    One session flow exercises every seam phase in order -- a preflight
    rejection (no round), a reverse-overwhelm ordinary round, a friendly-fire
    penalty rollback on a failed terminal settlement, and the terminal
    settlement itself -- so later changes to ``submit_player_action``/
    ``settle_session`` cannot silently break the shared outer transaction.
    """

    def setUp(self):
        _open_scope(self, monster_tiers=False)
        super().setUp()
        register_catalog()
        # ANY-faction synthetic area skill (zero cost, so the deliberately
        # weak seam caster can still pay for it).
        self.room = create_object(Room, key="seam arena")
        self.player = _player("seam player")
        self.player.location = self.room
        self.player.db.skills = {
            "active": [_T_SEAM_CASCADE.key],
            "passive": [],
        }
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 2
        self.player.traits.hp.base = 390
        self.player.traits.hp.current = 390
        self.companion = create_object(NPC, key="誤傷夥伴", location=self.room)
        self.companion.race = _race_key()
        self.companion.apply_race_baseline()
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.companion.traits, key).base = 2
        self.companion.traits.hp.base = 100
        self.companion.traits.hp.current = 100
        join_party(self.companion, self.player)
        from world.rules.affinity import AffinitySource, apply_affinity_change

        apply_affinity_change(
            self.companion, self.player, AffinitySource.QUEST_COMPLETION, 10
        )
        # Foe team overwhelming by the power-ratio rule alone (>= 100x):
        # power = stat sum x hp = (200+30+100) x 1300 = 429000 vs player team
        # 3920, with a <= 5-round estimate (198 base damage at a 0.78 hit
        # rate). Monster magic_power is a static trait pinned to the (0, 0)
        # band, so the
        # attack/agility/defense carry the power. The monster's d100 margin
        # (77) stays below the critical threshold: its solid hit lands for
        # 298 damage, flooring the companion but leaving the player standing.
        self.monster = create_object(Monster, key="seam goblin")
        self.monster.threat_tier = "low"
        self.monster.apply_monster_tier("floor")
        for key, value in {
            "atk_phys": 200,
            "agility": 30,
            "defense": 100,
        }.items():
            getattr(self.monster.traits, key).base = value
        self.monster.traits.hp.base = 1300
        self.monster.traits.hp.current = 1300
        self.monster.location = self.room

    def tearDown(self):

        super().tearDown()

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_one_session_flow_covers_all_seam_phases(self):
        engage(self.player, self.monster)
        from world.rules.overwhelm import classify_overwhelm

        # Reverse overwhelm: the FOE team is the overwhelming one, so the
        # player's action runs one ordinary round, never the compression.
        self.assertEqual(
            classify_overwhelm(
                reconstruct_battlefield(self.player, read_session(self.player))
            ),
            "foes",
        )
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            # 1. A preflight rejection consumes no round and no world time.
            result = submit_player_action(
                self.player, "no_such_skill", [self.monster]
            )
            self.assertEqual(result["outcome"], "rejected")
            self.assertEqual(read_session(self.player).rounds_elapsed, 0)
            self.assertEqual(clock.tick, 0)
            self.assertEqual(self.monster.traits.hp.current, 1300)

            # 2. The reverse-overwhelm action drives one ordinary round: the
            #    monster's solid hit floors the companion nonlethally, and
            #    the player's area attack hits both the monster and the
            #    companion, so the friendly-fire penalty applies (-1 per hit)
            #    inside the seam.
            with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch("world.rules.combat.damage.roll_d100", return_value=100), patch("world.rules.combat.rounds.roll_d100", return_value=100):
                result = submit_player_action(
                    self.player,
                    _T_SEAM_CASCADE.key,
                    [self.monster, self.companion],
                )
            self.assertEqual(result["outcome"], "round")
            self.assertEqual(read_session(self.player).rounds_elapsed, 1)
            self.assertEqual(clock.tick, 0)
            self.assertEqual(
                self.companion.relations.affinity_for(self.player), 9
            )
            self.assertEqual(self.player.traits.hp.current, 390)
            self.assertEqual(self.companion.traits.hp.current, 1)

            # 3. A terminal settlement failure rolls the round back,
            #    including the fresh friendly-fire penalty (party/relations
            #    surfaces are restored with the round). The player's attack
            #    kills the pinned monster, so the settlement step runs and
            #    fails; the monster is held from fleeing so the round stays
            #    on the kill path.
            self.monster.traits.hp.current = 1
            with (
                patch("world.rules.combat.battlefield.roll_d100", return_value=100),
                patch("world.rules.combat.damage.roll_d100", return_value=100),
                patch("world.rules.combat.rounds.roll_d100", return_value=100),
                patch(
                    "world.rules.combat_session.settlement.settle_combat_result",
                    side_effect=RuntimeError("clock write failed"),
                ),
                patch(
                    "world.rules.monster_behaviour._should_flee",
                    return_value=False,
                ),
            ):
                with self.assertRaises(RuntimeError):
                    submit_player_action(
                        self.player,
                        _T_SEAM_CASCADE.key,
                        [self.monster, self.companion],
                    )
            self.assertEqual(read_session(self.player).rounds_elapsed, 1)
            self.assertEqual(clock.tick, 0)
            self.assertEqual(self.monster.traits.hp.current, 1)
            self.assertEqual(
                self.companion.relations.affinity_for(self.player), 9
            )
            self.assertEqual(self.player.traits.hp.current, 390)

            # 4. A player-defeat round settles exactly once and clears the
            #    session: the monster's solid hit floors the weakened player
            #    on its initiative turn. Both elapsed rounds settle (12 s).
            self.player.traits.hp.current = 40
            settled: list[int] = []
            from world.rules.combat_session import settle_combat_result as real_settle

            def spy(result_, entities_):
                settled.append(result_.total_seconds)
                return real_settle(result_, entities_)

            with (
                patch("world.rules.combat.battlefield.roll_d100", return_value=100),
                patch("world.rules.combat.damage.roll_d100", return_value=100),
                patch("world.rules.combat.rounds.roll_d100", return_value=100),
                patch(
                    "world.rules.monster_behaviour._should_flee",
                    return_value=False,
                ),
                patch(
                    "world.rules.combat_session.settlement.settle_combat_result",
                    side_effect=spy,
                ),
            ):
                result = submit_player_action(
                    self.player,
                    _T_SEAM_CASCADE.key,
                    [self.monster, self.companion],
                )
            self.assertEqual(result["outcome"], "defeat")
            # The round-time settlement ran exactly once for exactly 12 s.
            # The defeat aftermath's recovery advance (defeat-aftermath-
            # recovery) is a further, separately priced advance, so the
            # final tick is the 12 s settle plus that fixture-priced window.
            self.assertEqual(settled, [12])
            self.assertGreaterEqual(clock.tick, 12)
            self.assertIsNone(self.player.db.active_combat)
            self.assertFalse(is_in_active_session(self.player))


class CommandSessionTests(BattlefieldIsolation, QuestRegistryIsolation, EvenniaCommandTestMixin, EvenniaTest):
    def setUp(self):
        _open_scope(self)
        super().setUp()
        self.room1 = create_object(Room, key="cmd arena")
        self.char1.location = self.room1
        self.char1.race = _race_key()
        self.char1.apply_race_baseline()
        self.monster = _monster("cmd goblin")
        self.monster.location = self.room1

    @covers_requirement("world-clock::cmdcast-advances-command-time-only-outside-a-persistent-combat-session")
    def test_active_session_cast_does_not_advance_command_time(self):
        from world.rules.combat_session import engage

        grant_lineage(self.char1, [_T_CAST])
        engage(self.char1, self.monster)
        clock = WorldClock()
        with patch("world.rules.cast_settlement.get_world_clock", return_value=clock):
            self.call(CmdCast(), f"{_T_CAST}=cmd goblin", None)
        self.assertEqual(clock.tick, 0)
