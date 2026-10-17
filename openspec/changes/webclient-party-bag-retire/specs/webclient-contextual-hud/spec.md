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
