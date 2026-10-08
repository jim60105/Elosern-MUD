# masterwork-price-band Specification

## Purpose
Bound the price of master-crafted goods whose worth is set by scarcity rather
than by materials, and keep the one-of-a-kind keepsake band strictly out of
trade.

## Requirements

### Requirement: A masterwork price band spans everyday and scarce prices for the same object
`PRICE_TABLE` SHALL carry a `masterwork_gear` band whose floor is 100 copper
and whose ceiling is 500,000 copper. The band SHALL describe goods whose
price is set by scarcity rather than materials: ordinary where the maker's
own community trades them, extraordinary where they are rare. The ceiling
SHALL stay strictly below the `relic` band's floor so the keepsake band
retains an exclusive price region.

#### Scenario: One item carries an ordinary and a scarce price
- **WHEN** two shops offer the same `masterwork_gear` item, one at an
  everyday price near the band floor and one at a far higher price
- **THEN** both offers pass price-band validation, and a purchase from
  either shop yields the same item key with the same item definition

#### Scenario: A price above the masterwork ceiling is rejected
- **WHEN** a shop offer prices a `masterwork_gear` item above 500,000 copper
- **THEN** catalog validation raises before any registry or merchant state
  changes

#### Scenario: The masterwork ceiling does not reach the keepsake floor
- **WHEN** the `masterwork_gear` ceiling and the `relic` floor are compared
- **THEN** the ceiling is strictly lower, so no price is legal in both bands

#### Scenario: One price band describes the object, not one market
- **WHEN** the band's width is considered
- **THEN** it SHALL be wide enough that one item key can legally carry an everyday price in the
  community that makes it and a far higher price elsewhere, because a price band describes what an
  object is, not what one market charges for it

#### Scenario: The band key names no race or culture
- **WHEN** the band key is authored
- **THEN** it SHALL NOT name a race or a culture, and master-crafted goods from any people are
  admissible

### Requirement: A keepsake-band item can never be offered for sale
No item whose price-table band is `relic` SHALL be offered for sale, at any
price. The `relic` band means a one-of-a-kind keepsake that is never traded.

#### Scenario: A relic-band item is unshelvable at any price
- **WHEN** an item whose band is `relic` is priced at exactly the band floor
- **THEN** it is still not offerable, because the prohibition is on the band
  rather than on falling short of a price

#### Scenario: A keepsake stays reachable outside trade
- **WHEN** a `relic`-band item is granted through authored content rather
  than a shop
- **THEN** it is held and inspected normally; only the shop offer path is
  closed

#### Scenario: The prohibition is made absolute over the band floor
- **WHEN** the band's 999,999 copper floor is considered — today only an implicit consequence of
  the prohibition, which an author can satisfy exactly
- **THEN** this requirement makes the prohibition absolute, so a keepsake cannot reach a shelf by
  being priced at its own floor

#### Scenario: Enforcement is owned by the goods-list validator
- **WHEN** the load-time rejection for a relic-band offer is located
- **THEN** it is owned by the goods-list validator described in the `commerce-assortments`
  capability; this requirement states the rule the band carries

### Requirement: Goods a community trades everyday do not sit in the keepsake band
An item that authored content places on sale SHALL NOT declare the `relic`
band. Goods a community produces as ordinary output belong in a band whose
floor admits an everyday price, even when their rarity classification is
epic or legendary.

Rarity SHALL remain a presentation classification only: an item's rarity
SHALL NOT constrain which band it may declare, and SHALL NOT feed price
validation.

#### Scenario: A legendary item trades at an everyday price
- **WHEN** an item classified legendary is offered at a price near the
  `masterwork_gear` floor
- **THEN** the offer passes validation, because rarity does not participate
  in price-band checks

#### Scenario: A community's everyday output is shelvable
- **WHEN** an item declared non-sellable in the keepsake band is re-declared
  sellable in `masterwork_gear` and offered at an everyday price
- **THEN** the offer passes validation and the item is buyable, where the
  keepsake declaration would have refused both
