## MODIFIED Requirements

### Requirement: Connection loss locks stale controls

On WebSocket loss after a successful connection, the shell SHALL preserve the last rendered state under
a non-dismissible offline overlay and SHALL prevent all graphical mutation submission. The offline
overlay SHALL render above every other surface the client can have open — an open reference drawer, an
open full-screen overlay (map/settings/help), a full-view art or scene surface, and the full-log
overlay all included — so a connection loss is visibly announced regardless of what the player had open
when it occurred. Reconnection SHALL request a full snapshot and remove the overlay only after a valid
new-epoch snapshot is adopted.

#### Scenario: Offline controls cannot submit
- **WHEN** the active WebSocket closes while an enabled test action is focused
- **THEN** the offline overlay appears and keyboard or mouse activation emits no mutation

#### Scenario: Reconnect waits for canonical state
- **WHEN** the socket reconnects but no valid full snapshot has arrived
- **THEN** the offline/synchronizing lock remains until the new-epoch snapshot is accepted

#### Scenario: A dropped first sync is re-requested on a bounded budget
- **WHEN** the first reconnection `ui_sync` lands before the portal re-attaches the account puppet and the snapshot is dropped
- **THEN** the client re-requests `ui_sync` on a bounded, disarming schedule, ceasing on adoption, on disconnect, or once the attempt budget is spent

#### Scenario: Extremely stale reconnections recover once
- **WHEN** the authenticated snapshot never arrives after the bounded re-request budget, so the portal has lost the browser's authenticated session
- **THEN** the client reloads the page at most once per tab session (guarded by a persistent marker) and otherwise leaves the synchronizing lock in place

#### Scenario: The overlay stays off before any successful connection
- **WHEN** a first-time visitor opens the WebClient and no connection has ever reached the active phase
- **THEN** the offline overlay remains hidden so the stock connect/create prompt underneath stays visible and usable

#### Scenario: The offline overlay outranks an open reference drawer
- **WHEN** a reference drawer (skill, inventory, shop, quest, lore, or status) is open and the WebSocket then closes
- **THEN** the offline overlay is the topmost visible surface, painted above the drawer's scrim and panel

#### Scenario: The offline overlay outranks an open full-screen overlay or full-view
- **WHEN** the map, settings, or help overlay — or the portrait/scene full-view, or the full-log overlay
  — is open and the WebSocket then closes
- **THEN** the offline overlay is the topmost visible surface, painted above that surface
