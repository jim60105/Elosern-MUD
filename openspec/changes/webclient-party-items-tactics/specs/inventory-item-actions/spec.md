# Spec Delta

## MODIFIED Requirements

### Requirement: Inventory tiles confirm use and directly toggle equipment
The combat dock root SHALL add one client-local `背包` row that opens the frameless inventory
drawer without dispatching, inventing a gameplay action, pushing a router frame, or changing
server-authored combat actions. In exploration an enabled `inventory.use` SHALL open a labelled modal
confirmation naming the item; confirm SHALL dispatch exactly once, while cancel, close, or
Escape SHALL dispatch nothing and restore focus to the originating tile.

#### Scenario: Combat root opens the frameless bag locally
- **WHEN** the player activates `背包` from the combat dock root
- **THEN** the inventory drawer opens with no `ui_action`, no router frame push, and no change to the committed combat action list

#### Scenario: Exploration healing potion asks before use
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

#### Scenario: Tile activation follows the committed descriptor
- **WHEN** an inventory tile is deliberately activated
- **THEN** the activation follows its committed action descriptor, while pointer hover and
  keyboard focus continue to expose the shared inspector

#### Scenario: An inspect-only tile dispatches nothing
- **WHEN** a tile whose committed action descriptor is inspect-only is activated
- **THEN** the UI dispatches no action

#### Scenario: A disabled action shows its reason without dispatching
- **WHEN** a tile with a disabled action is activated
- **THEN** the UI shows the committed bounded reason and dispatches nothing

#### Scenario: Pointer and keyboard activation are equivalent
- **WHEN** an inventory tile is activated by pointer or by keyboard
- **THEN** both activation paths produce the same dispatch behavior

#### Scenario: Combat use belongs to the commanded member
- **WHEN** a usable item is chosen through the in-combat drawer
- **THEN** it uses that actor canonical choices and the same target/review/combat.command flow, never actorless inventory.use; inspection and commander equipment toggles remain free and no companion equipment-management surface is introduced


