## ADDED Requirements

### Requirement: Router frames store descriptors and a focus key and resolve at access time

The keyboard router SHALL treat each frame as `{descriptor, focusKey}` (plus, during the staged migration only, a transitional legacy `menu` copy that behaves exactly as today's frame until its surface family migrates). For every declarative frame, all menu reads — render, arrow navigation, geometry, breadcrumb, trail, pointer row, and activation payload — SHALL come from resolving the frame's descriptor through the store registry at the moment of the read, never from data captured when the frame was opened. A committed panel update SHALL require no router or store refresh action for any declarative frame to reflect the newer state on its next read. The action dock's derived views (`rootMenu`, breadcrumb trail) SHALL be produced from the frame stack with the same item shapes the components already render, and no commit-driven refresh/rehome/replace function over copied menus SHALL exist for a migrated family.

#### Scenario: An open move frame follows a committed move

- **WHEN** the move frame is open on the three-exit south-gate fixture, the player activates an exit, and the resulting full snapshot commits the new room
- **THEN** the move frame's next render lists exactly the new room's exits, its activation submits the new room's `exit_ref` with the new `current_node`, and no stale row from the previous room is rendered or submittable

#### Scenario: Committing an update issues no refresh call

- **WHEN** a committed snapshot replaces a panel a declarative exploration frame derives from
- **THEN** the commit path performs no per-frame rebuild, replace, re-home, or signature-comparison step for exploration frames, and the frame's next read already reflects the new panel

### Requirement: Focus tracks the item key across re-resolution

Each declarative frame SHALL carry the resolved item key of its focused row as `focusKey`. After any re-resolution the focus SHALL land on the row with the same key at its new geometry; when that key is absent the focus SHALL land on the nearest surviving row by index order, choosing the earlier row on equal distance; an empty menu SHALL have null focus. Any confirm — keyboard Enter or a pointer activation — SHALL write the activated item's key to the frame's `focusKey` before dispatching. A newly pushed declarative frame SHALL focus its first item.

#### Scenario: Same-key focus survives geometry change

- **WHEN** a frame focused on key `exit-west` re-resolves into a menu where that row moved to a different position
- **THEN** focus remains on `exit-west` at its new position

#### Scenario: Lost focus key lands deterministically

- **WHEN** a frame focused on a key absent from the re-resolved menu with multiple surviving rows
- **THEN** focus lands on the nearest surviving row by index with ties resolved to the earlier row, and the empty result focuses nothing

#### Scenario: A pointer pick updates the tracked key

- **WHEN** the player pointer-activates a row that is not the currently focused row
- **THEN** the activated row's key becomes the frame's `focusKey` before the action dispatches

### Requirement: Unresolvable frames pop one level; only the root frame renders a degraded reason row

When a declarative frame resolves to the unresolvable marker as the current frame, the stack SHALL immediately pop one level and the parent frame SHALL restore focus to the key of the row that opened the popped frame; when consecutive top frames are unresolvable the pop SHALL cascade until a frame resolves, and when no frame resolves the stack SHALL end at the mode's root frame. The cascade is bounded by stack depth and completes without any timer, animation, or deferred check. Only when the root frame itself is unresolvable — with no parent to return to — SHALL the client render a single disabled row whose text is the marker's server-authored reason when present, otherwise the local fallback 「畫面狀態已更新，請返回上層」; that row is focusable and submits nothing. Resolution exceptions reaching the stack rules are indistinguishable from unresolvable markers.

#### Scenario: A vanished target pops back to its parent

- **WHEN** the interact target frame for an `identity` is open and a committed snapshot no longer lists that identity
- **THEN** the stack pops exactly one level and the interact root frame restores focus to the vanished target's former row position by the nearest-row rule

#### Scenario: Cascading loss returns to the root

- **WHEN** a committed snapshot makes the top two frames' identities unresolvable at once
- **THEN** both frames pop in one access and the next lower resolvable frame renders with restored opener focus

#### Scenario: An unresolvable root degrades in place

- **WHEN** the exploration panel enters its unavailable form while the root frame is current
- **THEN** the root renders one disabled row naming the server-authored reason, focus lands on it, and activating it submits nothing

### Requirement: Suggestions frames are status-driven: generating never pops, unavailable exits to the root

The suggestions frame SHALL be declarative but status-driven, never timer-driven. While the committed envelope status is `generating`, `ready`, or `degraded` the frame SHALL resolve to content under the suggestions surface's existing four-status contract (including the muted generating row) with in-place row replacement and key-surviving focus, and SHALL NOT pop. When an open suggestions frame's envelope becomes `unavailable` — the status under which the surface presents no root entry and no pane at all — the stack SHALL deterministically leave that frame by returning to the exploration root frame (restoring focus under the key rule) without rendering a degraded reason row; the root entry's own visibility rule is unchanged.

#### Scenario: Generating status keeps the frame open

- **WHEN** the suggestions frame is current and a committed update flips its envelope to `generating`
- **THEN** the frame stays current rendering the muted generating row, no pop occurs, and a later `ready` update replaces the rows in place with key-tracked focus

#### Scenario: Withdrawn suggestions return to the root

- **WHEN** the suggestions frame is current and a committed update flips its envelope to `unavailable`
- **THEN** the suggestions frame is gone, the exploration root renders with the 建議 entry absent, focus lands deterministically, no reason row appears, and no timer was involved

### Requirement: Teardown resets the stack to the mode root from one decision point

Mode switch (exploration / combat / creation), presentation epoch reset, transport loss, and no-puppet detach SHALL each replace the whole descriptor stack with a single-frame stack holding the new mode's root frame — a declarative root descriptor once that mode's family is migrated, the transitional legacy root menu copy otherwise — from the single existing teardown decision point, and the stack SHALL never sit empty in a live mode. Teardown SHALL be the only event that replaces the whole stack; ordinary commits never pop or reset migrated frames.

#### Scenario: Combat adoption resets to the combat root

- **WHEN** a valid committed snapshot switches the mode from exploration to combat while exploration submenus are open
- **THEN** the stack contains exactly one root frame, the exploration frames and their focus keys are gone, and no exploration row remains activatable

#### Scenario: Transport loss leaves only the root frame

- **WHEN** the transport is lost while exploration frames are open
- **THEN** the stack holds only the root frame of the mode and no stale activation can dispatch after reconnect without a fresh player action

### Requirement: Activation payloads read committed state at dispatch time

A row activation SHALL dispatch the server-authored action identifier and payload derived from the resolve that produced the currently rendered frame, so a frame that has already re-resolved submits the new state's payload. The server-side stale guards (`stale_location` rejection, `base_revision` admission gate) SHALL remain unchanged as backstops against multi-session and event races, not as the user-facing freshness mechanism.

#### Scenario: No stale-payload rejection is reachable through the UI

- **WHEN** a player moves and then activates a move row in the refreshed frame
- **THEN** the submitted `explore.move` carries the new room's `current_node` and the server accepts it, leaving the stale rejection unreachable by normal dock play
