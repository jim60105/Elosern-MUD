# Spec Delta

## MODIFIED Requirements

### Requirement: Inventory mutations use exact allowlisted UI actions
The production UI action registry SHALL register `inventory.use` and `inventory.toggle_equip`.
`inventory.toggle_equip` SHALL accept exactly `{item_key}`. `inventory.use` SHALL accept exactly
`{item_key}` or `{item_key, target_key}`, where each key is a bounded non-empty string containing
no whitespace. A supplied `target_key` SHALL name **whom** an effect reaches and SHALL NOT
influence **what** the item does. The authenticated session SHALL be the only exploration actor source. During active combat, inventory.use SHALL reject; actor-scoped item commands SHALL use the guarded party command path instead. Existing free inventory.toggle_equip remains authenticated-commander scoped.

#### Scenario: Item use delegates once
- **WHEN** an authenticated actor in exploration submits `inventory.use` with one held usable item key
- **THEN** the adapter revalidates current state and invokes the exploration deterministic facade exactly once

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

#### Scenario: Item keys stay byte-replayable in echoed input
- **WHEN** the whitespace ban on item and target keys is examined
- **THEN** it holds because the typed `use`/`equip` commands parse their arguments as
  whitespace-delimited tokens and the browser input echo prints the line verbatim, so an echoed
  line must stay byte-replayable

#### Scenario: Effects and scopes come from the item-effect rulebook
- **WHEN** an `inventory.use` settlement determines what an item does
- **THEN** the item's effects and their scopes are fixed by the item-effect rulebook, and a
  supplied target is consumed only by an effect the rulebook already scoped to a single entity

#### Scenario: Payloads reject non-key fields
- **WHEN** an `inventory.use` or `inventory.toggle_equip` payload carries actor, quantity, effect,
  consumable, slot, HP, combat, or presentation fields
- **THEN** exact payload validation rejects it before adapter invocation

#### Scenario: Adapters use only public deterministic APIs
- **WHEN** an inventory adapter handles a validated payload
- **THEN** it re-resolves current canonical state and calls only the public deterministic
  item-use, combat-session, or equipment-toggle APIs, and it never assigns persistent state
  directly or routes through the text parser

#### Scenario: Active combat cannot use actorless inventory adapter
- **WHEN** inventory.use is submitted during a party combat session
- **THEN** it rejects without mutation; only guarded combat.command may save an actor item selection


