## ADDED Requirements

### Requirement: Reference drawers present no router frame and never host a dock row region
No reference drawer SHALL present a keyboard router frame. Opening any reference drawer — including the 背包 · 裝備 drawer from the top navigation's 背包 entry, the 商店 drawer from a merchant's `navigate` affordance row, and the 任務 drawer from the top navigation's 任務 entry or from a guild clerk's `navigate` affordance row — SHALL push no frame, switch no sub-dock, and record no drawer-hosted service surface; an opener that is itself a top-navigation entry MAY first return the dock to its root frame exactly as every top-navigation entry does, and the drawer open SHALL add nothing to the stack after that. The client SHALL NOT maintain a second frame stack, a second focus model, or a second set of menu keys for a drawer. No reference drawer body SHALL render the dock's shared row renderer: no `dock-menu` row region and no `dock-detail` pane SHALL exist inside any drawer in any state, and each drawer's own surface SHALL be its only presentation of the committed rows it shows. Every committed row a drawer shows SHALL be reachable by keyboard through that surface's own focusable controls: the bag's item tiles with their shared inspector, the shop's per-row bounded quantity entries with their buy and sell controls, and the quest drawer's guild-counter and quest-book controls. Closing any reference drawer — by Escape, its close control, or the scrim — SHALL pop no menu level, SHALL dispatch nothing, and SHALL restore focus to the control that opened it.

A drawer SHALL be openable only while its backing payload is present. When the committed mode changes so that a drawer's payload is no longer available, when the presentation epoch resets, or when the transport is lost, every open drawer SHALL close and every local selection, quantity and confirmation state inside it SHALL be discarded.

#### Scenario: Opening the quest drawer from the guild clerk pushes no frame
- **WHEN** the player activates the guild clerk's `navigate` affordance row inside an open target frame
- **THEN** the 任務 drawer opens with the quest book and the guild counter, the router's current frame is still that target frame, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: Opening the bag or the shop pushes no frame
- **WHEN** the player activates the top navigation's 背包 entry at the exploration root, or a merchant's shop `navigate` affordance row inside an open target frame
- **THEN** the matching drawer opens, the router's current frame is the frame that was current before the open, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: Keyboard reachability does not depend on a hosted list
- **WHEN** a keyboard-only player moves through the open bag drawer, or moves into a shop stock row, types a quantity within its advertised bounds, and activates its buy control
- **THEN** every committed inventory row is reachable through the focusable item tiles with the shared inspector, the shop row becomes the selected row carrying the quantity hooks and exactly one `shop.buy` is emitted with that row's `item_key` and quantity, and no parallel navigation list of those rows exists to traverse

#### Scenario: Opening the quest drawer from the top navigation pushes no frame
- **WHEN** the player activates the top navigation's 任務 entry at any dock depth
- **THEN** the dock returns to its root frame as for every top-navigation entry, the 任務 drawer opens, and the router's depth is 1 with no frame pushed by the open

#### Scenario: No drawer renders the dock's row renderer
- **WHEN** any reference drawer is open, including the quest drawer while a guild counter control or a quest-book row holds focus
- **THEN** no `dock-menu` row region and no `dock-detail` pane exists inside the drawer, and the dock itself renders exactly the router's current frame

#### Scenario: Closing a drawer pops nothing and returns focus
- **WHEN** the open 任務 drawer closes by Escape, by its close control, or by the scrim
- **THEN** the router's frame stack is exactly what it was right after the open, no action is dispatched, and focus returns to the control that opened the drawer

#### Scenario: A mode change closes the drawers it invalidates
- **WHEN** the committed mode changes from exploration to combat while a services-backed drawer is open
- **THEN** that drawer closes, its local selection, quantity and confirmation state is discarded, and no stale service surface remains reachable

## REMOVED Requirements

### Requirement: A drawer hosting a dock frame renders that frame rather than a second navigation model
**Reason**: No reference drawer hosts a router frame any more: the bag, shop, and quest drawers are all frameless client-local opens, and each drawer's own surface already presents every committed row the hosted frame listed. The hosted row region was a duplicate navigation model over the same data.
**Migration**: The payload-gated open, the teardown-close rules, and the "no second frame stack / focus model / menu keys" clause move into "Reference drawers present no router frame and never host a dock row region". Guild and quest actions are taken through the quest drawer's own `GuildCounter` / `QuestLog` controls; shop trades through `ShopPanel`.

### Requirement: The bag drawer opens without a router frame and hosts no row region
**Reason**: Folded into the generic "Reference drawers present no router frame and never host a dock row region" requirement, which now covers every drawer, so the bag-specific copy would duplicate it.
**Migration**: The bag's opener, body, close, and keyboard-reachability rules are stated in the generic requirement and its "Opening the bag or the shop pushes no frame", "No drawer renders the dock's row renderer", "Closing a drawer pops nothing and returns focus", and "Keyboard reachability does not depend on a hosted list" scenarios. Tests annotated with the bag ID re-anchor to the generic ID.

### Requirement: The shop drawer opens without a router frame and hosts no row region
**Reason**: Folded into the generic "Reference drawers present no router frame and never host a dock row region" requirement, which now covers every drawer, so the shop-specific copy (added by `make-shop-drawer-frameless`) would duplicate it.
**Migration**: The shop's opener, body, close, and keyboard-trade rules are stated in the generic requirement and its scenarios. Tests annotated with the shop ID re-anchor to the generic ID.
