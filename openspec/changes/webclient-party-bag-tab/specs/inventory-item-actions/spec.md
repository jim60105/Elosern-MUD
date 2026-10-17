# Spec Delta

## MODIFIED Requirements

### Requirement: Inventory tiles confirm use and directly toggle equipment
The combat dock root SHALL add one client-local `背包` row that opens the party window on its 背包 tab
without dispatching, inventing a gameplay action, pushing a router frame, or changing
server-authored combat actions. In exploration an enabled `inventory.use` SHALL open a labelled modal
confirmation naming the item; confirm SHALL dispatch exactly once, while cancel, close, or
Escape SHALL dispatch nothing and restore focus to the originating tile.

#### Scenario: Combat root opens the frameless bag locally
- **WHEN** the player activates `背包` from the combat dock root
- **THEN** the party window opens on 背包 with no `ui_action` other than the read-only viewed-member selection, no router frame push, and no change to the committed combat action list

#### Scenario: Healing potion asks before use
- **WHEN** an eligible healing-potion tile is activated in exploration
- **THEN** a confirmation dialog names the healing potion and no request is sent until the player confirms

#### Scenario: Cancel preserves the item
- **WHEN** the player cancels or presses Escape in the use confirmation
- **THEN** no action is dispatched, focus returns to the potion tile, and committed inventory remains unchanged

#### Scenario: Equipment toggles without confirmation
- **WHEN** an enabled equipment tile is activated by pointer or keyboard
- **THEN** one `inventory.toggle_equip` request carrying the viewed member's `actor_id` and the item key is dispatched immediately and no confirmation dialog opens

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
- **WHEN** a usable item is chosen through the in-combat bag tab as 設為 X 本回合的行動…
- **THEN** it uses the viewed member's canonical combat choices and the same target/review/combat.command flow, never `inventory.use`; inspection and every member's equipment toggles remain free, and transfer controls are absent

### Requirement: Item dialogs and dispatch state fail closed across replacement and transport changes
The confirmation dialog and tile-local action state SHALL be client-local and SHALL never mutate
committed panel data. A `party_inventory` replacement, viewed-member change, window close, mode change, epoch change, or
transport reset SHALL close the dialog and discard its pending local intent. While any mutation
is in flight, repeated tile activation SHALL emit no second request.

#### Scenario: Replaced inventory retires an open confirmation
- **WHEN** an item-use confirmation is open and a new `party_inventory` panel commits
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

#### Scenario: A post-confirmation rejection uses the existing alert
- **WHEN** the server rejects a confirmed action because state changed after the confirmation
  opened
- **THEN** the rejection uses the existing action-result alert and the next canonical publication
  remains authoritative
