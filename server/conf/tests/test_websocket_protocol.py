"""Unit tests for the reconnect-safe portal WebSocket protocol.

The protocol's ``disconnect`` decides whether the shared Django login
(``webclient_authenticated_uid``) survives: graceful closes invalidate it
(Evennia's stock rule with the nonce protection for Chrome-style fast
reconnects), abnormal closes preserve it so the same tab's reconnecting
socket can still auto-login. These tests drive the decision logic directly
without a portal or browser.
"""

import unittest

from server.conf.websocket_protocol import WebSocketClient

_UID = 1
_NONCE = 2


class _FakeCSession(dict):
    """dict stand-in for the Django session with a recording ``save``."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.saves = []

    def save(self):
        self.saves.append(dict(self))


class _FakeHandler:
    """Records which session the handler was asked to disconnect."""

    def __init__(self):
        self.disconnected = []

    def disconnect(self, session):
        self.disconnected.append(session)


def _make_client(
    close_code: int | None,
    csession: _FakeCSession,
    nonce: int = _NONCE,
    logged_in: bool = True,
) -> WebSocketClient:
    client = object.__new__(WebSocketClient)
    client.http_request_uri = "ws://127.0.0.1/websocket?csessid123&1&chrome"
    client.get_client_session = lambda: csession
    client.nonce = nonce
    client.logged_in = logged_in
    if close_code is not None:
        client.websocket_close_code = close_code
    client.sessionhandler = _FakeHandler()
    client.sent_close = None

    def send_close(code, reason):
        client.sent_close = (code, reason)

    client.sendClose = send_close
    return client


class WebSocketClientDisconnectTests(unittest.TestCase):
    """The shared-login uid survives exactly the disconnects it must."""

    def test_graceful_close_clears_uid_when_nonce_unchanged(self):
        csession = _FakeCSession(
            webclient_authenticated_uid=_UID, webclient_authenticated_nonce=_NONCE
        )
        client = _make_client(close_code=None, csession=csession, nonce=_NONCE)
        client.disconnect()
        self.assertIsNone(csession.get("webclient_authenticated_uid"))
        self.assertEqual(csession.get("webclient_authenticated_nonce"), 0)

    def test_graceful_close_keeps_uid_when_nonce_changed(self):
        # Chrome-style fast reconnect: a newer HTTP request re-set the uid,
        # so this stale disconnect must not erase it (Evennia stock rule).
        csession = _FakeCSession(
            webclient_authenticated_uid=_UID, webclient_authenticated_nonce=_NONCE + 3
        )
        client = _make_client(close_code=None, csession=csession, nonce=_NONCE)
        client.disconnect()
        self.assertEqual(csession.get("webclient_authenticated_uid"), _UID)

    def test_abnormal_close_preserves_uid_for_reconnect(self):
        # The 4001-style transport failure must leave the uid in place: the
        # same tab reconnects and its new socket auto-login depends on it.
        csession = _FakeCSession(
            webclient_authenticated_uid=_UID, webclient_authenticated_nonce=_NONCE
        )
        client = _make_client(close_code=4001, csession=csession, nonce=_NONCE)
        client.disconnect()
        self.assertEqual(csession.get("webclient_authenticated_uid"), _UID)
        self.assertEqual(csession.get("webclient_authenticated_nonce"), _NONCE)
        self.assertFalse(client.logged_in)

    def test_normal_and_going_away_codes_clear_uid(self):
        for code in (1000, 1001):
            csession = _FakeCSession(
                webclient_authenticated_uid=_UID,
                webclient_authenticated_nonce=_NONCE,
            )
            client = _make_client(close_code=code, csession=csession, nonce=_NONCE)
            client.disconnect()
            self.assertIsNone(
                csession.get("webclient_authenticated_uid"), f"code {code}"
            )

    def test_disconnect_still_notifies_handler_and_sends_close(self):
        csession = _FakeCSession(
            webclient_authenticated_uid=_UID, webclient_authenticated_nonce=_NONCE
        )
        client = _make_client(close_code=4001, csession=csession)
        client.disconnect("reason")
        self.assertEqual(client.sessionhandler.disconnected, [client])
        self.assertEqual(client.sent_close, (1000, "reason"))


if __name__ == "__main__":
    unittest.main()
