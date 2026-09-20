## Purpose

Let shops share named bundles of goods so a baseline supply is declared,
priced and validated once instead of once per shop that stocks it.

## ADDED Requirements

### Requirement: An assortment is a named reusable bundle of goods
The system SHALL support named assortments. An assortment SHALL carry a
stable key, a Traditional Chinese display name, and an immutable set of item
keys as its identity; exact integer buy/sell copper, max/initial stock and
restock quantity for each of those keys SHALL come from tunable rules
outside the identity registry.

Loading SHALL join the two sources and reject an assortment whose item set
and offer rules disagree in either direction, an unknown item key, a
non-integer money value, a negative price, a sell price above its buy price,
a buy price outside the item's price band, and stock outside
`0 <= initial <= max` with a positive restock quantity. These are the same
rejections the per-shop join enforced; they are now evaluated once per
assortment.

An assortment SHALL NOT declare opening hours, a host, or a location. It
describes goods, not a business.

#### Scenario: An assortment missing an offer fails load
- **WHEN** an assortment names an item key for which no offer rule exists
- **THEN** catalog validation raises naming the assortment and the item,
  before any registry or merchant state changes

#### Scenario: An offer for an item outside the assortment fails load
- **WHEN** an offer rule names an item key the assortment's item set does
  not contain
- **THEN** catalog validation raises naming the assortment and the item

#### Scenario: One assortment is validated once however many shops use it
- **WHEN** several shops reference the same assortment
- **THEN** its item/offer alignment is evaluated once, and a defect in it is
  reported against the assortment rather than repeated per shop

### Requirement: An assortment may not contain a keepsake-band item
Catalog loading SHALL reject an assortment containing an item whose
price-table band is the keepsake band, at any price, naming the assortment
and the item.

The keepsake band means a one-of-a-kind item that is never traded. Its
prohibition is otherwise only an implicit consequence of its very high price
floor, which an author can satisfy exactly. Because an assortment is the only
route by which an item reaches a shelf, rejecting it here closes the rule for
every shop at once.

#### Scenario: A keepsake in an assortment fails load
- **WHEN** an assortment names an item whose band is the keepsake band, at
  any price including exactly the band floor
- **THEN** catalog validation raises naming the assortment and the item,
  before any registry or merchant state changes

#### Scenario: A keepsake stays holdable
- **WHEN** a keepsake-band item is granted through authored content
- **THEN** it is held and inspected normally; only the assortment route is
  closed

### Requirement: A shop's offered goods are derived from the assortments it references
A shop SHALL declare which assortments it references rather than listing its
own item keys. Its offered goods SHALL be the union of those assortments'
item sets, and its offer rules SHALL be those assortments' offer rules.

A shop SHALL reference at least one assortment. Referencing an unknown
assortment SHALL fail catalog load. An item key contained by two of one
shop's referenced assortments SHALL fail catalog load naming the shop, the
item and both assortments, because the resolver would otherwise have to pick
one of two prices by an unstated precedence rule.

That rejection SHALL be scoped to a single shop. Two different shops whose
assortments both contain one item key SHALL be accepted: one good sold in
two places at two prices is the model working, not a collision.

The resolved result SHALL be indistinguishable to every downstream consumer
from a hand-listed shop: trading, stock persistence, restocking, opening
hours and the player-facing commands SHALL observe the same flat set of
priced offers they observed before assortments existed.

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

### Requirement: Every shop's numeric rules are accounted for at load
Catalog loading SHALL verify that every shop in the identity registry has
tunable rules, and SHALL reject the catalog naming any shop that does not.
The accounting SHALL be keyed on shop identity, so the check scales with the
number of shops.

The check SHALL NOT be keyed on any value shared between shops: a key that
is constant across the registry collapses the accounting to a single entry
and silently accepts every shop after the first.

#### Scenario: A second shop with no rules is rejected
- **WHEN** two shops exist in the identity registry and only the first has
  tunable rules
- **THEN** catalog validation raises naming the shop whose rules are absent

#### Scenario: A shop with rules but no identity is rejected
- **WHEN** tunable rules name a shop key absent from the identity registry
- **THEN** catalog validation raises naming that key
