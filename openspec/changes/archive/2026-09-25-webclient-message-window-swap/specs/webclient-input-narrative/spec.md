## MODIFIED Requirements

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
lost), and the command line SHALL stay expanded. The completion of a borrowed
dialogue SHALL be signalled by collapsing the command line and returning focus
to the action dock. Text written into the command field without
sending (typing, a history walk, or Tab completion) SHALL NOT echo: it dispatches
nothing, so no line exists to append until the player sends. The echo line SHALL be inserted as literal text via the same
narrative append path used by server output — it heads the response it begins,
is presented in the full-log surface, and is never one of that response's
pages — SHALL NOT enter the markup pipeline, SHALL NOT be sent or reused as a
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
  retained in the field and the command line still expanded

#### Scenario: Free-form dialogue echoes exactly one line

- **WHEN** a player sends free-form speech to a present NPC and the
  `explore.talk_freeform` request dispatches
- **THEN** exactly one `talk <NPC> <speech>` line is appended at dispatch, the
  field clears, the command line collapses and returns focus to the action
  dock, and no second raw-text echo appears

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

## ADDED Requirements

### Requirement: The message window's reading controls advance pages and a new action flushes unread pages
A pointer activation on the message window SHALL advance to the next page of the current response,
except when it lands on a control inside the window or ends a text selection inside it. The window's
page surface SHALL be focusable and in the tab order. Enter or Space SHALL advance only while keyboard
focus is on that page surface. Such a key SHALL be consumed by the window and SHALL NOT reach the
action dock's keyboard routing, and a held key's auto-repeat SHALL NOT advance. While focus is
anywhere else (the action dock, a drawer, an overlay, the command line, or a control in the band),
Enter and Space SHALL keep their existing meaning and SHALL NOT advance a page. Advancing on the last
page SHALL do nothing. Pages SHALL appear in full at once.

The player SHALL be able to act at any time while pages remain. When an action records its response
mark or appends its input line, the window SHALL stop presenting the previous response's unread pages
and SHALL show that response's last page until the new response's first line is retained. It SHALL
then show the new response's first page. The unread pages SHALL remain in the full-log surface. Lines
appended to the response being read SHALL NOT move the reader off the page on screen. A change of the
window's box or of the prose scale SHALL re-page the current response, and SHALL keep the reader on
the page that holds the first character that was on screen.

Paging SHALL wait until the client's fonts have loaded. Until then the window SHALL show the current
response's first block, scrollable. When the window mounts, including after a reconnect, it SHALL show
the last page of the last response and SHALL NOT replay earlier pages.

A polite live region SHALL announce each page's full text once, when the page is shown. It SHALL
announce each line later appended to the page on screen once, and SHALL announce nothing on a re-page
or on a mount. The page surface itself SHALL NOT be a live region. None of this SHALL change the
narrative log, the dispatch path, or any request.

#### Scenario: A click advances the page
- **WHEN** the current response has three pages and the player clicks the window twice
- **THEN** the window shows page 2 and then page 3, and the marker reads `■`

#### Scenario: Enter on the page surface advances
- **WHEN** the page surface has keyboard focus and the player presses Enter, then Space
- **THEN** each key advances one page, and the action dock's focused item is not activated and
  its multi-select state does not change

#### Scenario: Enter on the dock does not advance
- **WHEN** the current response has further pages and the player presses Enter with focus on the
  action dock
- **THEN** the dock activates its focused item exactly as before, and the window's page does not
  change

#### Scenario: A held key does not skip pages
- **WHEN** the player holds Enter on the page surface of a four-page response
- **THEN** the window advances exactly one page

#### Scenario: Acting while reading flushes the unread pages
- **WHEN** the player is on page 1 of a three-page response and activates a dock move whose echo
  and room text then arrive
- **THEN** the window shows the move's response from its first page, and pages 2 and 3 of the
  earlier response are still present in the full-log surface

#### Scenario: A silent action flushes before its reply arrives
- **WHEN** the player is on page 1 of a two-page response and activates the dialogue exit row,
  and no line has arrived yet
- **THEN** the window shows the earlier response's last page with `■` until the farewell line
  arrives, and then shows that line's page

#### Scenario: New lines do not move the reader
- **WHEN** the player is on page 1 of the current response and further lines of the same response
  arrive and form a second page
- **THEN** the window stays on page 1 and the marker reads `▼`

#### Scenario: A resize keeps the reader's text on screen
- **WHEN** the player is on page 2 and the viewport shrinks from 1920x1080 to 1280x720
- **THEN** the window shows the page of the new paging that holds the first character that was on
  screen before the resize

#### Scenario: A prose-scale change keeps the reader's text on screen
- **WHEN** the player is on page 2 and changes the prose scale in the settings surface
- **THEN** the current response is re-paged, and the window shows the page holding the first
  character that was on screen

#### Scenario: Pages wait for fonts
- **WHEN** the client's fonts have not finished loading and a response arrives
- **THEN** the window shows that response's first block, scrollable, and pages it only after the
  fonts have loaded

#### Scenario: A reconnect shows the last page
- **WHEN** the transport drops and reconnects, or the window mounts with a retained log
- **THEN** the window shows the last page of the last response, and no earlier page is shown or
  announced

#### Scenario: Each page is announced once
- **WHEN** a two-page response arrives, the player advances once, and the viewport is then
  resized
- **THEN** the polite live region has announced page 1's text once and page 2's text once, and
  announced nothing on the resize
