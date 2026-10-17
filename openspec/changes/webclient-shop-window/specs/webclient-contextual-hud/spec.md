# Spec Delta

## MODIFIED Requirements

### Requirement: The party purse renders exactly once per window
The party purse (the commander's wallet) SHALL be rendered exactly once per window: in the party window's `WindowFrame` header extras (read from `party_inventory`) and in the shop window's header (read from `services.player.wallet`). The shop action bar MAY show the after-trade remainder, labelled as the remaining purse, and nothing else in the drawer layer SHALL render a balance.

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

#### Scenario: The shop shows the purse once and a labelled remainder
- **WHEN** the shop window is open on 購買 with three potions at 40 copper selected and a purse of 1,240
- **THEN** the header shows 1,240 once and the action bar shows the remaining purse 1,120 labelled as remaining
