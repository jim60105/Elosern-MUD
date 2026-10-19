# Spec Delta

## REMOVED Requirements

### Requirement: The bag renders the bounded inventory rows without inventing a total or a rarity
**Reason**: The frameless inventory drawer (`InventoryPanel`) is deleted; the party window's 背包 tab renders the viewed member's `party_inventory` rows instead.
**Migration**: See `webclient-party-window` requirement "The bag tab presents the viewed member's doll, bag and holdings".

### Requirement: The equipment doll renders only server-authored slots and drops nothing
**Reason**: `EquipmentDoll` is deleted; the bag tab's doll renders the `party_inventory` equipment section of the viewed member.
**Migration**: See `webclient-party-window` requirement "The bag tab presents the viewed member's doll, bag and holdings".

## RENAMED Requirements

- FROM: `### Requirement: The drawer layer renders the wallet exactly once`
- TO: `### Requirement: The party purse renders exactly once per window`

## MODIFIED Requirements

### Requirement: The party purse renders exactly once per window
The party purse (the commander's wallet, read from the committed `party_inventory` panel) SHALL be rendered exactly once in the party window, in its `WindowFrame` header extras, and nowhere else in the drawer layer apart from the shop window's own header.

#### Scenario: No other drawer or body element carries a balance
- **WHEN** the lore reference, the character-status drawer, or any tab body of the party window renders
- **THEN** none of them renders a balance of its own

#### Scenario: An unreadable wallet renders nothing rather than zero
- **WHEN** the `party_inventory` panel is unavailable or carries no committed non-negative integer purse
- **THEN** the party window renders no balance at all rather than a zero

#### Scenario: The body row is gated with the inventory section
- **WHEN** the bag tab is open with an available `party_inventory` panel
- **THEN** the bag tab body renders no 金錢 row; the header purse is the only balance

#### Scenario: One wallet per drawer-layer opening
- **WHEN** every drawer and the party window are opened in turn with their panels available
- **THEN** the only balance in the party window is its header purse, carrying the commander's integer copper, and no other drawer body renders a balance

#### Scenario: An unavailable panel renders no balance
- **WHEN** the panel that carries the purse is unavailable
- **THEN** no balance and no zero is rendered in its place

#### Scenario: A missing wallet field renders no body row
- **WHEN** the purse field is not a committed non-negative integer
- **THEN** neither the header nor any body renders a balance or a zero

#### Scenario: Possession shows the same purse
- **WHEN** the player possesses a companion
- **THEN** the header purse still shows the commander's wallet

### Requirement: Empty drawer guidance preserves unavailable reasons
An available but empty list — the quest book with no rows, the world codex with nothing discovered, the party window bag tab with no rows, and the party window member rail with no companions — SHALL render the shared empty guidance: a decorative registry glyph, a short headline, and one line of guidance in a solid ink frame, adding no control of its own.

#### Scenario: The party keeps its invite row
- **WHEN** the party has no companions
- **THEN** the member tab shows the empty guidance and the rail keeps the commander entry and the 空位 entry, which keeps the only invite descriptor

#### Scenario: Unavailable is never merely empty
- **WHEN** a panel is unavailable, or a section is absent
- **THEN** an unavailable panel retains its authoritative registry reason and is not presented as merely empty, and an absent section keeps its own absence line

#### Scenario: Empty becomes unavailable
- **WHEN** an empty quest panel is replaced by an unavailable panel
- **THEN** empty guidance is replaced by the registered reason with no invented quest/action

#### Scenario: Every empty list shares one guidance form
- **WHEN** the quest book, the codex, the bag tab, or the party is available and empty
- **THEN** each renders the shared glyph, headline, and guidance card, and the empty party additionally keeps its 空位 entry

### Requirement: Reference drawers present no router frame and never host a dock row region
No reference drawer SHALL present a keyboard router frame. Opening any reference drawer SHALL push no frame, switch no sub-dock, and record no drawer-hosted service surface; an opener that is itself a top-navigation entry MAY first return the dock to its root frame exactly as every top-navigation entry does, and the drawer open SHALL add nothing to the stack after that. The client SHALL NOT maintain a second frame stack, a second focus model, or a second set of menu keys for a drawer.

#### Scenario: Every drawer opener pushes nothing
- **WHEN** the party window opens on its 背包 tab from the top navigation's 背包 entry, the 商店 drawer from a merchant's `navigate` affordance row, or the 任務 drawer from the top navigation's 任務 entry or from a guild clerk's `navigate` affordance row
- **THEN** the opening pushes no frame, switches no sub-dock, and records no drawer-hosted service surface

#### Scenario: No drawer body hosts dock chrome
- **WHEN** any reference drawer body renders in any state
- **THEN** it renders neither the dock's row renderer (`dock-menu`) nor its detail pane (`dock-detail`)

#### Scenario: Closing leaves the router alone and returns focus
- **WHEN** a reference drawer closes — by Escape, its close control, or the scrim
- **THEN** the router is left alone, no menu level is popped, and focus is restored to the control that opened it

#### Scenario: Drawer rows stay keyboard reachable
- **WHEN** a committed row inside a reference drawer takes the keyboard
- **THEN** it remains reachable without a hosted router frame

#### Scenario: Lost payloads close their drawers
- **WHEN** a drawer's backing payload is absent, the committed mode changes so it is no longer available, the presentation epoch resets, or the transport is lost
- **THEN** the drawer is openable only while its backing payload is present, every open drawer closes, and every local selection, quantity and confirmation state inside it is discarded

#### Scenario: Opening the quest drawer from the guild clerk pushes no frame
- **WHEN** the player activates the guild clerk's `navigate` affordance row inside an open target frame
- **THEN** the 任務 drawer opens with the quest book and the guild counter, the router's current frame is still that target frame, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: Opening the bag or the shop pushes no frame
- **WHEN** the player activates the top navigation's 背包 entry at the exploration root, or a merchant's shop `navigate` affordance row inside an open target frame
- **THEN** the party window (on its 背包 tab) or the shop drawer opens, the router's current frame is the frame that was current before the open, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: Keyboard reachability does not depend on a hosted list
- **WHEN** a keyboard-only player moves through the party window's open 背包 tab, or moves into a shop stock row, types a quantity within its advertised bounds, and activates its buy control
- **THEN** every committed `party_inventory` row is reachable through the bag tab's single-tab-stop listbox, whose selected row drives the detail column, the shop row becomes the selected row carrying the quantity hooks and exactly one `shop.buy` is emitted with that row's `item_key` and quantity, and no parallel navigation list of those rows exists to traverse

#### Scenario: Opening the quest drawer from the top navigation pushes no frame
- **WHEN** the player activates the top navigation's 任務 entry at any dock depth
- **THEN** the dock returns to its root frame as for every top-navigation entry, the 任務 drawer opens, and the router's depth is 1 with no frame pushed by the open

#### Scenario: No drawer renders the dock's row renderer
- **WHEN** any reference drawer is open, including the quest drawer while a guild counter control or a quest-book row holds focus
- **THEN** no `dock-menu` row region and no `dock-detail` pane exists inside the drawer, and the dock itself renders exactly the router's current frame

#### Scenario: Closing a drawer pops nothing and returns focus
- **WHEN** the open 任務 drawer closes by Escape, by its close control, or by the scrim
- **THEN** the router's frame stack is exactly what it was right after the open, no action is dispatched, and focus returns to the control that opened it

#### Scenario: A mode change closes the drawers it invalidates
- **WHEN** the committed mode changes from exploration to combat while a services-backed drawer is open
- **THEN** that drawer closes, its local selection, quantity and confirmation state is discarded, and no stale service surface remains reachable
