## ADDED Requirements

### Requirement: The shop drawer opens without a router frame and hosts no row region
The 商店 drawer SHALL present no router frame. Activating the 商店 entry — the exploration target frame's shop `navigate` affordance row — SHALL open the drawer as a client-local open: the router's frame stack, current frame, breadcrumb, and menu keys SHALL be unchanged by the open, no sub-dock switch SHALL occur, and no drawer-hosted service surface SHALL be recorded. The drawer's body SHALL present only the shop surface rendered from the committed `services` panel, and no hosted row container, listbox, or detail pane SHALL render inside it in any state. Closing the shop drawer — by Escape, its close control, or the scrim — SHALL leave the router alone, popping no menu level, and SHALL restore focus to the 商店 entry that opened it. Every committed stock and sellable row SHALL remain reachable by keyboard through the shop surface's own focusable controls — each row's bounded quantity entry and its buy or sell control — and those controls SHALL be the drawer's only row surface: the drawer SHALL NOT additionally render a navigation list of the same rows.

#### Scenario: Opening the shop leaves the router unchanged
- **WHEN** the player activates the shop `navigate` affordance row inside an open merchant target frame
- **THEN** the 商店 drawer opens, the router's current frame remains the frame that was current before the open, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: The shop body carries no hosted row region
- **WHEN** the shop drawer is open with the committed services panel available, including while a stock or sellable row's controls hold focus
- **THEN** the drawer body contains the shop surface only, and no `dock-menu` row region and no `dock-detail` pane renders inside it

#### Scenario: Closing the shop pops nothing and returns focus
- **WHEN** the open shop drawer closes by Escape, by its close control, or by the scrim
- **THEN** focus returns to the 商店 entry that opened it, the router's frame stack is exactly what it was before the open, and no action is dispatched

#### Scenario: A keyboard-only trade needs no router row
- **WHEN** a keyboard-only player moves into a stock row of the open shop drawer, types a quantity within the row's advertised bounds into that row's quantity entry, and activates its buy control
- **THEN** the row becomes the selected row carrying the quantity hooks, and exactly one `shop.buy` action is emitted with that row's `item_key` and the typed quantity through the client's single dispatch entry
