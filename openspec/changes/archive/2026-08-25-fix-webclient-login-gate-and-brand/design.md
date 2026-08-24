## Context

The WebClient is a Vue 3 SPA (`web/webclient-app/`) whose store
(`stores/elosern.js`) mirrors the preserved OOB protocol reducer and derives a
`connectionStatus` slice consumed by `ConnectOverlay.vue`. The live evennia.js
transport is bound by `web/webclient-app/transport.js`, which owns the shared
lifecycle events (`connection_open` / `connection_close` / `logged_in`).

A logged-out tab connects the WebSocket and the server emits `connection_open`,
but the `ui_sync` input function (`server/conf/inputfuncs.py`) silently no-ops
for sessions without a puppet, so no `ui_snapshot` ever arrives. The reducer's
phase stays `awaiting_initial_snapshot` and the overlay showed 「連線中…」
forever — a dead end with no login affordance on the page. The D10 text
console already models this correctly (`connected ? (loggedIn ? "ready" :
"waiting") : "offline"`); the store never received the `logged_in` signal.

The brand 「霧落」 was placeholder copy from the v2 redesign draft
(`docs/design/elosern-redesign/`); the real game name used across lore, prompts,
and commands is 「伊洛瑟恩」.

## Goals / Non-Goals

**Goals:**

- The overlay shows a truthful, non-dead-end status for a logged-out tab:
  「等待登入」 instead of 「連線中…」 forever.
- The brand surfaces (overlay, top bar, page title) carry the real game name.
- Mirror the D10 console's proven session model (`loggedIn` flag) without
  duplicating presentation logic.

**Non-Goals:**

- In-page login UI or redirect to `/auth/login/` (the login path is the Django
  website; the D10 console has the same behavior).
- Changing the server's `ui_sync` gate (anonymous sessions must stay silent —
  that gate is deliberate).
- Any change to the OOB protocol, the reducer, or the server presentation
  pipeline.

## Decisions

**D1: Track `loggedIn` client-locally in the store, driven by evennia.js events.**
The store gains a `loggedIn` boolean and a `setLoggedIn` action; the transport
sets it false on `connection_open` (fresh socket, not yet authenticated) and
true on the `logged_in` OOB event, and `setConnected(false)` resets it. The
status mapping becomes `!connected → offline`, `!loggedIn || detached →
waiting`, `phase === active → ready`, else `connecting`.

- *Alternative considered:* derive "logged in" from phase only. Rejected: an
  anonymous session's phase is indistinguishable from a genuine snapshot-in-
  flight (`awaiting_initial_snapshot` in both cases), which is exactly the bug.
- *Alternative considered:* query `evennia.isConnected()` / server state at
  render. Rejected: the store is the single writer of client view state; the
  transport already receives the authoritative `logged_in` event.

**D2: Map not-logged-in to the existing `waiting` overlay state.**
`ConnectOverlay` already has a 「◐ 等待登入…」 status with no production caller
path; reusing it keeps the component contract (connecting/waiting/offline/ready)
and the D10 vocabulary intact. No new overlay state is introduced.

**D3: Brand copy is literal and centralized at each surface.**
Replace 「霧落」 with 「伊洛瑟恩」 in `ConnectOverlay.vue` and `TopBar.vue`, and
set `SERVERNAME = "Elosern"` in `server/conf/settings.py` (the page `<title>`
comes from Evennia's `game_name` context variable). No new branding mechanism
or config surface is introduced for an unreleased game.

**D4: No spec-level changes to existing capabilities.**
The change is a delta spec (`webclient-login-gate`) rather than a modification
of `webclient-vue-application` because no existing requirement's behavior
changes; the new session-state and brand contract stands alone.

**D5: The post-login resync deferral also covers the detached phase.**
`resyncIfAwaiting` previously fired only while `awaiting_initial_snapshot`.
It is widened to also cover `detached`: a `no_puppet` detach around login (the
portal re-attaches the puppet asynchronously) previously left the one-shot
retry dead. One shot per `logged_in`, never a loop (the deferral is not
re-scheduled).

## Risks / Trade-offs

- **R1: `logged_in` may precede the puppet re-attach on reconnect** — the
  portal's `logged_in` event can arrive before the account's puppet is
  re-attached; the client's `ui_sync` then hits the server's silent no-op
  (anonymous syncs emit nothing — `ui_sync` never emits a `no_puppet` error;
  that error exists only on the `ui_action` path). The 500 ms deferred retry
  (now also covering `detached`) covers the portal's actual ordering; the
  browser reconnect suite proves the practical flow recovers. A puppet that
  attaches later than the one-shot window is a pre-existing residual edge and
  self-heals on any text command (command settlement refreshes presentation).
- **R2: Client-local flag divergence from the server session** — a session
  disconnect that the browser does not observe would leave `loggedIn` stale. →
  `connection_close` (and every subsequent `connection_open`) resets the flag;
  the server's session lifecycle is the only writer.
- **R3: Brand string duplication across components** — a future rename must
  touch two SFCs. → Accepted for an unreleased game; a shared constant is a
  trivial follow-up if a third surface appears.

## Migration Plan

No data migration or backward compatibility is required (unreleased project).
Deployment: rebuild the Vue bundle (`npm run build`) and the container image,
then recreate the `evennia` container.
