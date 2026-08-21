"""Portal WebSocket protocol with reconnect-safe shared login.

Evennia's stock ``WebSocketClient.disconnect`` invalidates the shared Django
login (``webclient_authenticated_uid``) whenever the session's captured nonce
still matches — on ANY disconnect, including one triggered after an abnormal
close (anything but CLOSE_NORMAL/GOING_AWAY, for example a transport failure
closing with code 4001). An abnormal close does not mean the browser tab is
gone: the same tab reconnects, and its new socket's auto-login depends on
that uid still being present. Clearing it races the reconnecting socket and
leaves it permanently anonymous (every ``ui_sync`` becomes a silent no-op and
the store stays in ``awaiting_initial_snapshot``), which the WebClient state
plugin previously had to work around with a one-shot page reload.

This subclass preserves the uid on abnormal closes (the tab intends to
reconnect) and keeps Evennia's exact stock clearing logic for graceful closes
(the tab is gone), including the nonce protection for Chrome-style fast
reconnects.
"""

from evennia.server.portal.webclient import (
    CLOSE_NORMAL,
    GOING_AWAY,
    WebSocketClient as EvenniaWebSocketClient,
)


class WebSocketClient(EvenniaWebSocketClient):
    """WebSocket protocol that keeps the shared-login uid across abnormal closes."""

    def disconnect(self, reason=None):
        csession = self.get_client_session()
        if csession:
            close_code = getattr(self, "websocket_close_code", None)
            if close_code is None or close_code in (CLOSE_NORMAL, GOING_AWAY):
                # Graceful close: the tab is gone for good. Keep Evennia's
                # stock shared-login invalidation, whose nonce check protects
                # Chrome-style fast reconnects (a newer HTTP request re-set
                # the uid, so this disconnect must not erase it).
                if csession.get("webclient_authenticated_nonce", 0) == self.nonce:
                    csession["webclient_authenticated_uid"] = None
                    csession["webclient_authenticated_nonce"] = 0
                    csession.save()
            # An abnormal close leaves the uid in place: the same tab
            # reconnects and the new socket's auto-login depends on it.
            self.logged_in = False
        self.sessionhandler.disconnect(self)
        self.sendClose(CLOSE_NORMAL, reason)
