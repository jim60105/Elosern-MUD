"""Tests for the single presentation-context factory and its publication paths.

Every publication path — the ``ui_sync``/snapshot refresh, the dispatcher's
completion, internal-error, and stale paths — MUST build its context through
``build_presentation_context`` so the ``context_actions`` presenter renders
``suggestions`` exclusively from the immutable ``OptionsSnapshot`` (an async
``ready`` result survives the next snapshot) and never from the raw session.
"""

from types import SimpleNamespace

from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest, EvenniaTestCase

from typeclasses.characters import PlayerCharacter
from typeclasses.rooms import Room
from web.webclient.actions import dispatcher
from web.webclient.actions.registry import build_production_action_registry
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.context import PresentationContext
from web.webclient.presentation.ingress import build_presentation_context, synchronize_session
from web.webclient.presentation.registry import build_production_registry

CARDS = [
    {
        "kind": "known_action",
        "action_code": "explore.look",
        "label": "環顧四周",
        "params": {"room": True},
    },
    {
        "kind": "known_action",
        "action_code": "explore.wait",
        "label": "等待午後",
        "params": {"daypart": "noon"},
    },
    {
        "kind": "known_action",
        "action_code": "explore.talk_scripted",
        "label": "向店員問候",
        "params": {"npc_id": 7, "keyword_id": "問候"},
    },
]


def _wire_cards():
    """The card list after the presenter's shape gate normalization (hint=None)."""
    return [{**card, "hint": None} for card in CARDS]


def _options_state(owner_pk, fingerprint, **overrides):
    state = {
        "owner_actor_id": owner_pk,
        "fingerprint": fingerprint,
        "status": "ready",
        "generation_token": 1,
        "displayed": [dict(card) for card in CARDS],
    }
    state.update(overrides)
    return state


class _FakeSession:
    def __init__(self, puppet):
        self.puppet = puppet
        self.sent = []
        self.ndb = SimpleNamespace(elosern_coordinator=None, elosern_actor_id=None)
        self.sessid = 1

    def msg(self, **kwargs):
        self.sent.append(kwargs)


    def _envelopes(self, message_name):
        return [
            call[message_name][0][0]
            for call in self.sent
            if message_name in call
        ]


class ContextFactoryTests(EvenniaTestCase):
    """Factory behavior on a fake session: no evennia fixtures required."""

    def _session(self, puppet_pk="1", state=None):
        session = _FakeSession(SimpleNamespace(pk=puppet_pk))
        if state is not None:
            session.ndb.options_state = state
        return session

    def test_absent_state_snapshots_to_none(self):
        context = build_presentation_context(self._session(), SimpleNamespace(pk="1"))
        self.assertIsNone(context.options_state)

    def test_valid_state_deep_copies_into_an_immutable_snapshot(self):
        state = _options_state("1", "fixture-fingerprint")
        session = self._session("1", state)
        context = build_presentation_context(session, SimpleNamespace(pk="1"))
        snapshot = context.options_state
        self.assertEqual(snapshot.fingerprint, "fixture-fingerprint")
        self.assertEqual(snapshot.status, "ready")
        self.assertEqual(len(snapshot.displayed), len(CARDS))
        self.assertEqual(snapshot.displayed[0].action_code, "explore.look")
        # Later replacement of the session state object must not move the
        # snapshot the presenter already holds.
        session.ndb.options_state = _options_state("1", "fixture-fingerprint", status="unavailable")
        self.assertEqual(snapshot.status, "ready")

    def test_aliens_owner_snapshot_is_refused(self):
        state = _options_state("other", "fixture-fingerprint", status="ready")
        context = build_presentation_context(self._session("1", state), SimpleNamespace(pk="1"))
        self.assertIsNone(context.options_state)

    def test_non_dict_state_degrades_to_none_without_raising(self):
        for state in ("garbage", 42, [1, 2]):
            context = build_presentation_context(self._session("1", state), SimpleNamespace(pk="1"))
            self.assertIsNone(context.options_state)

    def test_shape_invalid_displayed_entries_are_dropped_without_raising(self):
        state = _options_state("1", "fixture-fingerprint", displayed=[1, "x", dict(CARDS[0])])
        context = build_presentation_context(self._session("1", state), SimpleNamespace(pk="1"))
        self.assertIsNotNone(context.options_state)
        self.assertEqual(len(context.options_state.displayed), 1)


class PublicationPathSnapshotTests(EvenniaTest):
    """One state-preservation test per publication path: ui_sync, completion,
    internal-error, stale."""

    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        from web.webclient.presentation.fingerprints import derive_exploration_situation

        from world.rules.clock import get_world_clock

        get_world_clock()
        self.room = create_object(Room, key="snapshot room")
        self.player = create_object(PlayerCharacter, key="snapshot player")
        self.player.race = "human"
        self.player.apply_race_baseline()
        self.player.location = self.room
        self.registry = build_production_registry()
        self.session = _FakeSession(self.player)
        situation = derive_exploration_situation(self.player)
        self.assertIsNotNone(situation)
        self.fingerprint = situation[0]
        self.session.ndb.options_state = _options_state(
            str(self.player.pk), self.fingerprint
        )

    def test_context_factory_carries_the_current_situation_fingerprint(self):
        context = build_presentation_context(self.session, self.player)
        self.assertEqual(context.options_fingerprint, self.fingerprint)

    def test_context_factory_fails_closed_without_a_derivable_situation(self):
        # A malformed actor or an out-of-exploration mode never raises: the
        # context carries no fingerprint and the presenter emits unavailable.
        self.player.creation_pending = True
        context = build_presentation_context(self.session, self.player)
        self.assertIsNone(context.options_fingerprint)
        self.player.creation_pending = False
        self.player.location = None
        context = build_presentation_context(self.session, self.player)
        self.assertIsNone(context.options_fingerprint)

    def test_puppet_change_clears_options_state_and_barriers(self):
        from collections import OrderedDict

        from evennia.utils.create import create_object
        from typeclasses.rooms import Room

        second_room = create_object(Room, key="second snapshot room")
        other = create_object(PlayerCharacter, key="other snapshot player")
        other.race = "human"
        other.apply_race_baseline()
        other.location = second_room
        session = _FakeSession(self.player)
        session.ndb.elosern_actor_id = str(self.player.pk)
        session.ndb.options_state = _options_state(str(self.player.pk), self.fingerprint)
        session.ndb.options_barriers = OrderedDict([(self.fingerprint, 7)])
        from web.webclient.presentation.coordinator import attach_coordinator

        attach_coordinator(session, self.registry)
        session.puppet = other
        synchronize_session(session, other)
        # The puppet change cleared the previous character's barrier store and
        # options state before the reconnect trigger wrote the new puppet's
        # own state (the old fingerprint never survives the change).
        self.assertIsNone(session.ndb.options_barriers)
        state = session.ndb.options_state
        self.assertEqual(state["owner_actor_id"], str(other.pk))
        self.assertNotEqual(state["fingerprint"], self.fingerprint)

    def test_ui_sync_snapshot_carries_the_ready_suggestions(self):
        synchronize_session(self.session, self.player)
        snapshots = self.session._envelopes("ui_snapshot")
        self.assertTrue(snapshots)
        panel = snapshots[-1]["panels"]["context_actions"]
        self.assertEqual(panel["suggestions"]["status"], "ready")
        self.assertEqual(panel["suggestions"]["cards"], _wire_cards())

    def test_completion_publication_carries_the_ready_suggestions(self):
        coordinator = attach_coordinator(self.session, self.registry)
        state = dispatcher._sequence_state(self.session)
        state.in_flight = True
        state.epoch = coordinator.epoch
        dispatcher._publish_completion(
            self.session,
            self.player,
            {"outcome": "success", "affected_panels": ["context_actions"]},
            self.registry,
            "r1",
            coordinator.epoch,
        )
        updates = self.session._envelopes("ui_update")
        self.assertTrue(updates)
        panel = updates[-1]["panels"]["context_actions"]
        self.assertEqual(panel["suggestions"]["status"], "ready")
        self.assertEqual(panel["suggestions"]["cards"], _wire_cards())

    def test_internal_error_publication_carries_the_ready_suggestions(self):
        coordinator = attach_coordinator(self.session, self.registry)
        dispatcher._settle_internal_error(
            self.session,
            self.player,
            build_production_action_registry(),
            self.registry,
            "r1",
            coordinator.epoch,
        )
        snapshots = self.session._envelopes("ui_snapshot")
        self.assertTrue(snapshots)
        panel = snapshots[-1]["panels"]["context_actions"]
        self.assertEqual(panel["suggestions"]["status"], "ready")
        self.assertEqual(panel["suggestions"]["cards"], _wire_cards())

    def test_stale_rejection_publication_carries_the_ready_suggestions(self):
        coordinator = attach_coordinator(self.session, self.registry)
        state = dispatcher._sequence_state(self.session)
        dispatcher._send_stale(self.session, coordinator, state, "r1")
        snapshots = self.session._envelopes("ui_snapshot")
        self.assertTrue(snapshots)
        panel = snapshots[-1]["panels"]["context_actions"]
        self.assertEqual(panel["suggestions"]["status"], "ready")
        self.assertEqual(panel["suggestions"]["cards"], _wire_cards())
