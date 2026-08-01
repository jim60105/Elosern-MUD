## ADDED Requirements

### Requirement: Item and shop identities are immutable while numeric trade rules are YAML and lore-constrained
`ITEM_REGISTRY` SHALL contain frozen item definitions with stable key, Traditional Chinese display name,
price-table key, and sellability. `SHOP_REGISTRY` SHALL contain frozen definitions with stable identity,
merchant component key, and immutable offered item keys. Exact integer buy/sell copper, max/initial
stock, restock quantity, and opening/restock hours SHALL come from `guild_economy.yaml`. Loading SHALL
join both sources and reject unknown, missing, or extra references, floats, negative prices, sell above
buy, buy outside the referenced `PRICE_TABLE` range, and stock outside `0 <= initial <= max` with
positive restock quantity.

#### Scenario: Initial ordinary goods validate
- **WHEN** the meal, potion, and plain-sword offers are loaded
- **THEN** every exact buy price lies within its existing lore price range and every money value is int

#### Scenario: Floating price is rejected
- **WHEN** an offer declares `buy_copper=50.0`
- **THEN** catalog validation raises before registry or merchant state changes

### Requirement: Merchant stock is finite persistent repeated-item quantity state
Each Merchant host SHALL persist stock by item key and a last-restock day. Startup SHALL initialize only
missing stock from `initial_stock`; repeated synchronization SHALL preserve live quantities and SHALL
reject malformed or unknown stock keys instead of resetting them.

#### Scenario: Repeated startup preserves a sold-out item
- **WHEN** potion stock reaches zero and startup synchronization runs again
- **THEN** stock remains zero until a caravan restock boundary

#### Scenario: Malformed stock fails closed
- **WHEN** one merchant stores a negative quantity
- **THEN** trade with that merchant raises a data error without resetting stock

### Requirement: Buying and selling commit wallet, inventory, acquisition progress, and stock atomically
`buy()` and `sell()` SHALL require positive integer quantity, local open Merchant, known offered item,
and sufficient complete funds/stock/inventory. Buying SHALL subtract exact copper, add repeated item keys,
and decrement stock. Selling SHALL remove the quantity, add exact copper, and increment stock without
exceeding max. Buying SHALL stage ACQUIRE progress; selling SHALL not reverse it. Every surface SHALL
commit in one transaction with cache restoration.

#### Scenario: Successful purchase uses integer copper
- **WHEN** a player with 100 copper buys two 20-copper items from stock 3
- **THEN** wallet is 60, two item keys are added, and stock is 1 with no float created

#### Scenario: Insufficient funds changes nothing
- **WHEN** total exact price exceeds wallet
- **THEN** wallet, inventory, quest log, and merchant stock remain unchanged

#### Scenario: Sale cannot overflow merchant stock
- **WHEN** selling the requested quantity would exceed max stock
- **THEN** the complete sale is rejected rather than partially accepted or clamped

#### Scenario: Fault injection restores every trade surface
- **WHEN** any wallet, inventory, quest-log, or stock write raises during trade
- **THEN** database and in-process values for all four surfaces equal their pre-trade values

### Requirement: Opening status is clock-derived and emits ordered boundary events
Shop opening SHALL be computed from WorldClock calendar and support same-day and overnight intervals.
Closed shops SHALL reject trades. The registered `shop_hours` source SHALL emit JSON-safe open/close
ScheduledEvents for every crossed boundary without persisting a redundant open flag.

#### Scenario: Closed shop rejects trade
- **WHEN** buy is attempted outside the shop's configured interval
- **THEN** no trade surface changes

#### Scenario: Multi-boundary skip emits each transition
- **WHEN** one clock advance crosses close, next open, and next close
- **THEN** three shop-hour events appear in due-tick order

### Requirement: Caravan arrivals restock once per crossed merchant day up to cap
The registered `caravan_arrivals` source SHALL detect each crossed configured restock boundary by direct
tick arithmetic, add `restock_quantity` up to max, update last-restock day, and emit one JSON-safe event
per merchant/day. It SHALL not iterate per second. Malformed merchant isolation SHALL leave that host
unchanged and continue valid hosts.

#### Scenario: Daily restock fills only to cap
- **WHEN** stock 4 of max 5 crosses a boundary with restock quantity 3
- **THEN** stock becomes 5 and the event reports one item added

#### Scenario: Multi-day skip catches up deterministically
- **WHEN** a three-day skip crosses three restock boundaries from empty stock
- **THEN** at most three restocks are applied in day order and stock never exceeds max

#### Scenario: Caravan precedes shop opening
- **WHEN** one advance crosses a restock and opening boundary at their configured due ticks
- **THEN** returned events and mutations respect the existing `caravan_arrivals` before `shop_hours`
  settlement order

### Requirement: Player-facing shop commands use only a local unambiguous merchant
The character cmdset SHALL expose stock listing, buy, and sell commands with Traditional Chinese output.
Commands SHALL resolve one Merchant host in the caller's current room and SHALL not permit remote dbref
interaction.

#### Scenario: Altoria merchant is usable through commands
- **WHEN** the player enters the general store during opening hours
- **THEN** list, buy, and sell invoke the same deterministic APIs used by integration tests
