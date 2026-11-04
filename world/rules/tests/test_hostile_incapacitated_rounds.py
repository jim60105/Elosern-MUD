"""Incapacitated hostile parties receive real paid enemy-only rounds.

Every test here drives the actual admission and ordinary-round consumer paths
(``engage_group``/``engage``, ``submit_player_action``, the text ``engage``
command and the browser ``explore.engage`` adapter), never a helper in
isolation, and asserts the durable paid-prefix cursor, real enemy actions and
upkeep, the authored wake threshold, terminal-only remainder billing, reload
equivalence and a late-failure retry.
"""

from __future__ import annotations

from dataclasses import replace
from unittest.mock import patch

from evennia.objects.models import ObjectDB
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase
from evennia.contrib.grid.wilderness.wilderness import (
    WildernessScript,
    create_wilderness,
    enter_wilderness,
)

from commands.combat import CmdEngage
from tools.spec_traceability import covers_requirement
from typeclasses.rooms import Room
from world.maps import monster_activity, regional_population
from world.maps.monster_activity import (
    MODE_COMBAT,
    create_group,
    group_of_member,
    read_monster_activity,
)
from world.maps.regional_population import initialize_population_seed
from world.maps.wilderness_provider import (
    WILDERNESS_NAME,
    ElosernWildernessMapProvider,
)
from world.rules.buffs import entity_active_buffs
from world.rules.clock import (
    AdvanceSource,
    WorldClock,
    get_world_clock,
    read_world_clock,
)
from world.rules.combat_identity import stable_actor_id
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    _round_cap,
    engage,
    engage_group,
    forfeit,
    get_required_combat_actors,
    is_in_active_session,
    read_session,
    reconstruct_battlefield,
    submit_player_action,
)
from world.rules.fatigue import (
    FatigueActivity,
    IntervalCompletion,
    SleepPosture,
    predict_interval,
    read_optional_fatigue_state,
    read_fatigue_state,
    write_fatigue_state,
)
from world.rules.monster_individual import construct_species_individual
from world.rules.movement_edges import LocationRef
from world.tests.geography_fixture import publish_shipped_map_world
from world.tests.synthetic_data import SYNTH_MONSTER_VARIANTS, synthetic_registries
from world.skills.registry import SkillCategory, TargetSpec
from world.tests.synthetic_data import make_skill

from ._combat_session_helpers import (
    BattlefieldIsolation,
    _monster,
    _player,
    open_synthetic_scope,
    synth_innate_overlay,
)
from .combat_fixtures import grant_lineage
from .test_combat_session_flow._support import _open_scope

del monster_activity, regional_population  # imported for the mapped fixture's side effects only

#: The real temporary blocking effect: the live rulebook's ``paralysis`` buff
#: (20 authored seconds, ``actions_per_turn: 0``) applied by a synthetic
#: self-target skill. The skill row is fixture data; submission, resolution,
#: buff commit and upkeep are the production path.
_SELF_PARALYSIS = make_skill(
    "t_self_paralysis",
    label="自縛雷印",
    description="以雷印鎖住自己的行動。",
    target_spec=TargetSpec.SELF,
    cost={},
    effects=["self_buff_apply:paralysis"],
    category=SkillCategory.ENHANCEMENT,
)

_PROBE = (500, 700)
_SEED = 11
_FULL_RESERVE = 360000


def _scope(test) -> None:
    """Enter the synthetic skill/registry scope this module's fixtures need."""
    _open_scope(test, **{_SELF_PARALYSIS.key: _SELF_PARALYSIS})


def _write(entity, reserve: int, posture: SleepPosture) -> None:
    from world.rules.fatigue import project_fatigue_status

    write_fatigue_state(entity, reserve, posture)
    project_fatigue_status(entity)


def _room(key: str) -> Room:
    return create_object(Room, key=key)


class PaidRoundTests(BattlefieldIsolation, EvenniaTestCase):
    """The real enemy-only round, threshold, suffix and control authority."""

    def setUp(self) -> None:
        _scope(self)
        super().setUp()
        self.room = _room("paid hostile arena")
        self.player = _player("paid hostile player")
        self.player.location = self.room
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        self.monster = _monster("paid hostile goblin", hp=1000, atk=10)
        self.monster.location = self.room

    def _record(self):
        return read_session(self.player)

    def _hold_round(self):
        """The real one-round confirmation (no compression)."""
        return submit_player_action(
            self.player, BASIC_ATTACK_KEY, [self.monster]
        )

    @covers_requirement(
        "player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits"
    )
    @covers_requirement(
        "player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds"
    )
    @covers_requirement("mental-reserve::posture-and-forced-sleep-hysteresis-are-body-scoped")
    def test_one_paid_round_reaches_the_threshold_and_returns_choice(self):
        from world.rules.fatigue import project_fatigue_status

        _write(self.player, 71928, SleepPosture.FORCED)
        tick_before = get_world_clock().tick
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch(
            "world.rules.combat.damage.roll_d100", return_value=100
        ), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = engage(self.player, self.monster)
        continuation = result["continuation"]
        self.assertEqual(continuation["outcome"], "round")
        self.assertEqual(continuation["continued_rounds"], 1)
        self.assertIsNotNone(self._record(), "a waking ally keeps the session")
        record = self._record()
        self.assertEqual((record.rounds_elapsed, record.settled_rounds), (1, 1))
        # One real six-second round: the enemy acted (its attack is in the
        # delivered round logs) and the clock paid exactly six seconds.
        self.assertEqual(get_world_clock().tick, tick_before + 6)
        self.assertTrue(
            any(
                entry.kind == "damage"
                for log in continuation["logs"]
                for entry in log.entries
            )
        )
        state = read_fatigue_state(self.player)
        self.assertEqual(state.reserve_units, 72000)
        self.assertIs(state.posture, SleepPosture.AWAKE)
        # Choice resumes immediately: the normal player command is accepted.
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch(
            "world.rules.combat.damage.roll_d100", return_value=100
        ), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            following = self._hold_round()
        self.assertIn(following["outcome"], ("round", "victory"))
        self.assertEqual(self._record().rounds_elapsed, 2)
        project_fatigue_status(self.player)

    @covers_requirement(
        "player-combat-session::combat-time-settles-once-at-terminal-session-outcome"
    )
    def test_terminal_settlement_pays_only_the_unpaid_suffix(self):
        _write(self.player, 71928, SleepPosture.FORCED)
        tick_before = get_world_clock().tick
        advances = []
        real_advance = WorldClock.advance

        def capture(clock, seconds, source, entities, **kwargs):
            advances.append((int(seconds), source))
            return real_advance(clock, seconds, source, entities, **kwargs)

        with patch.object(WorldClock, "advance", capture):
            engage(self.player, self.monster)
            self.assertEqual(self._record().settled_rounds, 1)
            # Two ordinary interactive rounds stay unpaid.
            for expected in (2, 3):
                with patch(
                    "world.rules.combat.battlefield.roll_d100", return_value=100
                ), patch(
                    "world.rules.combat.damage.roll_d100", return_value=100
                ), patch("world.rules.combat.rounds.roll_d100", return_value=100):
                    self.assertEqual(self._hold_round()["outcome"], "round")
                self.assertEqual(self._record().rounds_elapsed, expected)
                self.assertEqual(self._record().settled_rounds, 1)
            reserve_before = read_fatigue_state(self.player).reserve_units
            result = forfeit(self.player)
        self.assertEqual(result["outcome"], "defeat")
        # Exactly the two unpaid rounds settle, once, through the combat source.
        combat = [width for width, source in advances if source is AdvanceSource.COMBAT]
        self.assertEqual(advances.count((12, AdvanceSource.COMBAT)), 1)
        self.assertNotIn((18, AdvanceSource.COMBAT), advances)
        # Six seconds for the already-paid prefix round plus the twelve
        # terminal seconds: the lifetime combat total is the round count.
        self.assertEqual(sum(combat), 18)
        # Awake combat consumes 12 units/s over only those 12 seconds.
        self.assertEqual(
            read_fatigue_state(self.player).reserve_units,
            reserve_before - 144,
        )
        self.assertIsNone(read_session(self.player))

    @covers_requirement(
        "player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits"
    )
    @covers_requirement(
        "player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds"
    )
    def test_sleep_alone_never_declares_defeat(self):
        _write(self.player, 0, SleepPosture.FORCED)
        self.monster.traits.atk_phys.base = 100000
        self.monster.traits.atk_phys.current = 100000
        advances = []
        real_advance = WorldClock.advance

        def capture(clock, seconds, source, entities, **kwargs):
            advances.append((int(seconds), source))
            return real_advance(clock, seconds, source, entities, **kwargs)

        with patch.object(WorldClock, "advance", capture):
            result = engage(self.player, self.monster)
        continuation = result["continuation"]
        self.assertEqual(continuation["outcome"], "defeat")
        self.assertGreaterEqual(continuation["rounds_elapsed"], 1)
        self.assertGreaterEqual(continuation["continued_rounds"], 1)
        self.assertIsNone(read_session(self.player))
        # The defeat was dealt by real enemy actions over paid rounds, not by
        # the opening posture.
        self.assertEqual(
            sum(
                width
                for width, source in advances
                if source is AdvanceSource.COMBAT
            ),
            continuation["rounds_elapsed"] * 6,
        )
        self.assertTrue(
            any(
                entry.kind == "damage"
                for log in continuation["logs"]
                for entry in log.entries
            )
        )

    @covers_requirement(
        "player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits"
    )
    @covers_requirement(
        "player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds"
    )
    def test_a_waking_companion_ends_automatic_play_under_normal_authority(self):
        from typeclasses.npcs import NPC
        from world.rules.party import join_party

        companion = create_object(NPC, key="waking ally", location=self.room)
        companion.race = self.player.race
        companion.apply_race_baseline()
        companion.traits.hp.base = 500
        companion.traits.hp.current = 500
        join_party(companion, self.player)
        _write(self.player, 0, SleepPosture.FORCED)
        _write(companion, 71928, SleepPosture.FORCED)
        result = engage(self.player, self.monster)
        continuation = result["continuation"]
        # The companion's own paid round reaches 72000 and it wakes: automatic
        # play stops with the commander still asleep.
        self.assertEqual(continuation["continued_rounds"], 1)
        self.assertEqual(continuation["outcome"], "round")
        self.assertIs(read_fatigue_state(companion).posture, SleepPosture.AWAKE)
        self.assertEqual(read_fatigue_state(companion).reserve_units, 72000)
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.FORCED)
        record = self._record()
        battlefield = reconstruct_battlefield(self.player, record)
        self.assertEqual(
            set(get_required_combat_actors(record, battlefield)),
            {int(companion.pk)},
        )
        # The awake companion retains ordinary command authority even though
        # the commander sleeps.
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch(
            "world.rules.combat.damage.roll_d100", return_value=100
        ), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            commanded = submit_player_action(
                self.player,
                BASIC_ATTACK_KEY,
                [self.monster],
                commanded_actor=companion,
            )
        self.assertEqual(commanded["outcome"], "round")

    @covers_requirement(
        "player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits"
    )
    @covers_requirement(
        "player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds"
    )
    def test_the_existing_cap_still_terminates_an_all_sleep_party(self):
        from world.rules.combat_session.settlement import _ROUND_SECONDS

        self.monster.traits.atk_phys.base = 0
        self.monster.traits.atk_phys.current = 0
        _write(self.player, 0, SleepPosture.FORCED)
        tick_before = get_world_clock().tick
        result = engage(self.player, self.monster)
        continuation = result["continuation"]
        self.assertEqual(continuation["outcome"], "cap")
        self.assertEqual(continuation["rounds_elapsed"], _round_cap())
        self.assertEqual(continuation["continued_rounds"], _round_cap())
        self.assertEqual(
            get_world_clock().tick - tick_before,
            _round_cap() * _ROUND_SECONDS,
        )
        self.assertIsNone(read_session(self.player))

    @covers_requirement(
        "world-clock::cmdcast-advances-command-time-only-outside-a-persistent-combat-session"
    )
    def test_no_combatant_action_advances_the_world_clock(self):
        import world.rules.combat_session.rounds as session_rounds
        from world.rules.combat import run_round as real_run_round

        _write(self.player, 71928, SleepPosture.FORCED)
        tick_before = get_world_clock().tick
        inside = {"value": False}
        real_advance = WorldClock.advance

        def guarded_advance(clock, seconds, source, entities, **kwargs):
            if inside["value"]:
                raise AssertionError("a combatant action advanced the world clock")
            return real_advance(clock, seconds, source, entities, **kwargs)

        def spy_round(*args, **kwargs):
            inside["value"] = True
            try:
                return real_run_round(*args, **kwargs)
            finally:
                inside["value"] = False

        with patch.object(WorldClock, "advance", guarded_advance), patch.object(
            session_rounds, "run_round", side_effect=spy_round
        ):
            result = engage(self.player, self.monster)
        self.assertEqual(result["continuation"]["continued_rounds"], 1)
        self.assertEqual(get_world_clock().tick, tick_before + 6)

    @covers_requirement(
        "player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits"
    )
    def test_the_text_engage_consumer_renders_the_automatic_rounds(self):
        _write(self.player, 71928, SleepPosture.FORCED)
        tick_before = get_world_clock().tick
        command = CmdEngage()
        command.caller = self.player
        command.args = self.monster.key
        with patch.object(self.player, "search", return_value=self.monster), patch.object(
            self.player, "msg"
        ) as message:
            command.func()
        lines = [call.args[0] for call in message.call_args_list]
        self.assertTrue(lines)
        self.assertEqual(get_world_clock().tick, tick_before + 6)
        self.assertIsNotNone(read_session(self.player))
        self.assertFalse(any("你被擊敗了" in str(line) for line in lines))

    @covers_requirement(
        "player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits"
    )
    def test_the_browser_engage_adapter_consumes_the_automatic_rounds(self):
        from web.webclient.actions.exploration_actions import _engage_adapter

        _write(self.player, 71928, SleepPosture.FORCED)
        tick_before = get_world_clock().tick
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch(
            "world.rules.combat.damage.roll_d100", return_value=100
        ), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            result = _engage_adapter(
                self.player, {"monster_id": int(self.monster.pk)}
            )
        self.assertEqual(result["outcome"], "success")
        self.assertEqual(result["code"], "engaged")
        self.assertEqual(get_world_clock().tick, tick_before + 6)
        self.assertIsNotNone(read_session(self.player))


class BlockingContinuationTests(BattlefieldIsolation, EvenniaTestCase):
    """A real temporary blocking effect on the final actionable ally."""

    def setUp(self) -> None:
        _scope(self)
        super().setUp()
        self.room = _room("blocked hostile arena")
        self.player = _player("blocked hostile player")
        self.player.location = self.room
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        self.monster = _monster("blocked hostile goblin", hp=5000, atk=5)
        self.monster.location = self.room
        grant_lineage(self.player, [_SELF_PARALYSIS.key])

    def _confirm_blocking_round(self):
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch(
            "world.rules.combat.damage.roll_d100", return_value=100
        ), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            return submit_player_action(
                self.player, _SELF_PARALYSIS.key, []
            )

    @covers_requirement(
        "player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits"
    )
    @covers_requirement(
        "player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds"
    )
    def test_a_confirmed_round_applies_a_blocking_effect_then_continues(self):
        import world.rules.combat_session.rounds as session_rounds
        from world.rules.combat import run_round as real_run_round

        tick_before = get_world_clock().tick
        engage(self.player, self.monster)
        observed: list[bool] = []

        def spy_round(*args, **kwargs):
            observed.append("paralysis" in entity_active_buffs(self.player))
            return real_run_round(*args, **kwargs)

        deferred: list = []
        with patch("world.rules.combat_session.rounds.log_info") as logged, patch.object(
            session_rounds, "run_round", side_effect=spy_round
        ), patch(
            "world.rules.combat_session.rounds.transaction.on_commit",
            side_effect=lambda callback, **kwargs: deferred.append(callback),
        ):
            result = self._confirm_blocking_round()
            for callback in deferred:
                callback()
        # The confirmed round executes before the blocker; every automatic
        # enemy-only round starts with the real temporary block still active.
        self.assertEqual(observed, [False, True, True, True])
        self.assertEqual(result["outcome"], "round")
        record = read_session(self.player)
        # The confirmed round plus three real enemy-only rounds until the
        # authored 20-second block expires through ordinary upkeep (6 s per
        # round, the applying round included).
        self.assertEqual(record.rounds_elapsed, 4)
        self.assertEqual(record.settled_rounds, 4)
        self.assertEqual(get_world_clock().tick, tick_before + 24)
        self.assertNotIn("paralysis", entity_active_buffs(self.player))
        events = [call.args[0] for call in logged.call_args_list if call.args]
        self.assertEqual(events.count("combat_incapacitated_continued"), 1)
        self.assertIsNotNone(read_session(self.player))
        # Choice is back.
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch(
            "world.rules.combat.damage.roll_d100", return_value=100
        ), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            resumed = submit_player_action(
                self.player, BASIC_ATTACK_KEY, [self.monster]
            )
        self.assertIn(resumed["outcome"], ("round", "victory"))

    @covers_requirement(
        "player-combat-session::combat-time-settles-once-at-terminal-session-outcome"
    )
    def test_a_paid_wake_then_deferred_round_then_reload_settles_the_truth(self):
        from world.rules.combat import COMBAT_YAML

        _write(self.player, 71928, SleepPosture.FORCED)
        engage(self.player, self.monster)
        record = read_session(self.player)
        self.assertEqual((record.rounds_elapsed, record.settled_rounds), (1, 1))
        self.assertIs(read_fatigue_state(self.player).posture, SleepPosture.AWAKE)
        # One deferred awake interactive round, then a reload.
        with patch("world.rules.combat.battlefield.roll_d100", return_value=100), patch(
            "world.rules.combat.damage.roll_d100", return_value=100
        ), patch("world.rules.combat.rounds.roll_d100", return_value=100):
            submit_player_action(self.player, BASIC_ATTACK_KEY, [self.monster])
        record = read_session(self.player)
        self.assertEqual((record.rounds_elapsed, record.settled_rounds), (2, 1))
        from world.rules.combat_session import restore_active_session

        tick_before = get_world_clock().tick
        reserve_before = read_fatigue_state(self.player).reserve_units
        restore_active_session(self.player)
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertEqual(read_session(self.player).rounds_elapsed, 2)
        advances = []
        real_advance = WorldClock.advance

        def capture(clock, seconds, source, entities, **kwargs):
            advances.append((int(seconds), source))
            return real_advance(clock, seconds, source, entities, **kwargs)

        with patch.object(WorldClock, "advance", capture):
            forfeit(self.player)
        # The deferred round is awake, never replayed as the pre-payment sleep.
        self.assertEqual(
            read_fatigue_state(self.player).reserve_units,
            reserve_before - 6 * 12,
        )
        self.assertEqual(advances.count((6, AdvanceSource.COMBAT)), 1)
        self.assertEqual(COMBAT_YAML["round"]["seconds"], 6)

    @covers_requirement(
        "player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits"
    )
    @covers_requirement(
        "player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds"
    )
    def test_a_late_failure_restores_the_round_and_the_retry_pays_once(self):
        import world.rules.combat_session.rounds as session_rounds

        engage(self.player, self.monster)
        real_persist = session_rounds._persist

        def failing(actor, record):
            if record.settled_rounds == 2:
                raise RuntimeError("injected late continuation failure")
            return real_persist(actor, record)

        tick_before = get_world_clock().tick
        reserve_before = read_fatigue_state(self.player).reserve_units
        with patch.object(session_rounds, "_persist", failing):
            with self.assertRaises(RuntimeError):
                self._confirm_blocking_round()
        # The round unit rolled back completely: the confirmed selection
        # survives (its own admission transaction committed) but no round, no
        # cursor, no clock, no physiology and no blocking effect did.
        pending = read_session(self.player)
        self.assertIsNotNone(pending)
        self.assertEqual(
            (pending.rounds_elapsed, pending.settled_rounds), (0, 0)
        )
        self.assertIn(int(self.player.pk), pending.draft_entries)
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertEqual(
            read_fatigue_state(self.player).reserve_units, reserve_before
        )
        self.assertNotIn("paralysis", entity_active_buffs(self.player))
        # A retry pays each accepted round exactly once.
        self._confirm_blocking_round()
        record = read_session(self.player)
        self.assertEqual((record.rounds_elapsed, record.settled_rounds), (4, 4))
        self.assertEqual(get_world_clock().tick, tick_before + 24)

    @covers_requirement(
        "player-combat-session::a-round-and-its-settlement-form-one-atomic-persistence-unit"
    )
    def test_a_receipt_failure_after_a_successful_continuation_restores_all(self):
        import world.rules.combat_session.rounds as session_rounds

        engage(self.player, self.monster)
        tick_before = get_world_clock().tick
        reserve_before = read_fatigue_state(self.player).reserve_units
        with patch.object(
            session_rounds,
            "write_last_combat_receipt",
            side_effect=RuntimeError("receipt write failed"),
        ):
            with self.assertRaises(RuntimeError):
                self._confirm_blocking_round()
        # The continuation already paid a prefix and automatic rounds; the
        # owner's later receipt failure must still restore every surface.
        pending = read_session(self.player)
        self.assertEqual(
            (pending.rounds_elapsed, pending.settled_rounds), (0, 0)
        )
        self.assertEqual(get_world_clock().tick, tick_before)
        self.assertEqual(
            read_fatigue_state(self.player).reserve_units, reserve_before
        )
        self.assertNotIn("paralysis", entity_active_buffs(self.player))
        self._confirm_blocking_round()
        record = read_session(self.player)
        self.assertEqual((record.rounds_elapsed, record.settled_rounds), (4, 4))
        self.assertEqual(get_world_clock().tick, tick_before + 24)


class PaidEvidenceRegressionTests(BattlefieldIsolation, EvenniaTestCase):
    """Boundary evidence and defeated-body wake rules of the paid writer."""

    def setUp(self) -> None:
        _scope(self)
        super().setUp()
        self.room = _room("paid evidence arena")
        self.player = _player("paid evidence player")
        self.player.location = self.room
        self.player.traits.hp.base = 2000
        self.player.traits.hp.current = 2000
        self.monster = _monster("paid evidence goblin", hp=5000, atk=1)
        self.monster.location = self.room

    @covers_requirement(
        "player-combat-session::terminal-mental-accounting-records-actual-round-boundary-posture-intervals"
    )
    def test_reconciliation_preserves_unchanged_boundary_transitions(self):
        from typeclasses.npcs import NPC
        from world.rules.combat_session import _persist
        from world.rules.combat_session.records import SleepTransition
        from world.rules.combat_session.rounds import _paid_sleep_evidence
        from world.rules.party import join_party

        companion = create_object(NPC, key="evidence ally", location=self.room)
        companion.race = self.player.race
        companion.apply_race_baseline()
        join_party(companion, self.player)
        _write(companion, 72000, SleepPosture.AWAKE)
        engage(self.player, self.monster)
        record = replace(
            read_session(self.player),
            rounds_elapsed=1,
            sleep_transitions=(SleepTransition(1, int(companion.pk), False),),
        )
        _persist(self.player, record)
        evidence = _paid_sleep_evidence(
            record, reconstruct_battlefield(self.player, record), 1
        )
        # The explicit awake transition at this boundary matches the live
        # posture and must survive untouched.
        self.assertIn(
            SleepTransition(1, int(companion.pk), False), evidence
        )
        # A contradiction (declared asleep, actually awake) is corrected for
        # that actor only.
        contradicted = replace(
            record,
            sleep_transitions=(SleepTransition(1, int(companion.pk), True),),
        )
        _persist(self.player, contradicted)
        corrected = _paid_sleep_evidence(
            contradicted,
            reconstruct_battlefield(self.player, contradicted),
            1,
        )
        self.assertIn(
            SleepTransition(1, int(companion.pk), False), corrected
        )
        self.assertNotIn(
            SleepTransition(1, int(companion.pk), True), corrected
        )

    @covers_requirement(
        "player-combat-session::terminal-physiology-cannot-reverse-defeat-and-prompts-follow-aftermath"
    )
    def test_a_knocked_out_forced_sleeper_is_not_woken_by_a_paid_round(self):
        from typeclasses.npcs import NPC
        from world.rules.combat_session import _persist
        from world.rules.combat_session.rounds import _pay_round_time
        from world.rules.party import join_party

        knocked = create_object(NPC, key="knocked sleeper", location=self.room)
        undefeated = create_object(
            NPC, key="undefeated sleeper", location=self.room
        )
        for member in (knocked, undefeated):
            member.race = self.player.race
            member.apply_race_baseline()
            member.traits.hp.base = 500
            member.traits.hp.current = 500
            join_party(member, self.player)
            _write(member, 71928, SleepPosture.FORCED)
        engage(self.player, self.monster)
        record = replace(
            read_session(self.player),
            knocked_out_ids=(int(knocked.pk),),
        )
        _persist(self.player, record)
        battlefield = reconstruct_battlefield(self.player, record)
        _pay_round_time(
            self.player,
            record,
            battlefield,
            through_round=1,
            automatic=True,
        )
        defeated_state = read_fatigue_state(knocked)
        self.assertIs(defeated_state.posture, SleepPosture.FORCED)
        self.assertEqual(defeated_state.reserve_units, 71928 + 72)
        undefeated_state = read_fatigue_state(undefeated)
        self.assertIs(undefeated_state.posture, SleepPosture.AWAKE)
        self.assertEqual(undefeated_state.reserve_units, 72000)


class MappedPaidCursorTests(EvenniaTest):
    """A mapped enemy's own cursor is paid once and never charged twice."""

    def setUp(self) -> None:
        super().setUp()
        publish_shipped_map_world()
        self.enterContext(
            synthetic_registries("monster_species", "monster_variants", "monster_tiers")
        )
        _scope(self)
        create_wilderness(
            name=WILDERNESS_NAME, mapprovider=ElosernWildernessMapProvider()
        )
        self.wilderness = WildernessScript.objects.get(db_key=WILDERNESS_NAME)
        initialize_population_seed(self.wilderness, seed=_SEED, tick=0)
        self.player = _player("mapped paid player")
        self.assertTrue(
            enter_wilderness(
                self.player, coordinates=_PROBE, name=WILDERNESS_NAME
            )
        )
        self.room = self.player.location
        _write(self.player, 71928, SleepPosture.FORCED)
        species = next(iter(SYNTH_MONSTER_VARIANTS.values())).species_key
        self.enemy = construct_species_individual(species, next(iter(SYNTH_MONSTER_VARIANTS)))
        self.enemy.key = "mapped paid enemy"
        self.enemy.traits.hp.base = 100000
        self.enemy.traits.hp.current = 100000
        self.enemy.location = self.room
        self.room.contents_cache.add(self.enemy)
        self.wilderness.db.itemcoordinates[self.enemy] = _PROBE
        _write(self.enemy, _FULL_RESERVE, SleepPosture.AWAKE)
        create_group(
            self.wilderness,
            operation_id="enemy:paid-cursor",
            owner_kind="zone",
            owner_key="t_zone",
            activity_key="t_whisper_quail_solitary_activity",
            home=LocationRef.wilderness(WILDERNESS_NAME, *_PROBE),
            position=LocationRef.wilderness(WILDERNESS_NAME, *_PROBE),
            member_ids=(self.enemy.pk,),
            seed=_SEED,
            tick=0,
        )

    @covers_requirement(
        "player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits"
    )
    @covers_requirement(
        "player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds"
    )
    def test_the_paid_endpoint_advances_the_map_cursor_once(self):
        from world.rules.fatigue import project_fatigue_status
        from world.rules.combat_session import policies as session_policies

        tick_before = get_world_clock().tick
        # The mapped cursor contract is the subject here; the enemy still
        # submits a real deterministic basic-attack request through the real
        # resolver, without depending on a shipped behaviour profile for this
        # synthetic species tier.
        with patch.object(
            session_policies,
            "_enemy_policy",
            side_effect=lambda entity, field, record: (
                session_policies._basic_attack_request(entity, field, record)
            ),
        ):
            result = engage_group(self.player, [self.enemy])
        self.assertEqual(result["continuation"]["continued_rounds"], 1)
        self.assertEqual(get_world_clock().tick, tick_before + 6)
        group = group_of_member(self.wilderness, int(self.enemy.pk))
        member = group.member_time[str(int(self.enemy.pk))]
        self.assertEqual(member.mode, MODE_COMBAT)
        self.assertEqual(member.settled_through_tick, 6)
        from world.rules.fatigue import FatigueState

        paid = predict_interval(
            FatigueState(_FULL_RESERVE, SleepPosture.AWAKE),
            FatigueActivity.AWAKE_COMBAT,
            6,
            completion=IntervalCompletion.INDIVISIBLE,
        ).end.reserve_units
        self.assertEqual(
            read_optional_fatigue_state(self.enemy).reserve_units, paid
        )
        # The terminal settlement pays no second interval for the same six
        # seconds and releases the member at the paid endpoint.
        advances = []
        real_advance = WorldClock.advance

        def capture(clock, seconds, source, entities, **kwargs):
            advances.append((int(seconds), source))
            return real_advance(clock, seconds, source, entities, **kwargs)

        with patch.object(WorldClock, "advance", capture):
            forfeit(self.player)
        self.assertEqual(
            sum(
                width
                for width, source in advances
                if source is AdvanceSource.COMBAT
            ),
            0,
        )
        self.assertEqual(
            read_optional_fatigue_state(self.enemy).reserve_units, paid
        )
        group = group_of_member(self.wilderness, int(self.enemy.pk))
        self.assertEqual(
            group.member_time[str(int(self.enemy.pk))].settled_through_tick, 6
        )
        project_fatigue_status(self.enemy)
        self.assertTrue(
            ObjectDB.objects.filter(pk=int(self.enemy.pk)).exists()
        )
        self.assertIsNone(read_session(self.player))
