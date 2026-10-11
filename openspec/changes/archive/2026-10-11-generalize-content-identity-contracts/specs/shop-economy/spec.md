# Spec Delta

## MODIFIED Requirements

### Requirement: Item and shop identities are immutable while numeric trade rules are YAML and lore-constrained
`ITEM_REGISTRY` SHALL contain frozen item definitions with stable identity and complete immutable
item presentation metadata. `SHOP_REGISTRY` SHALL contain frozen definitions with stable identity
and the immutable assortment keys the shop references. Exact integer buy/sell copper, max/initial
stock, restock quantity, and opening/restock hours SHALL come from the
`world/rules/rulebook/commerce/` slices (one file per settlement plus `scales.yaml`).

#### Scenario: Initial ordinary goods validate
- **WHEN** every currently offered item is loaded
- **THEN** each exact price lies in its existing lore range, money is integer and offered presentation metadata is valid

#### Scenario: Floating price is rejected
- **WHEN** an offer declares `buy_copper=50.0`
- **THEN** catalog validation raises before registry or merchant state changes

#### Scenario: A shop's offered keys follow its assortments
- **WHEN** a shop references two assortments and declares existing place-level additions/removals
- **THEN** resolved keys equal the union plus additions minus removals; data membership edits need no shop-specific approval table

#### Scenario: Item definitions carry the stable identity fields
- **WHEN** an `ITEM_REGISTRY` definition is inspected
- **THEN** it carries a stable key, Traditional Chinese display name, price-table key, sellability,
  and complete immutable item presentation metadata

#### Scenario: Presentation metadata stays within the closed field set
- **WHEN** item presentation metadata is validated
- **THEN** it contains only the closed kind, local-SVG icon key, rarity, and bounded Traditional
  Chinese summary defined by `item-presentation-metadata`, and it SHALL NOT carry numeric trade or
  gameplay rules

#### Scenario: Offered keys are derived, not listed on the shop
- **WHEN** a shop definition is inspected
- **THEN** its keys derive from referenced assortments and existing place adjustments, never a duplicate hand-authored shop item list

#### Scenario: Shops carry no component-type field
- **WHEN** any shop definition is inspected
- **THEN** it has no component-type field — every shop host bears the same component type, so such
  a field is constant across the registry and cannot identify a row

#### Scenario: Loading joins both sources and rejects malformed references
- **WHEN** loading joins the registries with the commerce rulebook slices
- **THEN** it rejects unknown, missing, or extra references, floats, negative prices, sell above
  buy, buy outside the referenced `PRICE_TABLE` range, and stock outside
  `0 <= initial <= max` with positive restock quantity

#### Scenario: Per-shop accounting keys on shop identity
- **WHEN** the accounting that every shop has numeric rules is maintained
- **THEN** it is keyed on shop identity
