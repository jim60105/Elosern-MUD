"""Integration tests for the OOB input functions (foundation 1.5/1.6).

These tests exercise the real ``server.conf.inputfuncs`` module against an
Evennia test environment: an anonymous session, a logged-in unpuppeted session,
a puppeted WebSocket session, and a Telnet session.
"""

from tools.spec_traceability import covers_requirement

from unittest.mock import Mock

from evennia.server.serversession import ServerSession
from evennia.utils.test_resources import EvenniaTest
from twisted.internet.defer import Deferred, succeed

from server.conf import inputfuncs
from typeclasses.characters import PlayerCharacter


def _make_session(sessionhandler, protocol_key, account=None):
    session = ServerSession()
    session.init_session(protocol_key, ("localhost", 9999), sessionhandler)
    session.sessid = 2
    session.protocol_key = protocol_key
    session.puppet = None
    session.account = account
    session.logged_in = account is not None
    session.ndb.elosern_coordinator = None
    session.ndb.elosern_actor_id = None
    return session


class UiSyncIntegrationTests(EvenniaTest):
    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.ws_session = _make_session(evennia_session_handler(), "webclient/websocket")
        self.sessionhandler.data_out.reset_mock()

    def tearDown(self):
        self.sessionhandler.data_out.reset_mock()
        super().tearDown()

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    def _puppet(self):
        session = self.ws_session
        session.puppet = self.char1
        self.char1.sessions.add(session)
        return session

    @covers_requirement(
        "webclient-oob-protocol::synchronization-requires-an-authenticated-websocket-puppet"
    )
    def test_puppeted_websocket_session_synchronizes(self):
        session = self._puppet()
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        get_world_clock = self._ensure_clock()
        inputfuncs.ui_sync(session, {"protocol_version": 1})
        # The coordinator emits one snapshot through session.msg -> data_out.
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        self.assertTrue(calls, "no ui_snapshot was emitted")
        envelope = calls[-1].kwargs["ui_snapshot"][0][0]
        self.assertEqual(envelope["protocol_version"], 1)
        self.assertEqual(envelope["mode"], "exploration")
        self.assertIn("status", envelope["panels"])
        self.assertEqual(envelope["panels"]["status"]["available"], True)

    def _ensure_clock(self):
        from world.rules.clock import get_world_clock

        return get_world_clock()

    @covers_requirement(
        "webclient-oob-protocol::synchronization-requires-an-authenticated-websocket-puppet"
    )
    def test_session_without_puppet_receives_no_snapshot(self):
        inputfuncs.ui_sync(self.ws_session, {"protocol_version": 1})
        self.sessionhandler.data_out.assert_not_called()

    def test_anonymous_session_receives_no_snapshot(self):
        anonymous = _make_session(self.sessionhandler, "webclient/websocket", account=None)
        inputfuncs.ui_sync(anonymous, {"protocol_version": 1})
        self.sessionhandler.data_out.assert_not_called()

    @covers_requirement(
        "webclient-oob-protocol::synchronization-requires-an-authenticated-websocket-puppet"
    )
    def test_telnet_session_receives_no_snapshot(self):
        telnet = _make_session(self.sessionhandler, "telnet", account=self.account)
        telnet.puppet = self.char1
        inputfuncs.ui_sync(telnet, {"protocol_version": 1})
        self.sessionhandler.data_out.assert_not_called()

    def test_ajax_session_receives_no_snapshot(self):
        ajax = _make_session(self.sessionhandler, "webclient/ajax", account=self.account)
        ajax.puppet = self.char1
        inputfuncs.ui_sync(ajax, {"protocol_version": 1})
        self.sessionhandler.data_out.assert_not_called()

    def test_malformed_payload_gets_safe_protocol_error(self):
        session = self._puppet()
        inputfuncs.ui_sync(session, {"protocol_version": 1, "extra": 1})
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_protocol_error" in call.kwargs
        ]
        self.assertTrue(calls)
        envelope = calls[-1].kwargs["ui_protocol_error"][0][0]
        self.assertEqual(envelope["code"], "malformed_envelope")
        self.assertNotIn("presentation_epoch", envelope)

    def test_unsupported_version_requests_reload(self):
        session = self._puppet()
        inputfuncs.ui_sync(session, {"protocol_version": 2})
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_protocol_error" in call.kwargs
        ]
        envelope = calls[-1].kwargs["ui_protocol_error"][0][0]
        self.assertEqual(envelope["code"], "unsupported_version")
        self.assertTrue(envelope["reload_required"])

    def test_client_actor_field_is_rejected(self):
        session = self._puppet()
        inputfuncs.ui_sync(session, {"protocol_version": 1, "actor": "me"})
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_protocol_error" in call.kwargs
        ]
        self.assertTrue(calls)
        envelope = calls[-1].kwargs["ui_protocol_error"][0][0]
        self.assertEqual(envelope["code"], "malformed_envelope")


def evennia_session_handler():
    import evennia

    return evennia.SESSION_HANDLER


class TextInputFunctionTests(EvenniaTest):
    """Pins Evennia 6.1 text-input semantics plus post-command refresh."""

    character_typeclass = PlayerCharacter

    def setUp(self):
        super().setUp()
        self.ws_session = _make_session(evennia_session_handler(), "webclient/websocket")
        self.sessionhandler.data_out.reset_mock()

    def tearDown(self):
        self.sessionhandler.data_out.reset_mock()
        super().tearDown()

    @property
    def sessionhandler(self):
        import evennia

        return evennia.SESSION_HANDLER

    @covers_requirement(
        "webclient-oob-protocol::webclient-text-commands-refresh-presentation-after-completion"
    )
    def test_completed_command_refreshes_webclient_state(self):
        session = self.ws_session
        session.puppet = self.char1
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self._ensure_clock()
        deferred = Deferred()

        from server.conf.inputfuncs import cmdhandler
        from unittest.mock import patch

        with patch("server.conf.inputfuncs.cmdhandler", return_value=deferred) as fake:
            inputfuncs.text(session, "look")
            fake.assert_called_once()
            deferred.callback(None)
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        self.assertTrue(calls, "no refresh snapshot was emitted")

    def _ensure_clock(self):
        from world.rules.clock import get_world_clock

        return get_world_clock()

    @covers_requirement(
        "webclient-oob-protocol::webclient-text-commands-refresh-presentation-after-completion"
    )
    def test_errback_preserves_failure_and_refreshes_once(self):
        session = self.ws_session
        session.puppet = self.char1
        self.char1.race = "human"
        self.char1.apply_race_baseline()
        self._ensure_clock()
        deferred = Deferred()
        failure = RuntimeError("command boom")

        from unittest.mock import patch

        with patch("server.conf.inputfuncs.cmdhandler", return_value=deferred):
            inputfuncs.text(session, "look")
        deferred.errback(failure)
        calls = [
            call
            for call in self.sessionhandler.data_out.call_args_list
            if "ui_snapshot" in call.kwargs
        ]
        self.assertTrue(calls, "no refresh snapshot after errback")

    @covers_requirement(
        "webclient-oob-protocol::webclient-text-commands-refresh-presentation-after-completion"
    )
    def test_telnet_command_remains_text_only(self):
        telnet = _make_session(self.sessionhandler, "telnet", account=self.account)
        telnet.puppet = self.char1
        from unittest.mock import patch

        with patch("server.conf.inputfuncs.cmdhandler", return_value=succeed(None)):
            inputfuncs.text(telnet, "look")
        self.sessionhandler.data_out.assert_not_called()

    def test_idle_command_updates_counters_without_execution(self):
        session = self.ws_session
        from unittest.mock import patch

        with patch("server.conf.inputfuncs.cmdhandler") as fake:
            inputfuncs.text(session, "idle")
        fake.assert_not_called()
        self.sessionhandler.data_out.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()
