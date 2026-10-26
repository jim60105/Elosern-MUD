"""Committed terminal-combat and completed-skip alignment checkpoints.

Focused behaviour tests for the settlement slice of the incremental
synchronization design:

- the committed fact of a real terminal combat settlement through the rules
  owner and through both transports (a text exit command and the graphical
  ``combat.exit_confirm`` action), including the terminal opening, the
  recoverable unparseable cleanup and the deduplicated replay branch, while an
  ordinary engagement and an ordinary continuing round publish none;
- the committed fact of a completed explicit rest/wait and of a completed
  accepted sleep, with entry-only sleep, the open dream question, a retained
  partial interval, a replayed receipt and a rolled-back advance all publishing
  none, and an owner continuation settling several intervals publishing once;
- the watcher outcome: one freshly rendered complete snapshot per lawful
  watcher instead of the settlement delta, a deliberately omitted candidate
  repaired by the checkpoint, a retired epoch publishing nothing, and Telnet
  receiving no graphical state.

The coordinator, registry and presenters are the production ones; sessions and
the reactor scheduler are synthetic so the ordering is deterministic.
"""

import unittest
from dataclasses import replace
from types import SimpleNamespace
from unittest import mock

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement
from typeclasses.characters import PlayerCharacter
from typeclasses.monsters import Monster
from typeclasses.npcs import NPC
from typeclasses.rooms import Room

from web.webclient.actions.dispatcher import handle_ui_action
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation import alignment
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.ingress import (
    build_presentation_context,
    build_production_registry,
)
from web.webclient.presentation.registry import PresenterSpec, PresentationRegistry
from web.webclient.presentation.watchers import clear_watchers, register_watcher
from world.rules.clock import (
    _EVENT_SOURCES,
    ScheduledEvent,
    get_world_clock,
    register_event_source,
)
from world.rules.combat_session import (
    BASIC_ATTACK_KEY,
    PARTY_EXIT_SURRENDER,
    confirm_actor_command,
    engage,
    read_session,
    reconstruct_battlefield,
    request_party_exit,
    restore_active_session,
    settle_session,
)
from world.rules.combat_session.records import to_storage
from world.rules.combat_session.settlement import settle_forced_sleep_opening
from world.rules.fatigue import SleepPosture, write_fatigue_state
from world.rules.party import join_party
from world.rules.presentation_events import (
    clear_alignment_observers,
    current_publication_group,
    publication_group,
    register_alignment_observer,
)
from world.rules.settlement_alignment import AWAKENED_SKIP, COMBAT_TERMINAL
from world.rules.tests._combat_session_helpers import (
    _monster,
    open_synthetic_scope,
    synth_innate_overlay,
)
from world.rules.tests.combat_fixtures import BattlefieldIsolation, grant_lineage
from world.rules.time_skip import (
    SkipRefused,
    advance_wait,
    begin_sleep,
    continue_owner_sleep,
    continue_sleep,
    decline_owner_sleep_dream,
    enter_sleep,
    owner_sleep_view_state,
)
from world.tests.synthetic_data import SYNTH_SKILLS

from .test_publication_settlements import FakeSession, QueuedScheduler, _coordinator


_T_SINGLE = SYNTH_SKILLS["t_ember_burst"].key
_T_AREA = SYNTH_SKILLS["t_glowmire_bloom"].key


class _FactRecorder:
    """Collect every committed alignment fact the owners emit."""

    def __init__(self) -> None:
        self.facts = []

    def __call__(self, fact):
        self.facts.append(fact)

    def causes(self):
        return [fact.cause for fact in self.facts]

    def actors(self):
        return [fact.actor_id for fact in self.facts]


def _clear_event_sources(test):
    """Isolate the process-global clock boundary registry for one test."""
    kept = dict(_EVENT_SOURCES)
    _EVENT_SOURCES.clear()
    test.addCleanup(_EVENT_SOURCES.update, kept)
    test.addCleanup(_EVENT_SOURCES.clear)


class CheckpointTestBase(BattlefieldIsolation, EvenniaTest):
    """One synthetic player in an isolated fact-recording world."""

    character_typeclass = PlayerCharacter
    room_typeclass = Room

    def setUp(self):
        super().setUp()
        get_world_clock()
        _clear_event_sources(self)
        self.player = self.char1
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room1
        write_fatigue_state(self.player, 360000, SleepPosture.AWAKE)
        clear_alignment_observers()
        self.recorder = _FactRecorder()
        register_alignment_observer(self.recorder)
        self.addCleanup(clear_alignment_observers)

    def _spawn(self, key="合成哥布林"):
        monster = create_object(Monster, key=key, location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        return monster

    def _engage(self, monster=None):
        engage(self.player, monster or self._spawn())
        return read_session(self.player)

    def _settle(self, record, outcome="victory"):
        battlefield = reconstruct_battlefield(self.player, record)
        with self.captureOnCommitCallbacks(execute=True):
            return settle_session(self.player, record, battlefield, outcome)

    def _companion(self, reserve, posture):
        companion = create_object(NPC, key="合成同伴", location=self.room1)
        companion.race = "human"
        companion.apply_race_baseline()
        join_party(companion, self.player)
        write_fatigue_state(companion, reserve, posture)
        return companion

    def _fill_gauges(self):
        for key in ("hp", "mp", "sp"):
            gauge = getattr(self.player.traits, key)
            gauge.current = gauge.max
            gauge.rate = 0.0


class TerminalCombatCheckpointTests(CheckpointTestBase):
    """Only a newly committed terminal settlement is a checkpoint."""

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_a_committed_terminal_settlement_publishes_one_checkpoint(self):
        record = self._engage()
        self._settle(record, "victory")

        self.assertEqual(self.recorder.causes(), [COMBAT_TERMINAL])
        fact = self.recorder.facts[0]
        self.assertEqual(fact.actor_id, int(self.player.pk))
        self.assertEqual(len(fact.group_id), 32)
        self.assertIsNone(fact.source)
        self.assertIsNone(fact.destination)

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_every_recorded_participant_receives_the_checkpoint(self):
        companion = self._companion(360000, SleepPosture.AWAKE)
        record = self._engage()
        self.assertIn(int(companion.pk), record.player_ids)
        self._settle(record, "victory")

        # Watchers are indexed under the session's current puppet, which can be
        # a possessed companion — never only the commander owning the session.
        self.assertEqual(
            sorted(self.recorder.actors()),
            sorted([int(self.player.pk), int(companion.pk)]),
        )
        self.assertEqual(set(self.recorder.causes()), {COMBAT_TERMINAL})

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_a_terminal_settlement_joins_the_ambient_causal_group(self):
        record = self._engage()
        with publication_group() as captured:
            with self.captureOnCommitCallbacks(execute=True):
                settle_session(
                    self.player,
                    record,
                    reconstruct_battlefield(self.player, record),
                    "victory",
                )
        self.assertEqual(
            [fact.group_id for fact in self.recorder.facts], [captured.id]
        )

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_an_ordinary_engagement_publishes_no_checkpoint(self):
        self._engage()
        self.assertEqual(self.recorder.facts, [])

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_an_ordinary_nonterminal_round_publishes_no_checkpoint(self):
        monster = self._spawn()
        with (
            mock.patch("world.rules.combat.battlefield.roll_d100", return_value=50),
            mock.patch("world.rules.combat.damage.roll_d100", return_value=50),
            mock.patch("world.rules.combat.rounds.roll_d100", return_value=50),
        ):
            from world.rules.combat_initiation import initiate_field_combat

            result = initiate_field_combat(self.player, BASIC_ATTACK_KEY, monster)
        self.assertIn(result["outcome"], ("round", "continue", "draft"), result)
        self.assertIsNotNone(read_session(self.player))
        self.assertEqual(self.recorder.facts, [], "only changed candidates publish")

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_the_replayed_settlement_branch_publishes_no_checkpoint(self):
        record = self._engage()
        settled = replace(record, settled_tick=int(get_world_clock().tick))
        with self.captureOnCommitCallbacks(execute=True):
            replay = settle_session(self.player, settled, None, "victory")
        self.assertEqual(replay["outcome"], "victory")
        self.assertEqual(self.recorder.facts, [])

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_a_terminal_sleep_opening_publishes_the_checkpoint(self):
        record = self._engage()
        write_fatigue_state(self.player, 0, SleepPosture.FORCED)
        battlefield = reconstruct_battlefield(self.player, record)
        with self.captureOnCommitCallbacks(execute=True):
            result = settle_forced_sleep_opening(self.player, record, battlefield)
        self.assertIsNotNone(result, "the all-asleep opening settled terminally")
        self.assertEqual(self.recorder.causes(), [COMBAT_TERMINAL])

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_a_failed_terminal_write_publishes_nothing(self):
        record = self._engage()
        with mock.patch(
            "world.rules.combat_session.settlement.settle_combat_result",
            side_effect=RuntimeError("clock settlement failed"),
        ):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    settle_session(
                        self.player,
                        record,
                        reconstruct_battlefield(self.player, record),
                        "victory",
                    )
        self.assertEqual(self.recorder.facts, [], "a rolled-back unit emits nothing")

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_an_unparseable_recovery_cleanup_publishes_one_act_only_checkpoint(self):
        self.player.db.active_combat = {"not": "a valid record"}
        with self.captureOnCommitCallbacks(execute=True):
            restore_active_session(self.player)
        self.assertIsNone(self.player.db.active_combat, "the safe clear happened")
        self.assertEqual(self.recorder.causes(), [COMBAT_TERMINAL])
        self.assertEqual(self.recorder.actors(), [int(self.player.pk)])

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_an_already_settled_cleanup_publishes_nothing(self):
        record = self._engage()
        self.player.db.active_combat = to_storage(
            replace(record, settled_tick=int(get_world_clock().tick))
        )
        with self.captureOnCommitCallbacks(execute=True):
            restore_active_session(self.player)
        self.assertIsNone(self.player.db.active_combat)
        self.assertEqual(self.recorder.facts, [])


class SkipCheckpointTests(CheckpointTestBase):
    """Only a completed explicit skip is a checkpoint."""

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_positive_awake_skip_publishes_one_checkpoint(self):
        with self.captureOnCommitCallbacks(execute=True):
            result = advance_wait(self.player, 60)
        self.assertEqual(result.elapsed_seconds, 60)
        self.assertEqual(self.recorder.causes(), [AWAKENED_SKIP])
        self.assertEqual(self.recorder.actors(), [int(self.player.pk)])

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_truncated_interval_that_ends_the_request_still_qualifies(self):
        self._companion(0, SleepPosture.FORCED)
        with self.captureOnCommitCallbacks(execute=True):
            result = advance_wait(self.player, 10000)
        self.assertEqual(result.elapsed_seconds, 6000)
        self.assertEqual(self.recorder.causes(), [AWAKENED_SKIP])

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_zero_time_wait_publishes_nothing(self):
        with self.captureOnCommitCallbacks(execute=True):
            result = advance_wait(self.player, 0)
        self.assertEqual(result.elapsed_seconds, 0)
        self.assertEqual(self.recorder.facts, [])

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_refused_skip_publishes_nothing(self):
        self._spawn()
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(SkipRefused):
                advance_wait(self.player, 60)
        self.assertEqual(self.recorder.facts, [])

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_rolled_back_advance_publishes_nothing(self):
        clock = get_world_clock()
        before = int(clock.tick)
        with mock.patch.object(
            type(clock), "advance", side_effect=RuntimeError("clock failed")
        ):
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    advance_wait(self.player, 60)
        self.assertEqual(int(get_world_clock().tick), before)
        self.assertEqual(self.recorder.facts, [])

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_an_ambient_causal_group_is_reused(self):
        with publication_group() as captured:
            with self.captureOnCommitCallbacks(execute=True):
                advance_wait(self.player, 60)
        self.assertEqual(
            [fact.group_id for fact in self.recorder.facts], [captured.id]
        )

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_duplicate_operation_receipt_publishes_nothing(self):
        with self.captureOnCommitCallbacks(execute=True):
            first = advance_wait(self.player, 60, operation_id="synthetic-once")
            second = advance_wait(self.player, 60, operation_id="synthetic-once")
        self.assertEqual(first, second)
        self.assertEqual(self.recorder.causes(), [AWAKENED_SKIP])

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_sleep_entry_publishes_nothing(self):
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        with self.captureOnCommitCallbacks(execute=True):
            entry = enter_sleep(self.player)
        self.assertIsNotNone(entry.receipt)
        self.assertEqual(self.recorder.facts, [], "sleep entry is not a settlement")

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_the_open_owner_dream_question_publishes_nothing(self):
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        with self.captureOnCommitCallbacks(execute=True):
            outcome = begin_sleep(self.player)
        self.assertIsNone(outcome.result)
        self.assertEqual(self.recorder.facts, [], "the choice is not a settlement")

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_retained_partial_sleep_publishes_nothing_then_completes_once(self):
        self._fill_gauges()
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        self._companion(0, SleepPosture.FORCED)
        entry = enter_sleep(self.player)

        with self.captureOnCommitCallbacks(execute=True):
            partial = continue_sleep(self.player, entry)
        self.assertGreater(partial.elapsed_seconds, 0)
        self.assertFalse(partial.completed)
        self.assertEqual(
            self.recorder.facts, [], "a retained continuation aligns later"
        )

        with self.captureOnCommitCallbacks(execute=True):
            completed = continue_sleep(self.player, entry)
        self.assertTrue(completed.completed, completed)
        self.assertEqual(self.recorder.causes(), [AWAKENED_SKIP])

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_an_owner_continuation_publishes_exactly_one_checkpoint(self):
        self._fill_gauges()
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        # A forced companion waking mid-interval splits the owner's settlement
        # into several committed intervals that must still publish once.
        self._companion(0, SleepPosture.FORCED)
        with self.captureOnCommitCallbacks(execute=True):
            begin_sleep(self.player)
        state = owner_sleep_view_state(self.player)
        decline_owner_sleep_dream(
            self.player,
            sleep_id=state["sleep_id"],
            revision=state["revision"],
            generation=state["generation"],
        )
        self.assertEqual(
            self.recorder.facts, [], "the accepted entry alone aligns nothing"
        )

        with self.captureOnCommitCallbacks(execute=True):
            result = continue_owner_sleep(
                self.player,
                sleep_id=state["sleep_id"],
                expected_generation=state["generation"],
            )
        self.assertTrue(result.completed, result)
        self.assertEqual(self.recorder.causes(), [AWAKENED_SKIP])

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_replayed_sleep_interval_publishes_nothing(self):
        self._fill_gauges()
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        entry = enter_sleep(self.player)
        with self.captureOnCommitCallbacks(execute=True):
            continue_sleep(self.player, entry, operation_id="synthetic-interval")
        self.recorder.facts.clear()
        with self.captureOnCommitCallbacks(execute=True):
            continue_sleep(self.player, entry, operation_id="synthetic-interval")
        self.assertEqual(self.recorder.facts, [])

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_sleep_completing_on_an_interactive_boundary_publishes_the_checkpoint(
        self,
    ):
        # An interactive event due exactly at the accepted target coincides with
        # completion. The authoritative receipt outranks the pause disposition,
        # so the operation is a completed settlement and must align.
        self._fill_gauges()
        write_fatigue_state(self.player, 180000, SleepPosture.AWAKE)
        with self.captureOnCommitCallbacks(execute=True):
            begin_sleep(self.player)
        state = owner_sleep_view_state(self.player)
        decline_owner_sleep_dream(
            self.player,
            sleep_id=state["sleep_id"],
            revision=state["revision"],
            generation=state["generation"],
        )
        # The fixture's full gauges and half reserve accept 15,000 seconds, and
        # the registered interactive stage is due inside that same interval.
        previous = _EVENT_SOURCES.get("shop_hours")
        register_event_source(
            "shop_hours",
            lambda start, end: [
                ScheduledEvent(
                    "synthetic_interactive", start + 14999, {}
                )
            ],
            next_boundary=lambda start, end: start + 15000,
        )
        self.addCleanup(
            lambda: (
                _EVENT_SOURCES.pop("shop_hours", None)
                if previous is None
                else _EVENT_SOURCES.__setitem__("shop_hours", previous)
            )
        )
        self.assertEqual(self.recorder.facts, [])

        with self.captureOnCommitCallbacks(execute=True):
            result = continue_owner_sleep(
                self.player,
                sleep_id=state["sleep_id"],
                expected_generation=state["generation"],
            )
        self.assertEqual(result.elapsed_seconds, 15000)
        self.assertTrue(result.interrupted, "the event coincided with completion")
        self.assertTrue(result.completed, result)
        self.assertEqual(self.recorder.causes(), [AWAKENED_SKIP])


class _WatcherFixture:
    """Two live webclient watchers plus one Telnet control session."""

    def _install_watchers(self):
        import evennia

        clear_alignment_observers()
        clear_watchers()
        alignment.connect_alignment_observer()
        self.addCleanup(clear_alignment_observers)
        self.addCleanup(clear_watchers)
        get_world_clock()
        _clear_event_sources(self)
        self.registry = build_production_registry()
        self.action_registry = build_production_action_registry()
        self.sessions = []
        self.schedulers = []
        for index in (0, 1):
            session = FakeSession(sessid=80 + index)
            session.puppet = self.char1
            scheduler = QueuedScheduler()
            _coordinator(session, self.registry, scheduler=scheduler)
            self.sessions.append(session)
            self.schedulers.append(scheduler)
        self.telnet = FakeSession(sessid=89)
        self.telnet.protocol_key = "telnet"
        self.telnet.puppet = self.char1
        _coordinator(self.telnet, self.registry, scheduler=QueuedScheduler())
        self.sessionhandler = mock.patch.object(
            evennia.SESSION_HANDLER,
            "get_sessions",
            return_value=[*self.sessions, self.telnet],
        )
        self.sessionhandler.start()
        self.addCleanup(self.sessionhandler.stop)

    def _prepare_player(self):
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        write_fatigue_state(self.char1, 360000, SleepPosture.AWAKE)

    def _prime(self):
        for session, scheduler in zip(self.sessions, self.schedulers):
            coordinator = session.ndb.elosern_coordinator
            coordinator.full_snapshot(
                build_presentation_context(session, self.char1)
            )
            register_watcher(session)
            scheduler.run()
            session.sent.clear()
        register_watcher(self.telnet)
        self.telnet.sent.clear()

    def _drain(self):
        for scheduler in self.schedulers:
            scheduler.run()

    def _clear_all_sent(self):
        for session in (*self.sessions, self.telnet):
            session.sent.clear()

    def _spawn(self, key="合成哥布林"):
        monster = create_object(Monster, key=key, location=self.room1)
        monster.threat_tier = "low"
        monster.apply_monster_tier("floor")
        return monster

    def _envelope(self, session, action_id, payload, request_id):
        coordinator = session.ndb.elosern_coordinator
        return {
            "protocol_version": 1,
            "presentation_epoch": coordinator.epoch,
            "request_id": request_id,
            "base_revision": coordinator.revision,
            "action_id": action_id,
            "payload": payload,
        }

    def _result(self, session):
        return session.frames("ui_action_result")[-1]

    def _graphical_terminal_exit(self, session):
        """Drive one graphical party exit through its prompt and confirmation."""
        monster = self._spawn()
        engage(self.char1, monster)
        record = read_session(self.char1)
        operation = {
            "session_id": record.session_id,
            "round_revision": record.round_revision,
            "operation": PARTY_EXIT_SURRENDER,
        }
        handle_ui_action(
            session,
            self.char1,
            self._envelope(session, "combat.exit_prompt", dict(operation), "exit-1"),
            self.action_registry,
            self.registry,
        )
        self._drain()
        prompt = self._result(session)
        self._clear_all_sent()
        with self.captureOnCommitCallbacks(execute=True):
            handle_ui_action(
                session,
                self.char1,
                self._envelope(
                    session,
                    "combat.exit_confirm",
                    {
                        **operation,
                        "confirmation_token": prompt["data"]["confirmation_token"],
                    },
                    "exit-2",
                ),
                self.action_registry,
                self.registry,
            )
        self._drain()


class SettlementPublicationTests(BattlefieldIsolation, _WatcherFixture, EvenniaTest):
    """Every watcher receives one fresh complete snapshot for a checkpoint."""

    character_typeclass = PlayerCharacter
    room_typeclass = Room

    def setUp(self):
        super().setUp()
        self._prepare_player()
        self._install_watchers()
        self.recorder = _FactRecorder()
        register_alignment_observer(self.recorder)

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_graphical_terminal_combat_publishes_one_snapshot_then_its_result(self):
        self._prime()
        self._graphical_terminal_exit(self.sessions[0])

        for session in self.sessions:
            snapshots = session.frames("ui_snapshot")
            self.assertEqual(len(snapshots), 1, session.names())
            snapshot = snapshots[0]
            self.assertNotIn("base_revision", snapshot)
            self.assertEqual(snapshot["mode"], "exploration")
        # Only the initiating watcher carries the action result, and it follows
        # the fresh complete snapshot: no settlement delta is published first.
        initiator = self.sessions[0]
        names = initiator.names()
        self.assertEqual(
            names.index("ui_action_result"), names.index("ui_snapshot") + 1, names
        )
        self.assertEqual(
            initiator.frames("ui_action_result")[0]["presentation_revision"],
            initiator.frames("ui_snapshot")[0]["revision"],
        )
        self.assertEqual(self.telnet.sent, [], "Telnet receives no graphical state")

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_text_terminal_combat_publishes_one_snapshot(self):
        from commands.combat import CmdCombatForfeit

        self._prime()
        monster = self._spawn()
        engage(self.char1, monster)
        record = read_session(self.char1)
        prompt = request_party_exit(
            self.char1,
            record.session_id,
            record.round_revision,
            PARTY_EXIT_SURRENDER,
        )
        command = CmdCombatForfeit()
        command.caller = self.char1
        command.args = f"confirm {prompt['confirmation_token']}"
        with self.captureOnCommitCallbacks(execute=True):
            command.func()
        self._drain()

        self.assertIsNone(read_session(self.char1), "the text path settled terminally")
        for session in self.sessions:
            self.assertEqual(session.names(), ["ui_snapshot"])
            self.assertEqual(session.frames("ui_snapshot")[0]["mode"], "exploration")

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_completed_rest_publishes_one_snapshot(self):
        self._prime()
        session = self.sessions[0]
        with self.captureOnCommitCallbacks(execute=True):
            handle_ui_action(
                session,
                self.char1,
                self._envelope(session, "explore.wait", {"seconds": 600}, "wait-1"),
                self.action_registry,
                self.registry,
            )
        self._drain()

        self.assertEqual(
            [fact.cause for fact in self.recorder.facts], [AWAKENED_SKIP]
        )
        names = session.names()
        self.assertEqual(len(session.frames("ui_snapshot")), 1, names)
        self.assertEqual(
            names.index("ui_action_result"),
            names.index("ui_snapshot") + 1,
            names,
        )
        self.assertEqual(
            session.frames("ui_action_result")[0]["presentation_revision"],
            session.frames("ui_snapshot")[0]["revision"],
        )
        # The second watcher has no initiating action, so its checkpoint
        # arrives as the complete snapshot alone.
        self.assertEqual(len(self.sessions[1].frames("ui_snapshot")), 1)

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_zero_time_wait_publishes_a_delta_only(self):
        self._prime()
        session = self.sessions[0]
        with self.captureOnCommitCallbacks(execute=True):
            handle_ui_action(
                session,
                self.char1,
                self._envelope(session, "explore.wait", {"seconds": 0}, "wait-0"),
                self.action_registry,
                self.registry,
            )
        self._drain()

        self.assertEqual(session.frames("ui_snapshot"), [])
        self.assertIn("ui_action_result", session.names())

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_sleep_entry_publishes_a_delta_only(self):
        self._prime()
        session = self.sessions[0]
        with self.captureOnCommitCallbacks(execute=True):
            handle_ui_action(
                session,
                self.char1,
                self._envelope(session, "explore.wait", {"sleep": True}, "sleep-1"),
                self.action_registry,
                self.registry,
            )
        self._drain()

        self.assertEqual(
            session.frames("ui_snapshot"), [], "entry is not a settlement"
        )
        self.assertIn("ui_action_result", session.names())

    def test_a_retired_epoch_checkpoint_publishes_nothing(self):
        self._prime()
        record = read_session(self._engage_once())
        with self.captureOnCommitCallbacks(execute=True):
            settle_session(
                self.char1,
                record,
                reconstruct_battlefield(self.char1, record),
                "victory",
            )
        for session in self.sessions:
            session.ndb.elosern_coordinator.reset()
        self._drain()
        for session in self.sessions:
            self.assertEqual(session.sent, [])

    def _engage_once(self):
        monster = self._spawn()
        engage(self.char1, monster)
        return self.char1


class NonterminalRoundPublicationTests(BattlefieldIsolation, _WatcherFixture, EvenniaTest):
    """An ordinary continuing round publishes changed candidates only."""

    character_typeclass = PlayerCharacter
    room_typeclass = Room

    def setUp(self):
        open_synthetic_scope(self, "skills", extra=synth_innate_overlay())
        super().setUp()
        self._prepare_player()
        grant_lineage(self.char1, [_T_SINGLE])
        self._install_watchers()

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_a_nonterminal_round_publishes_a_delta_and_no_snapshot(self):
        self._prime()
        monster = self._spawn()
        engage(self.char1, monster)
        record = read_session(self.char1)
        session = self.sessions[0]
        with (
            mock.patch("world.rules.combat.battlefield.roll_d100", return_value=50),
            mock.patch("world.rules.combat.damage.roll_d100", return_value=50),
            mock.patch("world.rules.combat.rounds.roll_d100", return_value=50),
            mock.patch("world.rules.action.gates.roll_d100", return_value=50),
        ):
            handle_ui_action(
                session,
                self.char1,
                self._envelope(
                    session,
                    "combat.command",
                    {
                        "session_id": record.session_id,
                        "round_revision": record.round_revision,
                        "draft_version": record.draft_version,
                        "actor_id": int(self.char1.pk),
                        "command": {
                            "kind": "skill",
                            "payload": {
                                "skill_key": _T_SINGLE,
                                "target_ids": [int(monster.pk)],
                            },
                        },
                    },
                    "round-1",
                ),
                self.action_registry,
                self.registry,
            )
        self._drain()

        self.assertIsNotNone(read_session(self.char1), "the fight continues")
        self.assertEqual(session.frames("ui_snapshot"), [])
        self.assertIn("ui_update", session.names())
        self.assertEqual(self._result(session)["code"], "round_committed")
        self.assertEqual(
            self._result(session)["presentation_revision"],
            session.ndb.elosern_coordinator.revision,
        )


class TextTerminalRoundPublicationTests(BattlefieldIsolation, _WatcherFixture, EvenniaTest):
    """A text terminal round coalesces its preterminal work with the checkpoint."""

    character_typeclass = PlayerCharacter
    room_typeclass = Room

    def setUp(self):
        open_synthetic_scope(self, "skills", extra=synth_innate_overlay())
        super().setUp()
        self._prepare_player()
        grant_lineage(self.char1, [_T_SINGLE])
        self._install_watchers()
        self.recorder = _FactRecorder()
        register_alignment_observer(self.recorder)

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_a_text_terminal_round_coalesces_its_preterminal_work(self):
        from world.rules.combat_session import rounds as rounds_module

        self._prime()
        # The round's consequence scans run before the terminal settlement and
        # register their committed effects there, so they must already be in the
        # round owner's causal group.
        monster = self._spawn()
        monster.traits.hp.current = 1
        engage(self.char1, monster)
        record = read_session(self.char1)

        seen = {}
        real_scan = rounds_module._scan_friendly_fire

        def spy(*args, **kwargs):
            seen.setdefault("group", current_publication_group())
            return real_scan(*args, **kwargs)

        with (
            mock.patch.object(rounds_module, "_scan_friendly_fire", spy),
            mock.patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            mock.patch("world.rules.combat.damage.roll_d100", return_value=100),
            mock.patch("world.rules.combat.rounds.roll_d100", return_value=100),
            mock.patch("world.rules.action.gates.roll_d100", return_value=100),
            self.captureOnCommitCallbacks(execute=True),
        ):
            # The text owner: no dispatcher action group is active here.
            result = confirm_actor_command(
                self.char1,
                record.session_id,
                record.round_revision,
                record.draft_version,
                int(self.char1.pk),
                {
                    "kind": "skill",
                    "payload": {
                        "skill_key": _T_SINGLE,
                        "targets_or_shorthand": [int(monster.pk)],
                        "scale": 1.0,
                    },
                },
            )
        self.assertEqual(result.get("outcome"), "victory", result)
        self.assertIsNone(read_session(self.char1))
        self._drain()

        group = seen.get("group")
        self.assertIsNotNone(
            group, "the preterminal consequence work runs in the causal group"
        )
        self.assertEqual(
            [fact.group_id for fact in self.recorder.facts],
            [group.id],
            "the terminal checkpoint joins the round's own causal group",
        )
        for session in self.sessions:
            snapshots = session.frames("ui_snapshot")
            self.assertEqual(len(snapshots), 1, session.names())
            self.assertEqual(
                session.frames("ui_update"),
                [],
                "the settlement never separates its preterminal delta",
            )


class TerminalOpeningPublicationTests(BattlefieldIsolation, _WatcherFixture, EvenniaTest):
    """A field cast that starts and ends the fight is one checkpoint."""

    character_typeclass = PlayerCharacter
    room_typeclass = Room

    def setUp(self):
        open_synthetic_scope(self, "skills", extra=synth_innate_overlay())
        super().setUp()
        self._prepare_player()
        grant_lineage(self.char1, [_T_SINGLE])
        self._install_watchers()

    @covers_requirement("webclient-settlement-alignment::every-completed-combat-termination-is-a-fresh-checkpoint")
    def test_a_field_cast_opening_that_ends_the_fight_publishes_one_snapshot(self):
        from world.rules.combat_initiation import initiate_field_combat

        self._prime()
        monster = self._spawn()
        monster.traits.hp.current = 1
        # The fight never reaches combat mode, so a mode transition cannot hide
        # a missing checkpoint: the fresh complete snapshot is the checkpoint.
        with (
            mock.patch("world.rules.combat.battlefield.roll_d100", return_value=100),
            mock.patch("world.rules.combat.damage.roll_d100", return_value=100),
            mock.patch("world.rules.combat.rounds.roll_d100", return_value=100),
            self.captureOnCommitCallbacks(execute=True),
        ):
            result = initiate_field_combat(self.char1, _T_SINGLE, monster)
        self.assertEqual(result["outcome"], "victory", result)
        self.assertIsNone(read_session(self.char1))
        self._drain()

        for session in self.sessions:
            snapshots = session.frames("ui_snapshot")
            self.assertEqual(len(snapshots), 1, session.names())
            self.assertEqual(snapshots[0]["mode"], "exploration")


class CheckpointCompletenessTests(BattlefieldIsolation, _WatcherFixture, EvenniaTest):
    """A checkpoint renders every eager panel, not only the changed ones."""

    character_typeclass = PlayerCharacter
    room_typeclass = Room

    def setUp(self):
        super().setUp()
        self._prepare_player()
        clear_alignment_observers()
        clear_watchers()
        alignment.connect_alignment_observer()
        self.addCleanup(clear_alignment_observers)
        self.addCleanup(clear_watchers)
        get_world_clock()
        _clear_event_sources(self)
        self.state = {"status": 1, "party": "one"}
        self.map_calls = []
        registry = PresentationRegistry("settlement-alignment")
        for name in ("status", "party"):
            registry.register(
                PresenterSpec(
                    name=name,
                    schema_version=1,
                    unavailable_reason=("missing_data", "無法讀取"),
                    presenter=(
                        lambda context, _name=name: {
                            "available": True,
                            "value": self.state[_name],
                        }
                    ),
                )
            )
        registry.register(
            PresenterSpec(
                name="area_map",
                schema_version=1,
                unavailable_reason=("missing_data", "無法讀取"),
                presenter=self._unopened_map,
                on_demand=True,
            )
        )
        self.web = FakeSession(sessid=90)
        self.web.puppet = self.char1
        self.scheduler = QueuedScheduler()
        self.coordinator = PresentationCoordinator(
            self.web,
            registry,
            calendar_provider=lambda: SimpleNamespace(
                year=1204,
                season_index=2,
                season_name="仲夏",
                day_in_season=17,
                hour=14,
                minute=30,
                second=5,
            ),
            mode_provider=lambda context: "exploration",
            scheduler=self.scheduler,
        )
        self.web.ndb.elosern_coordinator = self.coordinator
        self.sessionhandler = mock.patch.object(
            __import__("evennia").SESSION_HANDLER,
            "get_sessions",
            return_value=[self.web],
        )
        self.sessionhandler.start()
        self.addCleanup(self.sessionhandler.stop)
        register_watcher(self.web)

    def _unopened_map(self, context):
        self.map_calls.append(context)
        return {"available": False}

    def _prime(self):
        self.coordinator.full_snapshot(
            build_presentation_context(self.web, self.char1)
        )
        self.scheduler.run()
        self.web.sent.clear()

    @covers_requirement(
        "webclient-settlement-alignment::completed-explicit-skips-align-after-authoritative-settlement"
    )
    def test_a_checkpoint_restores_a_deliberately_omitted_panel(self):
        self._prime()
        self.state["status"] = 2
        # The client is told only about ``party``; the changed status panel is
        # deliberately left out of that ordinary publication.
        self.coordinator.enqueue_publication(
            lambda: build_presentation_context(self.web, self.char1),
            candidate_panels={"party": {"available": True, "value": "one"}},
        )
        self.scheduler.run()
        self.assertFalse(
            any(
                frame.get("panels", {}).get("status")
                for frame in self.web.frames("ui_update")
            ),
            "the omitted candidate never reaches the client",
        )

        self.web.sent.clear()
        with self.captureOnCommitCallbacks(execute=True):
            advance_wait(self.char1, 600)
        self.scheduler.run()

        snapshots = self.web.frames("ui_snapshot")
        self.assertEqual(len(snapshots), 1)
        self.assertEqual(snapshots[0]["panels"]["status"]["value"], 2)
        self.assertEqual(self.web.frames("ui_update"), [])
        self.assertEqual(self.map_calls, [], "an unopened map presenter never runs")


if __name__ == "__main__":
    unittest.main()
