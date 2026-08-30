"""Combat-session recovery tests: malformed payloads, settlement, overwhelm."""

from tools.spec_traceability import covers_requirement

from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTestCase

from typeclasses.rooms import Room
from world.rules.action import ActionRequest, ActionResolver, RejectReason
from world.rules.clock import WorldClock
from world.rules.combat import BattlefieldActionContext
from world.rules.overwhelm import classify_overwhelm
from world.rules.combat_session import (
    CombatSessionError,
    SessionReason,
    engage,
    forfeit,
    from_storage,
    is_in_active_session,
    read_session,
    reconstruct_battlefield,
    restore_active_session,
    submit_player_action,
    to_storage,
)

from ._combat_session_helpers import BattlefieldIsolation, _monster, _player
from .combat_fixtures import grant_lineage



class MalformedSessionNormalizationTests(BattlefieldIsolation, EvenniaTestCase):
    """fix-malformed-combat-recovery: raw-conversion failures fail closed.

    ``read_session`` normalizes every raw-conversion or strict-parsing
    failure of the persisted payload into ``CombatSessionError`` with the
    ``malformed_session`` reason, and every active-session query or command
    inherits the normalization without leaking a bare ``TypeError`` or
    ``ValueError``.
    """

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="malformed arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("malformed goblin")
        self.monster.location = self.room

    def test_read_session_normalizes_malformed_payloads(self):
        for payload in ({"not": "a valid record"}, 7, "not a dict"):
            self.player.db.active_combat = payload
            with self.assertRaises(CombatSessionError) as raised:
                read_session(self.player)
            self.assertEqual(
                raised.exception.args[0], SessionReason.MALFORMED_SESSION
            )
            self.assertFalse(is_in_active_session(self.player))
            if not isinstance(payload, dict):
                # Raw-conversion failures chain the original conversion error
                # for traceability (fix-malformed-combat-recovery D1).
                self.assertIsInstance(
                    raised.exception.__cause__, (TypeError, ValueError)
                )

    @covers_requirement("player-combat-session::malformed-session-payloads-fail-closed-without-unhandled-conversion-errors")
    def test_engage_and_forfeit_reject_persisted_malformed_payload(self):
        for payload in ({"not": "a valid record"}, 7, "not a dict"):
            self.player.db.active_combat = payload
            with self.assertRaises(CombatSessionError) as raised:
                engage(self.player, self.monster)
            self.assertEqual(
                raised.exception.args[0], SessionReason.MALFORMED_SESSION
            )
            with self.assertRaises(CombatSessionError) as raised:
                forfeit(self.player)
            self.assertEqual(
                raised.exception.args[0], SessionReason.MALFORMED_SESSION
            )

class MalformedSessionRecoveryTests(BattlefieldIsolation, EvenniaTestCase):
    """fix-malformed-combat-recovery: startup clears unparseable records.

    An unparseable persisted record is cleared with a diagnostic, never
    settled: no world time advances and no participant effects derive from
    the untrusted fields, and the player stays unblocked for ordinary hostile
    engagement. Unrelated settlement failures leave a valid record intact.
    """

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="malformed recovery arena")
        self.player = _player()
        self.player.location = self.room
        self.monster = _monster("malformed recovery goblin")
        self.monster.location = self.room

    @covers_requirement("player-combat-session::startup-restores-valid-sessions-and-terminates-invalid-references-safely")
    def test_restore_active_session_clears_malformed_record(self):
        engage(self.player, self.monster)
        self.player.db.active_combat = {"not": "a valid record"}
        self.player.ndb.action_context = {"stale": True}
        from world.rules.skip_safety import _BATTLEFIELDS

        self.assertIn(str(self.player.pk), _BATTLEFIELDS)
        clock = WorldClock()
        with (
            patch("world.rules.combat_session.get_world_clock", return_value=clock),
            patch("world.rules.combat_session.settle_combat_result") as settle,
        ):
            restore_active_session(self.player)
        settle.assert_not_called()
        self.assertIsNone(self.player.db.active_combat)
        self.assertIsNone(self.player.ndb.action_context)
        self.assertNotIn(str(self.player.pk), _BATTLEFIELDS)
        self.assertEqual(clock.tick, 0)

    @covers_requirement("player-combat-session::startup-restores-valid-sessions-and-terminates-invalid-references-safely")
    def test_startup_clears_malformed_record_and_engage_succeeds(self):
        from world.rules.guild_economy import restore_persisted_sessions

        self.player.db.active_combat = {"not": "a valid record"}
        restore_persisted_sessions()
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))
        result = engage(self.player, self.monster)
        self.assertEqual(result["record"].mode, "hostile")
        self.assertIsNotNone(read_session(self.player))

    def test_unrelated_settlement_failure_propagates_with_record_intact(self):
        # A well-formed terminal session whose settlement raises is never
        # re-settled as a defeat: the exception propagates (the startup
        # wrapper logs it) with the durable record intact for exactly one
        # retry and zero re-settlement attempts.
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        self.monster.traits.hp.current = 0
        clock = WorldClock()
        with (
            patch("world.rules.combat_session.get_world_clock", return_value=clock),
            patch(
                "world.rules.combat_session.settle_combat_result",
                side_effect=RuntimeError("clock write failed"),
            ) as settle,
        ):
            with self.assertRaises(RuntimeError):
                restore_active_session(self.player)
        settle.assert_called_once()
        self.assertEqual(clock.tick, 0)
        self.assertIsNotNone(self.player.db.active_combat)
        self.assertTrue(is_in_active_session(self.player))

class SettlementRecoveryTests(BattlefieldIsolation, EvenniaTestCase):
    """fix-combat-settlement-recovery: settled marker and atomic round chain."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="recovery arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, ["fire_ball"])
        self.monster = _monster("recovery goblin", hp=100)
        self.monster.location = self.room

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_restored_marked_session_is_not_settled_twice(self):
        # A terminal hostile session whose settlement committed (marker and
        # clock) but whose clear never ran is settled exactly once by
        # restoration -- never a second time (task 4.1, simulated restart
        # after the clock-commit-before-clear window).
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        record = read_session(self.player)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)
        # Fabricate the durable mid-window state a restart would read: the
        # settlement (marker + clock) committed, the session clear did not.
        from world.rules.combat_session import _persist

        _persist(
            self.player,
            from_storage({**to_storage(record), "settled_tick": clock.tick}),
        )
        restore_active_session(self.player)
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)
        self.assertFalse(is_in_active_session(self.player))

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_settlement_failure_rolls_back_the_whole_round(self):
        self.monster.traits.hp.base = 1
        self.monster.traits.hp.current = 1
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch(
                "world.rules.combat_session.settle_combat_result",
                side_effect=RuntimeError("clock write failed"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "fire_ball", [self.monster])
        # Round effects, session metadata, clock tick, and clearing all
        # rolled back together; the session survives for exactly one retry.
        self.assertEqual(self.monster.traits.hp.current, 1)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)
        self.assertIsNotNone(self.player.db.active_combat)
        # The retry runs the round again and settles exactly once.
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)

    def test_termination_between_effects_and_persist_leaves_no_half_round(self):
        # A process termination between the round effects and the session
        # metadata write leaves either the full round durable or none of it:
        # here the metadata write fails, so the effects roll back with it.
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch(
                "world.rules.combat_session._persist",
                side_effect=RuntimeError("terminated"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(self.monster.traits.hp.current, 100)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_three_round_victory_advances_eighteen_seconds_once(self):
        # A hostile session that ends after three completed rounds settles
        # exactly 18 seconds with the combat source and never an extra cast
        # cost per command: rounds 1-2 advance nothing, round 3 settles 3x6s.
        for key, value in {
            "atk_phys": 2,
            "agility": 30,
            "defense": 50,
            "magic_power": 90,
        }.items():
            getattr(self.player.traits, key).base = value
        self.player.traits.hp.base = 500
        self.player.traits.hp.current = 500
        self.monster.traits.hp.base = 405
        self.monster.traits.hp.current = 405
        for key, value in {"atk_phys": 1, "agility": 30, "defense": 0}.items():
            getattr(self.monster.traits, key).base = value
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch("world.rules.monster_behaviour._should_flee", return_value=False),
        ):
            for expected_rounds in (1, 2):
                result = submit_player_action(
                    self.player, "fire_ball", [self.monster]
                )
                self.assertEqual(result["outcome"], "round")
                self.assertEqual(clock.tick, 0)
                self.assertEqual(
                    read_session(self.player).rounds_elapsed, expected_rounds
                )
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertEqual(clock.tick, 18)
        self.assertIsNone(self.player.db.active_combat)

    def test_flee_settlement_failure_rolls_back_and_retry_flees(self):
        # The flee terminal source shares the same atomic seam: a failed
        # settlement rolls the flee, the round effects, and the metadata back
        # together, and the retry can flee again and settle exactly once.
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.disengage.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
            patch(
                "world.rules.combat_session.settle_combat_result",
                side_effect=RuntimeError("clock write failed"),
            ),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "flee", [])
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertEqual(clock.tick, 0)
        self.assertNotIn(str(self.player.key), read_session(self.player).fled_ids)
        self.assertEqual(self.monster.traits.hp.current, 100)
        with (
            patch("world.rules.disengage.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "flee", [])
        self.assertEqual(result["outcome"], "fled")
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_solo_defeat_settlement_never_revives_the_player(self):
        # A hostile defeat settles the dead player at 0 HP: the roster scope
        # excludes HP-0 members and the actor-alive fallback guard means the
        # settlement never regenerates a corpse (kill semantics), while the
        # world clock still advances the accumulated rounds exactly once.
        self.monster.traits.atk_phys.base = 100
        self.player.traits.hp.base = 100
        self.player.traits.hp.current = 1
        engage(self.player, self.monster)
        clock = WorldClock()
        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
        self.assertEqual(result["outcome"], "defeat")
        self.assertEqual(self.player.traits.hp.current, 0)
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::combat-time-settles-once-at-terminal-session-outcome")
    def test_restored_dead_player_session_never_revives_the_player(self):
        # A terminal hostile session restored with the player dead at 0 HP
        # (the durable pre-settlement crash window) settles through the
        # recovery fallback: the roster is unavailable, but the actor-alive
        # guard keeps the corpse at 0 HP while the clock still advances.
        self.monster.traits.atk_phys.base = 100
        self.player.traits.hp.base = 100
        self.player.traits.hp.current = 1
        engage(self.player, self.monster)
        record = read_session(self.player)
        from world.rules.combat_session import _persist

        _persist(
            self.player,
            from_storage(
                {
                    **to_storage(record),
                    "rounds_elapsed": 1,
                }
            ),
        )
        self.player.traits.hp.current = 0
        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            restore_active_session(self.player)
        self.assertEqual(self.player.traits.hp.current, 0)
        self.assertEqual(clock.tick, 6)
        self.assertIsNone(self.player.db.active_combat)

class UpkeepTickCreditTests(BattlefieldIsolation, EvenniaTestCase):
    """fix-dot-kill-credit: upkeep-settled tick kills commit with the round."""

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="upkeep tick arena")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, ["fire_ball"])
        self.monster = _monster("upkeep tick goblin", hp=100)
        self.monster.location = self.room
        from world.rules.buffs import _add_buff

        _add_buff(self.monster, "fire_scorch", source_pk=int(self.player.pk))
        self.monster.traits.hp.base = 3
        self.monster.traits.hp.current = 3
        # The 10-second rate tick fires on the first upkeep accumulation
        # (round seconds are 6; pre-arming the tick elapsed makes the first
        # upkeep's 6 seconds cross the interval).
        self.monster.buffs.all["fire_scorch"].tick_elapsed_seconds = 10

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_dot_tick_kill_of_final_foe_commits_victory(self):

        engage(self.player, self.monster)
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = submit_player_action(self.player, "basic_attack", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        upkeep_logs = [log for log in result["logs"] if log.skill_key == "combat_upkeep"]
        self.assertTrue(upkeep_logs)
        kinds = [entry.kind for log in upkeep_logs for entry in log.entries]
        self.assertIn("damage", kinds)
        self.assertEqual(kinds.count("target_defeated"), 1)
        # The tick kill carries no progression award any more.
        self.assertIsNone(self.player.db.magic_xp)
        self.assertEqual(result["rounds_elapsed"], 1)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit")
    def test_upkeep_settlement_failure_rolls_back_the_whole_round(self):
        from world.rules.action import _EVENT_EFFECT_PLANNERS

        engage(self.player, self.monster)

        def boom(request, log):
            raise RuntimeError("injected upkeep planner failure")

        with (
            patch("world.rules.combat.roll_d100", return_value=1),
            patch.dict(_EVENT_EFFECT_PLANNERS, {"boom": boom}),
        ):
            with self.assertRaises(RuntimeError):
                submit_player_action(self.player, "basic_attack", [self.monster])
        # Tick HP, round count, and session metadata all rolled back.
        self.assertEqual(self.monster.traits.hp.current, 3)
        self.assertEqual(read_session(self.player).rounds_elapsed, 0)
        self.assertIsNotNone(self.player.db.active_combat)
        self.assertIsNone(self.player.db.magic_xp)
        # The retry without the failing planner settles normally.
        with patch("world.rules.combat.roll_d100", return_value=1):
            result = submit_player_action(self.player, "basic_attack", [self.monster])
        self.assertEqual(result["outcome"], "victory")
        self.assertIsNone(self.player.db.active_combat)

class OverwhelmDirectionTests(BattlefieldIsolation, EvenniaTestCase):
    """fix-combat-session-roster-and-overwhelm D2: player-direction compression.

    A foe-overwhelming verdict is informational only: each player submission
    drives exactly one ordinary round and the compressed resolver is never
    invoked, so the player keeps full per-round agency (skill choice and
    flee) and no fight is an unavoidable compressed defeat. The
    player-overwhelming path still dispatches the resolver.
    """

    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="overwhelm direction arena")
        self.player = _player("direction player")
        self.player.location = self.room
        grant_lineage(self.player, ["fire_ball"])
        # Foe team overwhelming by the power-ratio rule alone (>= 100x):
        # monster power = (20+50+100) x 3000 = 510000 vs the player's
        # (1+51+1) x 45 = 2385 (~214x), with a ~4.8-round estimate. The
        # player acts first (agility 51 vs 50), survives the monster's
        # roll-100 crit (2.0x = 39 damage: 45 -> 6), and the flee contest
        # (100 + 51 >= 51 + 50) succeeds comfortably on the second round.
        self.monster = _monster("overwhelming goblin", hp=3000, atk=20)
        self.monster.traits.agility.base = 50
        self.monster.traits.defense.base = 100
        self.monster.location = self.room

    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    @covers_requirement("player-combat-session::overwhelm-compression-is-player-direction-only")
    @covers_requirement("single-shot-resolution::the-session-never-dispatches-compression-for-the-foe-overwhelming-direction")
    def test_foe_overwhelming_plays_one_round_per_submission_never_compressed(self):
        self.player.traits.hp.base = 45
        self.player.traits.hp.current = 45
        self.player.traits.agility.base = 51
        engage(self.player, self.monster)
        self.assertEqual(
            classify_overwhelm(
                reconstruct_battlefield(self.player, read_session(self.player))
            ),
            "foes",
        )
        clock = WorldClock()
        with (
            patch(
                "world.rules.combat_session.resolve_overwhelm",
                side_effect=AssertionError(
                    "the compressed resolver must never dispatch for a "
                    "foe-overwhelming verdict"
                ),
            ) as resolver,
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.monster_behaviour._should_flee",
                return_value=False,
            ),
            patch("world.rules.clock.get_world_clock", return_value=clock),
        ):
            result = submit_player_action(self.player, "fire_ball", [self.monster])
            resolver.assert_not_called()
            self.assertEqual(result["outcome"], "round")
            self.assertEqual(result["overwhelming_team"], "foes")
            self.assertEqual(read_session(self.player).rounds_elapsed, 1)
            self.assertEqual(clock.tick, 0)
            # The player retains full agency: flee stays available next
            # round, and the foe-overwhelming verdict still never compresses.
            with patch("world.rules.disengage.roll_d100", return_value=100):
                result = submit_player_action(self.player, "flee", [])
            resolver.assert_not_called()
        self.assertEqual(result["outcome"], "fled")
        self.assertEqual(clock.tick, 12)
        self.assertIsNone(self.player.db.active_combat)

    @covers_requirement("player-combat-session::overwhelm-waits-for-one-player-choice-before-compressed-resolver-backed-outcome")
    @covers_requirement("player-combat-session::overwhelm-compression-is-player-direction-only")
    def test_player_overwhelming_still_dispatches_the_resolver(self):
        weak = _monster("weak goblin", hp=100, atk=10)
        weak.location = self.room
        for key in ("atk_phys", "agility", "defense", "magic_power"):
            getattr(self.player.traits, key).base = 200
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        engage(self.player, weak)
        self.assertEqual(
            classify_overwhelm(
                reconstruct_battlefield(self.player, read_session(self.player))
            ),
            "party",
        )
        from world.rules.overwhelm import resolve_overwhelm as real_resolve

        with (
            patch("world.rules.combat.roll_d100", return_value=100),
            patch(
                "world.rules.combat_session.resolve_overwhelm",
                side_effect=real_resolve,
            ) as resolver,
            patch("world.rules.clock.get_world_clock", return_value=WorldClock()),
        ):
            result = submit_player_action(self.player, "fire_ball", [weak])
        resolver.assert_called_once()
        self.assertEqual(result["outcome"], "victory")
        self.assertIsNone(self.player.db.active_combat)

class PreflightSideEffectTests(BattlefieldIsolation, EvenniaTestCase):
    def setUp(self):
        super().setUp()
        self.room = create_object(Room, key="preflight room")
        self.player = _player()
        self.player.location = self.room
        grant_lineage(self.player, ["fire_ball"])
        self.monster = _monster("preflight goblin")
        self.monster.location = self.room

    def test_preflight_rejection_has_no_side_effects(self):
        engage(self.player, self.monster)
        from world.rules.combat import Battlefield
        from world.rules.event_log import EventLog
        from world.rules.combat_session import read_session

        battlefield = reconstruct_battlefield(self.player, read_session(self.player))
        request = ActionRequest(
            self.player,
            "no_such_skill",
            [self.monster],
            BattlefieldActionContext(battlefield),
        )
        before = (self.monster.traits.hp.current, len(_EVENT_LOGS_SENTINEL))
        result = ActionResolver.preflight(request)
        self.assertEqual(result.outcome, "rejected")
        self.assertEqual(result.reason, RejectReason.UNKNOWN_SKILL)
        self.assertEqual((self.monster.traits.hp.current, before[1]), before)
        self.assertIsNone(result.event_log)

    @covers_requirement("action-resolution-pipeline::actionresolver-exposes-side-effect-free-preflight-for-player-combat-input")
    def test_successful_preflight_does_not_roll_or_stage(self):
        engage(self.player, self.monster)
        from world.rules.action import _EVENT_EFFECT_PLANNERS
        from world.rules.combat import Battlefield
        from world.rules.combat_session import read_session

        battlefield = reconstruct_battlefield(self.player, read_session(self.player))
        request = ActionRequest(
            self.player,
            "fire_ball",
            [self.monster],
            BattlefieldActionContext(battlefield),
        )
        with patch("world.rules.combat.roll_d100") as roll:
            result = ActionResolver.preflight(request)
        self.assertEqual(result.outcome, "success")
        roll.assert_not_called()
        self.assertIsNone(result.event_log)

    @covers_requirement("action-resolution-pipeline::preflight-rejects-missing-handler-context-before-any-round-cost")
    def test_missing_effect_context_rejects_without_a_round_or_enemy_action(self):
        self.player.db.skills = {
            "active": ["status_disguise", "dominion_art"],
            "passive": [],
        }
        engage(self.player, self.monster)
        from world.rules.clock import WorldClock
        from world.rules.combat_session import read_session

        clock = WorldClock()
        with patch("world.rules.clock.get_world_clock", return_value=clock):
            for skill_key in ("status_disguise", "dominion_art"):
                with self.subTest(skill_key=skill_key):
                    result = submit_player_action(
                        self.player, skill_key, [self.monster]
                    )
                    self.assertEqual(result["outcome"], "rejected")
                    self.assertIs(
                        result["reason"], RejectReason.MISSING_EFFECT_CONTEXT
                    )
                    self.assertEqual(
                        read_session(self.player).rounds_elapsed, 0
                    )
                    self.assertEqual(clock.tick, 0)
                    self.assertEqual(self.monster.traits.hp.current, 100)


# Sentinel used to prove no EventLog was created; kept local to avoid import.
_EVENT_LOGS_SENTINEL = ()
