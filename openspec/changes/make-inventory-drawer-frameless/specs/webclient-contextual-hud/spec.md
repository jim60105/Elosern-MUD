## ADDED Requirements

### Requirement: The bag drawer opens without a router frame and hosts no row region
The 背包 · 裝備 drawer SHALL present no router frame. Activating a 背包 entry — the exploration root's row or the services sub-dock's row — SHALL open the drawer as a client-local open: the router's frame stack, current frame, breadcrumb, and menu keys SHALL be unchanged by the open, no sub-dock switch SHALL occur, and no drawer-hosted service surface SHALL be recorded. The drawer's available body SHALL present only its own committed-panel stack, and no hosted row container, listbox, or detail pane SHALL render inside it in any state. Closing the bag drawer — by Escape, its close control, or the scrim — SHALL leave the router alone, popping no menu level, and SHALL restore focus to the 背包 entry that opened it. Committed inventory rows SHALL remain reachable by keyboard through the focusable item tiles and their shared inspector, and those tiles SHALL be the drawer's only row surface: the drawer SHALL NOT additionally render a navigation list of the same rows.

#### Scenario: Opening the bag leaves the router unchanged
- **WHEN** the player activates the 背包 entry from the exploration root or from the services sub-dock root
- **THEN** the 背包 · 裝備 drawer opens, the router's current frame remains the root that was current before the open, no frame was pushed, no sub-dock switch occurred, and the breadcrumb is unchanged

#### Scenario: The bag body carries no hosted row region
- **WHEN** the bag drawer is open with the committed services and character panels available
- **THEN** the drawer body contains the equipment, items, and money sections only, and no row listbox or detail pane renders inside it

#### Scenario: Closing the bag pops nothing and returns focus
- **WHEN** the open bag drawer closes by Escape, by its close control, or by the scrim
- **THEN** focus returns to the 背包 entry that opened it and the router's frame stack is exactly what it was before the open

#### Scenario: Keyboard reachability does not depend on the removed list
- **WHEN** a keyboard-only player moves through the open bag drawer
- **THEN** every committed inventory row is reachable through the focusable item tiles with the shared inspector, and no parallel navigation list of those rows exists to traverse
