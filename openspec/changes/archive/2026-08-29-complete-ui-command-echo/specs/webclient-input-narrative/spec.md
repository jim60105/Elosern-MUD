# Delta: webclient-input-narrative

## MODIFIED Requirements

### Requirement: The command-line catalog resolves a display line deterministically

The browser SHALL resolve, for every button-triggered mutation submission,
exactly one readable display command line from `(actionId, payload, display)`
where `display` is a bounded descriptor of server-authored labels (exit label,
NPC display name, keyword label, skill label, item key, quantity,
seconds/daypart) attached to the item at menu-build time — through a single
DOM-independent catalog function
(`commandLine(actionId, payload, display)`): the catalog SHALL be pure and
deterministic (no `document`/`window`, no storage, no transport, no network),
and every registered mutation action SHALL be a supported mutation action: the
catalog SHALL return a non-empty bounded string for every registered mutation
action except the explicitly declared silent presentation controls, and SHALL
return `null` for the silent presentation control `options.dismiss` (a UI
visibility control with no game action and no typed equivalent) and for every
non-mutation item (menu navigation, back rows, submenu opens, scripted-keyword
category entries, disabled rows) so no inner menu step produces a log line.
Where the server exposes a canonical typed command, the line SHALL be that
command with the descriptor values filled in (such as `talk <NPC> <話題>`,
`engage <目標>`, `cast <技能>[=<目標>]`, `wait <時段>`, `rest <秒數>`, `sleep`,
`buy <物品> <數量>`, `sell <物品> <數量>`, `use <item_key>`,
`equip <item_key>`, and the guild/creation forms). For the inventory surface
the line SHALL be built from the payload's own `item_key` — the literal
argument the typed `use`/`use` alias `使用` and `equip` alias `裝備` commands
accept — and the equipment toggle SHALL echo `equip <item_key>` for both the
equip and the unequip direction, because the typed command is itself the
toggle. Where no typed command exists — exit traversal (no `move` command),
`combat.flee`, and the `creation.reset` control — the catalog SHALL emit a
bounded action label of the activating control as a documented action
description (the server-authored exit label where the panel carries one, a
verbatim-pinned client-owned control label where it does not) and SHALL NOT
invent a command. The catalog
SHALL be fully unit-testable in Node and SHALL NOT read or duplicate any
availability rule — enabled/disabled, cost, and target set SHALL continue to
come only from the server.

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

### Requirement: Every deliberate mutation echo appears exactly once at dispatch

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
from any surface (backpack row, shop drawer row, quantity-form Enter, minimap
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
rather than by closing a surface. A quick-word chip SHALL NOT echo: it prepares
text in the field and dispatches nothing, so no line exists to append until the
player sends. The echo line SHALL be inserted as literal text via the same
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

#### Scenario: Preparing a command from a chip echoes nothing

- **WHEN** the player activates a quick-word chip and the verb is written into
  the command field
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

### Requirement: Catalog coverage is pinned against the action registry

The test suites SHALL pin the command-line catalog's coverage of the action
registry: the Node catalog suite SHALL enumerate every registered mutation
action id and assert each one either resolves to a non-empty bounded line from
a pinned fixture or appears on the declared silent presentation-control list,
and a Python test SHALL assert the production action registry's action ids
equal the same enumerated set, so a newly registered action cannot ship with a
silent catalog gap. The pinned lists SHALL be deterministic literals (no live
services, no parsing of the other language's source at runtime). These pins
complement — and never replace — the per-surface behavioral test table of the
dispatch requirement, where every dispatch surface (and every intentional
silence) is a reviewed row and the set of action ids exercised by that table
covers every registered mutation id except the silent presentation controls.

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
