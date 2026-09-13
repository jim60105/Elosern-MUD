## MODIFIED Requirements

### Requirement: Inventory mutations use exact allowlisted UI actions
The production UI action registry SHALL register `inventory.use` and `inventory.toggle_equip`. `inventory.toggle_equip` SHALL accept exactly `{item_key}`. `inventory.use` SHALL accept exactly `{item_key}` or `{item_key, target_key}`, where each key is a bounded non-empty string containing no whitespace (the typed `use`/`equip` commands parse their arguments as whitespace-delimited tokens and the browser input echo prints the line verbatim, so an echoed line must stay byte-replayable). `target_key` SHALL name **whom** an effect reaches and SHALL NOT influence **what** the item does: the item's effects and their scopes are fixed by the item-effect rulebook, and a supplied target is consumed only by an effect the rulebook already scoped to a single entity. The authenticated session SHALL be the only actor source. Neither payload SHALL accept actor, quantity, effect, consumable, slot, HP, combat, or presentation fields. The adapters SHALL re-resolve current canonical state and call only the public deterministic item-use, combat-session, or equipment-toggle APIs; they SHALL NOT assign persistent state directly or route through the text parser.

#### Scenario: Item use delegates once
- **WHEN** an authenticated actor submits `inventory.use` with one held usable item key
- **THEN** the adapter revalidates current state and invokes the correct exploration or active-combat deterministic facade exactly once

#### Scenario: Client cannot choose an effect or slot
- **WHEN** an inventory payload includes an `effect`, `slot`, or other extra field
- **THEN** exact payload validation rejects it before adapter invocation and state remains unchanged

#### Scenario: Whitespace-bearing item keys are rejected
- **WHEN** an inventory payload carries an `item_key` containing a space, tab, or line break
- **THEN** exact payload validation rejects it before adapter invocation and state remains unchanged

#### Scenario: Unknown action cannot reach item rules
- **WHEN** a client submits an unregistered inventory action ID
- **THEN** the dispatcher rejects it without invoking an item, equipment, or text-command path

#### Scenario: A supplied target cannot widen an item's reach
- **WHEN** an `inventory.use` payload supplies a `target_key` for an item whose every effect is scoped
  to the acting entity
- **THEN** the target is ignored by scope resolution and the item affects only the actor, exactly as it
  would with no target supplied

#### Scenario: A target key naming a group shorthand is rejected
- **WHEN** an `inventory.use` payload supplies a `target_key` equal to a group shorthand token
- **THEN** the deterministic preflight rejects it, because group reach is fixed by the rulebook and is
  never selectable by the client

### Requirement: Text clients expose the same deterministic item operations
The player command surface SHALL provide `使用 <item_key> [target]` with alias `use` and
`裝備 <item_key>` with alias `equip`. These commands SHALL pass only the parsed item key, and for
`使用` the optional parsed target token, into the same deterministic APIs used by UI adapters. Both
commands SHALL be available in exploration and active combat. Combat use SHALL enter the same
combat-session facade and consume one round on success; equipment toggle SHALL consume no round.
Stable rejections SHALL render the same Traditional Chinese reason semantics as UI actions, including
the no-target and invalid-target reasons. Command additions and syntax SHALL update both
`docs/game/commands.md` and `docs/game/command-reference.md` in the same change.

#### Scenario: Telnet healing matches WebClient healing
- **WHEN** equivalent injured actors use the same potion through the text command and `inventory.use`
- **THEN** both paths produce the same eligibility, HP, consumption, time, and combat-round outcomes

#### Scenario: Text equipment toggle uses exact item semantics
- **WHEN** a text client toggles a held accessory by item key
- **THEN** the same named accessory is equipped or unequipped under the five-slot rule without duplicating mutation logic

#### Scenario: Telnet targeting matches WebClient targeting
- **WHEN** equivalent actors use the same single-scope item on the same target, once through
  `使用 <item_key> <target>` and once through `inventory.use` with a `target_key`
- **THEN** both paths resolve the same target, apply the same effects, and consume the same resources

#### Scenario: A missing target renders the stable reason
- **WHEN** a text client runs `使用` on a single-scope item with no target argument
- **THEN** the no-target rejection renders in Traditional Chinese through the shared reason surface and
  nothing is consumed
