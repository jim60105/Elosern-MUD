## MODIFIED Requirements

### Requirement: The services panel is an exact read-only exploration-mode panel
The production presentation registry SHALL register `services` schema version 2. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `host`, `player`, `guild`, `shop`, `inventory`, and `pagination`; `available` SHALL be true and `kind` SHALL be `services`. `schema_version` SHALL be integer 2. `host` SHALL be null or contain exactly `identity` (1..64 opaque ASCII characters) and `display_name` (1..256 Unicode code points) and SHALL be display-only reconciliation metadata that never enters a `ui_action` payload. `pagination` SHALL contain exactly `board_total`, `quest_total`, `stock_total`, `sellable_total`, and `inventory_total`, each a non-negative JavaScript-safe integer no greater than its surface's row ceiling and equal to the number of rows shipped in that surface (zero when the surface is null). `player` SHALL contain exactly `wallet`, `guild_registered`, `guild_rank`, `guild_merit`, `next_rank`, and `next_threshold`: wallet SHALL be a non-negative JavaScript-safe integer, `guild_registered` a boolean, `guild_rank` null or a 1..8-character rank key, `guild_merit` a non-negative safe integer, and `next_rank`/`next_threshold` null when the actor holds the top rank, otherwise the next rank key and its positive catalog merit threshold. `guild`, `shop`, and `inventory` SHALL each be null or an exact section object. The presenter SHALL strictly read canonical records and registries through the no-mutation service read model, SHALL emit no live object reference and no filesystem path, and SHALL NOT mutate registration, quests, wallet, inventory, merchant stock, rank, merit, traits, location, or world time. The whole panel SHALL use the registered common unavailable form only when a global prerequisite fails: the puppet is not in exploration mode or the actor/player summary cannot be read without mutation. A failure confined to one surface SHALL make only that surface unavailable with a stable reason while the other surfaces and narrative remain available.

#### Scenario: Exploration snapshot carries the full services panel
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot
- **THEN** `services` reports the display-only host, wallet/rank/merit summary, the available guild, shop, and inventory sections, and pagination totals equal to the shipped row counts while a before/after comparison of canonical game state is unchanged

#### Scenario: Pagination totals match shipped rows
- **WHEN** the guild surface ships 1 board offer and 2 quest rows and the shop surface is null
- **THEN** `pagination` reports `board_total` 1, `quest_total` 2, and `stock_total` 0

#### Scenario: Combat and creation do not receive fabricated services
- **WHEN** the active puppet is in an active combat session or is creation-pending
- **THEN** `services` uses its schema-valid unavailable form and contains no register, accept, abandon, turn-in, exam, buy, sell, or inventory row

#### Scenario: Surface failure does not disable the panel
- **WHEN** the actor's merchant stock is malformed but the actor's quest log and wallet are healthy
- **THEN** the `shop` surface is unavailable with a stable reason while `guild`/`inventory` sections and narrative still render

#### Scenario: Presenter failure remains isolated
- **WHEN** services presentation raises while status and narrative remain healthy
- **THEN** only `services` becomes correlated unavailable, status still renders, and normal text output remains usable

### Requirement: The shop surface covers stock, quantity, buy, sell, and sellable inventory
The `shop` section SHALL contain exactly `open`, `stock`, and `sellable` and SHALL be present only when exactly one local `Merchant` host resolves. `open` SHALL be the boolean derived from the world-clock opening computation with no redundant flag. `stock` SHALL be a bounded list of at most 12 rows in catalog offer order, each containing exactly `item_key`, `display_name`, `buy_copper`, `sell_copper`, `stock`, `max_stock`, and `buy`; every copper value SHALL be the exact integer catalog value. `buy` SHALL be enabled only when the shop is open, the item is known and offered, stock is positive, and the actor can afford at least one unit; otherwise it SHALL carry a stable disabled reason. `sellable` SHALL be a bounded list of at most 12 rows in deterministic order, each containing exactly `item_key`, `display_name`, `sell_copper`, `held`, and `sell`; `sell` SHALL be enabled only when the shop is open, the item is sellable and offered, the actor holds at least one, and the merchant's stock cap is not already at maximum. `inventory` SHALL be present in exploration mode and SHALL contain exactly `rows` and `wallet`, with at most 32 rows. Each row SHALL contain exactly `item_key`, `display_name`, `held`, `equipped`, and `presentation`, preserving repeated item keys and showing aggregate quantities as presentation only. `presentation` SHALL be null for an unregistered but structurally valid item key; otherwise it SHALL contain exactly `kind`, `icon_key`, `rarity`, and `summary`, copied verbatim from the immutable item registry. Each non-null key SHALL be 1..32 lowercase ASCII letters or underscores and `summary` SHALL be 1..240 Unicode code points. No row SHALL carry a use, consume, equip, drag, or drop action in this schema version.

#### Scenario: Open shop lists exact integer stock and prices
- **WHEN** the merchant is open during opening hours
- **THEN** `open` is true and each stock row reports the exact catalog `buy_copper`/`sell_copper`, live `stock`, and `max_stock` with no float and no local path

#### Scenario: Closed shop shows disabled purchases
- **WHEN** the merchant is outside opening hours
- **THEN** `open` is false and every `buy`/`sell` descriptor is disabled with a stable closed reason while stock rows still render

#### Scenario: Quantity descriptor advertises a bounded maximum
- **WHEN** a buy row has stock 3
- **THEN** its `buy` action carries `quantity` with minimum 1 and a server-advertised maximum no greater than 3, and no client value can authorize a larger purchase

#### Scenario: Registered inventory projects its immutable visual identity
- **WHEN** the actor holds repeated `healing_potion` keys
- **THEN** the one aggregate inventory row reports its registry `kind`, `icon_key`, `rarity`, and summary together with its count and canonical equipped state

#### Scenario: Unknown inventory remains present without fabricated metadata
- **WHEN** the actor holds a syntactically valid inventory key absent from `ITEM_REGISTRY`
- **THEN** the aggregate row reports its key-derived display name and `presentation` null without a guessed category, icon, rarity, summary, or action descriptor

#### Scenario: Inventory never offers use or equip
- **WHEN** the actor holds repeated `healing_potion` keys
- **THEN** the inventory rows aggregate the count as presentation, show equipped state from canonical equipment, and contain no use, consume, or equip action descriptor
