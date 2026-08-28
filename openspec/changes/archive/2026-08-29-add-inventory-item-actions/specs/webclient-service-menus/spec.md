## MODIFIED Requirements

### Requirement: The services panel is an exact read-only exploration-mode panel
The production presentation registry SHALL register `services` schema version 3. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `host`, `player`, `guild`, `shop`, `inventory`, and `pagination`; `available` SHALL be true and `kind` SHALL be `services`. `schema_version` SHALL be integer 3. `host` SHALL be null or contain exactly `identity` (1..64 opaque ASCII characters) and `display_name` (1..256 Unicode code points) and SHALL be display-only reconciliation metadata that never enters a `ui_action` payload. `pagination` SHALL contain exactly `board_total`, `quest_total`, `stock_total`, `sellable_total`, and `inventory_total`, each a non-negative JavaScript-safe integer no greater than its surface's row ceiling and equal to the number of rows shipped in that surface (zero when the surface is null). `player` SHALL contain exactly `wallet`, `guild_registered`, `guild_rank`, `guild_merit`, `next_rank`, and `next_threshold`: wallet SHALL be a non-negative JavaScript-safe integer, `guild_registered` a boolean, `guild_rank` null or a 1..8-character rank key, `guild_merit` a non-negative safe integer, and `next_rank`/`next_threshold` null when the actor holds the top rank, otherwise the next rank key and its positive catalog merit threshold. `guild`, `shop`, and `inventory` SHALL each be null or an exact section object. In exploration mode all sections SHALL retain their ordinary availability. In active combat `host`, `guild`, and `shop` SHALL be null, their pagination totals SHALL be zero, and canonical `player` plus `inventory` SHALL remain available so personal item actions expose no remote service. The presenter SHALL strictly read canonical records and registries through the no-mutation service read model, SHALL emit no live object reference and no filesystem path, and SHALL NOT mutate registration, quests, wallet, inventory, equipment, merchant stock, rank, merit, traits, location, combat, or world time. The whole panel SHALL use the registered common unavailable form only when a global prerequisite fails — the actor is creation-pending or the actor/player/inventory summary cannot be read without mutation; a failure confined to one exploration surface SHALL make only that surface unavailable with a stable reason while the other surfaces and narrative stay healthy.

#### Scenario: Exploration snapshot carries the full services panel
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot
- **THEN** `services` reports the display-only host, wallet/rank/merit summary, available guild, shop, and inventory sections, and pagination totals equal shipped row counts without mutating canonical state

#### Scenario: Pagination totals match shipped rows
- **WHEN** the guild surface ships 1 board offer and 2 quest rows and the shop surface is null
- **THEN** `pagination` reports `board_total` 1, `quest_total` 2, and `stock_total` 0

#### Scenario: Combat snapshot carries personal inventory only
- **WHEN** a puppeted WebClient in active combat receives a full snapshot
- **THEN** `services` reports canonical player and inventory data while host, guild, and shop are null and all guild/shop pagination totals are zero

#### Scenario: Creation does not receive fabricated services
- **WHEN** the active puppet is creation-pending
- **THEN** `services` uses its schema-valid unavailable form and contains no service or inventory row

#### Scenario: Surface failure does not disable unrelated exploration surfaces
- **WHEN** exploration merchant stock is malformed but the actor's quest log, wallet, and inventory are healthy
- **THEN** the shop surface is unavailable with a stable reason while guild, inventory, and narrative still render

#### Scenario: Presenter failure remains isolated
- **WHEN** services presentation raises while status and narrative remain healthy
- **THEN** only `services` becomes correlated unavailable, status still renders, and normal text output remains usable

### Requirement: The shop surface covers stock, quantity, buy, sell, and sellable inventory
The `shop` section SHALL contain exactly `open`, `stock`, and `sellable` and SHALL be present only in exploration mode when exactly one local `Merchant` host resolves. `open` SHALL be the boolean derived from the world-clock opening computation with no redundant flag. `stock` SHALL be a bounded list of at most 12 rows in catalog offer order, each containing exactly `item_key`, `display_name`, `buy_copper`, `sell_copper`, `stock`, `max_stock`, and `buy`; every copper value SHALL be the exact integer catalog value. `buy` SHALL be enabled only when the shop is open, the item is known and offered, stock is positive, and the actor can afford at least one unit; otherwise it SHALL carry a stable disabled reason. `sellable` SHALL be a bounded list of at most 12 rows in deterministic order, each containing exactly `item_key`, `display_name`, `sell_copper`, `held`, and `sell`; `sell` SHALL be enabled only when the shop is open, the item is sellable and offered, the actor holds at least one, and the merchant's stock cap is not already at maximum. `inventory` SHALL be present in exploration and combat modes and SHALL contain exactly `rows` and `wallet`, with at most 32 rows. Each row SHALL contain exactly `item_key`, `display_name`, `held`, `equipped`, `presentation`, and `action`, preserving repeated item keys and showing aggregate quantities as presentation only. `presentation` SHALL be null for an unregistered but structurally valid item key; otherwise it SHALL contain exactly `kind`, `icon_key`, `rarity`, and `summary`, copied verbatim from the immutable item registry. Each non-null presentation key SHALL be 1..32 lowercase ASCII letters or underscores and `summary` SHALL be 1..240 Unicode code points. `action` SHALL be null for unknown or inspect-only items. A usable item SHALL carry an `inventory.use` descriptor and equipment SHALL carry an `inventory.toggle_equip` descriptor, with current `enabled` state and a stable disabled reason derived by side-effect-free deterministic preflight. No inventory row SHALL expose an effect amount, condition threshold, consumable flag, slot choice, actor, target, drag, or drop action.

#### Scenario: Open shop lists exact integer stock and prices
- **WHEN** the merchant is open during opening hours
- **THEN** `open` is true and each stock row reports the exact catalog `buy_copper`/`sell_copper`, live `stock`, and `max_stock` with no float and no local path

#### Scenario: Closed shop shows disabled purchases
- **WHEN** the merchant is outside opening hours
- **THEN** `open` is false and every `buy`/`sell` descriptor is disabled with a stable closed reason while stock rows still render

#### Scenario: Quantity descriptor advertises a bounded maximum
- **WHEN** a buy row has stock 3
- **THEN** its `buy` action carries `quantity` with minimum 1 and a server-advertised maximum no greater than 3, and no client value can authorize a larger purchase

#### Scenario: Registered inventory projects visual identity and use action
- **WHEN** an injured actor holds repeated `healing_potion` keys
- **THEN** one aggregate row reports registry presentation, count, canonical equipped state, and an enabled `inventory.use` descriptor

#### Scenario: Full HP disables potion use truthfully
- **WHEN** an actor holds a healing potion at full HP
- **THEN** its row retains real presentation and count while its `inventory.use` descriptor is disabled with `hp_full`

#### Scenario: Unknown inventory remains inspect-only
- **WHEN** the actor holds a structurally valid key absent from `ITEM_REGISTRY`
- **THEN** its aggregate row has a key-derived display name, `presentation` null, and `action` null without fabricated mechanics

#### Scenario: Full accessory set advertises manual removal
- **WHEN** five accessories are equipped and an additional held accessory is listed
- **THEN** the additional item's toggle descriptor is disabled with the accessory-cap reason while each equipped accessory remains enabled for unequip

### Requirement: Service actions are exact, allowlisted, and server-authoritative
The production action registry SHALL retain every existing combat, service, creation, exploration, and options action and SHALL add exactly `inventory.use` and `inventory.toggle_equip`. The service action set SHALL therefore contain `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.exam_start`, `shop.buy`, `shop.sell`, `inventory.use`, and `inventory.toggle_equip`. `guild.register` SHALL accept exactly an empty payload and retain its current idempotency. Guild quest and exam actions SHALL retain their exact bounded identifiers; `shop.buy` and `shop.sell` SHALL retain exactly bounded `item_key` and integer `quantity`. Each inventory action SHALL accept exactly `item_key` as a 1..64-character non-empty string. Every adapter SHALL obtain the actor from the authenticated session, re-resolve every local host and referenced quest, definition, item, rank, mechanic, and current condition, and invoke only its listed public deterministic API. No inventory payload SHALL accept actor, host, branch, session, effect, consumable, quantity, target, slot, HP, combat, price, stock, or wallet fields. No adapter SHALL assign `.db`, traits, registration, rank, merit, quest log, wallet, inventory, equipment, merchant stock, location, combat, or clock state directly. No action SHALL route an action ID or payload through the text command parser.

#### Scenario: Existing registration reaches its deterministic API once
- **WHEN** an unregistered actor submits an empty `guild.register` at the local guild hall
- **THEN** the adapter resolves the local staff host and calls `register_adventurer`, and the snapshot thereafter reports rank F with the recorded branch

#### Scenario: Repeated registration is idempotent
- **WHEN** a registered actor submits an empty `guild.register` again after a state change between render and submit
- **THEN** the adapter returns the original record without replacing branch, tick, or snapshot, reports success, and refreshes canonical services/status panels

#### Scenario: Quest accept is board-gated
- **WHEN** a registered member submits `guild.quest_accept` with a visible definition key
- **THEN** the adapter revalidates board eligibility and creates exactly the deterministic quest record

#### Scenario: Exam start cannot choose an examiner or rank
- **WHEN** a client submits a non-next rank or includes a host or examiner identity
- **THEN** the adapter rejects before exam creation and only the exact next-rank payload is accepted

#### Scenario: Existing buy and sell submit only item and quantity
- **WHEN** a client submits `shop.buy` with item key and quantity only
- **THEN** the adapter re-resolves and rechecks the local merchant before calling deterministic economy settlement

#### Scenario: Inventory use submits only item key
- **WHEN** a client submits `inventory.use` with one item key
- **THEN** the adapter resolves current actor mode and delegates to the matching deterministic item-use facade exactly once

#### Scenario: Inventory toggle submits only item key
- **WHEN** a client submits `inventory.toggle_equip` with one item key
- **THEN** the adapter delegates to deterministic equipment toggle without accepting a client-selected slot

#### Scenario: Authority-like fields can never be supplied
- **WHEN** any service or inventory action contains an unknown actor, host, session, effect, or slot-like field
- **THEN** exact-schema validation rejects before adapter invocation

### Requirement: Service actions reject stale, duplicate, and tampered input without mutation
Every service and inventory action SHALL pass the existing dispatcher's epoch, base revision, in-flight, and request-ID checks before adapter invocation; a `presentation_epoch` or `base_revision` that does not equal the newest values issued for the live session SHALL return `stale` with a fresh full snapshot and SHALL invoke no adapter. A duplicate live request ID SHALL return its cached result without re-executing. After those checks, commit-time domain revalidation is authoritative: a price, stock, rank, quest, claim, HP value, ownership fact, mechanic, or equipment capacity that changed between render and commit SHALL be handled against current canonical state and SHALL not double-apply any mutation. A tampered or no-longer-valid identifier SHALL reject with a stable code and Traditional Chinese message, leaving wallet, inventory, contained mirrors, equipment, stock, quests, merit, rank, claims, traits, clock, combat, and every in-process cache unchanged. A service host that disappeared or became ambiguous SHALL close its controls and return current local-service state without mutation.

#### Scenario: Stale inventory revision invokes no adapter
- **WHEN** a potion dialog rendered at revision N submits after a newer revision is active
- **THEN** the dispatcher returns `stale`, invokes no item resolver, and publishes current canonical state without consumption

#### Scenario: Stale revision cannot pay a reward twice
- **WHEN** a turn-in row rendered at revision N is submitted after a newer revision is active
- **THEN** the dispatcher returns `stale`, invokes no adapter, and appends no reward claim

#### Scenario: Price change between render and commit is not stale
- **WHEN** `shop.buy` passes current epoch/revision checks but canonical price or stock changes before commit
- **THEN** deterministic economy settles or rejects against current state without float or double application

#### Scenario: Live HP change uses domain rejection
- **WHEN** an item request passes current epoch/revision checks but HP becomes full before deterministic settlement
- **THEN** item preflight rejects with `hp_full` and all item-use surfaces remain unchanged

#### Scenario: Duplicate item request executes once
- **WHEN** the same live request ID for `inventory.use` is delivered twice
- **THEN** item settlement runs once, consumption and effect occur once, and the duplicate receives the cached first result

#### Scenario: Duplicate buy request executes once
- **WHEN** the same live request ID for `shop.buy` is delivered twice
- **THEN** economy settlement runs once, wallet and stock change once, and the duplicate receives the cached first result

#### Scenario: Unknown quest cannot be turned in
- **WHEN** a tampered quest ID is submitted for turn-in
- **THEN** reward settlement is not invoked and wallet, inventory, merit, quest log, and claims remain unchanged

#### Scenario: Removed host closes without mutation
- **WHEN** a merchant disappears between render and `shop.buy`
- **THEN** the adapter rejects with a stable reason, no trade state changes, and current local-service state is published

#### Scenario: Tampered item cannot be used or equipped
- **WHEN** an unknown, unheld, or mechanically incompatible item key passes envelope validation
- **THEN** domain revalidation rejects before mutation and returns the canonical refreshed inventory

### Requirement: Service action completion updates canonical panels and preserves narrative
After an admitted service or inventory action settles, the server SHALL emit every returned message through the ordinary escaped text output path and SHALL publish canonical panel replacements at one newer revision before sending the matching safe `ui_action_result`. Existing guild, quest, and shop actions SHALL retain their established affected-panel sets. `inventory.use` and `inventory.toggle_equip` SHALL publish a full snapshot because they may change inventory, contained mirrors, status, character equipment, clock-derived state, combat/context state, terminal mode, and art. Entering combat SHALL unload exploration service menus and their local forms, but services v3 SHALL retain personal player/inventory data and the combat UI SHALL own a separate inventory affordance; guild and shop actions SHALL remain absent in combat. Every success or domain-rejection message SHALL be emitted as text and never parsed by the browser to update panel state.

#### Scenario: Turn-in updates wallet and merit panels together
- **WHEN** a completed quest is turned in successfully
- **THEN** narrative carries the reward message and status/services reflect wallet, merit, claim, and quest-log state at one newer revision before unlock

#### Scenario: Item use updates HP and inventory atomically
- **WHEN** `inventory.use` succeeds for a consumable healing potion
- **THEN** narrative reports the safe result and one newer canonical commit shows HP, item count, mode, clock, and combat state from the same settlement

#### Scenario: Exam start hands off while retaining personal inventory
- **WHEN** `guild.exam_start` succeeds for the exact next rank
- **THEN** mode becomes combat, context actions become combat, guild and shop services disappear, and canonical personal inventory remains reachable from the combat affordance

#### Scenario: Mode change tears down exploration service state
- **WHEN** the browser adopts combat mode
- **THEN** exploration service menus discard local quantity, selection, confirmation, and speech state while the combat dock owns focus and can open a fresh combat inventory surface

#### Scenario: Rejected inventory action emits no fabricated prose
- **WHEN** deterministic item or equipment preflight rejects
- **THEN** only the stable safe rejection is emitted, canonical state remains unchanged, and refreshed inventory permits another legal choice

#### Scenario: Rejected purchase emits no fabricated prose
- **WHEN** deterministic economy rejects for insufficient funds
- **THEN** only the stable safe rejection is emitted, wallet and stock remain unchanged, and refreshed services permits another legal choice

### Requirement: Service browser acceptance is keyboard-only, confirmation-protected, and desktop-bounded
The managed localhost browser suite SHALL exercise, using keyboard controls at 1440x900 and 1280x720, all existing registration, quest, exam, shop, stale/duplicate, repeated-inventory, and reconnect journeys plus item-use confirmation at both viewports, full-HP refusal, combat item use through the frameless combat bag drawer, and direct equipment toggle. Singleton replacement and the five-accessory cap with its sixth-accessory warning SHALL be established by deterministic rule and action-adapter tests and rendered in the component showcase, because the shipped item registry publishes no accessory items and no second singleton weapon for a live browser journey to hold. Exploration service submenus SHALL retain their existing roots and drawer-hosted shared row renderer. The bag SHALL retain its frameless client-local drawer model in exploration and combat. Every pointer affordance SHALL emit the same server-authored action identifier and payload as keyboard activation through the same dispatch entry and gates. Tests SHALL use deterministic fixtures and make no remote, LLM, or image-generation request. No remote or ambiguous host control SHALL render, no inspect-only item SHALL gain an action, and no reference surface SHALL be present while its drawer is closed.

#### Scenario: Guild board journey completes in Chromium
- **WHEN** a seeded registered member uses arrows and Enter to reach and accept an eligible board offer
- **THEN** exactly one expected quest action is submitted and refreshed quest state appears without typed input

#### Scenario: Abandon requires confirmation
- **WHEN** the player focuses or points to active-quest abandon before confirmation
- **THEN** no mutation is sent, cancel or Escape returns without abandoning, and confirm is the only submit path

#### Scenario: Item use requires confirmation at both viewports
- **WHEN** an eligible potion tile is activated by keyboard at 1440x900 or 1280x720
- **THEN** the accessible confirmation remains fully operable, no request precedes confirm, and focus returns to the tile on cancel

#### Scenario: Equipment and cap behavior are enforced deterministically
- **WHEN** rule and adapter tests drive a singleton replacement and fill the accessory slots to the cap
- **THEN** singleton replacement dispatches once, five accessories can be equipped, a sixth refuses with the committed warning without dispatch, and the showcase renders the capped state

#### Scenario: Minimum viewport retains service essentials
- **WHEN** shop or bag is open at 1280x720 with a disabled action focused
- **THEN** committed values, disabled reason, controls, and close path remain readable and operable without overlap

#### Scenario: No service surface is mounted while its drawer is closed
- **WHEN** every reference drawer is closed in exploration or combat
- **THEN** no shop, quest-board, lore, or inventory surface exists in the DOM or tab order and no fabricated row renders
