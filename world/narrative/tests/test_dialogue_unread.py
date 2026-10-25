"""Behavior test: durable unread observation and live unlock batches.

Pins ``authored-dialogue-unread-notices`` (Shared contract v2):

- ``observe_availability`` classifies per stable topic ID: a first-seen topic
  (a first visit, or a newly permitted generated phase) is recorded without an
  unlock notice, a previously observed locked/hidden topic that opens is one
  pending announcement while unread, and refusal playback, a variant change
  and relock/reopen never reset completion or re-announce;
- ``claim_unlock_batch`` consumes a pending batch at most once;
- the committed fan-out observes the live conversation, claims before any
  push, wraps the claimed batch per current watcher with that watcher's own
  host/context, never ships it in a snapshot, consumes it with no watcher,
  ships nothing for a rolled-back write and still pushes the plain panel when
  observation fails.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from web.webclient.presentation import watchers
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.coordinator import PresentationCoordinator
from web.webclient.presentation.registry import build_production_registry
from world.lore.dialogue.conditions import RaceIs
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic
from world.lore.scenes import Scene, Speech
from world.narrative.dialogue_reading import (
    MAX_PENDING_BATCH_TOPICS,
    READING_ATTRIBUTE,
    claim_unlock_batch,
    observe_availability,
    reading_for,
    reading_revision,
    record_completion,
)
from world.quests.catalog import register_catalog
from world.rules.affinity_config import get_config
from world.rules.dialogue import (
    clear_dialogue_session,
    complete_dialogue_delivery,
    live_dialogue_session,
    open_or_refresh_dialogue,
    select_authored_topic,
)
from world.rules.dialogue_availability import refresh_dialogue_availability
from world.rules.dialogue_context import host_dialogue_binding
from world.tests.synthetic_data import SYNTH_RACES, synthetic_registries

_HOST = "s:t_unread_keeper"
_TABLE_KEY = "t_unread_keeper"
_OPEN = f"{_TABLE_KEY}.open"
_LOCKED = f"{_TABLE_KEY}.locked"
_HIDDEN = f"{_TABLE_KEY}.hidden"
_SECOND = f"{_TABLE_KEY}.second"
_CHAIN = f"{_TABLE_KEY}.chain"
_RACE_KEY = next(iter(SYNTH_RACES))
_OTHER_RACE = next(key for key in SYNTH_RACES if key != _RACE_KEY)

_CALENDAR = SimpleNamespace(
    year=1,
    season_index=0,
    season_name="春季",
    day_in_season=3,
    hour=12,
    minute=0,
    second=0,
)


def _scene(scene_id: str, text: str) -> Scene:
    return Scene(
        scene_id=scene_id,
        revision="r1",
        lines=(
            Speech(speaker="actor", text="合成問句。"),
            Speech(speaker="host", text=text),
        ),
    )


def _dialogue() -> AuthoredDialogue:
    gate = RaceIs(race_key=_OTHER_RACE)
    return AuthoredDialogue(
        greeting="合成守門人抬眼。",
        topics=(
            AuthoredTopic(
                topic_id=_OPEN,
                keyword="合成路況",
                label="合成路況",
                fallback=_scene("t_unread_open", "合成路況內文"),
            ),
            AuthoredTopic(
                topic_id=_CHAIN,
                keyword="合成接續",
                label="合成接續",
                fallback=_scene("t_unread_chain", "合成接續內文"),
                predecessors=(_OPEN,),
                disclosure="pure_chain",
            ),
            AuthoredTopic(
                topic_id=_LOCKED,
                keyword="合成霧門",
                label="合成霧門",
                fallback=_scene("t_unread_locked", "合成霧門內文"),
                requires=gate,
                unavailable="locked",
                refusal=_scene("t_unread_refusal", "合成婉拒內文"),
            ),
            AuthoredTopic(
                topic_id=_HIDDEN,
                keyword="合成密語",
                label="合成密語",
                fallback=_scene("t_unread_hidden", "合成密語內文"),
                requires=gate,
                unavailable="hidden",
            ),
            AuthoredTopic(
                topic_id=_SECOND,
                keyword="合成舊渡",
                label="合成舊渡",
                fallback=_scene("t_unread_second", "合成舊渡內文"),
                requires=gate,
                unavailable="locked",
                refusal=_scene("t_unread_second_refusal", "合成舊渡婉拒"),
            ),
        ),
    )


class _OwnerBase(EvenniaTest):
    def setUp(self) -> None:
        super().setUp()
        # The affinity rulebook resolves its cap-break quest keys against the
        # shipped catalog before the synthetic scope replaces it.
        register_catalog()
        get_config()
        scope = synthetic_registries(
            "races", "dialogue", extra={"dialogue": {_TABLE_KEY: _dialogue()}}
        )
        scope.__enter__()
        self.addCleanup(scope.__exit__, None, None, None)
        self.room = create_object(Room, key="合成未讀廳")
        self.player = create_object(PlayerCharacter, key="合成未讀玩家")
        self.player.race = _RACE_KEY
        self.player.apply_race_baseline()
        self.player.location = self.room


class ObservationSemanticsTests(_OwnerBase):
    """Pure per-topic classification through the narrative API."""

    def _observe(self, open_ids, declared=None, *, quiet=(), host=_HOST, initial=False):
        return observe_availability(
            self.player,
            host,
            open_ids,
            declared_topic_ids=declared if declared is not None else ("a", "b", "c"),
            initial=initial,
            quiet_topic_ids=quiet,
        )

    def _row(self, topic_id, host=_HOST):
        return reading_for(self.player, host).topics[topic_id]

    def test_first_observation_records_open_as_announced_without_a_batch(self):
        self.assertIsNone(self._observe(("a",), initial=True))
        host = reading_for(self.player, _HOST)
        self.assertTrue(host.initialized)
        self.assertEqual(
            (self._row("a").ever_open, self._row("a").announced), (True, True)
        )
        for locked in ("b", "c"):
            self.assertEqual(
                (self._row(locked).ever_open, self._row(locked).announced),
                (False, False),
            )
        self.assertIsNone(host.pending_batch)
        # Observation never moves the completion revision.
        self.assertEqual(reading_revision(self.player), 0)

    def test_a_canonical_refresh_first_observation_initializes_silently(self):
        self.assertIsNone(self._observe(("a", "b"), initial=False))
        self.assertTrue(reading_for(self.player, _HOST).initialized)
        self.assertTrue(self._row("b").announced)

    def test_a_later_opening_is_one_pending_batch_and_claims_once(self):
        self._observe(("a",), initial=True)
        batch = self._observe(("a", "b", "c"))
        self.assertEqual(batch.topic_ids, ("b", "c"))
        self.assertEqual(batch.host_key, _HOST)
        # A duplicate refresh before the claim keeps the same batch.
        again = self._observe(("a", "b", "c"))
        self.assertEqual(again.batch_id, batch.batch_id)
        claimed = claim_unlock_batch(self.player, batch.batch_id)
        self.assertEqual(claimed, batch)
        self.assertIsNone(claim_unlock_batch(self.player, batch.batch_id))
        self.assertTrue(self._row("b").announced)
        self.assertIsNone(reading_for(self.player, _HOST).pending_batch)
        self.assertIsNone(self._observe(("a", "b", "c")))

    def test_read_and_unread_topics_relock_and_reopen_without_a_new_batch(self):
        self._observe(("a",), initial=True)
        batch = self._observe(("a", "b", "c"))
        claim_unlock_batch(self.player, batch.batch_id)
        record_completion(self.player, host_key=_HOST, topic_id="b")
        self.assertIsNone(self._observe(("a",)))  # both relock
        self.assertIsNone(self._observe(("a", "b", "c")))  # both reopen
        self.assertTrue(self._row("b").completed)
        self.assertFalse(self._row("c").completed)
        self.assertTrue(self._row("c").announced)

    def test_a_relock_before_the_claim_keeps_the_topic_eligible(self):
        self._observe(("a",), initial=True)
        self._observe(("a", "b"))
        self.assertIsNone(self._observe(("a",)))
        self.assertFalse(self._row("b").announced)
        reopened = self._observe(("a", "b"))
        self.assertEqual(reopened.topic_ids, ("b",))

    def test_completion_before_the_claim_suppresses_the_announcement(self):
        self._observe(("a",), initial=True)
        self._observe(("a", "b"))
        record_completion(self.player, host_key=_HOST, topic_id="b")
        self.assertIsNone(self._observe(("a", "b")))
        self.assertTrue(self._row("b").announced)

    def test_a_completed_but_unobserved_topic_opens_silently(self):
        self._observe((), initial=True)
        record_completion(self.player, host_key=_HOST, topic_id="a")
        self.assertIsNone(self._observe(("a",)))

    def test_a_quiet_chain_successor_opens_without_a_notice(self):
        self._observe(("a",), initial=True)
        self.assertIsNone(self._observe(("a", "b"), quiet=("b",)))
        self.assertTrue(self._row("b").ever_open)
        self.assertTrue(self._row("b").announced)

    def test_new_phase_ids_initialize_and_phase_return_keeps_history(self):
        phase_1 = ("phase_1.a", "phase_1.b")
        phase_2 = ("phase_2.a", "phase_2.b")
        self._observe(("phase_1.a",), phase_1, initial=True)
        pending = self._observe(phase_1, phase_1)
        self.assertEqual(pending.topic_ids, ("phase_1.b",))
        record_completion(self.player, host_key=_HOST, topic_id="phase_1.a")
        # The phase changes before the claim: phase-2 IDs are first-seen even
        # though the host is initialized, and phase-1's pending notice retires.
        self.assertIsNone(self._observe(("phase_2.a",), phase_2))
        self.assertTrue(self._row("phase_2.a").announced)
        self.assertFalse(self._row("phase_2.b").ever_open)
        self.assertTrue(self._row("phase_1.b").announced)
        self.assertIsNone(reading_for(self.player, _HOST).pending_batch)
        # Returning to phase 1 keeps completion and creates no notice.
        self.assertIsNone(self._observe(phase_1, phase_1))
        self.assertTrue(self._row("phase_1.a").completed)

    def test_a_batch_holds_at_most_sixteen_topics_and_the_rest_follow(self):
        declared = tuple(f"t{index:02d}" for index in range(20))
        self._observe((), declared, initial=True)
        first = self._observe(declared, declared)
        self.assertEqual(len(first.topic_ids), MAX_PENDING_BATCH_TOPICS)
        self.assertEqual(first.topic_ids, declared[:16])
        claim_unlock_batch(self.player, first.batch_id)
        second = self._observe(declared, declared)
        self.assertEqual(second.topic_ids, declared[16:])
        self.assertNotEqual(second.batch_id, first.batch_id)

    def test_hosts_and_owners_stay_independent(self):
        self._observe(("a",), initial=True)
        self._observe(("a", "b"))
        other_host = "s:t_unread_other"
        self.assertIsNone(self._observe(("a", "b"), host=other_host, initial=True))
        other = create_object(PlayerCharacter, key="合成未讀他人")
        self.assertIsNone(reading_for(other, _HOST))
        self.assertIsNotNone(reading_for(self.player, _HOST).pending_batch)

    def test_a_failed_write_restores_the_cached_record(self):
        self._observe(("a",), initial=True)
        before = self.player.attributes.get(READING_ATTRIBUTE)
        with patch(
            "world.narrative.dialogue_reading._write_record",
            side_effect=RuntimeError("disk"),
        ):
            with self.assertRaises(RuntimeError):
                self._observe(("a", "b"))
        self.assertEqual(self.player.attributes.get(READING_ATTRIBUTE), before)
        self.assertIsNone(reading_for(self.player, _HOST).pending_batch)


class LiveUnlockBatchTests(_OwnerBase):
    """The committed fan-out: observe, claim, then wrap per watcher."""

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def setUp(self) -> None:
        super().setUp()
        watchers.clear_watchers()
        self.addCleanup(watchers.clear_watchers)
        self.host = create_object(NPC, key="合成未讀守門人", location=self.room)
        self.host.components.add(
            ScriptedDialogue.create(self.host, dialogue_key=_TABLE_KEY)
        )
        self.host_key = host_dialogue_binding(self.host)[0]
        self.registry = build_production_registry()
        self._next_sessid = 960

    def tearDown(self) -> None:
        clear_dialogue_session(self.player)
        super().tearDown()

    # -- helpers ---------------------------------------------------------

    def _watch(self, puppet):
        real = ServerSession()
        real.init_session("webclient/websocket", ("localhost", 9999), self.sessionhandler)
        self._next_sessid += 1
        real.sessid = self._next_sessid
        self.sessionhandler[real.sessid] = real
        real.protocol_key = "webclient/websocket"
        real.puppet = puppet
        puppet.sessions.add(real)
        recorded: list[dict] = []
        real.msg = lambda **kwargs: recorded.append(kwargs)
        coordinator = PresentationCoordinator(
            real, self.registry, calendar_provider=lambda: _CALENDAR
        )
        real.ndb.elosern_coordinator = coordinator
        coordinator.full_snapshot(PresentationContext(actor=puppet, protocol_version=1))
        watchers.register_watcher(real)
        sessid = real.sessid
        self.addCleanup(lambda: self.sessionhandler.__delitem__(sessid))
        return real, coordinator, recorded

    @staticmethod
    def _dialogue_updates(recorded):
        return [
            call["ui_update"][0][0]["panels"]["dialogue"]
            for call in recorded
            if "ui_update" in call and "dialogue" in call["ui_update"][0][0]["panels"]
        ]

    @staticmethod
    def _snapshot_batches(recorded):
        return [
            call["ui_snapshot"][0][0]["panels"].get("dialogue", {}).get("unlock_batch")
            for call in recorded
            if "ui_snapshot" in call
        ]

    def _open(self):
        with self.captureOnCommitCallbacks(execute=True):
            open_or_refresh_dialogue(self.player, self.host, "合成守門人抬眼。")
        return live_dialogue_session(self.player)

    def _unlock(self, cause="social_identity"):
        self.player.race = _OTHER_RACE
        with self.captureOnCommitCallbacks(execute=True):
            refresh_dialogue_availability(self.player, cause=cause)

    def _row(self, topic_id):
        return reading_for(self.player, self.host_key).topics[topic_id]

    # -- behavior --------------------------------------------------------

    def test_initial_open_marks_unread_without_a_batch(self):
        _real, _coordinator, recorded = self._watch(self.player)
        self._open()
        updates = self._dialogue_updates(recorded)
        self.assertTrue(updates)
        panel = updates[-1]
        self.assertIsNone(panel["unlock_batch"])
        choices = {row["topic_id"]: row for row in panel["choices"]}
        self.assertTrue(choices[_OPEN]["unread"])
        self.assertEqual(choices[_LOCKED]["availability"], "locked")
        self.assertFalse(choices[_LOCKED]["unread"])
        self.assertNotIn(_HIDDEN, choices)
        self.assertTrue(self._row(_OPEN).announced)
        self.assertFalse(self._row(_LOCKED).ever_open)
        self.assertFalse(self._row(_HIDDEN).ever_open)

    def test_refusal_then_unlock_is_one_batch_for_every_owner_connection(self):
        self._open()
        session = live_dialogue_session(self.player)
        with self.captureOnCommitCallbacks(execute=True):
            refusal = select_authored_topic(
                self.player,
                self.host,
                _LOCKED,
                selection_id="sel-refusal",
                expected_context_id=session.context_id,
            )
        self.assertEqual(refusal.kind, "refusal")
        self.assertFalse(self._row(_LOCKED).ever_open)
        self.assertEqual(reading_revision(self.player), 0)

        _first, _c1, recorded_1 = self._watch(self.player)
        _second, _c2, recorded_2 = self._watch(self.player)
        other = create_object(PlayerCharacter, key="合成同帳號他角")
        other.location = self.room
        _third, _c3, recorded_3 = self._watch(other)
        with patch("world.rules.dialogue_availability.log_info") as log_info:
            self._unlock()
        claimed_events = [
            call for call in log_info.call_args_list
            if call.args and call.args[0] == "dialogue_unlock_batch_claimed"
        ]
        self.assertEqual(len(claimed_events), 1)
        self.assertEqual(claimed_events[0].kwargs["context"]["topics"], 3)

        live = live_dialogue_session(self.player)
        batches = [
            self._dialogue_updates(recorded)[-1]["unlock_batch"]
            for recorded in (recorded_1, recorded_2)
        ]
        self.assertEqual(batches[0], batches[1])
        batch = batches[0]
        self.assertEqual(batch["host_id"], self.host.pk)
        self.assertEqual(batch["context_id"], live.context_id)
        # Locked and hidden topics observed earlier both announce, in
        # declaration order.
        self.assertEqual(batch["topic_ids"], [_LOCKED, _HIDDEN, _SECOND])
        self.assertEqual(self._dialogue_updates(recorded_3), [])
        panel = self._dialogue_updates(recorded_1)[-1]
        choices = {row["topic_id"]: row for row in panel["choices"]}
        self.assertTrue(choices[_LOCKED]["unread"])
        self.assertTrue(choices[_HIDDEN]["unread"])

        # A duplicate refresh claims nothing further and a reconnect snapshot
        # never carries the batch.
        with self.captureOnCommitCallbacks(execute=True):
            refresh_dialogue_availability(self.player, cause="duplicate")
        self.assertIsNone(self._dialogue_updates(recorded_1)[-1]["unlock_batch"])
        _fresh, coordinator, fresh_recorded = self._watch(self.player)
        coordinator.full_snapshot(PresentationContext(actor=self.player, protocol_version=1))
        self.assertEqual(set(self._snapshot_batches(fresh_recorded)), {None})
        self.assertTrue(
            {row["topic_id"]: row for row in self._dialogue_updates(recorded_1)[-1]["choices"]}[
                _LOCKED
            ]["unread"]
        )

    def test_no_watcher_consumes_the_batch_and_keeps_unread_markers(self):
        self._open()
        self._unlock()
        self.assertTrue(self._row(_LOCKED).announced)
        self.assertIsNone(reading_for(self.player, self.host_key).pending_batch)
        _real, coordinator, recorded = self._watch(self.player)
        self.assertEqual(set(self._snapshot_batches(recorded)), {None})
        snapshot = [call for call in recorded if "ui_snapshot" in call][-1]
        choices = {
            row["topic_id"]: row
            for row in snapshot["ui_snapshot"][0][0]["panels"]["dialogue"]["choices"]
        }
        self.assertTrue(choices[_LOCKED]["unread"])

    def test_a_rolled_back_write_observes_nothing(self):
        from django.db import transaction

        self._open()
        self.player.race = _OTHER_RACE
        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            try:
                with transaction.atomic():
                    refresh_dialogue_availability(self.player, cause="quest_state")
                    raise RuntimeError("owning write rolled back")
            except RuntimeError:
                pass
        self.assertEqual(list(callbacks), [])
        self.assertFalse(self._row(_LOCKED).ever_open)

    def test_completion_survives_relock_and_reopen_without_another_batch(self):
        self._open()
        _real, _coordinator, recorded = self._watch(self.player)
        self._unlock()
        session = live_dialogue_session(self.player)
        with self.captureOnCommitCallbacks(execute=True):
            delivery = select_authored_topic(
                self.player,
                self.host,
                _LOCKED,
                selection_id="sel-formal",
                expected_context_id=session.context_id,
            )
        self.assertEqual(delivery.kind, "formal")
        with self.captureOnCommitCallbacks(execute=True):
            complete_dialogue_delivery(
                self.player,
                delivery_id=delivery.delivery_id,
                context_id=delivery.context_id,
                topic_id=delivery.topic_id,
                scene_revision=delivery.scene_revision,
            )
        self.player.race = _RACE_KEY
        with self.captureOnCommitCallbacks(execute=True):
            refresh_dialogue_availability(self.player, cause="social_identity")
        self._unlock()
        panel = self._dialogue_updates(recorded)[-1]
        self.assertIsNone(panel["unlock_batch"])
        choices = {row["topic_id"]: row for row in panel["choices"]}
        self.assertFalse(choices[_LOCKED]["unread"])
        self.assertTrue(choices[_SECOND]["unread"])
        self.assertTrue(self._row(_LOCKED).completed)

    def test_an_observation_failure_still_pushes_the_plain_panel(self):
        self._open()
        _real, _coordinator, recorded = self._watch(self.player)
        before = len(self._dialogue_updates(recorded))
        self.player.race = _OTHER_RACE
        with patch(
            "world.narrative.dialogue_reading.observe_availability",
            side_effect=RuntimeError("storage"),
        ), patch("world.rules.dialogue_availability.log_warn") as log_warn:
            with self.captureOnCommitCallbacks(execute=True):
                refresh_dialogue_availability(self.player, cause="inventory")
        self.assertEqual(
            log_warn.call_args_list[0].args[0], "dialogue_unlock_observation_failed"
        )
        updates = self._dialogue_updates(recorded)
        self.assertGreater(len(updates), before)
        self.assertIsNone(updates[-1]["unlock_batch"])
        self.assertFalse(self._row(_LOCKED).ever_open)

    def test_a_freeform_host_is_never_observed(self):
        plain = create_object(NPC, key="合成閒聊者", location=self.room)
        with patch(
            "world.narrative.dialogue_reading.observe_availability"
        ) as observe, self.captureOnCommitCallbacks(execute=True):
            open_or_refresh_dialogue(self.player, plain, "閒聊。")
        observe.assert_not_called()

    def test_a_context_owner_other_than_the_refreshed_owner_observes_nothing(self):
        from types import SimpleNamespace as _NS

        from world.rules import dialogue_availability

        self._open()
        stranger = create_object(PlayerCharacter, key="合成他人主人")
        session = live_dialogue_session(self.player)
        foreign = _NS(owner=stranger, host_key=self.host_key)
        with patch(
            "world.rules.dialogue_context.resolve_dialogue_context",
            return_value=foreign,
        ), patch(
            "world.narrative.dialogue_reading.observe_availability"
        ) as observe, patch(
            "world.rules.dialogue_availability.log_warn"
        ) as log_warn:
            claimed = dialogue_availability._observe_unlocks(
                self.player, self.player, session, "inventory"
            )
        self.assertIsNone(claimed)
        observe.assert_not_called()
        self.assertEqual(
            log_warn.call_args.kwargs["context"]["reason"], "owner_mismatch"
        )
