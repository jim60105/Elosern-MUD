## ADDED Requirements

### Requirement: A deliberate mutation echo appears exactly once at dispatch

The browser SHALL append the resolved display line to the narrative exactly once
per deliberate mutation in the single submit path: the echo fires at the moment
the `ui_action` request is dispatched (a request id is returned), never on
retry, resync, reconnect-replay, or a second client-local toggle, and never
when submission is blocked (offline, mutations locked, not initialized, or a
duplicate/in-flight request). A button click and the identical keyboard
activation SHALL each echo exactly once. Every surface that dispatches a
mutation SHALL hand the catalog the labels it already holds — forwarded row
descriptors (including the chosen non-default cast magnitude's label and the
explicit target labels on combat rows, and the descriptor on creation
confirmation items), fields read verbatim from committed state at dispatch
time (shop row display names, the uniquely matching local-map edge label or
the destination node label, NPC display names, the committed creation
confirmation descriptor), or the payload itself — so a deliberate activation
from any surface (backpack row, shop drawer row, minimap
move, combat row with or without a non-default magnitude, services row,
creation activate/reset confirmation) produces its line instead of silently
resolving to `null`; an ambiguous local-map edge match MUST NOT pick an
arbitrary edge and instead degrades to the destination-node label. A surface
that genuinely has no label for the line stays silent rather than fabricating
one, and any such silence SHALL be an explicit, reviewed expectation of the
test suite covering the surfaces — no dispatch path may fall silent
unannounced. A borrowed free-form dialogue SHALL be owned by the action
path: the command field's borrowed branch SHALL not append its own line, so a
single free-form send yields exactly one line (`talk <NPC> <speech>`), and when
submission is blocked the typed speech SHALL remain in the field and the field
SHALL keep focus (the borrowed interaction is not complete and nothing is
lost). Because the command field is permanently present, the completion of a
borrowed dialogue SHALL be signalled by returning focus to the action dock
rather than by closing a surface. Text written into the command field without
sending (typing, a history walk, or Tab completion) SHALL NOT echo: it dispatches
nothing, so no line exists to append until the player sends. The echo line SHALL be inserted as literal text via the same
narrative append path (scroll-keep + polite unread marker) used by server
output, SHALL NOT enter the markup pipeline, SHALL NOT be sent or reused as a
submitted command, and SHALL have no effect on the validated action payload
(`U9` intact: dispatch stays allowlist + exact). A later rejection of the
action SHALL NOT remove the line, because the line records what the player
acted.

#### Scenario: A staged submit echoes at dispatch

- **WHEN** a player activates a button that dispatches a valid `combat.cast`
- **THEN** exactly one input line appears in the narrative at that moment, the
  `ui_action` envelope is byte-identical with and without the echo, and a
  rejected outcome leaves the line in place

#### Scenario: Locked state never echoes

- **WHEN** the browser is offline, awaiting its first snapshot, or another
  mutation is in flight
- **THEN** a menu activation does not dispatch, no input line appears, and a
  borrowed free-form send keeps its typed speech in the field with focus
  retained in the field

#### Scenario: Free-form dialogue echoes exactly one line

- **WHEN** a player sends free-form speech to a present NPC and the
  `explore.talk_freeform` request dispatches
- **THEN** exactly one `talk <NPC> <speech>` line is appended at dispatch, the
  field clears and returns focus to the action dock, and no second raw-text
  echo appears

#### Scenario: Preparing a command in the field echoes nothing

- **WHEN** the player types a command into the field, walks the history, or
  completes it with Tab, without sending
- **THEN** no display line is appended and no request is dispatched, and exactly
  one line is appended only once the player sends the prepared command

#### Scenario: Reconnect replay does not double-echo

- **WHEN** a transport drops after a submit and reconnects
- **THEN** the store rebuilds panels, the uncertain-result notice shows, and no
  second echo is appended

#### Scenario: A backpack row echoes its typed command

- **WHEN** the player confirms an item use (or activates an equipment toggle)
  on a backpack row and the request dispatches
- **THEN** exactly one line — `use <item_key>` or `equip <item_key>` — is
  appended at dispatch and the dispatch envelope is unchanged

#### Scenario: A shop drawer purchase echoes from the row's server label

- **WHEN** the player buys from a shop drawer row and the `shop.buy` request
  dispatches
- **THEN** exactly one `buy <物品> <數量>` line appears, composed from the
  server-authored row display name, and the envelope carries no echo data

#### Scenario: A minimap move echoes the server-authored exit label

- **WHEN** the player activates a movable minimap node and the `explore.move`
  request dispatches
- **THEN** exactly one line carrying the uniquely matching committed local-map
  edge label, or the destination node's label when no unique edge label
  exists, appears, and with neither available the dispatch stays silent

#### Scenario: An AREA cast on explicit targets echoes every target

- **WHEN** the player confirms an AREA cast whose payload carries explicit
  selected target ids (no approved shorthand)
- **THEN** the one echoed line names the skill and every selected target's
  display name in payload order, joined with `、`, and nothing is dropped

#### Scenario: A scaled cast echoes the chosen magnitude

- **WHEN** the player submits a combat cast row (single-target or AREA) with a
  non-default freeform magnitude
- **THEN** the one echoed line carries the skill label with the chosen
  magnitude label suffix and the target/shorthand, and the payload is
  unchanged

#### Scenario: A creation confirmation echoes the path it re-runs

- **WHEN** the player confirms `creation.activate` for a chosen preset draft
  (or confirms `creation.reset`) and the request dispatches
- **THEN** exactly one line — `character preset <key>` for a preset (else
  `character create`), or the reset row's bounded action label (the pinned
  no-typed-command form) — is appended at dispatch

## REMOVED Requirements

### Requirement: Every deliberate mutation echo appears exactly once at dispatch
**Reason**: Re-titled as "A deliberate mutation echo appears exactly once at dispatch" so the retired quick-word-chip scenario can be dropped (a MODIFIED block cannot drop a scenario); the stale quantity-form surface named in the text is removed with it.
**Migration**: The behaviour is unchanged and fully restated by "A deliberate mutation echo appears exactly once at dispatch"; tests annotated with the old requirement ID re-anchor to the new one.
