## Purpose

The display-only client command-line catalog that fountains the player-facing narrative: typed drawer
commands and button-triggered `ui_action` mutations resolve to exactly one readable command line each,
so the narrative log reads as a complete, explainable action→result flow. The catalog is pure client
presentation — it never submits, never replays, never alters dispatch payloads, and never touches the
transport.

## ADDED Requirements

### Requirement: The command-line catalog resolves a display line deterministically

The browser SHALL resolve, for every button-triggered mutation submission, exactly one readable
display command line from `(actionId, payload, display)` where `display` is a bounded descriptor of
server-authored labels (exit label, NPC display name, keyword label, skill label, quantity,
seconds/daypart) attached to the item at menu-build time — through a single DOM-independent catalog
function (`commandLine(actionId, payload, display)`): the catalog SHALL be pure and deterministic (no
`document`/`window`, no storage, no transport, no network), SHALL return a non-empty bounded string
for every supported mutation action, and SHALL return `null` for every non-mutation item (menu
navigation, back rows, submenu opens, scripted-keyword category entries, disabled rows) so no inner
menu step produces a log line. Where the server exposes a canonical typed command, the line SHALL be
that command with the descriptor values filled in (such as `talk <NPC> <話題>`, `engage <目標>`,
`cast <技能>[=<目標>]`, `wait <時段>`, `rest <秒數>`, `sleep`, `buy <物品> <數量>`,
`sell <物品> <數量>`, and the guild/creation forms). Where no typed command exists — exit traversal
(no `move` command) and `combat.flee` — the catalog SHALL emit the bounded server-authored action
label as a documented action description and SHALL NOT invent a command. The catalog SHALL be fully
unit-testable in Node and SHALL NOT read or duplicate any availability rule — enabled/disabled, cost,
and target set SHALL continue to come only from the server.

#### Scenario: A talk button resolves to its typed command
- **WHEN** the player submits `explore.talk_scripted` with a keyword whose descriptor carries the NPC
  display name and the keyword label
- **THEN** the catalog returns `talk <NPC> <話題>` with the descriptor values filled in and the log
  shows one input line for it

#### Scenario: A navigation item emits nothing
- **WHEN** the player opens a submenu or presses a back row
- **THEN** the catalog returns `null` and no narrative line is appended

#### Scenario: An action without a typed command shows its label
- **WHEN** the player submits an action that has no canonical typed form (for example `combat.flee`)
- **THEN** the catalog returns a bounded display line derived from its server label, not a guessed
  command

#### Scenario: The catalog never guesses a name from an opaque id
- **WHEN** a display descriptor lacks a label the command line needs
- **THEN** the catalog returns `null` for that action rather than fabricating a name

### Requirement: Every deliberate mutation echo appears exactly once at dispatch

The browser SHALL append the resolved display line to the narrative exactly once per deliberate
mutation in the single submit path: the echo fires at the moment the `ui_action` request is dispatched
(a request id is returned), never on retry, resync, reconnect-replay, or a second client-local toggle,
and never when submission is blocked (offline, mutations locked, not initialized, or a duplicate/
in-flight request). A button click and the identical keyboard activation SHALL each echo exactly once.
A borrowed free-form dialogue SHALL be owned by the action path: the drawer's borrowed branch SHALL
not append its own line, so a single free-form send yields exactly one line (`talk <NPC> <speech>`),
and when submission is blocked the typed speech SHALL remain in the field and the drawer SHALL stay
open (the borrowed interaction is not complete and nothing is lost). The echo line SHALL be inserted
as literal text via the same narrative append path (scroll-keep + polite unread marker) used by server
output, SHALL NOT enter the markup pipeline, SHALL NOT be sent or reused as a submitted command, and
SHALL have no effect on the validated action payload (`U9` intact: dispatch stays allowlist + exact).
A later rejection of the action SHALL NOT remove the line, because the line records what the player
acted.

#### Scenario: A staged submit echoes at dispatch
- **WHEN** a player activates a button that dispatches a valid `combat.cast`
- **THEN** exactly one input line appears in the narrative at that moment, the `ui_action` envelope is
  byte-identical with and without the echo, and a rejected outcome leaves the line in place

#### Scenario: Locked state never echoes
- **WHEN** the browser is offline, awaiting its first snapshot, or another mutation is in flight
- **THEN** a menu activation does not dispatch, no input line appears, and a borrowed free-form send
  keeps its typed speech in the field with the drawer open

#### Scenario: Free-form dialogue echoes exactly one line
- **WHEN** a player sends free-form speech to a present NPC and the `explore.talk_freeform` request
  dispatches
- **THEN** exactly one `talk <NPC> <speech>` line is appended at dispatch, the drawer closes, and no
  second raw-text echo appears

#### Scenario: Reconnect replay does not double-echo
- **WHEN** a transport drops after a submit and reconnects
- **THEN** the store rebuilds panels, the uncertain-result notice shows, and no second echo is appended

### Requirement: Echoed command lines never affect state

The display command line SHALL be strictly input-side and presentation-only. It SHALL never be
evaluated, parsed, held for re-execution, or sent as a `text` message; it SHALL NOT write to
localStorage, session state, transport, epoch, or revision, and it SHALL degrade gracefully: an
unknown `actionId`, a missing payload, or a descriptor missing a required label SHALL produce `null`
(silent) rather than a guessed command, and an oversized or non-string server label SHALL be truncated
to a bounded length with literal-text rendering. The catalog module SHALL keep no stored state and be
safe to instantiate per page.

#### Scenario: Unknown action stays silent
- **WHEN** the catalog is asked for an unregistered `actionId`
- **THEN** it returns `null` and no narrative line is created

#### Scenario: Display text is never treated as markup
- **WHEN** a label-derived line contains characters that resemble markup
- **THEN** the narrative renders it as literal text with no element or script created

#### Scenario: Oversized labels degrade to bounded literal text
- **WHEN** a server label used by the catalog exceeds the bound
- **THEN** the emitted line is truncated to the bounded length and rendered as literal text