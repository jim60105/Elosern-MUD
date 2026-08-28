## Purpose

Allowlisted UI actions, adapters, client confirmation and toggle behavior, text commands, and canonical presentation for inventory item use and equipment toggling.

## Requirements

### Requirement: Inventory mutations use exact allowlisted UI actions
The production UI action registry SHALL register `inventory.use` and `inventory.toggle_equip`. Each action SHALL accept exactly `{item_key}` where `item_key` is a bounded non-empty string. The authenticated session SHALL be the only actor source. Neither payload SHALL accept actor, target, quantity, effect, consumable, slot, HP, combat, or presentation fields. The adapters SHALL re-resolve current canonical state and call only the public deterministic item-use, combat-session, or equipment-toggle APIs; they SHALL NOT assign persistent state directly or route through the text parser.

#### Scenario: Item use delegates once
- **WHEN** an authenticated actor submits `inventory.use` with one held usable item key
- **THEN** the adapter revalidates current state and invokes the correct exploration or active-combat deterministic facade exactly once

#### Scenario: Client cannot choose an effect or slot
- **WHEN** an inventory payload includes an `effect`, `slot`, or other extra field
- **THEN** exact payload validation rejects it before adapter invocation and state remains unchanged

#### Scenario: Unknown action cannot reach item rules
- **WHEN** a client submits an unregistered inventory action ID
- **THEN** the dispatcher rejects it without invoking an item, equipment, or text-command path

### Requirement: Inventory tiles confirm use and directly toggle equipment
The combat dock root SHALL add one client-local `背包` row that opens the frameless inventory drawer without dispatching, inventing a gameplay action, pushing a router frame, or changing server-authored combat actions. Deliberate activation of an inventory tile SHALL follow its committed action descriptor while pointer hover and keyboard focus continue to expose the shared inspector. An inspect-only tile SHALL dispatch nothing. A disabled action SHALL show its committed bounded reason and dispatch nothing. An enabled `inventory.use` SHALL open a labelled modal confirmation naming the item; confirm SHALL dispatch exactly once, while cancel, close, or Escape SHALL dispatch nothing and restore focus to the originating tile. An enabled `inventory.toggle_equip` SHALL dispatch exactly once immediately without confirmation. Pointer and keyboard activation SHALL be equivalent.

#### Scenario: Combat root opens the frameless bag locally
- **WHEN** the player activates `背包` from the combat dock root
- **THEN** the inventory drawer opens with no `ui_action`, no router frame push, and no change to the committed combat action list

#### Scenario: Healing potion asks before use
- **WHEN** an eligible healing-potion tile is activated
- **THEN** a confirmation dialog names the healing potion and no request is sent until the player confirms

#### Scenario: Cancel preserves the item
- **WHEN** the player cancels or presses Escape in the use confirmation
- **THEN** no action is dispatched, focus returns to the potion tile, and committed inventory remains unchanged

#### Scenario: Equipment toggles without confirmation
- **WHEN** an enabled equipment tile is activated by pointer or keyboard
- **THEN** one `inventory.toggle_equip` request carrying only its item key is dispatched immediately and no confirmation dialog opens

#### Scenario: Full accessory set warns without dispatch
- **WHEN** five accessories are equipped and the player activates a disabled unequipped accessory tile
- **THEN** the UI presents the server-authored accessory-cap warning, sends no request, and does not choose an accessory to remove

### Requirement: Item dialogs and dispatch state fail closed across replacement and transport changes
The confirmation dialog and tile-local action state SHALL be client-local and SHALL never mutate committed panel data. A services-panel replacement, drawer close, mode change, epoch change, or transport reset SHALL close the dialog and discard its pending local intent. While any mutation is in flight, repeated tile activation SHALL emit no second request. A server rejection caused by state changing after confirmation opened SHALL use the existing action-result alert and the next canonical publication SHALL remain authoritative.

#### Scenario: Replaced inventory retires an open confirmation
- **WHEN** an item-use confirmation is open and a new services panel commits
- **THEN** the dialog closes, its old item key cannot be confirmed, and only the new committed rows are actionable

#### Scenario: Rapid activation emits one request
- **WHEN** the player confirms use and immediately activates the tile again while the action client is locked
- **THEN** exactly one request is emitted until the resulting canonical revision is accepted

#### Scenario: Retired revision wins before domain revalidation
- **WHEN** HP changes under a newer committed presentation revision before the old dialog is confirmed
- **THEN** the dispatcher returns `stale`, invokes no item adapter, refreshes canonical presentation, and consumes no potion

#### Scenario: Live revision domain change uses the named reason
- **WHEN** the request passes current epoch/revision checks but HP becomes full before deterministic settlement
- **THEN** item preflight rejects with `hp_full`, no potion is consumed, and the UI displays the current-state rejection without optimistic mutation

### Requirement: Inventory actions publish all affected canonical panels
A completed inventory action SHALL publish one canonical presentation commit covering every surface its settlement may change. Item use SHALL refresh inventory, status, combat/context state, clock-derived state, and terminal mode when applicable. Equipment toggle SHALL refresh inventory equipped flags, status, combat previews, and character equipment rows whenever the character panel is available; in combat, where the character panel retains its registered unavailable form, canonical inventory equipped flags SHALL remain the visible equipment truth. The client SHALL derive quantity and equipped indicators only from that accepted commit and SHALL NOT optimistically decrement or toggle them.

#### Scenario: Successful potion use refreshes quantity and HP together
- **WHEN** a consumable healing potion action succeeds
- **THEN** the accepted publication shows increased canonical HP and a quantity reduced by one in the same committed view update

#### Scenario: Equipment replacement refreshes both rows
- **WHEN** a new main-hand item replaces the equipped main-hand item during exploration
- **THEN** the accepted publication marks only the new item equipped and reports the new character equipment row without an intermediate mixed state

#### Scenario: Combat equipment refresh uses available truth
- **WHEN** equipment is toggled during combat while the character panel is unavailable
- **THEN** the accepted publication updates canonical inventory equipped flags and combat-derived panels without fabricating character equipment rows

### Requirement: Text clients expose the same deterministic item operations
The player command surface SHALL provide `使用 <item_key>` with alias `use` and `裝備 <item_key>` with alias `equip`. These commands SHALL pass only the parsed item key into the same deterministic APIs used by UI adapters. Both commands SHALL be available in exploration and active combat. Combat use SHALL enter the same combat-session facade and consume one round on success; equipment toggle SHALL consume no round. Stable rejections SHALL render the same Traditional Chinese reason semantics as UI actions. Command additions and syntax SHALL update both `docs/game/commands.md` and `docs/game/command-reference.md` in the same change.

#### Scenario: Telnet healing matches WebClient healing
- **WHEN** equivalent injured actors use the same potion through the text command and `inventory.use`
- **THEN** both paths produce the same eligibility, HP, consumption, time, and combat-round outcomes

#### Scenario: Text equipment toggle uses exact item semantics
- **WHEN** a text client toggles a held accessory by item key
- **THEN** the same named accessory is equipped or unequipped under the five-slot rule without duplicating mutation logic
