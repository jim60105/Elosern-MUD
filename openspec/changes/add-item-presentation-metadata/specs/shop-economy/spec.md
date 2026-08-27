## MODIFIED Requirements

### Requirement: Item and shop identities are immutable while numeric trade rules are YAML and lore-constrained
`ITEM_REGISTRY` SHALL contain frozen item definitions with stable key, Traditional Chinese display name, price-table key, sellability, and complete immutable item presentation metadata. Presentation metadata SHALL contain only the closed kind, local-SVG icon key, rarity, and bounded Traditional Chinese summary defined by `item-presentation-metadata`; it SHALL NOT carry numeric trade or gameplay rules. `SHOP_REGISTRY` SHALL contain frozen definitions with stable identity, merchant component key, and immutable offered item keys. Exact integer buy/sell copper, max/initial stock, restock quantity, and opening/restock hours SHALL come from `guild_economy.yaml`. Loading SHALL join both sources and reject unknown, missing, or extra references, floats, negative prices, sell above buy, buy outside the referenced `PRICE_TABLE` range, and stock outside `0 <= initial <= max` with positive restock quantity.

#### Scenario: Initial ordinary goods validate
- **WHEN** the meal, potion, and plain-sword offers are loaded
- **THEN** every exact buy price lies within its existing lore price range, every money value is int, and every offered item has complete valid presentation metadata

#### Scenario: Floating price is rejected
- **WHEN** an offer declares `buy_copper=50.0`
- **THEN** catalog validation raises before registry or merchant state changes
