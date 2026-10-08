## Purpose

The display-only client command-line catalog that fountains the player-facing narrative: typed drawer
commands and button-triggered `ui_action` mutations resolve to exactly one readable command line each,
so the narrative log reads as a complete, explainable action→result flow. The catalog is pure client
presentation — it never submits, never replays, never alters dispatch payloads, and never touches the
transport.

## Requirements

### Requirement: The command-line catalog resolves a display line deterministically

The browser SHALL resolve, for every button-triggered mutation submission, exactly one readable display command line from `(actionId, payload, display)` — `display` a bounded descriptor of server-authored labels attached at menu-build time — through a single pure, deterministic, DOM-independent catalog function `commandLine(actionId, payload, display)` that touches no `document`/`window`, storage, transport, or network.

#### Scenario: A talk button resolves to its typed command

- **WHEN** the player submits `explore.talk_scripted` with a keyword whose
  descriptor carries the NPC display name and the keyword label
- **THEN** the catalog returns `talk <NPC> <話題>` with the descriptor values
  filled in and the log shows one input line for it

#### Scenario: A navigation item emits nothing

- **WHEN** the player opens a submenu or presses a back row
- **THEN** the catalog returns `null` and no narrative line is appended

#### Scenario: An action without a typed command shows its label

- **WHEN** the player submits an action that has no canonical typed form (for
  example `combat.flee`)
- **THEN** the catalog returns a bounded display line derived from the
  control's action label (server- or client-authored, verbatim-pinned), not a
  guessed command

#### Scenario: The catalog never guesses a name from an opaque id

- **WHEN** a display descriptor lacks a label the command line needs
- **THEN** the catalog returns `null` for that action rather than fabricating a
  name

#### Scenario: An inventory use resolves to the typed use command

- **WHEN** the catalog is asked for `inventory.use` with payload
  `{ item_key: "healing_potion" }`
- **THEN** it returns `use healing_potion`, the exact text the typed command
  line accepts

#### Scenario: The equipment toggle echoes the typed equip command in both directions

- **WHEN** the catalog is asked for `inventory.toggle_equip` with payload
  `{ item_key: "leather_vest" }`, whether the click equips or unequips
- **THEN** it returns `equip leather_vest` and never invents an `unequip`
  command

#### Scenario: The silent presentation control emits nothing

- **WHEN** the catalog is asked for `options.dismiss`
- **THEN** it returns `null` and no narrative line is appended

#### Scenario: The silent control is a pure visibility control

- **WHEN** the declared silent presentation control `options.dismiss` is examined
- **THEN** it is a UI visibility control with no game action and no typed equivalent

#### Scenario: The display descriptor is a bounded label bundle from menu-build time

- **WHEN** the catalog composes a line from the `display` descriptor
- **THEN** the descriptor carries only server-authored labels attached to the item at menu-build time — exit label, NPC display name, keyword label, skill label, item key, quantity, seconds/daypart — and nothing else

#### Scenario: The catalog is pure and deterministic

- **WHEN** the catalog function runs
- **THEN** it is pure and deterministic — no `document`/`window`, no storage, no transport, no network

#### Scenario: Every registered mutation action is a supported action
- **WHEN** the catalog is asked for any registered mutation action other than the explicitly declared silent presentation controls
- **THEN** it returns a non-empty bounded string

#### Scenario: Non-mutation menu items never log

- **WHEN** the catalog is asked for a non-mutation item — menu navigation, a back row, a submenu open, a scripted-keyword category entry, or a disabled row
- **THEN** it returns `null` so no inner menu step produces a log line

#### Scenario: Canonical typed commands carry descriptor values

- **WHEN** the server exposes a canonical typed command for the action
- **THEN** the line is that command with the descriptor values filled in — such as `talk <NPC> <話題>`, `engage <目標>`, `cast <技能>[=<目標>]`, `wait <時段>`, `rest <秒數>`, `sleep`, `buy <物品> <數量>`, `sell <物品> <數量>`, `use <item_key>`, `equip <item_key>`, and the guild/creation forms

#### Scenario: Inventory lines come from the payload's own item_key

- **WHEN** the catalog builds an inventory line
- **THEN** it is built from the payload's own `item_key` — the literal argument the typed `use`/`use` alias `使用` and `equip` alias `裝備` commands accept
- **AND** the equipment toggle echoes `equip <item_key>` for both the equip and the unequip direction, because the typed command is itself the toggle

#### Scenario: Exit traversal emits the server-authored exit label

- **WHEN** the player traverses an exit and the panel carries a server-authored exit label
- **THEN** the catalog emits that label as a documented action description, because no `move` command exists, and SHALL NOT invent a command

#### Scenario: Labelless controls emit a pinned client-owned label

- **WHEN** an action with no typed command (`combat.flee`, `creation.reset`, an exit traversal) activates on a panel that carries no server-authored label
- **THEN** the catalog emits a bounded action label of the activating control, verbatim-pinned and client-owned, and SHALL NOT invent a command

#### Scenario: The catalog never reads availability

- **WHEN** the catalog composes any line
- **THEN** it reads and duplicates no availability rule — enabled/disabled, cost, and target set continue to come only from the server — and the module is fully unit-testable in Node

### Requirement: A deliberate mutation echo appears exactly once at dispatch

The browser SHALL append the resolved display line to the narrative exactly once per deliberate mutation in the single submit path: the echo fires at the moment the `ui_action` request is dispatched (a request id is returned), never on retry, resync, reconnect-replay, or a second client-local toggle, and never when submission is blocked (offline, mutations locked, not initialized, or a duplicate/in-flight request).

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

#### Scenario: A button click and its keyboard activation each echo once

- **WHEN** a player activates a mutation by a button click, and separately by the identical keyboard activation
- **THEN** each of the two SHALL echo exactly once

#### Scenario: Every dispatch surface hands the catalog its labels

- **WHEN** a deliberate activation comes from any dispatch surface — backpack row, shop drawer row, minimap move, combat row with or without a non-default magnitude, services row, creation activate/reset confirmation
- **THEN** the surface SHALL hand the catalog the labels it already holds — forwarded row descriptors (including the chosen non-default cast magnitude's label and the explicit target labels on combat rows, and the descriptor on creation confirmation items), fields read verbatim from committed state at dispatch time (shop row display names, the uniquely matching local-map edge label or the destination node label, NPC display names, the committed creation confirmation descriptor), or the payload itself — so the activation produces its line instead of silently resolving to `null`

#### Scenario: An ambiguous local-map edge degrades to the destination node

- **WHEN** a minimap move's local-map edge match is ambiguous
- **THEN** the echo MUST NOT pick an arbitrary edge and instead degrades to the destination-node label

#### Scenario: A label-less surface stays silent only by reviewed expectation

- **WHEN** a surface genuinely has no label for the line
- **THEN** it stays silent rather than fabricating one, and any such silence SHALL be an explicit, reviewed expectation of the test suite covering the surfaces — no dispatch path may fall silent unannounced

#### Scenario: The action path owns the borrowed free-form dialogue

- **WHEN** a free-form send dispatches through the borrowed command field
- **THEN** the command field's borrowed branch SHALL not append its own line, so the single free-form send yields exactly one line (`talk <NPC> <speech>`)

#### Scenario: The echo line is positioned as literal narrative text

- **WHEN** the echo line is appended
- **THEN** it is inserted as literal text via the same narrative append path used by server output, it heads the response it begins, is presented in the full-log surface, and is never one of that response's pages

#### Scenario: The echo line is inert to markup and dispatch

- **WHEN** an echo line exists
- **THEN** it SHALL NOT enter the markup pipeline, SHALL NOT be sent or reused as a submitted command, and SHALL have no effect on the validated action payload (`U9` intact: dispatch stays allowlist + exact)

#### Scenario: Rejection keeps the record of the act

- **WHEN** the server later rejects the action whose echo line was appended
- **THEN** the line is not removed, because the line records what the player acted

### Requirement: Echoed command lines never affect state

The display command line SHALL be strictly input-side and presentation-only. It SHALL never be evaluated, parsed, held for re-execution, or sent as a `text` message, and it SHALL NOT write to localStorage, session state, transport, epoch, or revision. The catalog module SHALL keep no stored state and be safe to instantiate per page.

#### Scenario: Unknown action stays silent
- **WHEN** the catalog is asked for an unregistered `actionId`
- **THEN** it returns `null` and no narrative line is created

#### Scenario: Display text is never treated as markup
- **WHEN** a label-derived line contains characters that resemble markup
- **THEN** the narrative renders it as literal text with no element or script created

#### Scenario: Oversized labels degrade to bounded literal text
- **WHEN** a server label used by the catalog exceeds the bound
- **THEN** the emitted line is truncated to the bounded length and rendered as literal text

#### Scenario: A missing payload stays silent
- **WHEN** the catalog is asked for a valid `actionId` with a missing payload
- **THEN** it returns `null` (silent) rather than a guessed command

#### Scenario: A descriptor missing a required label stays silent
- **WHEN** a display descriptor lacks a label the command line needs
- **THEN** the catalog returns `null` (silent) rather than a guessed command

#### Scenario: A non-string server label degrades to bounded literal text
- **WHEN** a server label used by the catalog is not a string
- **THEN** it is handled as an oversized label: truncated to a bounded length with literal-text rendering

### Requirement: Catalog coverage is pinned against the action registry

The test suites SHALL pin the command-line catalog's coverage of the action registry: the Node catalog suite SHALL enumerate every registered mutation action id and assert each one either resolves to a non-empty bounded line from a pinned fixture or appears on the declared silent presentation-control list, so a newly registered action cannot ship with a silent catalog gap.

#### Scenario: A new registered action without catalog coverage fails the gate

- **WHEN** an action id is registered in the production registry but is absent
  from both the catalog coverage fixtures and the silent presentation-control
  list
- **THEN** the Node coverage test or the registry equality test fails, naming
  the missing id

#### Scenario: Silent status is an explicit declaration

- **WHEN** the Node coverage test processes `options.dismiss`
- **THEN** it asserts the id is on the silent presentation-control list and
  resolves to `null`, and any other registered mutation action is required to
  resolve non-null

#### Scenario: The registry mirrors the enumerated set

- **WHEN** the Python test runs against the production action registry
- **THEN** it asserts the registry's action ids equal the same enumerated set the Node catalog suite pins

#### Scenario: The pinned lists are deterministic literals

- **WHEN** either coverage pin executes
- **THEN** it reads deterministic literals only — no live services, and no parsing of the other language's source at runtime

#### Scenario: The pins complement the per-surface test table

- **WHEN** the dispatch requirement's per-surface behavioral test table is considered
- **THEN** these pins complement — and never replace — that table, where every dispatch surface (and every intentional silence) is a reviewed row and the set of action ids exercised by that table covers every registered mutation id except the silent presentation controls

### Requirement: The full-log surface opens at its latest line
Whenever the full-log surface opens, it SHALL present the most recent retained narrative line in view, with its scroll region scrolled to the end of its content, so the player sees the latest one or two replies without scrolling. The scroll region is the log's one scrolling box inside its frame; it SHALL take the initial focus, so the reading keys scroll it at once.

#### Scenario: A long log opens at the latest reply
- **WHEN** the narrative retains more lines than the full-log surface can show at once and the player
  opens the full-log surface
- **THEN** the scroll region's offset is at the end of its content, the most recently retained line
  is inside the scroll region's visible box, and the first retained line is scrolled out of view above

#### Scenario: Older lines stay reachable
- **WHEN** the full-log surface has opened at its latest line and the player scrolls up
- **THEN** earlier retained lines come into view in their original order, rendered through the same
  markup renderer

#### Scenario: A line arriving while reading does not move the reader
- **WHEN** the player has scrolled the open full-log surface up to read older lines and a new
  narrative line is retained
- **THEN** the scroll region's offset is unchanged, and the new line is present at the end of the log

#### Scenario: Reopening returns to the latest line
- **WHEN** the player scrolls the full-log surface up, closes it, a new line is retained, and the
  player opens it again
- **THEN** the surface opens at its end again, with the newly retained line in view

#### Scenario: The latest line is reached before any interaction
- **WHEN** the full-log surface is opening
- **THEN** it reaches the end-of-content position after it takes focus and before the player can
  interact with it, and it does NOT first flash its opening lines

#### Scenario: The complete narrative keeps rendering
- **WHEN** the surface has opened at its latest line
- **THEN** older lines stay reachable by scrolling up, and the surface keeps presenting the complete
  retained narrative through the same markup renderer as before

#### Scenario: Open-surface offset survives retention trimming
- **WHEN** the surface is open and a newly retained line arrives, including once retention trimming
  removes the oldest line
- **THEN** the new line does not change the scroll region's offset

#### Scenario: Only opening places the reader at the latest line
- **WHEN** the reader has moved away from the end of the content after the surface opened
- **THEN** nothing but opening the surface places the reader back at the latest line

#### Scenario: The surface keeps its modal lifecycle
- **WHEN** the full-log surface is open
- **THEN** its focus trap, its Escape close, and its focus restore to the opening control are
  unchanged

### Requirement: The narrative log is segmented into responses at each player action
The browser SHALL derive a sequence of responses from the retained narrative log as a client-local
presentation view. A response SHALL begin at each retained player input line and at each response
mark, and SHALL collect every following server, system, and error line until the next response
begins.

#### Scenario: A typed command begins a response
- **WHEN** the player sends `look` from the command line and two server lines follow
- **THEN** the latest response has the `look` input line as its header and exactly those two
  server lines as its blocks

#### Scenario: A silent action begins a response
- **WHEN** the player activates the dialogue exit row, `explore.dialogue_leave` dispatches with no
  echo line, and the server's farewell line follows
- **THEN** the farewell line is the first block of a new response that has no input line, and it
  is not appended to the previous response

#### Scenario: An echoing action begins exactly one response
- **WHEN** the player activates a dock move row, the `explore.move` echo line is appended at
  dispatch, and room text follows
- **THEN** exactly one new response begins, its header is the echo line, and no empty response
  sits between the previous response and it

#### Scenario: A late line joins the current response
- **WHEN** a response has begun for the player's latest action and a further server line arrives
  before any other action
- **THEN** that line is appended to the latest response's blocks

#### Scenario: Output before any action forms a leading response
- **WHEN** the log holds only lines retained since login with no input line and no response mark
- **THEN** exactly one response exists, with no header, holding every retained line as a block

#### Scenario: A blocked dispatch records no boundary
- **WHEN** a dock activation is refused because a mutation is in flight and a server line then
  arrives
- **THEN** no response mark is recorded and the line joins the current response

#### Scenario: Trimming keeps segmentation stable
- **WHEN** the log exceeds its retention bound and its oldest lines are trimmed
- **THEN** every response whose lines are all still retained has the same header and blocks as
  before the trim, and no response mark refers to a trimmed line

#### Scenario: A response mark is recorded at the dispatch moment
- **WHEN** a deliberate mutation is dispatched (a request id is returned)
- **THEN** a response mark is recorded at that moment, whether or not that dispatch appends an echo
  line, so an action the echo catalog declares silent still begins a new response

#### Scenario: The response view never leaks outward
- **WHEN** the browser derives the response view
- **THEN** the view never mutates the log, never reaches the server, and never changes what the
  full-log surface presents

#### Scenario: A synchronously failed send records no mark
- **WHEN** a dispatch's send fails synchronously
- **THEN** no response mark is recorded

#### Scenario: The input header is full-log-only and never pageable
- **WHEN** a response displays its input line as its header
- **THEN** that line is presented only in the full-log surface and is not one of the response's
  pageable blocks

#### Scenario: A fresh mark begins no response yet
- **WHEN** a response mark has no retained line after it yet
- **THEN** it begins no response

#### Scenario: Connection notices and first login output lead the leading response
- **WHEN** lines retained before any response begins include a connection notice or the first
  output after login
- **THEN** they form a leading response with no input line

#### Scenario: Retained lines carry ordinals that survive the trim
- **WHEN** lines are retained and the oldest are later trimmed
- **THEN** every retained line carries a monotonically increasing ordinal that survives the
  retention trim, so trimming the oldest lines leaves the segmentation of the lines still retained
  unchanged

#### Scenario: Marks older than the trim are discarded
- **WHEN** retention trimming removes the oldest lines
- **THEN** response marks older than the oldest retained line are discarded with the trim

### Requirement: A response is cut into pages that fit a measured box and never mid-sentence
The browser SHALL cut a response's pageable blocks into pages through a pure, deterministic function
of the blocks and an injected fit test. Each server, system, or error line SHALL be one block, in log
order. A page SHALL hold as many whole blocks as fit. When a block does not fit the room left on the
page, it SHALL be split at the last point that fits, trying in this order: a hard line break or the
end of a sentence, then a clause mark, then a character boundary.

#### Scenario: Whole blocks are packed first
- **WHEN** a response has three short prose blocks that together fit the box
- **THEN** the response has exactly one page holding all three blocks unsplit

#### Scenario: A system or error block begins a new page
- **WHEN** a response holds one prose block followed by an error block, and both would fit together
- **THEN** the response has two pages, and the error block is the first block of the second page

#### Scenario: A long block splits at a sentence end
- **WHEN** a prose block of several sentences does not fit the room left, and a sentence end falls
  inside the part that fits
- **THEN** the earlier page ends at the last sentence end that fits, including any closing quote
  after it, and the later page starts with the next sentence

#### Scenario: A block without a fitting sentence end splits at a clause mark
- **WHEN** no sentence end or hard break falls inside the part of a block that fits, but a `，`
  does
- **THEN** the earlier page ends at the last clause mark that fits

#### Scenario: A block without any mark splits at a character
- **WHEN** neither a sentence end, a hard break, nor a clause mark falls inside the part that fits
- **THEN** the block is split at the last character that fits, and no surrogate pair is divided

#### Scenario: A split inside a styled span keeps its style
- **WHEN** a split point falls inside a span carrying a colour class
- **THEN** the earlier page's text ends inside a span with that class, the later page's text
  begins inside a new span with the same class and style, and no other markup is emitted

#### Scenario: A box-drawing block too tall for the box gets its own scrolling page
- **WHEN** a response holds a box-drawing map taller than the box
- **THEN** the map is not split, sits alone on a page marked oversize, and every row of it is
  present on that page

#### Scenario: Box-drawing blocks are never split
- **WHEN** a response's blocks include a box-drawing block and paging runs
- **THEN** the box-drawing block is never split

#### Scenario: Paging is lossless
- **WHEN** any response is paged for any box
- **THEN** the pages' text, concatenated in order, equals the blocks' text less only the line
  breaks consumed at split points

#### Scenario: A re-page finds the reader's character
- **WHEN** a response paged for one box is paged again for a narrower box
- **THEN** for any character offset, the function names the page of the new paging that holds
  that character

#### Scenario: The fit test answers box containment
- **WHEN** the paging function consults its injected fit test
- **THEN** the fit test reports whether a candidate page's content fits the message box

#### Scenario: A sentence end is a defined punctuation run
- **WHEN** the pager looks for the sentence-end split point
- **THEN** a sentence end is `。`, `！`, `？`, `…`, or ASCII `.`, `!`, `?` followed by whitespace,
  taken together with any directly following run of end marks and closing quotes or brackets
  (`」`, `』`, `）`, `"`, `'`)

#### Scenario: A clause mark is a defined punctuation set
- **WHEN** the pager looks for the clause-mark split point
- **THEN** a clause mark is `，`, `、`, `；`, `：`, or ASCII `,`, `;`, `:` followed by whitespace

#### Scenario: A character boundary keeps surrogate pairs whole
- **WHEN** the pager falls back to a character boundary
- **THEN** the split SHALL NOT separate a surrogate pair

#### Scenario: An unplaceable block moves whole to a new page
- **WHEN** no split point of the block fits the room left on a non-empty page
- **THEN** the whole block moves to a new page first

#### Scenario: A continuation does not repeat its split break
- **WHEN** a block is split at a hard line break
- **THEN** the continuation does not begin with the hard line break it was split at

#### Scenario: Paging runs on tokens, not rendered HTML
- **WHEN** paging executes
- **THEN** it runs on the markup pipeline's token stream, never on rendered HTML, and emits no
  markup the pipeline did not produce

#### Scenario: A block too large for any page gets an oversize page
- **WHEN** a block fits no empty page after every split point (a box-drawing block taller than the
  box, or a box too small for one character)
- **THEN** it gets a page of its own marked oversize, which the view presents with internal
  scrolling

#### Scenario: Nothing is truncated or dropped
- **WHEN** a response's pages are concatenated
- **THEN** they reproduce its blocks' text in order, less only the line breaks consumed at split
  points — no content is ever truncated or dropped

### Requirement: The message window's reading controls advance pages and a new action flushes unread pages
A pointer activation on the message window SHALL act on the current page. While the page is still
typing, the activation SHALL show the page in full and SHALL NOT advance; once the page is fully
shown, it SHALL advance to the next page of the current response. Enter or Space SHALL act the same
way as the activation, and only while keyboard focus is on the window's page surface.

#### Scenario: A click advances the page
- **WHEN** the current response has three pages shown at the `instant` text speed and the player
  clicks the window twice
- **THEN** the window shows page 2 and then page 3, and the marker reads `■`

#### Scenario: A click during a playing round ends it
- **WHEN** a combat round is playing its second of three beats and the player presses Enter on the page
  surface
- **THEN** the round ends, the window shows the response's page after the beat pages, and no beat page is
  skipped in the full log

#### Scenario: A press while typing completes the page
- **WHEN** page 1 of a two-page response is still typing and the player clicks the window, then
  presses Enter on the page surface
- **THEN** the click shows page 1 in full with the marker `▼` and does not advance, and the Enter
  advances to page 2

#### Scenario: Enter on the page surface advances
- **WHEN** the page surface has keyboard focus on a fully shown page and the player presses Enter,
  then Space, with each following page fully shown before the next key
- **THEN** each key advances one page, and the action dock's focused item is not activated and
  its multi-select state does not change

#### Scenario: Enter on the dock does not advance
- **WHEN** the current response has further pages, its page is typing, and the player presses
  Enter with focus on the action dock
- **THEN** the dock activates its focused item exactly as before, the page keeps typing, and the
  window's page does not change

#### Scenario: A held key does not skip pages
- **WHEN** the player holds Enter on the page surface of a four-page response whose first page is
  typing
- **THEN** the first key event completes page 1, the auto-repeated events do nothing, and the
  window stays on page 1

#### Scenario: Acting while reading flushes the unread pages
- **WHEN** the player is on page 1 of a three-page response while it types and activates a dock
  move whose echo and room text then arrive
- **THEN** typing stops, the window shows the move's response from its first page, and pages 2 and
  3 of the earlier response are still present in the full-log surface

#### Scenario: A silent action flushes before its reply arrives
- **WHEN** the player is on page 1 of a two-page response and activates the dialogue exit row,
  and no line has arrived yet
- **THEN** the window shows the earlier response's last page, fully shown with `■`, until the
  farewell line arrives, and then shows that line's page

#### Scenario: New lines do not move the reader
- **WHEN** the player is on page 1 of the current response and further lines of the same response
  arrive and form a second page
- **THEN** the window stays on page 1, and once page 1 is fully shown the marker reads `▼`

#### Scenario: A resize keeps the reader's text on screen
- **WHEN** the player is on page 2 with its typing position at a known character, and the viewport
  shrinks from 1451x790 to an off-contract 1200x700 window
- **THEN** the window shows the page of the new paging that holds that character, the text before
  it on that page is shown at once, and typing continues from it

#### Scenario: A prose-scale change keeps the reader's text on screen
- **WHEN** page 2 is fully shown and the player changes the prose scale in the settings surface
- **THEN** the current response is re-paged, and the window shows the page holding the last
  character that was shown, with that character and everything before it on the page shown

#### Scenario: Pages wait for fonts
- **WHEN** the client's fonts have not finished loading and a response arrives
- **THEN** the window shows that response's first block in full, scrollable, and pages it only
  after the fonts have loaded

#### Scenario: A reconnect shows the last page
- **WHEN** the transport drops and reconnects, or the window mounts with a retained log
- **THEN** the window shows the last page of the last response fully shown with no typing, and no
  earlier page is shown or announced

#### Scenario: Each page is announced once
- **WHEN** a two-page response arrives at the `normal` text speed, the player waits for page 1 to
  finish typing, advances once, and the viewport is then resized
- **THEN** the polite live region has announced page 1's full text once, when page 1 started
  typing, and page 2's full text once, when page 2 started typing. It announced nothing on the
  typed characters, on the completions, or on the resize.

#### Scenario: A control or a text selection absorbs the activation
- **WHEN** a pointer activation lands on a control inside the window or ends a text selection
  inside it
- **THEN** it does not act on the current page

#### Scenario: Either activation ends a playing round
- **WHEN** a combat round plays by itself, as `webclient-combat-menu` "A combat round plays beat by
  beat" defines, and the player uses the same pointer activation or key
- **THEN** it instead ends the round at once and does not complete or advance a page

#### Scenario: The key is consumed by the window and repeats do not act
- **WHEN** the page surface has focus and a page-advancing Enter or Space is pressed, or the key is
  held
- **THEN** the key is consumed by the window and does not reach the action dock's keyboard routing,
  and a held key's auto-repeat does not act

#### Scenario: The page surface is focusable and in the tab order
- **WHEN** the player tabs through the message window's surface
- **THEN** the window's page surface is focusable and appears in the tab order

#### Scenario: Other focus locations keep Enter and Space
- **WHEN** focus is on a drawer, an overlay, the command line, or a control in the band
- **THEN** Enter and Space keep their existing meaning and do not complete or advance a page

#### Scenario: Advancing past the last page does nothing
- **WHEN** the current response's last page is fully shown and the player activates the window
- **THEN** advancing does nothing

#### Scenario: Reading is never blocked and the log reveals are separately defined
- **WHEN** a page is typing or pages remain
- **THEN** the player can act at any time, and how a page is revealed is defined by "A page types
  in at the reader's text speed and auto-advance is opt-in"

#### Scenario: A new action flushes the window between responses
- **WHEN** an action records its response mark or appends its input line while the previous
  response still has unread pages
- **THEN** the window stops typing and stops presenting those unread pages, shows the previous
  response's last page fully shown until the new response's first line is retained, then shows the
  new response's first page, and the unread pages remain in the full-log surface

#### Scenario: The typing position is well defined
- **WHEN** the window needs the reader's typing position for a re-page
- **THEN** it is the next character to reveal while a page is typing, or the last character shown
  once the page is complete

#### Scenario: Paging waits for fonts
- **WHEN** the client's fonts have not yet loaded
- **THEN** paging waits, and until then the window shows the current response's first block in
  full, scrollable

#### Scenario: Mounting shows the last page without replay
- **WHEN** the window mounts, including after a reconnect
- **THEN** it shows the last page of the last response fully shown, and does not type or replay
  earlier pages

#### Scenario: Appended lines are announced once
- **WHEN** a line is later appended to the page on screen
- **THEN** the polite live region announces that line once

#### Scenario: Silence on completion, re-page, and mount
- **WHEN** typing completes, a re-page happens, or the window mounts
- **THEN** the polite live region announces nothing

#### Scenario: The page surface is not a live region and nothing else changes
- **WHEN** the reading controls and announcements operate
- **THEN** the page surface itself is not a live region, and none of it changes the narrative log,
  the dispatch path, or any request

### Requirement: A page types in at the reader's text speed and auto-advance is opt-in
In every mode, dialogue included, each page the message window starts to show SHALL reveal its text
in reading order, one character at a time, at the reader's text speed. The speeds are `slow` 20
characters per second, `normal` 45, `fast` 90, and `instant`, which shows the page in full at once.
The reveal SHALL keep every character's final position from the first frame. Auto-advance is off by
default.

#### Scenario: A page types at the normal speed
- **WHEN** a one-page response of 90 characters arrives at the `normal` text speed with the effective
  motion level `full`
- **THEN** after about one second about 45 characters are visible, the page is fully shown after
  about two seconds, the marker is absent until then, and the text's rendered line boxes do not
  change between the first frame and the last

#### Scenario: Styled spans survive the reveal
- **WHEN** a page whose text carries a coloured span across the typing position is typing
- **THEN** the visible part of the span and its hidden remainder carry the same colour class, and
  the fully shown page's markup equals the markup of the same page at the `instant` speed

#### Scenario: Reduced motion forces instant pages
- **WHEN** the text speed is `slow` and the operating system requests reduced motion with no motion
  level stored, or the stored motion level is `reduced` or `off`
- **THEN** each page is fully shown with its marker as soon as it is shown, and a page that was
  typing when the level changed away from `full` completes at once

#### Scenario: An explicit off lets pages type
- **WHEN** the operating system requests reduced motion and the stored motion level is `full`, which
  turns reduced motion off
- **THEN** pages type at the chosen text speed

#### Scenario: Auto-advance waits in proportion to the page and stops at the last page
- **WHEN** auto-advance is on and a three-page response arrives whose first page holds 100
  characters
- **THEN** page 2 starts about 7.2 seconds after page 1 is fully shown, page 3 follows the same
  rule, and the window stays on page 3 with `■`

#### Scenario: Auto-advance holds while a surface is open
- **WHEN** auto-advance is on, page 1 of two is fully shown, and the player opens the full-log
  surface for ten seconds and then closes it
- **THEN** the window is still on page 1 when the surface closes, and it advances only after the
  rest of the wait has passed

#### Scenario: Auto-advance leaves maps to the player
- **WHEN** auto-advance is on and the page on screen is an oversize box-drawing map with a next
  page behind it
- **THEN** the window stays on the map page until the player advances

#### Scenario: Auto-advance holds on oversize and map pages
- **WHEN** auto-advance is on and the page on screen is an oversize page, or a page that holds a
  box-drawing map
- **THEN** auto-advance does not advance it; the page waits for the player

#### Scenario: The dialogue variant does not type
- **WHEN** mode is `dialogue`, the panel is available, and a two-page reply commits at the `slow` text
  speed with auto-advance on
- **THEN** no unpaged dialogue presentation renders: page 1 types at 20 characters per second with no
  choice row visible, the window advances to page 2 after the auto-advance wait, page 2 types, and
  the window stays on page 2 with `■` while the dialogue choice list appears over the stage

#### Scenario: Line breaks and map lines reveal as units
- **WHEN** the reveal reaches a hard line break or a box-drawing map line
- **THEN** the hard line break counts as one character and the map line appears whole

#### Scenario: Unrevealed text holds its place invisibly
- **WHEN** a page is mid-type
- **THEN** text not yet revealed occupies its place invisibly, so no line re-wraps and nothing
  moves while the page types, and the unrevealed text is hidden from assistive technology

#### Scenario: The reveal renders the pipeline's own markup
- **WHEN** a page types
- **THEN** the reveal renders the same markup, spans, and classes as the fully shown page, emits
  no markup the narrative pipeline does not produce, and runs that pipeline no more than once per
  line

#### Scenario: Reduced or off motion forces instant typing
- **WHEN** the effective motion level is `reduced` or `off`, as `webclient-contextual-hud` "The
  motion level is a client-local preference that governs every client animation" resolves it: a
  stored level, or, while none is stored, `reduced` when the operating system requests reduced
  motion
- **THEN** typing is instant, whatever the text speed

#### Scenario: Speed and motion changes apply from the next page
- **WHEN** the text speed or the effective motion level changes
- **THEN** the change applies from the next page, except that a change to `instant`, or to a level
  other than `full`, also completes the page that is typing

#### Scenario: The marker waits for the full page
- **WHEN** a page is typing
- **THEN** the page marker renders only once the page is fully shown

#### Scenario: Hidden-tab time does not type
- **WHEN** the page's browser tab is hidden while it types
- **THEN** the hidden time does not count toward typing

#### Scenario: The auto-advance wait is defined
- **WHEN** auto-advance is on and the page on screen is fully shown
- **THEN** the window advances to the next page after `1.2s + 60ms × the page's characters`, with
  the wait counted from the later of the page becoming fully shown and a next page existing

#### Scenario: The auto-advance wait pauses behind surfaces and hidden tabs
- **WHEN** any drawer, overlay, or the full-log surface is open, or the browser tab is hidden
- **THEN** the auto-advance wait pauses

#### Scenario: Player events restart or cancel the wait
- **WHEN** a manual advance, a flush by a new action, or a re-page happens
- **THEN** it restarts or cancels the auto-advance wait for the page then on screen

#### Scenario: Dialogue mode has no separate presentation
- **WHEN** mode is `dialogue` and the session line arrives
- **THEN** there is no separate dialogue presentation: the session line is part of the current
  response and types and auto-advances like any other page, the conversation's choices appear only
  once the response's last page is fully shown, as `webclient-contextual-hud` "Dialogue choices
  appear centred over the stage after the line is fully read" defines, and auto-advance does not
  advance past the last page into the choices — the choices are not a page

### Requirement: The full log is framed without changing retained content
The full-log surface SHALL present itself in the shared reference workspace used by the drawers and
utility overlays: one opaque panel under the shared reference header, which draws the log's glyph,
the title `日誌` labelling the dialog, and one close control. A scrim SHALL cover the whole viewport
behind the panel. The header SHALL only lend markup: the surface SHALL keep its own focus trap,
Escape close and focus restore, and SHALL NOT nest a second modal host.

#### Scenario: Echo is a section heading
- **WHEN** a retained response begins with a player input echo
- **THEN** that echo appears exactly once in its original position, styled as the response's heading
  after its divider, and its response lines remain unchanged

#### Scenario: The frame keeps the log's own modal lifecycle
- **WHEN** the player opens the full log, clicks the scrim, and presses Escape
- **THEN** the click neither closes the log nor moves focus out of it, Escape closes it, and focus
  returns to the control that opened it

#### Scenario: The scrim covers the top navigation too
- **WHEN** the scrim is drawn behind the panel
- **THEN** it covers the whole viewport, the top navigation included

#### Scenario: The scrim absorbs pointer input without closing
- **WHEN** pointer input lands on the scrim
- **THEN** the scrim absorbs it and the log does not close

#### Scenario: Pressing frame chrome keeps focus inside
- **WHEN** a pointer press lands on the frame's non-focusable chrome or the scrim
- **THEN** focus stays inside the surface, so Escape still closes it

#### Scenario: The column's measure, size, and face
- **WHEN** the log's lines render
- **THEN** they read as one centred column with a 42em measure at the log's reading size — the
  message window's page size, 18px at the 1451x790 reference scale with the same leading, which the
  narrative prose scale multiplies — set in the same bundled monospace reading face the message
  window's page text uses

#### Scenario: Chrome does not scale
- **WHEN** the narrative prose scale changes
- **THEN** the header, footer and their controls are chrome and do not scale

#### Scenario: The column reuses the message window's prose styling
- **WHEN** retained lines render in the column
- **THEN** the column reuses the message window's prose styling — the `sys` aside, the `err` line,
  the progressive CJK spacing — and every line shares the column's edge

#### Scenario: Map lines scroll inside their block
- **WHEN** a box-drawing map line renders in the column
- **THEN** it keeps its monospace grid and scrolls horizontally inside its own block rather than
  widening the column

#### Scenario: Input echoes head their responses
- **WHEN** a retained input echo renders in place
- **THEN** it is styled as the heading of the response it begins, after the existing divider
  hairline

#### Scenario: Every retained line renders exactly once in order
- **WHEN** the surface presents the retained narrative
- **THEN** every retained line renders exactly once and in its original order through the existing
  safe renderer, with no line duplicated, reordered, rewritten or removed, input echoes included,
  and opening still shows the latest line before interaction

### Requirement: Log readers can return to latest without losing their place involuntarily
When the scroll region's visible box ends above the end of its content, the full log SHALL offer a
labelled `回到最新` control in a footer strip outside the scroll region, so the control never covers a
line or a text selection; at the end of the content the control SHALL be absent. Arriving lines SHALL
NOT force-scroll the reader. Activating the control SHALL move focus to the scroll region and reveal
the latest retained line.

#### Scenario: New text arrives during review
- **WHEN** the player has scrolled upward and a new response arrives
- **THEN** the viewed position remains stable and the return control reveals the new end only when
  activated

#### Scenario: The control is absent at the end
- **WHEN** the full log opens at its latest line
- **THEN** no return control is rendered until the player scrolls above the end

#### Scenario: Returning leaves the message window alone
- **WHEN** the player activates the return control while the message window shows page 1 of a
  multi-page response
- **THEN** the scroll region shows its latest line with focus on it, the control is gone, the message
  window still shows the same page, and no action is sent

#### Scenario: New content changes the control's label
- **WHEN** a line has been retained since the reader last saw the end
- **THEN** the control also reads `新內容`, until the end is in view again

#### Scenario: Arrival is recognised by the retention ordinal
- **WHEN** retention trimming keeps the line count constant while a new line arrives
- **THEN** the arrival is still recognised, because it is recognised by the newest line's retention
  ordinal

#### Scenario: The smooth reveal obeys the motion level
- **WHEN** activating the control reveals the latest retained line
- **THEN** the scroll moves smoothly only at the full motion level

#### Scenario: Returning changes nothing else
- **WHEN** the player activates the return control
- **THEN** it does not re-page the message window, dispatch any action, or change the log's
  retention

#### Scenario: Focus hands off before the control leaves
- **WHEN** the end comes into view while the control holds focus
- **THEN** focus moves to the scroll region before the control leaves

#### Scenario: Reading keys scroll from the log's controls
- **WHEN** the reading keys (arrows, Page Up and Page Down, Home and End) are pressed on the log's
  controls
- **THEN** they scroll the region as they do when it has focus

#### Scenario: Only the full log gets the control
- **WHEN** the message window renders
- **THEN** its own rule of rendering no jump-to-latest control is unchanged; this control belongs
  to the full log only
