"""Tests for the ephemeral puppet → live-session watcher registry.

Covers idempotent registration, the current-coordinator-epoch read at query
time (freshness after a sequence reset), connected/repuppeted pruning at the
next registration, the non-webclient/unpuppeted exclusion, and the ingress
wiring that registers a session on a successful ``ui_sync``.
"""

from evennia.server.serversession import ServerSession
from evennia.utils.create import create_object
from evennia.utils.test_resources import EvenniaTest

from tools.spec_traceability import covers_requirement

from server.conf import inputfuncs
from typeclasses.characters import PlayerCharacter
from web.webclient.presentation import watchers
from web.webclient.presentation.coordinator import attach_coordinator
from web.webclient.presentation.ingress import reset_client_sequence
from web.webclient.presentation.registry import build_production_registry


def _make_session(sessionhandler, protocol_key, account, sessid):
    session = ServerSession()
    session.init_session(protocol_key, ("localhost", 9999), sessionhandler)
    session.sessid = sessid
    session.protocol_key = protocol_key
    session.puppet = None
    session.account = account
    session.logged_in = True
    session.ndb.elosern_coordinator = None
    session.ndb.elosern_actor_id = None
    sessionhandler[session.sessid] = session
    return session


class WatcherRegistryTests(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        watchers.clear_watchers()

    def tearDown(self):
        watchers.clear_watchers()
        super().tearDown()

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def _puppet_session(self, sessid, character=None):
        character = character or self.char1
        session = _make_session(
            self.sessionhandler, "webclient/websocket", self.account, sessid
        )
        session.puppet = character
        character.sessions.add(session)
        return session

    @covers_requirement(
        "action-options-trigger-service::watcher-registry-resolves-live-sessions-for-the-room-entry-hook"
    )
    def test_puppeted_window_registers_and_resolves_once(self):
        session = self._puppet_session(11)
        attach_coordinator(session, build_production_registry())
        watchers.register_watcher(session)
        watchers.register_watcher(session)
        found = watchers.watchers_for(self.char1)
        self.assertEqual(len(found), 1)
        self.assertIs(found[0][0], session)
        self.assertEqual(
            found[0][1], attach_coordinator(session, build_production_registry()).epoch
        )

    @covers_requirement(
        "action-options-trigger-service::watcher-registry-resolves-live-sessions-for-the-room-entry-hook"
    )
    def test_non_webclient_and_unpuppeted_are_never_registered(self):
        telnet = _make_session(self.sessionhandler, "telnet", self.account, 12)
        telnet.puppet = self.char1
        watchers.register_watcher(telnet)
        self.assertEqual(watchers.watchers_for(self.char1), ())
        ajax = _make_session(self.sessionhandler, "webclient/ajax", self.account, 13)
        ajax.puppet = self.char1
        watchers.register_watcher(ajax)
        self.assertEqual(watchers.watchers_for(self.char1), ())
        unpuppeted = _make_session(
            self.sessionhandler, "webclient/websocket", self.account, 14
        )
        watchers.register_watcher(unpuppeted)
        self.assertEqual(watchers.watchers_for(self.char1), ())

    @covers_requirement(
        "action-options-trigger-service::watcher-registry-resolves-live-sessions-for-the-room-entry-hook"
    )
    def test_epoch_is_read_fresh_after_a_sequence_reset(self):
        session = self._puppet_session(15)
        old_epoch = attach_coordinator(session, build_production_registry()).epoch
        watchers.register_watcher(session)
        self.assertEqual(watchers.watchers_for(self.char1)[0][1], old_epoch)
        reset_client_sequence(session)
        fresh = attach_coordinator(session, build_production_registry()).epoch
        self.assertNotEqual(fresh, old_epoch)
        self.assertEqual(watchers.watchers_for(self.char1)[0][1], fresh)

    @covers_requirement(
        "action-options-trigger-service::watcher-registry-resolves-live-sessions-for-the-room-entry-hook"
    )
    def test_disconnected_session_is_pruned_at_the_next_registration(self):
        first = self._puppet_session(16)
        attach_coordinator(first, build_production_registry())
        second = self._puppet_session(17)
        attach_coordinator(second, build_production_registry())
        watchers.register_watcher(first)
        watchers.register_watcher(second)
        self.assertEqual(len(watchers.watchers_for(self.char1)), 2)
        del self.sessionhandler[first.sessid]
        watchers.register_watcher(second)
        remaining = watchers.watchers_for(self.char1)
        self.assertEqual(len(remaining), 1)
        self.assertIs(remaining[0][0], second)

    @covers_requirement(
        "action-options-trigger-service::watcher-registry-resolves-live-sessions-for-the-room-entry-hook"
    )
    def test_repuppeted_session_moves_to_the_new_puppet(self):
        session = self._puppet_session(18)
        attach_coordinator(session, build_production_registry())
        watchers.register_watcher(session)
        self.assertEqual(len(watchers.watchers_for(self.char1)), 1)
        other = create_object(PlayerCharacter, key="other-puppet")
        session.puppet = other
        watchers.register_watcher(session)
        self.assertEqual(watchers.watchers_for(self.char1), ())
        self.assertEqual(len(watchers.watchers_for(other)), 1)

    @covers_requirement(
        "action-options-trigger-service::watcher-registry-resolves-live-sessions-for-the-room-entry-hook"
    )
    def test_ingress_registers_on_a_successful_ui_sync(self):
        session = self._puppet_session(19)
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        from world.rules.clock import get_world_clock

        get_world_clock()
        inputfuncs.ui_sync(session, {"protocol_version": 1})
        found = watchers.watchers_for(self.char1)
        self.assertEqual(len(found), 1)
        self.assertIs(found[0][0], session)
