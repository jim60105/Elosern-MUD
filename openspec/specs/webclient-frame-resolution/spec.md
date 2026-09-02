# webclient-frame-resolution Specification

## Purpose
TBD - created by archiving change webclient-frame-resolver-registry. Update Purpose after archive.
## Requirements
### Requirement: Frame descriptors resolve to committed-state menus at access time

The store SHALL own a frame resolver registry that maps a frame descriptor `{source, params}` to a menu derived from the committed presentation state at the moment of the call. A resolver SHALL read only committed panels (the state the protocol reducer has atomically committed under the revision gate) and SHALL NOT read router frame copies, component state, or any other cached menu data. Resolving the same descriptor twice across two committed states SHALL return menus reflecting each state respectively; resolving the same descriptor twice against one committed state SHALL return deep-equal menus and SHALL NOT mutate store, model, or committed state. Later table waves (combat selection preservation through the existing `rebuildForPanel` seam) SHALL declare any permitted model-state exception as a spec-visible amendment with its own idempotency scenario. A resolver that throws SHALL be caught by the registry and reported as unresolvable rather than propagating to callers.

#### Scenario: Resolution follows committed state

- **WHEN** a descriptor is resolved, a newer committed snapshot replaces the panels it names, and the same descriptor is resolved again
- **THEN** the second menu reflects the newer committed panels and no row from the superseded state remains

#### Scenario: Resolution is pure against one committed state

- **WHEN** the same descriptor is resolved twice against the same committed state through the bridge-exposed resolver
- **THEN** both results are deep-equal and the committed state, router state, and model state are unchanged

#### Scenario: A throwing resolver degrades instead of crashing

- **WHEN** a registered resolver raises on a well-formed descriptor
- **THEN** `resolve` returns the shared unresolvable marker and no exception reaches the caller

### Requirement: The descriptor registry implements the exploration family as a finite table

The registry SHALL implement exactly the exploration-family source table and nothing else in this change, each entry producing the menu its current push site produces today. Sources (panel `exploration`; `exploration.move` additionally reads `local_map.current_node`; `exploration.suggestions` reads `context_actions.suggestions`): `exploration.root` `{}`, `exploration.move` `{}`, `exploration.look` `{}`, `exploration.interact` `{}`, `exploration.wait` `{}`, `exploration.target` `{identity}`, `exploration.keywords` `{identity}`, `exploration.suggestions` `{}` — resolvable only while the envelope status is `generating`, `ready`, or `degraded`; status `unavailable` resolves to the unresolvable marker so an open suggestions frame can honor the surface's no-pane rule. The services family (guild/board/quests/quest-detail/shop/stock/sell frames plus the abandon-confirm frame, keyed by `questIndex`), the combat family (`root`, `categories`, `category{categoryIndex}`, `group{categoryIndex, groupIndex}`, `skill{skillKey}`, `target{skillKey}`, `forfeit`), and the creation family (`root`, `presets`, `form{view}`, `confirm{kind, presetKey?}`) SHALL be added as further table rows by the later migration changes that cut their push sites over; a source absent from the implemented table SHALL resolve to the shared unresolvable marker without throwing, and every table addition SHALL be a spec-visible change.

#### Scenario: Every table source resolves from a live snapshot

- **WHEN** each table source is resolved against a committed snapshot of its owning mode with valid params
- **THEN** each returns the menu its current push site produces, with the same row keys, server-authored payloads, and titles

#### Scenario: An unregistered source degrades

- **WHEN** `resolve` is called with a source absent from the table
- **THEN** it returns the unresolvable marker and the caller can render or pop without catching an exception

#### Scenario: A withdrawn suggestions envelope degrades like a lost identity

- **WHEN** `exploration.suggestions` is resolved while the committed envelope status is `unavailable`
- **THEN** resolve returns the unresolvable marker so the consumer-side rule can leave the frame, and a `generating` status instead resolves to the muted generating row menu

### Requirement: Dynamic rows and payloads are verbatim from the panel while client-owned navigation rows are reproduced

Domain rows — entity lists, exits, targets, quest/board/shop entries, skill descriptors, and every action identifier and payload — SHALL come verbatim from the committed panel exactly as the existing menu builders produce them: the resolver SHALL NOT invent, reorder, filter, or relabel domain content beyond what the named builder already does. Client-owned navigation and presentation rows that the shipped dock contract requires — the exploration/services/creation root entries, `back` rows of submenus, the combat forfeit confirm/cancel pair, and disabled explanatory rows — SHALL be reproduced by the same builders, and reproducing them SHALL NOT count as fabrication.

#### Scenario: A resolved submenu keeps its back row

- **WHEN** `exploration.move` resolves against a room with two exits
- **THEN** the menu holds exactly the two server-authored exit rows plus the builder's `back` row, with payloads identical to the committed panel's

#### Scenario: Domain relabeling is absent by construction

- **WHEN** a look or target frame resolves against a panel whose rows carry server-authored labels and disabled reasons
- **THEN** every domain row's label, sub-line, action identifier, payload, and disabled reason equal the committed panel's values

### Requirement: An unresolvable descriptor yields the shared degradation marker with the server-authored reason

A descriptor whose identity or index is absent from the committed panel, whose panel is in an unavailable form, or whose resolver threw SHALL resolve to a shared unresolvable marker `{unresolvable: true, reason}`. Where the committed panel carries a server-authored `reason.message`, the marker's `reason` SHALL be that message verbatim; otherwise the marker's `reason` SHALL be null and the local fallback string 「畫面狀態已更新，請返回上層」 SHALL only be chosen by the consumer when rendering. The marker is data: resolving an unresolvable descriptor SHALL never throw, and pop-versus-disabled handling belongs to the consumer-side stack rules, not the registry.

#### Scenario: Identity loss reports the server message

- **WHEN** a target descriptor names an `identity` the committed `exploration` panel no longer lists and the panel carries `reason.message`
- **THEN** resolve returns the unresolvable marker whose reason equals that server-authored message

#### Scenario: Missing server message leaves the reason null

- **WHEN** an unresolvable descriptor's panel carries no authored message
- **THEN** resolve returns the unresolvable marker with a null reason



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

#### Scenario: Epoch reset leaves only the root frame

- **WHEN** a new transport generation retires the epoch and a fresh-epoch snapshot establishes the new one while exploration submenus are open
- **THEN** the stack contains exactly one root frame for the new presentation before any player action

#### Scenario: No-puppet detach collapses the stack without a mode change

- **WHEN** a `no_puppet` protocol error detaches the character while exploration submenus are open and neither the mode nor the epoch changes
- **THEN** the stack collapses to exactly the single root frame and no open submenu row remains activatable

### Requirement: Activation payloads read committed state at dispatch time

A row activation SHALL dispatch the server-authored action identifier and payload derived from the resolve that produced the currently rendered frame, so a frame that has already re-resolved submits the new state's payload. The server-side stale guards (`stale_location` rejection, `base_revision` admission gate) SHALL remain unchanged as backstops against multi-session and event races, not as the user-facing freshness mechanism.

#### Scenario: No stale-payload rejection is reachable through the UI

- **WHEN** a player moves and then activates a move row in the refreshed frame
- **THEN** the submitted `explore.move` carries the new room's `current_node` and the server accepts it, leaving the stale rejection unreachable by normal dock play
