# shop-economy Specification

## Purpose

Define deterministic, finite-stock merchant trading and clock-driven restocking.

## Requirements

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
and sufficient complete funds/stock/inventory, committing every trade surface in one transaction
with cache restoration.

#### Scenario: Successful purchase uses integer copper
- **WHEN** a player with 100 copper buys two 20-copper items from stock 3
- **THEN** wallet is 60, two item keys are added, stock is 1, the merchant's affinity value rises
  by 1, and no float is created

#### Scenario: Insufficient funds changes nothing
- **WHEN** total exact price exceeds wallet
- **THEN** wallet, inventory, quest log, merchant stock, and the merchant's affinity record remain
  unchanged

#### Scenario: Sale cannot overflow merchant stock
- **WHEN** selling the requested quantity would exceed max stock
- **THEN** the complete sale is rejected rather than partially accepted or clamped, and no affinity
  is granted

#### Scenario: Fault injection restores every trade surface
- **WHEN** any wallet, inventory, quest-log, stock, or affinity write raises during trade
- **THEN** database and in-process values for all five surfaces equal their pre-trade values

#### Scenario: Buying moves copper, keys, and stock
- **WHEN** a buy succeeds
- **THEN** it subtracts exact copper, adds repeated item keys, and decrements stock

#### Scenario: Selling moves quantity, copper, and stock
- **WHEN** a sell succeeds
- **THEN** it removes the quantity, adds exact copper, and increments stock without exceeding max

#### Scenario: Buying stages ACQUIRE progress irreversibly
- **WHEN** a buy and later a sell occur
- **THEN** buying stages ACQUIRE progress and selling does not reverse it

#### Scenario: Successful trades grant merchant affinity
- **WHEN** a buy or sell succeeds
- **THEN** it additionally grants +1 affinity (`trade` source) with the local Merchant host through
  the sole-writer affinity API (`world/rules/affinity.py`) within the same transaction

#### Scenario: The transaction covers every surface including affinity
- **WHEN** a trade commits or fails
- **THEN** every surface — wallet, inventory, quest log, merchant stock, the host's `relations_data`
  affinity attribute, and the actor's traits — commits in one transaction; the trade snapshot
  includes the host's affinity record and a failed trade restores it alongside the other surfaces

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
The character cmdset SHALL expose stock listing, buy, and sell commands with Traditional Chinese
output. The stock listing SHALL identify the shop by its authored place name rather than a
generic word. Host acceptance SHALL flow through `world/rules/service_gate.py::service_available`,
and every refusal writes no transaction.

#### Scenario: Explicit and implicit merchant selection
- **WHEN** a player appends an explicit terminal `@#dbid` to `shop stock`, `buy`, or `sell`
- **THEN** exactly that visible eligible Merchant in the caller's current room is selected, without
  substitution, and a remote target remains forbidden
- **WHEN** no such suffix is supplied
- **THEN** the established unambiguous implicit discovery applies

#### Scenario: Altoria merchant is usable through commands
- **WHEN** the player enters the general store during opening hours
- **THEN** list, buy, and sell invoke the same deterministic APIs used by integration tests

#### Scenario: Two shops are distinguishable by their stock listing
- **WHEN** a player lists stock in one shop and then in another in the same settlement
- **THEN** each listing names its own place, and the two headers differ

#### Scenario: A traveling place-bound merchant refuses trade with the fixed line
- **WHEN** the merchant host is moved to the town square beside the player and the player lists
  stock or attempts a purchase
- **THEN** the command replies the gate's fixed `off_anchor` message and no wallet, inventory, or
  stock state changes

#### Scenario: A remote merchant keeps its existing rejection lineage
- **WHEN** the player attempts shop interaction with a merchant in another room
- **THEN** the refusal matches the pre-change remote-merchant behavior

#### Scenario: Gate verdicts map to fixed refusals
- **WHEN** the service gate returns a verdict on a candidate merchant host
- **THEN** `remote` keeps the existing remote-interaction rejection lineage, and an `off_anchor` or
  `malformed_binding` verdict refuses the trade with the gate's fixed registry message

#### Scenario: An at-anchor merchant behaves exactly as before
- **WHEN** a co-located, at-anchor (or `person`-bound) merchant is used
- **THEN** it behaves exactly as before the gate existed

#### Scenario: Place-named listings distinguish same-settlement shops
- **WHEN** two shops operate in one settlement
- **THEN** they are distinguishable by their listing alone

#### Scenario: Explicit provider survives same-class bystanders
- **WHEN** a player supplies the terminal target suffix for a visible eligible provider while another same-class provider is present
- **THEN** only the selected provider is used; if it departs before execution the command rejects without substituting the bystander

### Requirement: Shop economy stays consistent with the canonical inventory
Buy and sell SHALL keep operating on `db.inventory` as the canonical record, and their preflight checks
SHALL remain authoritative for stock, funds, and holdings regardless of object containment. Buy SHALL
materialize one contained mirror object per bought unit inside the same transaction that writes the
key list; sell SHALL remove the mirrored contained objects of the sold units in the same transaction.

#### Scenario: Sell sees every canonical item including picked-up ones
- **WHEN** a player picked up a registry item via `拿` and then opens the shop sell flow
- **THEN** the item appears in sellable holdings, selling removes its key from `db.inventory`, and the
  mirrored contained objects of the sold units are removed

#### Scenario: Buy materializes the contained object
- **WHEN** a player buys a registry item
- **THEN** the item's Evennia Object exists in the character's containment in the same transaction as
  the key-list write, so it can be dropped or given

### Requirement: Purchases debit the party purse and fill the recipient's bag
A purchase SHALL name a recipient member (authorized for the organizing purpose), debit the unchanged buy price from the commander's wallet (the party purse), add the items to the recipient's bag, and decrement merchant stock, all in one transaction that restores every surface on failure.

#### Scenario: Buying potions for a companion
- **WHEN** the commander, holding 1,240 copper, buys three 40-copper potions for companion 艾拉
- **THEN** the commander's wallet is 1,120, 艾拉 holds three more potions, the commander's bag is unchanged, and stock drops by three

#### Scenario: Insufficient purse rejects for any recipient
- **WHEN** the purse holds less than the total price
- **THEN** the purchase is rejected with the existing insufficient-funds reason and nothing changes

#### Scenario: A forged recipient is refused
- **WHEN** the recipient names an NPC outside the party
- **THEN** the purchase is rejected with `not_party_member` and the commander does not receive the items

### Requirement: Sales draw from the seller's unequipped items and credit the party purse
A sale SHALL name a seller member (authorized for the organizing purpose), remove only that member's unequipped copies, credit the unchanged sell price (half the buy price) to the commander's wallet, and raise merchant stock up to its cap, atomically.

#### Scenario: Selling a companion's spare sword
- **WHEN** the commander sells companion 卡恩's two unequipped rusty swords
- **THEN** 卡恩 holds none, the purse rises by twice the sell price, and his equipped weapon is untouched

#### Scenario: An equipped copy is not sellable
- **WHEN** the seller's only copy of an item is equipped
- **THEN** the sale is rejected with the existing `equipped_item` refusal and nothing changes

### Requirement: Text shop commands name the recipient or seller
`buy <物品> [數量] [= <成員>]` (aliases `購買`, `買`, `shop buy`) and `sell <物品> [數量] [= <成員>]` (aliases `販賣`, `賣`, `shop sell`) SHALL name the recipient or seller (default: the caller) with the same rules and messages as the actions, and SHALL be documented in both player command documents.

#### Scenario: Text purchase for a companion
- **WHEN** the player types `買 治療藥水 3 = 艾拉` at an open merchant
- **THEN** the outcome equals `shop.buy` with `recipient_id` naming 艾拉

### Requirement: Possessed trades use the named bag and the party purse
While possessing a companion, text `buy`/`sell` and web `shop.buy`/`shop.sell` SHALL use normal trade settlement. The named member's bag, commander's purse and merchant affinity, configured prices, authorization, and atomicity SHALL remain unchanged. Possession alone SHALL NOT refuse a trade. Text commands without a member suffix SHALL use the acting puppet's bag; web actions SHALL retain their explicit recipient or seller field.

#### Scenario: Possessed text purchase defaults to the acting puppet
- **WHEN** a player possessing a companion uses `buy <item_key> 2` at a valid open local merchant with stock and sufficient party funds
- **THEN** two items enter the companion's bag, the commander's bag is unchanged, the commander's purse is debited by twice the configured buy price, stock drops by two, and merchant affinity accrues to the commander exactly as for an unpossessed purchase

#### Scenario: Possessed text sale defaults to the acting puppet
- **WHEN** a player possessing a companion uses `sell <item_key> 1` for an unequipped offered item with merchant stock headroom
- **THEN** one item leaves that companion's bag, the commander's bag is unchanged, stock rises by one, and the commander's purse and merchant affinity receive the normal sale result

#### Scenario: Possessed web trades name the acting puppet explicitly
- **WHEN** an authenticated possessing client submits a legal `shop.buy` with the puppet's `recipient_id`, or `shop.sell` with its `seller_id`
- **THEN** the matching trade succeeds once against that puppet's bag and the commander's purse with normal configured prices and commander-keyed merchant affinity, without creating a companion wallet

#### Scenario: A possessed trade can name another authorized member
- **WHEN** the possessed actor names the commander or another authorized present party member through the text suffix or web member field
- **THEN** only the named member's bag changes and the same commander's purse pays or receives the configured price

#### Scenario: Possession does not bypass normal trade refusals
- **WHEN** a possessing actor requests a forged or absent member, insufficient funds or stock, a closed or unavailable merchant, an equipped-only sale, or a sale beyond the merchant cap
- **THEN** the normal party or trade refusal is returned without changing any transaction surface, with no fallback to the commander's bag

#### Scenario: Read-only stock remains available
- **WHEN** a player possessing a companion requests `shop stock` at a normally available local merchant
- **THEN** the existing read-only stock listing remains available and changes no state

### Requirement: Text inventory reports the party purse independently of the caller's bag
Text `inventory` SHALL display the commander's current party purse for an authenticated possessed companion and the caller's wallet for an unpossessed player. Its bag rows and existing character breakdown SHALL continue to describe the caller. Both player command documents SHALL describe possessed trade availability and distinguish the party purse from the caller's bag.

#### Scenario: Inventory shows the purchase debit from the party purse
- **WHEN** a companion with no wallet is possessed and a legal text purchase debits the commander's purse
- **THEN** `inventory` displays that same remaining purse as the web party window, lists the companion's updated bag, and does not display zero from the companion's absent wallet

#### Scenario: Unpossessed inventory keeps its existing bag presentation
- **WHEN** an unpossessed player requests `inventory`
- **THEN** the displayed purse remains that player's wallet and the existing bag ordering, quantities, item prose, and breakdown header remain unchanged
