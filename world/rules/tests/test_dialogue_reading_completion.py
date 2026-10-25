"""Behavior test: formal reading receipts, completion and public chains.

Pins the session-writer half of Shared contract v2: formal deliveries issue
bounded server receipts, completion accepts only a retained receipt of the
current authenticated context, duplicate/foreign/stale/refusal/out-of-order
claims write nothing, a delayed completion from an earlier topic never
replaces the playing scene, possession shares the owner's reading, a
rematerialized host keeps its logical record, and only an accepted completion
queues the availability refresh.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from typeclasses.characters import PlayerCharacter
from typeclasses.components import ScriptedDialogue
from typeclasses.npcs import NPC
from typeclasses.rooms import Room
from world.lore.dialogue.conditions import RaceIs
from world.lore.dialogue.shape import AuthoredDialogue, AuthoredTopic
from world.lore.scenes import Scene, Speech
from world.narrative.dialogue_reading import completed_topic_ids
from world.rules.dialogue import (
    COMPLETION_CLOSED,
    COMPLETION_PREDECESSOR_UNREAD,
    COMPLETION_RECEIPT_KIND,
    COMPLETION_RECEIPT_STALE,
    COMPLETION_RECEIPT_UNKNOWN,
    MAX_COMPLETION_RECEIPTS,
    MAX_RECEIPTS_PER_TOPIC,
    DialogueCompletionError,
    _parse_dialogue_session,
    chain_deliveries,
    clear_dialogue_session,
    complete_dialogue_delivery,
    live_dialogue_session,
    select_authored_topic,
)
from world.rules.dialogue_context import host_dialogue_binding
from world.rules.affinity_config import get_config
from world.rules.party import join_party
from world.rules.possession import enter_possession, release_possession
from world.quests.catalog import register_catalog
from world.tests.synthetic_data import SYNTH_RACES, synthetic_registries

_TABLE_KEY = "t_reading_keeper"
_ROOT = f"{_TABLE_KEY}.root"
_CHILD = f"{_TABLE_KEY}.child"
_GRANDCHILD = f"{_TABLE_KEY}.grandchild"
_QUALIFIED = f"{_TABLE_KEY}.qualified"
_LOCKED = f"{_TABLE_KEY}.locked"
_RACE_KEY = next(iter(SYNTH_RACES))
_OTHER_RACE = next(key for key in SYNTH_RACES if key != _RACE_KEY)


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
    return AuthoredDialogue(
        greeting="合成櫃檯後的人抬眼。",
        topics=(
            AuthoredTopic(
                topic_id=_ROOT,
                keyword="合成起頭",
                label="合成起頭",
                fallback=_scene("t_reading_root", "合成起頭內文"),
            ),
            AuthoredTopic(
                topic_id=_CHILD,
                keyword="合成接續",
                label="合成接續",
                fallback=_scene("t_reading_child", "合成接續內文"),
                predecessors=(_ROOT,),
                disclosure="pure_chain",
            ),
            AuthoredTopic(
                topic_id=_GRANDCHILD,
                keyword="合成再續",
                label="合成再續",
                fallback=_scene("t_reading_grandchild", "合成再續內文"),
                predecessors=(_CHILD,),
                disclosure="pure_chain",
            ),
            AuthoredTopic(
                topic_id=_QUALIFIED,
                keyword="合成資格",
                label="合成資格",
                fallback=_scene("t_reading_qualified", "合成資格內文"),
                requires=RaceIs(race_key=_OTHER_RACE),
                predecessors=(_ROOT,),
            ),
            AuthoredTopic(
                topic_id=_LOCKED,
                keyword="合成婉拒",
                label="合成婉拒",
                fallback=_scene("t_reading_locked_formal", "合成鎖定內文"),
                requires=RaceIs(race_key=_OTHER_RACE),
                unavailable="locked",
                refusal=_scene("t_reading_locked_refusal", "合成婉拒內文"),
            ),
        ),
    )


class DialogueReadingCompletionTests(EvenniaTest):
    """Receipt issuance, completion acceptance and rejection."""

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
        self.room = create_object(Room, key="合成閱讀廳")
        self.player = create_object(PlayerCharacter, key="合成閱讀玩家")
        self.player.race = _RACE_KEY
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.host = self._new_host()

    def tearDown(self) -> None:
        clear_dialogue_session(self.player)
        if self.player.db.possession:
            release_possession(self.player, reason="handback")
        super().tearDown()

    def _new_host(self) -> NPC:
        host = create_object(NPC, key="合成閱讀店主", location=self.room)
        host.components.add(ScriptedDialogue.create(host, dialogue_key=_TABLE_KEY))
        return host

    # -- helpers ---------------------------------------------------------

    def _select(self, topic_id: str, *, selection_id: str = "sel-1"):
        session = live_dialogue_session(self.player)
        return select_authored_topic(
            self.player,
            self.host,
            topic_id,
            selection_id=selection_id,
            expected_context_id=session.context_id if session is not None else None,
        )

    def _ack(self, delivery, *, player=None, **overrides):
        actor = player or self.player
        return complete_dialogue_delivery(
            actor,
            delivery_id=overrides.get("delivery_id", delivery.delivery_id),
            context_id=overrides.get("context_id", delivery.context_id),
            topic_id=overrides.get("topic_id", delivery.topic_id),
            scene_revision=overrides.get("scene_revision", delivery.scene_revision),
        )

    def _host_key(self) -> str:
        return host_dialogue_binding(self.host)[0]

    # -- issuance --------------------------------------------------------

    def test_formal_selection_issues_a_receipt_and_a_refusal_does_not(self):
        delivery = self._select(_ROOT)
        session = live_dialogue_session(self.player)
        receipts = session.completion_receipts
        self.assertEqual(len(receipts), 3)  # root + two public successors
        self.assertEqual(receipts[0]["delivery_id"], delivery.delivery_id)
        self.assertEqual(receipts[0]["topic_id"], _ROOT)
        self.assertEqual(receipts[0]["predecessors"], [])
        self.assertEqual(receipts[1]["topic_id"], _CHILD)
        self.assertEqual(receipts[1]["predecessors"], [_ROOT])
        self.assertEqual(receipts[1]["kind"], "formal")
        chain = chain_deliveries(session, self.host, actor=self.player)
        self.assertEqual(
            [node.delivery.topic_id for node in chain], [_CHILD, _GRANDCHILD]
        )
        self.assertNotIn(
            _QUALIFIED, [node.delivery.topic_id for node in chain]
        )

        clear_dialogue_session(self.player)
        refusal = self._select(_LOCKED, selection_id="sel-locked")
        self.assertEqual(refusal.kind, "refusal")
        self.assertEqual(live_dialogue_session(self.player).completion_receipts, ())

    # -- acceptance and idempotency --------------------------------------

    def test_duplicate_acks_from_two_connection_snapshots_are_monotonic(self):
        delivery = self._select(_ROOT)
        stored = self.player.db.dialogue_session
        first_snapshot = _parse_dialogue_session(stored)
        second_snapshot = _parse_dialogue_session(stored)
        self.assertIsNotNone(first_snapshot)
        self.assertIsNotNone(second_snapshot)

        first = self._ack(delivery)
        self.assertEqual((first.status, first.reading_revision), ("saved", 1))
        second = self._ack(delivery)
        self.assertEqual(
            (second.status, second.reading_revision), ("already_saved", 1)
        )
        self.assertEqual(
            completed_topic_ids(self.player, self._host_key()), (_ROOT,)
        )

    def test_already_saved_requires_the_receipt_in_the_current_set(self):
        delivery = self._select(_ROOT)
        self._ack(delivery)
        # A retired context discards its receipts, so a replayed claim cannot
        # ride the saved reading record.
        clear_dialogue_session(self.player)
        with self.assertRaises(DialogueCompletionError) as caught:
            self._ack(delivery)
        self.assertEqual(caught.exception.code, COMPLETION_CLOSED)

    # -- rejection -------------------------------------------------------

    def test_unknown_and_forged_claims_write_nothing(self):
        delivery = self._select(_ROOT)
        for overrides, code in (
            ({"delivery_id": "0000000000000000"}, COMPLETION_RECEIPT_UNKNOWN),
            ({"scene_revision": "r9"}, COMPLETION_RECEIPT_STALE),
            ({"topic_id": _CHILD}, COMPLETION_RECEIPT_STALE),
            ({"context_id": "ffffffffffffffff"}, COMPLETION_RECEIPT_STALE),
        ):
            with self.subTest(code=code):
                with self.assertRaises(DialogueCompletionError) as caught:
                    self._ack(delivery, **overrides)
                self.assertEqual(caught.exception.code, code)
        self.assertEqual(completed_topic_ids(self.player, self._host_key()), ())
        # The unmodified claim still succeeds afterwards.
        self.assertEqual(self._ack(delivery).status, "saved")

    def test_refusal_delivery_never_holds_an_acknowledgeable_receipt(self):
        refusal = self._select(_LOCKED)
        with self.assertRaises(DialogueCompletionError) as caught:
            self._ack(refusal)
        self.assertEqual(caught.exception.code, COMPLETION_RECEIPT_UNKNOWN)
        self.assertNotEqual(caught.exception.code, COMPLETION_RECEIPT_KIND)

    def test_successor_ack_before_its_predecessor_is_refused(self):
        delivery = self._select(_ROOT)
        session = live_dialogue_session(self.player)
        child = chain_deliveries(session, self.host, actor=self.player)[0]
        with self.assertRaises(DialogueCompletionError) as caught:
            self._ack(child.delivery)
        self.assertEqual(caught.exception.code, COMPLETION_PREDECESSOR_UNREAD)
        self.assertEqual(completed_topic_ids(self.player, self._host_key()), ())

        self._ack(delivery)
        self.assertEqual(self._ack(child.delivery).status, "saved")
        self.assertEqual(
            completed_topic_ids(self.player, self._host_key()), (_ROOT, _CHILD)
        )

    # -- delayed completion and control ----------------------------------

    def test_delayed_topic_a_completion_keeps_topic_b_playing(self):
        topic_a = self._select(_ROOT, selection_id="sel-a")
        topic_b = self._select(_LOCKED, selection_id="sel-b")
        self.assertEqual(topic_b.kind, "refusal")
        # B is a refusal and records no receipt, so it cannot be acknowledged;
        # the scene it replaced stays the current playback either way.
        with self.assertRaises(DialogueCompletionError):
            self._ack(topic_b)
        self.assertEqual(self._ack(topic_a).status, "saved")
        session = live_dialogue_session(self.player)
        self.assertEqual(session.delivery.delivery_id, topic_b.delivery_id)
        self.assertEqual(session.delivery.topic_id, _LOCKED)
        self.assertEqual(
            completed_topic_ids(self.player, self._host_key()), (_ROOT,)
        )

    def test_possession_completion_belongs_to_the_owner(self):
        # The EvenniaTest account character owns a lawful possession: the
        # companion acts, the owner's reading record changes.
        owner = self.char1
        owner.location = self.room
        owner.race = _RACE_KEY
        owner.apply_race_baseline()
        companion = create_object(NPC, key="合成閱讀同伴", location=self.room)
        companion.race = _RACE_KEY
        companion.apply_race_baseline()
        join_party(companion, owner)
        enter_possession(owner, companion)
        self.addCleanup(release_possession, owner, companion, "handback")

        delivery = select_authored_topic(
            companion,
            self.host,
            _ROOT,
            selection_id="sel-possessed",
            expected_context_id=None,
        )
        outcome = complete_dialogue_delivery(
            companion,
            delivery_id=delivery.delivery_id,
            context_id=delivery.context_id,
            topic_id=delivery.topic_id,
            scene_revision=delivery.scene_revision,
        )
        self.assertEqual(outcome.status, "saved")
        self.assertEqual(completed_topic_ids(owner, self._host_key()), (_ROOT,))
        self.assertEqual(completed_topic_ids(companion, self._host_key()), ())

        release_possession(owner, reason="handback")
        clear_dialogue_session(owner)
        self.assertEqual(completed_topic_ids(owner, self._host_key()), (_ROOT,))

    def test_rematerialized_host_keeps_the_logical_record(self):
        delivery = self._select(_ROOT)
        self._ack(delivery)
        host_key = self._host_key()
        self.host.delete()
        clear_dialogue_session(self.player)
        self.host = self._new_host()
        self.assertEqual(host_dialogue_binding(self.host)[0], host_key)
        self.assertEqual(completed_topic_ids(self.player, host_key), (_ROOT,))
        # The new physical host starts a new context; the old receipt is gone.
        with self.assertRaises(DialogueCompletionError):
            self._ack(delivery)

    def test_receipt_set_stays_bounded_and_retires_the_oldest(self):
        deliveries = [
            self._select(_ROOT, selection_id=f"sel-{index}") for index in range(3)
        ]
        session = live_dialogue_session(self.player)
        self.assertLessEqual(len(session.completion_receipts), MAX_COMPLETION_RECEIPTS)
        same_topic = [
            receipt
            for receipt in session.completion_receipts
            if receipt["topic_id"] == _ROOT
        ]
        self.assertEqual(len(same_topic), MAX_RECEIPTS_PER_TOPIC)
        self.assertEqual(same_topic[-1]["delivery_id"], deliveries[-1].delivery_id)
        with self.assertRaises(DialogueCompletionError):
            self._ack(deliveries[0])
        self.assertEqual(self._ack(deliveries[-1]).status, "saved")

    def test_completion_queues_refresh_only_when_accepted(self):
        delivery = self._select(_ROOT)
        with patch(
            "world.rules.dialogue_availability.refresh_dialogue_availability"
        ) as refresh:
            with self.assertRaises(DialogueCompletionError):
                self._ack(delivery, scene_revision="r9")
            refresh.assert_not_called()
            self._ack(delivery)
            refresh.assert_called_once()
            self.assertEqual(refresh.call_args.kwargs["cause"], "reading_completed")

    def test_ack_does_not_settle_effects_or_eligibility_again(self):
        delivery = self._select(_ROOT)
        affinity_before = self.host.relations.affinity_for(self.player)
        inventory_before = list(self.player.db.inventory or [])
        self._ack(delivery)
        self.assertEqual(
            self.host.relations.affinity_for(self.player), affinity_before
        )
        self.assertEqual(list(self.player.db.inventory or []), inventory_before)
