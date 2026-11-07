## MODIFIED Requirements

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

- **WHEN** the catalog is asked for any declared silent presentation control (the account create/switch actions, the name roll, and the dialogue leave)
- **THEN** it returns `null` and no narrative line is appended, and the retired `options.dismiss` is not among them

#### Scenario: The silent control is a pure visibility control

- **WHEN** the declared silent presentation controls are examined
- **THEN** each is a control with no typed-command equivalent and no game action of its own, and no `options.*` action is declared or registered

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

### Requirement: Catalog coverage is pinned against the action registry

The test suites SHALL pin the command-line catalog's coverage of the action registry: the Node catalog suite SHALL enumerate every registered mutation action id and assert each one resolves to a non-empty bounded line from a pinned fixture, so a newly registered action cannot ship with a silent catalog gap.

#### Scenario: A new registered action without catalog coverage fails the gate

- **WHEN** an action id is registered in the production registry but is absent
  from both the catalog coverage fixtures and the silent presentation-control
  list
- **THEN** the Node coverage test or the registry equality test fails, naming
  the missing id

#### Scenario: Silent status is an explicit declaration

- **WHEN** the Node coverage test processes the retired `options.dismiss` id
- **THEN** it asserts the id is absent from both the production registry and the
  silent presentation-control list, and that every other registered mutation
  action resolves non-null unless it is one of the explicitly declared silent
  controls

#### Scenario: The registry mirrors the enumerated set

- **WHEN** the Python test runs against the production action registry
- **THEN** it asserts the registry's action ids equal the same enumerated set the Node catalog suite pins

#### Scenario: The pinned lists are deterministic literals

- **WHEN** either coverage pin executes
- **THEN** it reads deterministic literals only — no live services, and no parsing of the other language's source at runtime

#### Scenario: The pins complement the per-surface test table

- **WHEN** the dispatch requirement's per-surface behavioral test table is considered
- **THEN** these pins complement — and never replace — that table, where every dispatch surface (and every intentional silence) is a reviewed row and the set of action ids exercised by that table covers every registered mutation id
