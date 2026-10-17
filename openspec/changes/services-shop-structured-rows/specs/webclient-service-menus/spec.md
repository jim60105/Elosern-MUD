# Spec Delta

## MODIFIED Requirements

### Requirement: The services panel is an exact read-only exploration-mode panel

The production presentation registry SHALL register `services` schema version 7. Its available payload SHALL
contain exactly `schema_version`, `available`, `kind`, `host`, `player`, `guild`, `shop`, and
`pagination`; `available` SHALL be true, `kind` SHALL be `services`, and `schema_version` SHALL be integer 7.
Personal inventory SHALL NOT appear; the `party_inventory` panel owns it.
The presenter SHALL strictly read canonical records and registries through the no-mutation service read model.

#### Scenario: Exploration snapshot carries the full services panel
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot
- **THEN** `services` reports the display-only host, wallet/rank/merit summary, and available guild and shop sections, and pagination totals equal shipped row counts without mutating canonical state

#### Scenario: Pagination totals match shipped rows
- **WHEN** the guild surface ships 1 board offer and 2 quest rows and the shop surface is null
- **THEN** `pagination` reports `board_total` 1, `quest_total` 2, and `stock_total` 0

#### Scenario: Combat snapshot carries personal inventory only
- **WHEN** a puppeted WebClient in active combat receives a full snapshot
- **THEN** `services` reports the canonical player summary while host, guild, and shop are null and all guild/shop pagination totals are zero; personal inventory is published by `party_inventory`

#### Scenario: Creation does not receive fabricated services
- **WHEN** the active puppet is creation-pending
- **THEN** `services` uses its schema-valid unavailable form and contains no service row

#### Scenario: Surface failure does not disable unrelated exploration surfaces
- **WHEN** exploration merchant stock is malformed but the actor's quest log and wallet are healthy
- **THEN** the shop surface is unavailable with a stable reason while guild and narrative still render

#### Scenario: Presenter failure remains isolated
- **WHEN** services presentation raises while status and narrative remain healthy
- **THEN** only `services` becomes correlated unavailable, status still renders, and normal text output remains usable

#### Scenario: Below merit request stays enabled
- **WHEN** a registered next-rank member below true merit threshold stands at a functioning guild counter and the qualified host is absent
- **THEN** merit_qualified is false, exam_request is enabled and dispatch returns exam_schedule without mutation

#### Scenario: Host metadata shape is bounded and display-only
- **WHEN** the `host` field is present on an available payload
- **THEN** it contains exactly `identity` (1..64 opaque ASCII characters) and `display_name` (1..256 Unicode code
  points), and host metadata is display-only reconciliation metadata that never enters a `ui_action` payload

#### Scenario: Pagination totals are exact safe integers of shipped rows
- **WHEN** any surface ships rows or is null
- **THEN** `pagination` contains exactly `board_total`, `quest_total`, `stock_total`, and `sellable_total`, each a non-negative JavaScript-safe integer no greater than its surface's row ceiling and
  equal to the number of rows shipped in that surface (zero when the surface is null)

#### Scenario: Player summary carries its exact six fields
- **WHEN** the `player` section is built
- **THEN** it contains exactly `wallet`, `guild_registered`, `guild_rank`, `guild_merit`, `next_rank`, and
  `next_threshold`: `wallet` is a non-negative JavaScript-safe integer, `guild_registered` a boolean,
  `guild_rank` null or a 1..8-character rank key, and `guild_merit` a non-negative safe integer

#### Scenario: Top rank reports no next threshold
- **WHEN** the actor holds the top rank
- **THEN** `next_rank` and `next_threshold` are null, and otherwise they carry the next rank key and its positive
  catalog merit threshold

#### Scenario: Section fields are null or exact objects
- **WHEN** an available services payload is built in exploration mode
- **THEN** `guild` and `shop` are each null or an exact section object, and both retain their ordinary
  availability

#### Scenario: Combat keeps personal data with no remote service
- **WHEN** the actor is in active combat
- **THEN** the canonical `player` summary remains available and exposes no remote service; personal item actions read `party_inventory`

#### Scenario: Presenter output leaks no internals
- **WHEN** the presenter serializes any services payload
- **THEN** it emits no live object reference and no filesystem path, and does not mutate registration, quests,
  wallet, inventory, equipment, merchant stock, rank, merit, traits, location, combat, or world time

#### Scenario: Unreadable summary triggers the common unavailable form
- **WHEN** the actor/player summary cannot be read without mutation
- **THEN** the whole panel uses the registered common unavailable form, which is reserved for such global
  prerequisite failures

### Requirement: The shop surface covers stock, quantity, buy, sell, and sellable inventory
The `shop` section SHALL contain exactly `open`, `member_id`, `stock`, and `sellable` and SHALL be present only in
exploration mode when exactly one local `Merchant` host resolves. `member_id` SHALL be the session's viewed party
member (falling back to the commander), the default recipient and seller. Copper values SHALL be exact integer
catalog values, stock rows SHALL carry only the buy price and sellable rows only the sell price, and `buy`/`sell`
SHALL be enabled only when the shop is open and the trade is legal for that member and the party purse,
otherwise carrying a stable disabled reason.

#### Scenario: Open shop lists exact integer stock and prices
- **WHEN** the merchant is open during opening hours
- **THEN** `open` is true and each stock row reports the exact catalog `buy_copper`, live `stock`, and `max_stock` with no float and no local path, and no stock row carries a sell price

#### Scenario: Closed shop shows disabled purchases
- **WHEN** the merchant is outside opening hours
- **THEN** `open` is false and every `buy`/`sell` descriptor is disabled with a stable closed reason while stock rows still render

#### Scenario: Quantity descriptor advertises a bounded maximum
- **WHEN** a buy row has stock 3
- **THEN** its `buy` action carries `quantity` with minimum 1 and a server-advertised maximum no greater than 3, and no client value can authorize a larger purchase

#### Scenario: Registered inventory projects visual identity and use action
- **WHEN** the shop stocks `healing_potion` and the viewed member holds two
- **THEN** its stock row reports registry presentation and `viewed.held == 2` with a null `viewed.delta`

#### Scenario: Full HP disables potion use truthfully
- **WHEN** the shop stocks a steel shortsword and the viewed member wields a staff
- **THEN** its stock row's `viewed.delta` is the server equipment delta for that member (for example attack +6), or `{equippable: false, reason}` when the member cannot equip it

#### Scenario: Unknown inventory remains inspect-only
- **WHEN** a stocked key lacks registry presentation metadata
- **THEN** its stock row has `presentation` null and no fabricated mechanics

#### Scenario: Full accessory set advertises manual removal
- **WHEN** the viewed member has five accessories equipped and the shop stocks another accessory
- **THEN** that row's `viewed.delta` is `{equippable: false}` with the accessory-cap reason, and buying it stays enabled when otherwise legal

#### Scenario: Open flag is the world-clock boolean only
- **WHEN** the `open` field is computed
- **THEN** it is the boolean derived from the world-clock opening computation with no redundant flag

#### Scenario: Stock rows carry exact fields in catalog offer order
- **WHEN** the `stock` list ships
- **THEN** it is a bounded list of at most 12 rows in catalog offer order, each containing exactly `item_key`,
  `display_name`, `presentation`, `buy_copper`, `stock`, `max_stock`, `viewed` (exactly `held` and `delta`), and `buy`

#### Scenario: Buy enablement requires open, offer, stock, and affordability
- **WHEN** a stock row's `buy` descriptor is computed
- **THEN** it is enabled only when the shop is open, the item is known and offered, stock is positive, and the
  party purse can afford at least one unit

#### Scenario: Sellable rows carry exact fields and sell gates
- **WHEN** the `sellable` list ships
- **THEN** it is a bounded list of at most 12 rows in deterministic order listing the viewed member's unequipped
  items, each containing exactly `item_key`, `display_name`, `presentation`, `sell_copper`, `held` (unequipped
  copies), and `sell`, and `sell` is enabled only when the shop is open, the item is sellable and offered, the
  member holds at least one unequipped copy, and the merchant's stock cap is not already at maximum

#### Scenario: Inventory section carries its exact two fields
- **WHEN** a version-7 services payload is built
- **THEN** it contains no `inventory` section; personal rows and the purse are published by `party_inventory`

#### Scenario: Inventory rows preserve duplicates and aggregate honestly
- **WHEN** the viewed member holds repeated copies of one sellable item key, one of them equipped
- **THEN** one sellable row reports the unequipped count only, and aggregate quantities appear as presentation only

#### Scenario: Presentation is verbatim registry data with bounded shape
- **WHEN** a stock or sellable row's `presentation` is built for a registered item
- **THEN** it contains exactly `kind`, `icon_key`, `rarity`, and `summary`, copied verbatim from the immutable
  item registry; each non-null presentation key is 1..32 lowercase ASCII letters or underscores and `summary` is
  1..240 Unicode code points

#### Scenario: Action descriptors come from side-effect-free preflight
- **WHEN** a row's `buy` or `sell` descriptor is computed
- **THEN** it carries current `enabled` state and a stable disabled reason derived by side-effect-free
  deterministic preflight for the viewed member and the party purse

#### Scenario: Inventory rows leak no mechanics or authority fields
- **WHEN** any stock or sellable row ships
- **THEN** it exposes no effect amount, condition threshold, consumable flag, slot choice, target, drag, or drop
  action, and its only member reference is the panel's `member_id`

### Requirement: Reconnect rebuilds services without replaying intent
WebSocket loss SHALL preserve the last rendered services view under the foundation offline overlay and lock every
service mutation. After reconnect, the first valid new-epoch snapshot SHALL rebuild host, player summary, guild,
and shop sections from canonical persistence even when its revision is lower than the retired epoch.

#### Scenario: Reconnect restores a shop view
- **WHEN** the transport disconnects while the shop surface holds a typed but unsubmitted quantity and reconnects without another game action
- **THEN** the shop surface closes on the transport loss, the unsubmitted quantity is discarded, the new snapshot renders the current stock, purse and the viewed member's sellable rows the next time the shop surface opens, with every quantity entry back at its row action's own lower bound, and no automatic replacement purchase is sent

#### Scenario: Disconnect after submit never retries
- **WHEN** transport closes after sending `guild.quest_turnin` but before its result is observed
- **THEN** reconnect synchronizes canonical quest, wallet, merit, and claims state, shows the uncertain-result notice, and sends no automatic replacement turn-in

#### Scenario: Old-epoch packets are discarded
- **WHEN** a packet from the retired epoch arrives after reconnect
- **THEN** the browser discards it

#### Scenario: Stale selections are never restored as authority
- **WHEN** reconnect completes with an unsubmitted selection pending from before transport loss
- **THEN** the browser does not restore the unsubmitted selection as authority and does not resubmit an uncertain
  prior mutation

#### Scenario: Unconfirmed submissions get the approved notice
- **WHEN** an action was submitted but unconfirmed before transport loss
- **THEN** it is treated as unconfirmed with the approved notice and never retried
