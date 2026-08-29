# Delta: inventory-item-actions

## MODIFIED Requirements

### Requirement: Inventory mutations use exact allowlisted UI actions
The production UI action registry SHALL register `inventory.use` and `inventory.toggle_equip`. Each action SHALL accept exactly `{item_key}` where `item_key` is a bounded non-empty string containing no whitespace (the typed `use`/`equip` commands parse the key as their first whitespace-delimited token and the browser input echo prints the line verbatim, so an echoed line must stay byte-replayable). The authenticated session SHALL be the only actor source. Neither payload SHALL accept actor, target, quantity, effect, consumable, slot, HP, combat, or presentation fields. The adapters SHALL re-resolve current canonical state and call only the public deterministic item-use, combat-session, or equipment-toggle APIs; they SHALL NOT assign persistent state directly or route through the text parser.

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
