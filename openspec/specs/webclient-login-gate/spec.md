## Purpose

Keep the webclient connect overlay from presenting "connecting" forever for anonymous
sessions by tracking the server's `logged_in` session state client-locally, and present
the real game name (伊洛瑟恩 / Elosern) on the webclient's brand surfaces.

## Requirements

### Requirement: The WebClient overlay shows the waiting-for-login state for anonymous sessions
The WebClient SHALL track the authenticated session state client-locally (set when the
evennia.js `logged_in` OOB event arrives, cleared on `connection_open` and `connection_close`)
and SHALL map the committed transport status to the overlay slice by the exact precedence:
`!connected → 「連線中斷」`, `!loggedIn → 「等待登入」`, authenticated `detached` (a `no_puppet`
detach that cannot obtain a snapshot) → 「等待登入」, authenticated `awaiting_initial_snapshot`
→ 「連線中」, and `active` → 「就緒」. A session SHALL never present 「連線中」 indefinitely
while logged out, because the server sends no `ui_snapshot` to an anonymous session.

#### Scenario: A logged-out tab waits for login instead of connecting forever
- **WHEN** a browser tab opens the WebClient without a logged-in website session and the WebSocket connects
- **THEN** the overlay shows 「等待登入」 and not 「連線中」

#### Scenario: The logged_in event advances the status to connecting, then ready
- **WHEN** the server emits `logged_in` on an open socket
- **THEN** the overlay shows 「連線中」 while awaiting the initial snapshot and 「就緒」 once a valid `ui_snapshot` commits

#### Scenario: A reconnect re-enters the waiting-for-login state
- **WHEN** the WebSocket closes and reopens
- **THEN** the authenticated flag resets and the overlay shows 「等待登入」 again until the server re-emits `logged_in`

#### Scenario: A detached session waits for login and retries its synchronization
- **WHEN** a `no_puppet` detach happens around login and the server later re-emits `logged_in`
- **THEN** the overlay shows 「等待登入」 and the client sends one bounded `ui_sync` retry so a re-attached puppet can deliver the snapshot

### Requirement: The WebClient uses the real game name in its brand surfaces
The WebClient SHALL render the game name 「伊洛瑟恩」 as the brand on the connect overlay and
the top bar, and the webclient page `<title>` SHALL derive from the game's `SERVERNAME`
setting, never the placeholder 「霧落」 or the skeleton default. These three surfaces
(connect-overlay brand, top-bar title, page `<title>`) are the complete brand surface set.

#### Scenario: The connect overlay shows the real game name
- **WHEN** the connect overlay renders
- **THEN** its brand text is 「伊洛瑟恩」

#### Scenario: The top bar shows the real game name
- **WHEN** the top bar renders
- **THEN** its title text is 「伊洛瑟恩」

#### Scenario: The page title derives from the game name setting
- **WHEN** the webclient page is served
- **THEN** its `<title>` is the game name from settings, not `evennia-skeleton`
