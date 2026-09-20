## MODIFIED Requirements

### Requirement: Item and shop identities are immutable while numeric trade rules are YAML and lore-constrained
`ITEM_REGISTRY` SHALL contain frozen item definitions with stable key, Traditional Chinese display name,
price-table key, sellability, and complete immutable item presentation metadata. Presentation metadata
SHALL contain only the closed kind, local-SVG icon key, rarity, and bounded Traditional Chinese summary
defined by `item-presentation-metadata`; it SHALL NOT carry numeric trade or gameplay rules.
`SHOP_REGISTRY` SHALL contain frozen definitions with stable identity and the immutable assortment keys
the shop references; its offered item keys SHALL be derived from those assortments rather than listed on
the shop. A shop SHALL NOT carry a component-type field: every shop host bears the same component type,
so such a field is constant across the registry and cannot identify a row.
Exact integer buy/sell copper, max/initial stock, restock quantity, and opening/restock hours SHALL come
from `commerce.yaml`. Loading SHALL join both sources and reject
unknown, missing, or extra references, floats, negative prices, sell above buy, buy outside the referenced
`PRICE_TABLE` range, and stock outside `0 <= initial <= max` with positive restock quantity. The
per-shop accounting that every shop has numeric rules SHALL be keyed on shop identity.

#### Scenario: Initial ordinary goods validate
- **WHEN** the meal, potion, and plain-sword offers are loaded
- **THEN** every exact buy price lies within its existing lore price range, every money value is int,
  and every offered item has complete valid presentation metadata

#### Scenario: Floating price is rejected
- **WHEN** an offer declares `buy_copper=50.0`
- **THEN** catalog validation raises before registry or merchant state changes

#### Scenario: A shop's offered keys follow its assortments
- **WHEN** a shop references two assortments
- **THEN** its offered item keys are exactly the union of those assortments' item keys, and adding an
  item to one assortment adds it to that shop without editing the shop
