# Spec Delta

## MODIFIED Requirements

### Requirement: An assortment may not contain a keepsake-band item
Catalog loading SHALL reject a keepsake-band item in any resolved merchant offer, including assortment membership, place additions and overrides, regardless of price. Validation SHALL name the shop or assortment and item before registry or merchant state changes. Keepsakes SHALL remain grantable, holdable and inspectable; price-band eligibility SHALL NOT override non-sellability.

#### Scenario: A keepsake in an assortment fails load
- **WHEN** an assortment names an item whose band is the keepsake band, at
  any price including exactly the band floor
- **THEN** catalog validation raises naming the assortment and the item,
  before any registry or merchant state changes

#### Scenario: A keepsake stays holdable
- **WHEN** a keepsake-band item is granted through authored content
- **THEN** it remains holdable and inspectable but no listing route can authorize merchant trade


### Requirement: A shop's offered goods are derived from the assortments it references
A shop SHALL derive offered goods from its referenced assortment union plus existing authored place-level additions minus removals, with existing price scaling/overrides. Duplicate membership within one shop SHALL fail without implicit precedence; different shops MAY share an item. Item and shelf membership SHALL remain data and follow declared shop-purpose eligibility. All existing downstream trading, stock and opening semantics SHALL remain unchanged.

#### Scenario: Two shops referencing one assortment stock the same goods
- **WHEN** two shops reference the same assortment and nothing else
- **THEN** both resolve to the same item keys at the same prices, and a
  change to the assortment's offers moves both

#### Scenario: One shop overlapping its own assortments fails load
- **WHEN** one shop references two assortments that both contain the same
  item key
- **THEN** catalog validation raises naming the shop, the item and both
  assortments

#### Scenario: Two shops may share an item key
- **WHEN** two different shops reference assortments that both contain the
  same item key, at different prices
- **THEN** the catalog loads and each shop resolves that key at its own
  assortment's price

#### Scenario: An unknown assortment reference fails load
- **WHEN** a shop references an assortment key that does not exist
- **THEN** catalog validation raises naming the shop and the missing
  assortment

#### Scenario: Trading is unchanged by the indirection
- **WHEN** a player buys and sells against a shop whose goods came from an
  assortment
- **THEN** wallet, inventory, stock, acquisition progress and merchant
  affinity settle exactly as they do for a shop with hand-listed goods

#### Scenario: A shop must reference at least one assortment
- **WHEN** a shop is declared
- **THEN** it SHALL reference at least one assortment

#### Scenario: Duplicate item within one shop fails load for want of precedence
- **WHEN** an item key is contained by two of one shop's referenced assortments
- **THEN** it SHALL fail catalog load naming the shop, the item and both assortments, because the resolver would otherwise have to pick one of two prices by an unstated precedence rule

#### Scenario: The duplicate rejection is scoped to one shop
- **WHEN** two different shops' assortments both contain one item key
- **THEN** that rejection SHALL be scoped to a single shop and the two shops SHALL be accepted: one good sold in two places at two prices is the model working, not a collision

#### Scenario: Resolution is indistinguishable downstream
- **WHEN** a shop's goods resolve from assortments
- **THEN** the result SHALL be indistinguishable to every downstream consumer from a hand-listed shop: trading, stock persistence, restocking, opening hours and the player-facing commands SHALL observe the same flat set of priced offers they observed before assortments existed
