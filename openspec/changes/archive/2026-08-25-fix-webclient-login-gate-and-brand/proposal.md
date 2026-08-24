## Why

Opening `http://localhost:4001/webclient/` in a logged-out browser renders a
full-screen overlay stuck on 「● 連線中…」 forever with the placeholder brand
「霧落」. The connection status never advances because the server silently
refuses `ui_sync` for anonymous WebSocket sessions (no puppet → no snapshot),
and the UI has no notion of "authenticated" to display the waiting-for-login
state. The brand is likewise stale placeholder copy.

## What Changes

- Add a client-local `loggedIn` session flag to the WebClient store, driven by
  the evennia.js `logged_in` OOB event, so the overlay can distinguish
  「等待登入」(socket up, not authenticated) from 「連線中」(socket up,
  authenticated, snapshot in flight) from 「就緒」(snapshot committed).
- Reset the flag on `connection_open` and `connection_close` so a reconnect
  re-enters the waiting-for-login state until the server re-authenticates.
- Replace the placeholder brand 「霧落」 with the real game name 「伊洛瑟恩」
  in the connect overlay and the top bar, and set `SERVERNAME = "Elosern"` so
  the page `<title>` stops showing `evennia-skeleton`.

## Capabilities

### New Capabilities

- `webclient-login-gate`: the WebClient transport status distinguishes
  authenticated from anonymous sessions (waiting-for-login vs connecting), so
  the overlay no longer presents a dead-end 「連線中…」 for a logged-out tab
  and the player-facing brand is the real game name everywhere.

### Modified Capabilities

(none — no existing main spec requirement changes)

## Impact

- `web/webclient-app/stores/elosern.js` — new client-local `loggedIn` state
  and `setLoggedIn`; `connectionStatusFor` maps not-logged-in to `waiting`.
- `web/webclient-app/transport.js` — forwards `logged_in` / `connection_open`
  session signals to the store.
- `web/webclient-app/components/ConnectOverlay.vue` and
  `web/webclient-app/components/TopBar.vue` — brand copy 「霧落」 → 「伊洛瑟恩」.
- `server/conf/settings.py` — `SERVERNAME` 「evennia-skeleton」 → 「Elosern」
  (page title).
- Vitest unit tests for the store status slice, the transport wiring, and the
  brand copy; `web/static/webclient/app/dist` bundle rebuilt.
