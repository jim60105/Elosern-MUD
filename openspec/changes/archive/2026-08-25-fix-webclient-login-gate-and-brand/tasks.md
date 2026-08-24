## 1. Store: authenticated-session state

- [x] 1.1 Add a client-local `loggedIn` flag (init `false`) to `web/webclient-app/stores/elosern.js` and expose a `setLoggedIn(value)` store action that sets it and republishes the view
- [x] 1.2 Update `connectionStatusFor` in `stores/elosern.js` to the exact precedence `!connected → offline`, `!loggedIn || detached → waiting`, `active → ready`, else `connecting`, and wire `loggedIn` into the committed view (`store.view.loggedIn`)
- [x] 1.3 Reset `loggedIn` to `false` in `setConnected(false)` so a disconnect ends the authenticated session

## 2. Transport: forward session signals

- [x] 2.1 In `web/webclient-app/transport.js`, call `store.setLoggedIn(false)` on `connection_open` (fresh socket, not yet authenticated)
- [x] 2.2 In `transport.js`, call `store.setLoggedIn(true)` on the evennia.js `logged_in` event (before the deferred `resyncIfAwaiting`)
- [x] 2.3 Widen `resyncIfAwaiting` to also retry while `detached` (a `no_puppet` detach around login must not kill the one-shot retry); one shot per `logged_in`, never a loop

## 3. Brand: real game name

- [x] 3.1 Replace the brand 「霧落」 with 「伊洛瑟恩」 in `web/webclient-app/components/ConnectOverlay.vue`
- [x] 3.2 Replace the brand 「霧落」 with 「伊洛瑟恩」 in `web/webclient-app/components/TopBar.vue`
- [x] 3.3 Set `SERVERNAME = "Elosern"` in `server/conf/settings.py` so the webclient page `<title>` derives from the game name

## 4. Tests

- [x] 4.1 Update `web/webclient-app/tests/top_bar.test.js` to assert the 「伊洛瑟恩」 brand
- [x] 4.2 Add a `ConnectOverlay` brand assertion (「伊洛瑟恩」) to `web/webclient-app/tests/connect_overlay.test.js`
- [x] 4.3 Extend `web/webclient-app/tests/store/store_slices.test.js` to cover the full status mapping (waiting before login, connecting after `logged_in`, ready on snapshot, waiting again after reconnect) and keep `openActiveSession` realistic by calling `setLoggedIn(true)`
- [x] 4.4 Update `web/webclient-app/tests/store/store_protocol.test.js` `openSession` to call `setLoggedIn(true)` (the real protocol delivers `logged_in` before any snapshot)
- [x] 4.5 Extend `web/webclient-app/tests/transport.test.js` with a `setLoggedIn` stub + a real-store lifecycle test (waiting → connecting → ready → offline → waiting; a reconnect must not retain authentication; a detached-after-login still gets the deferred `ui_sync` retry, driven with fake timers)
- [x] 4.6 Add `server/conf/tests/test_webclient_page.py` — an `EvenniaTest` that renders `/webclient/` through Django's test client and asserts the served `<title>` carries `SERVERNAME` (never `evennia-skeleton`)

## 5. Verification

- [x] 5.1 Run `npm test` (Vitest suite, 253 tests) green and `node --test web/static/webclient/js/tests/*.test.js` green
- [x] 5.2 Run `MUD_TEST_SETTINGS=1 uv run --locked evennia test --settings test_settings.py --keepdb server.conf.tests.test_webclient_page` green; `uv run --locked python -m compileall -q world typeclasses commands server` clean; `git diff --check` clean
- [x] 5.3 Rebuild the bundle with `npm run build` and verify `web/static/webclient/app/dist` contains the changes; rebuild the container (`podman compose build`) and recreate it (`podman compose up -d --force-recreate evennia`); verify the served page title is `Elosern` and a logged-out tab shows 「等待登入」 while a logged-in tab reaches 「就緒」
- [x] 5.4 At archive time, after syncing the delta spec into `openspec/specs/webclient-login-gate/spec.md`, annotate the new requirements' tests with `covers_requirement` IDs obtained from `uv run --locked python -m tools.spec_traceability list` and run `uv run --locked python -m tools.spec_traceability check` (the new capability enters the main-spec index only at archive)
