## Purpose

The read-only version-2 `services` panel payload (host resolution, player summary, guild/quest/shop/inventory surfaces, pagination), the seven exact allowlisted service action adapters, the no-mutation service read model, service surfaces rendering in frameless reference drawers with bounded quantity entries and an abandon confirmation, and the Node/browser acceptance boundary.

## Requirements

### Requirement: The services panel is an exact read-only exploration-mode panel

The production presentation registry SHALL register `services` schema version 5. Its available payload SHALL
contain exactly `schema_version`, `available`, `kind`, `host`, `player`, `guild`, `shop`, `inventory`, and
`pagination`; `available` SHALL be true, `kind` SHALL be `services`, and `schema_version` SHALL be integer 5.
The presenter SHALL strictly read canonical records and registries through the no-mutation service read model.

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


#### Scenario: Below merit request stays enabled
- **WHEN** a registered next-rank member below true merit threshold stands at a functioning guild counter and the qualified host is absent
- **THEN** merit_qualified is false, exam_request is enabled and dispatch returns exam_schedule without mutation

#### Scenario: Host metadata shape is bounded and display-only
- **WHEN** the `host` field is present on an available payload
- **THEN** it contains exactly `identity` (1..64 opaque ASCII characters) and `display_name` (1..256 Unicode code
  points), and host metadata is display-only reconciliation metadata that never enters a `ui_action` payload

#### Scenario: Pagination totals are exact safe integers of shipped rows
- **WHEN** any surface ships rows or is null
- **THEN** `pagination` contains exactly `board_total`, `quest_total`, `stock_total`, `sellable_total`, and
  `inventory_total`, each a non-negative JavaScript-safe integer no greater than its surface's row ceiling and
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
- **THEN** `guild`, `shop`, and `inventory` are each null or an exact section object, and all sections retain
  their ordinary availability

#### Scenario: Combat keeps personal data with no remote service
- **WHEN** the actor is in active combat
- **THEN** canonical `player` plus `inventory` remain available so personal item actions expose no remote service

#### Scenario: Presenter output leaks no internals
- **WHEN** the presenter serializes any services payload
- **THEN** it emits no live object reference and no filesystem path, and does not mutate registration, quests,
  wallet, inventory, equipment, merchant stock, rank, merit, traits, location, combat, or world time

#### Scenario: Unreadable summary triggers the common unavailable form
- **WHEN** the actor/player/inventory summary cannot be read without mutation
- **THEN** the whole panel uses the registered common unavailable form, which is reserved for such global
  prerequisite failures

### Requirement: Service presentation resolves hosts per service class and a stable player summary

Each service surface SHALL resolve its own local host independently from the actor's current room through
`resolve_local_service_host`, under the same deterministic rule as commands: `guild` SHALL resolve a `GuildStaff`
host, `rank` the hall's `GuildExaminer` exam counter (never the qualified persistent host), and `shop` a
`Merchant` host; zero or multiple hosts of a surface's required class SHALL make that surface unavailable.

#### Scenario: Guild hall resolves one guild host and its examiner
- **WHEN** the actor stands in a room containing exactly one `GuildStaff` host that also carries `GuildExaminer`
- **THEN** `host` names that host, `guild` and `rank` surfaces are present, and `shop` is null

#### Scenario: General store resolves one merchant
- **WHEN** the actor stands in a room containing exactly one `Merchant` host and no `GuildStaff`
- **THEN** `host` names that merchant, `shop` is present, and `guild` is null

#### Scenario: Co-located different service classes stay independent
- **WHEN** the actor's room contains exactly one `GuildStaff` and exactly one `Merchant`
- **THEN** both the guild and shop surfaces render their own host data and neither availability is affected by the other class

#### Scenario: Ambiguous hosts close only the affected surface
- **WHEN** the actor's room contains two `GuildStaff` hosts and one `Merchant`
- **THEN** the guild surface is unavailable with a stable reason while the shop surface remains available, and no adapter can address either guild host

#### Scenario: Unregistered summary is honest
- **WHEN** the actor has no `guild_registration`
- **THEN** `player` reports `guild_registered` false, `guild_rank` null, and the board section renders no offers while the registration surface offers the register action

#### Scenario: Disguised elf does not distort the summary
- **WHEN** an elf with true rank F and true merit 0 holds a disguise
- **THEN** `player` reports rank F, merit 0, and no displayed-stat value, and no surface derives eligibility from the disguise


#### Scenario: Below merit request stays enabled
- **WHEN** a registered next-rank member below true merit threshold stands at a functioning guild counter and the qualified host is absent
- **THEN** merit_qualified is false, exam_request is enabled and dispatch returns exam_schedule without mutation

#### Scenario: Different host classes never create cross-class ambiguity
- **WHEN** different host classes are present in the same room
- **THEN** they create no cross-class ambiguity, and the co-location of `GuildStaff` with `GuildExaminer` makes
  both the guild and rank surfaces available

#### Scenario: Top-level host follows the guild-then-merchant preference
- **WHEN** the top-level `host` field is computed
- **THEN** it is the display-only reconciliation identity of the resolved single local `GuildStaff` host when
  exactly one exists, else the resolved single local `Merchant` host when exactly one exists, else null

#### Scenario: Host is metadata, never authority or payload field
- **WHEN** any surface availability is computed or any action is dispatched
- **THEN** the top-level `host` is not the availability authority for any surface and is never submitted in an
  action payload

#### Scenario: Player summary derives only from canonical sources
- **WHEN** the `player` summary is built
- **THEN** it derives from canonical wallet, parsed guild registration, canonical `guild_rank`, the true
  `guild_merit` counter, and the catalog's merit thresholds, and never reads `disguised_stats` or registration
  snapshot values for wallet, rank, merit, or eligibility

### Requirement: The guild surface covers registration, board, quest log, and rank examination

The `guild` section SHALL contain exactly `registration`, `board`, `quests`, and `rank` and SHALL be present only
when exactly one local `GuildStaff` host resolves. `board` and `quests` SHALL be bounded lists of at most 12
deterministic rows with server-rendered text; `rank` SHALL report true-merit `merit_qualified` separately from its
`guild.exam_request` descriptor, whose enabledness never depends on merit or host attendance.

#### Scenario: Unregistered player can register
- **WHEN** an unregistered actor stands in the guild hall
- **THEN** `registration.register` is enabled with the `guild.register` action and `board` contains no offers

#### Scenario: F member sees only rank-eligible board offers
- **WHEN** a registered F member stands in a hall whose board contains an F offer and an E offer
- **THEN** `board` contains only the F offer row and its `accept` carries the offer's definition key

#### Scenario: Quest log rows carry full server-rendered detail
- **WHEN** the actor has one active `introductory_hunt` record
- **THEN** the row names the quest, reports `in_progress`, carries stage/progress, a deadline line when set, and a `detail` string identical to the deterministic detail renderer, with `abandon` enabled and `turnin` null-disabled

#### Scenario: Quest log rows disclose tracking truth
- **WHEN** the actor tracks one active quest and leaves another active
- **THEN** the tracked row carries `tracked` true and the untracked row carries `tracked` false, and no other field differs from the untracked baseline

#### Scenario: Completed quest offers exactly-once turn-in preview
- **WHEN** the actor has a completed, unclaimed record at the local branch
- **THEN** the row's `turnin` is enabled with the `guild.quest_turnin` action and the quest ID, and after the claim is recorded the same row's `turnin` becomes disabled with a stable already-claimed reason

#### Scenario: Exam eligibility shows the exact next rank only
- **WHEN** a registered F member has merit at or above the E threshold and no active session
- **THEN** `rank` reports the exact next rank E and enables `exam_request` with payload `{target_rank: "E"}`, and no other rank can be selected

#### Scenario: Guild surface stays read-only
- **WHEN** the guild section is built for an actor with registration, an active quest, and eligible exam state
- **THEN** registration, quest log, merit, rank, wallet, and exam records are byte-for-byte unchanged


#### Scenario: Below merit request stays enabled
- **WHEN** a registered next-rank member below true merit threshold stands at a functioning guild counter and the qualified host is absent
- **THEN** merit_qualified is false, exam_request is enabled and dispatch returns exam_schedule without mutation

#### Scenario: Registration section shape and enablement gate
- **WHEN** the `registration` section is built
- **THEN** it contains exactly `registered` (boolean) and `register` (an action descriptor), and `register` is
  enabled only for an unregistered actor with one local `GuildStaff` host and otherwise carries a stable disabled
  reason

#### Scenario: Board rows carry their exact fields in board API order
- **WHEN** the `board` list ships
- **THEN** it holds at most 12 offer rows in the deterministic rank/key order returned by the board API, each
  containing exactly `definition_key`, `display_name`, `objective_summary`, `reward_summary`, `rank`, and `accept`

#### Scenario: Board accept gates on eligibility and no active record
- **WHEN** a board offer row's `accept` descriptor is computed
- **THEN** it is enabled only while that offer is board-eligible and the actor has no active record for it

#### Scenario: Quest rows carry their exact fields in record order
- **WHEN** the `quests` list ships
- **THEN** it holds at most 12 quest-log rows in deterministic record order, each containing exactly `quest_id`,
  `definition_key`, `display_name`, `state`, `stage_index`, `stage_progress`, `objective_summary`, `deadline_line`,
  `detail`, `abandon`, and `turnin`; `state` is one of `in_progress`, `completed`, or `failed`, and `detail` is the
  server-rendered full quest detail

#### Scenario: Abandon enables only for an in-progress record at a staff host
- **WHEN** a quest row's `abandon` descriptor is computed
- **THEN** it is enabled only for an `in_progress` record with one local `GuildStaff` host

#### Scenario: Turn-in requires an unclaimed completed record at a staff host
- **WHEN** a quest row's `turnin` descriptor is computed
- **THEN** it is enabled only for a `completed` record with one local `GuildStaff` host and the quest ID absent
  from the actor's reward claims

#### Scenario: Rank section presence and exact fields
- **WHEN** the `rank` section is computed
- **THEN** it is present only when exactly one local examination counter (the `GuildExaminer` counter of the
  hall) resolves, whether or not the qualified persistent host is present, and contains exactly `rank`, `merit`,
  `next_rank`, `next_threshold`, `merit_qualified`, and `exam_request`

#### Scenario: Exam start requires every condition and the next-rank payload
- **WHEN** `exam_request` is computed
- **THEN** it is enabled only when the actor is registered at the counter's branch, an exact next rank exists,
  and the local counter passes its service and schedule gates; merit and host presence never disable it, and its
  action payload carries exactly the next-rank key

#### Scenario: Unregistered and top-rank actors receive stable target reasons
- **WHEN** the actor is unregistered or already holds the top rank
- **THEN** `exam_request` is disabled with the stable `unregistered` or `top_rank` reason and never with a merit
  reason

### Requirement: The shop surface covers stock, quantity, buy, sell, and sellable inventory
The `shop` section SHALL contain exactly `open`, `stock`, and `sellable` and SHALL be present only in exploration
mode when exactly one local `Merchant` host resolves. Copper values SHALL be exact integer catalog values, and
`buy`/`sell` SHALL be enabled only when the shop is open and the trade is legal, otherwise carrying a stable
disabled reason. The `inventory` section SHALL be present in exploration and combat modes with at most 32 rows.

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

#### Scenario: Open flag is the world-clock boolean only
- **WHEN** the `open` field is computed
- **THEN** it is the boolean derived from the world-clock opening computation with no redundant flag

#### Scenario: Stock rows carry exact fields in catalog offer order
- **WHEN** the `stock` list ships
- **THEN** it is a bounded list of at most 12 rows in catalog offer order, each containing exactly `item_key`,
  `display_name`, `buy_copper`, `sell_copper`, `stock`, `max_stock`, and `buy`

#### Scenario: Buy enablement requires open, offer, stock, and affordability
- **WHEN** a stock row's `buy` descriptor is computed
- **THEN** it is enabled only when the shop is open, the item is known and offered, stock is positive, and the
  actor can afford at least one unit

#### Scenario: Sellable rows carry exact fields and sell gates
- **WHEN** the `sellable` list ships
- **THEN** it is a bounded list of at most 12 rows in deterministic order, each containing exactly `item_key`,
  `display_name`, `sell_copper`, `held`, and `sell`, and `sell` is enabled only when the shop is open, the item is
  sellable and offered, the actor holds at least one, and the merchant's stock cap is not already at maximum

#### Scenario: Inventory section carries its exact two fields
- **WHEN** the `inventory` section is built
- **THEN** it contains exactly `rows` and `wallet`

#### Scenario: Inventory rows preserve duplicates and aggregate honestly
- **WHEN** the actor holds repeated copies of one item key
- **THEN** each row contains exactly `item_key`, `display_name`, `held`, `equipped`, `presentation`, and `action`,
  repeated item keys are preserved, and aggregate quantities appear as presentation only

#### Scenario: Presentation is verbatim registry data with bounded shape
- **WHEN** a row's `presentation` is built for a registered item
- **THEN** it contains exactly `kind`, `icon_key`, `rarity`, and `summary`, copied verbatim from the immutable
  item registry; each non-null presentation key is 1..32 lowercase ASCII letters or underscores and `summary` is
  1..240 Unicode code points

#### Scenario: Action descriptors come from side-effect-free preflight
- **WHEN** a row's `action` descriptor is computed
- **THEN** it is null for unknown or inspect-only items; a usable item carries an `inventory.use` descriptor and
  equipment carries an `inventory.toggle_equip` descriptor, each with current `enabled` state and a stable
  disabled reason derived by side-effect-free deterministic preflight

#### Scenario: Inventory rows leak no mechanics or authority fields
- **WHEN** any inventory row ships
- **THEN** it exposes no effect amount, condition threshold, consumable flag, slot choice, actor, target, drag,
  or drop action

### Requirement: Service actions are exact, allowlisted, and server-authoritative

The production action registry SHALL retain every existing combat, service, creation, exploration, and options
action and SHALL add exactly `inventory.use`, `inventory.toggle_equip`, and `guild.quest_track`. The service action
set SHALL therefore contain `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`,
`guild.quest_track`, `guild.exam_request`, `shop.buy`, `shop.sell`, `inventory.use`, and
`inventory.toggle_equip`.

#### Scenario: Existing registration reaches its deterministic API once
- **WHEN** an unregistered actor submits an empty `guild.register` at the local guild hall
- **THEN** the adapter resolves the local staff host and calls `register_adventurer`, and the snapshot thereafter reports rank F with the recorded branch

#### Scenario: Repeated registration is idempotent
- **WHEN** a registered actor submits an empty `guild.register` again after a state change between render and submit
- **THEN** the adapter returns the original record without replacing branch, tick, or snapshot, reports success, and refreshes canonical services/status panels

#### Scenario: Quest accept is board-gated
- **WHEN** a registered member submits `guild.quest_accept` with a visible definition key
- **THEN** the adapter revalidates board eligibility and creates exactly the deterministic quest record

#### Scenario: Quest tracking rides the lifecycle operation anywhere
- **WHEN** a holder submits `guild.quest_track` with a tracked-true payload for one of their active quests while standing outside any guild hall
- **THEN** the adapter calls the tracking operation exactly once, the commit reports success, and the refreshed payload reports the row's `tracked` true

#### Scenario: The tracking cap refusal mutates nothing
- **WHEN** a holder with three tracked active quests submits a fourth `guild.quest_track` tracked-true payload
- **THEN** the dispatch rejects with the lifecycle module's bounded refusal message and every record's tracking state is unchanged

#### Scenario: Exam start cannot choose an examiner or rank
- **WHEN** a client submits a non-next rank or includes a host, examiner, branch, clock or threshold field
- **THEN** exact validation or the coordinator rejects before any exam creation and only the exact next-rank payload is accepted

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


#### Scenario: Below merit request stays enabled
- **WHEN** a registered next-rank member below true merit threshold stands at a functioning guild counter and the qualified host is absent
- **THEN** merit_qualified is false, exam_request is enabled and dispatch returns exam_schedule without mutation

#### Scenario: Payload schemas are exact and bounded
- **WHEN** any service action payload is validated
- **THEN** `guild.register` accepts exactly an empty payload, guild quest and exam actions retain their exact
  bounded identifiers, `guild.quest_track` accepts exactly `quest_id` (the shared bounded quest identifier) and
  boolean `tracked`, and `shop.buy` and `shop.sell` retain exactly bounded `item_key` and integer `quantity`

#### Scenario: Registration idempotency is retained
- **WHEN** registration is submitted again after the actor is already registered
- **THEN** `guild.register` retains its current idempotency

#### Scenario: Inventory actions carry only a bounded item key
- **WHEN** an `inventory.use` or `inventory.toggle_equip` payload is validated
- **THEN** it accepts exactly `item_key` as a 1..64-character non-empty string

#### Scenario: Adapters are session-scoped and re-resolve everything
- **WHEN** any service adapter runs
- **THEN** it obtains the actor from the authenticated session, re-resolves every local host and referenced quest,
  definition, item, rank, mechanic, and current condition, and invokes only its listed public deterministic API

#### Scenario: Inventory payloads reject every authority field
- **WHEN** an inventory payload carries any of actor, host, branch, session, effect, consumable, quantity, target,
  slot, HP, combat, price, stock, or wallet fields
- **THEN** exact-schema validation rejects it

#### Scenario: Adapters never write canonical state directly
- **WHEN** any adapter settles
- **THEN** no adapter assigns `.db`, traits, registration, rank, merit, quest log, wallet, inventory, equipment,
  merchant stock, location, combat, or clock state directly

#### Scenario: Actions never route through the text parser
- **WHEN** any service or inventory action is dispatched
- **THEN** no action routes an action ID or payload through the text command parser

### Requirement: Service actions reject stale, duplicate, and tampered input without mutation
Every service and inventory action SHALL pass the existing dispatcher's epoch, base revision, in-flight, and
request-ID checks before adapter invocation; a `presentation_epoch` or `base_revision` that does not equal the
newest values issued for the live session SHALL return `stale` with a fresh full snapshot and SHALL invoke no
adapter. A duplicate live request ID SHALL return its cached result without re-executing.

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

#### Scenario: Commit-time domain revalidation is authoritative
- **WHEN** a price, stock, rank, quest, claim, HP value, ownership fact, mechanic, or equipment capacity changed
  between render and commit
- **THEN** it is handled against current canonical state and no mutation is double-applied

#### Scenario: Tampered identifiers reject with full-state preservation
- **WHEN** a tampered or no-longer-valid identifier is submitted
- **THEN** it rejects with a stable code and Traditional Chinese message, leaving wallet, inventory, contained
  mirrors, equipment, stock, quests, merit, rank, claims, traits, clock, combat, and every in-process cache
  unchanged

#### Scenario: Vanished or ambiguous hosts close controls without mutation
- **WHEN** a service host disappeared or became ambiguous
- **THEN** its controls close and current local-service state is returned without mutation

### Requirement: Service action completion updates canonical panels and preserves narrative

After an admitted service or inventory action settles, the server SHALL emit every returned message through the
ordinary escaped text output path and SHALL publish canonical panel replacements at one newer revision before
sending the matching safe `ui_action_result`. Existing guild, quest, and shop actions SHALL retain their
established affected-panel sets, and a read-only `exam_schedule` reply SHALL leave mode and canonical state unchanged.

#### Scenario: Turn-in updates wallet and merit panels together
- **WHEN** a completed quest is turned in successfully
- **THEN** narrative carries the reward message and status/services reflect wallet, merit, claim, and quest-log state at one newer revision before unlock

#### Scenario: Item use updates HP and inventory atomically
- **WHEN** `inventory.use` succeeds for a consumable healing potion
- **THEN** narrative reports the safe result and one newer canonical commit shows HP, item count, mode, clock, and combat state from the same settlement

#### Scenario: Exam start hands off while retaining personal inventory
- **WHEN** `guild.exam_request` returns exam_started for the exact next rank
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

#### Scenario: Schedule information does not enter combat
- **WHEN** guild.exam_request returns exam_schedule
- **THEN** exploration mode/services remain available, planned attendance renders and no combat panel/session is created

#### Scenario: Inventory actions publish a full snapshot
- **WHEN** `inventory.use` or `inventory.toggle_equip` settles
- **THEN** a full snapshot is published because the action may change inventory, contained mirrors, status,
  character equipment, clock-derived state, combat/context state, terminal mode, and art

#### Scenario: Combat retains services v3 personal data and its own affordance
- **WHEN** the actor enters combat
- **THEN** exploration service menus and their local forms are unloaded, services v5 retains personal
  player/inventory data, the combat UI owns a separate inventory affordance, and guild and shop actions remain
  absent in combat

#### Scenario: Prose never drives panel state
- **WHEN** any success or domain-rejection message is produced
- **THEN** it is emitted as text and never parsed by the browser to update panel state

### Requirement: Reconnect rebuilds services without replaying intent
WebSocket loss SHALL preserve the last rendered services view under the foundation offline overlay and lock every
service mutation. After reconnect, the first valid new-epoch snapshot SHALL rebuild host, player summary, guild,
shop, and inventory sections from canonical persistence even when its revision is lower than the retired epoch.

#### Scenario: Reconnect restores a shop view
- **WHEN** the transport disconnects while the shop drawer holds a typed but unsubmitted quantity and reconnects without another game action
- **THEN** the shop drawer closes on the transport loss, the unsubmitted quantity is discarded, the new snapshot renders the current stock, wallet, and inventory the next time the shop drawer opens, with every quantity entry back at its row action's own lower bound, and no automatic replacement purchase is sent

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

### Requirement: Service browser acceptance is keyboard-only, confirmation-protected, and desktop-bounded
The managed localhost browser suite SHALL exercise, using keyboard controls at 1451x790 and 2560x1440, all
existing registration, quest, exam, shop, stale/duplicate, repeated-inventory, and reconnect journeys plus
item-use confirmation at both acceptance viewports, full-HP refusal, combat item use through the frameless
combat bag drawer, and direct equipment toggle.

#### Scenario: Guild board journey completes in Chromium
- **WHEN** a seeded registered member opens the quest drawer from the guild clerk's navigate row and uses Tab and Enter to reach and activate an eligible board offer's accept control
- **THEN** exactly one expected quest action is submitted, refreshed quest state appears in the quest book without typed input, and no `dock-menu` or `dock-detail` element renders inside the drawer at any step

#### Scenario: Shop buy journey completes by keyboard in the frameless drawer
- **WHEN** a player opens the shop drawer from the merchant's navigate row, Tabs to the first stock row's quantity entry, types a quantity above the row's advertised maximum and Tabs away, then replaces it with a quantity within bounds, Tabs to the row's buy control, and presses Enter
- **THEN** leaving the entry clamps the out-of-bounds value to the advertised maximum and sends nothing, exactly one `shop.buy` is sent only on the buy control's activation with the row's `item_key` and the corrected quantity, the wallet decreases by exactly that quantity times the row's `buy_copper`, and no `dock-menu` or `dock-detail` element renders inside the shop drawer at any step

#### Scenario: Abandon requires confirmation
- **WHEN** the player focuses or points to active-quest abandon before confirmation
- **THEN** no mutation is sent, cancel or Escape returns without abandoning, and confirm is the only submit path

#### Scenario: Item use requires confirmation at both viewports
- **WHEN** an eligible potion tile is activated by keyboard at 1451x790 or 2560x1440
- **THEN** the accessible confirmation remains fully operable, no request precedes confirm, and focus returns to the tile on cancel

#### Scenario: Equipment and cap behavior are enforced deterministically
- **WHEN** rule and adapter tests drive a singleton replacement and fill the accessory slots to the cap
- **THEN** singleton replacement dispatches once, five accessories can be equipped, a sixth refuses with the committed warning without dispatch, and the showcase renders the capped state

#### Scenario: Minimum viewport retains service essentials
- **WHEN** shop, quest, or bag is open at the 1451x790 reference viewport with a disabled action focused
- **THEN** committed values, disabled reason, controls, and close path remain readable and operable without overlap

#### Scenario: No service surface is mounted while its drawer is closed
- **WHEN** every reference drawer is closed in exploration or combat
- **THEN** no shop, quest-board, lore, or inventory surface exists in the DOM or tab order and no fabricated row renders

#### Scenario: Registry gaps move to rule tests and the showcase
- **WHEN** singleton replacement and the five-accessory cap with its sixth-accessory warning are validated
- **THEN** they are established by deterministic rule and action-adapter tests and rendered in the component
  showcase, because the shipped item registry publishes no accessory items and no second singleton weapon for a
  live browser journey to hold

#### Scenario: Services ride the frameless drawers only
- **WHEN** any acceptance journey opens guild services or the shop
- **THEN** guild services are reached through the frameless quest drawer and the shop through the frameless shop
  drawer, and neither drawer renders a `dock-menu` or `dock-detail` element in any journey

#### Scenario: Journeys assert the dispatch and layout invariants
- **WHEN** any acceptance journey runs
- **THEN** it asserts the single dispatch entry, in-flight locking, mode gating, honest wallet rendering, and
  bounded drawer dimensions

### Requirement: The quest browser exposes the tracking toggle
The quest book SHALL render, on each quest row, a tracking control that dispatches `guild.quest_track` for
that row's `quest_id`: labelled and enabled as tracking for an `in_progress` row whose `tracked` is false, as
untracking for a row whose `tracked` is true, and disabled with a stable reason otherwise.

#### Scenario: Tracking from the browser dispatches once
- **WHEN** the player activates a tracked-false active quest row's tracking control
- **THEN** exactly one `guild.quest_track` request with `{quest_id, tracked: true}` is submitted and the row flips only on the commit

#### Scenario: Completed rows offer no tracking
- **WHEN** a completed quest row renders
- **THEN** its tracking control is disabled with a stable reason and dispatches nothing

#### Scenario: Tracking works with no clerk present
- **WHEN** the player activates the tracking control on a row while standing away from any guild
  staff
- **THEN** exactly one `guild.quest_track` request is submitted and the row flips on the commit

#### Scenario: The control exists with no local service host
- **WHEN** a quest row renders with no local service host present
- **THEN** its tracking control is still present, because tracking is host-independent by contract

#### Scenario: Keyboard and pointer share one dispatch path
- **WHEN** the tracking control is activated by keyboard or pointer
- **THEN** both submit the same action identifier and payload through the same dispatch entry and gates

#### Scenario: Presented tracking state follows commits only
- **WHEN** the tracking control renders and the player activates it
- **THEN** the control renders only from the committed row's `tracked` field, and the row's presented tracking
  state changes only when a commit carrying the new field lands

### Requirement: The quest drawer separates the player's quest book from the guild counter

The quest drawer SHALL render two distinct surfaces. The quest book SHALL render from the
`quest_log` panel and SHALL be present whenever that panel is available, regardless of any local
service host. The guild counter SHALL render from the `services` panel's `guild` section and SHALL be
present only when that section is available. Each surface SHALL be its own component reading its own
panel; neither SHALL read the other's panel for its own content.

#### Scenario: The quest book renders away from any clerk
- **WHEN** a holder with stored records opens the quest drawer in a room with no guild staff
- **THEN** the quest book lists every record and the guild counter is absent, replaced by an explicit
  marker stating the counter needs a clerk

#### Scenario: Both surfaces render in front of a clerk
- **WHEN** the same holder opens the drawer in front of a guild clerk
- **THEN** the quest book lists every record and the guild counter additionally renders registration,
  the board, and rank

#### Scenario: A quest is never listed twice
- **WHEN** the drawer renders with the guild section available and the holder holding active quests
- **THEN** each accepted quest appears exactly once, in the quest book, and the counter lists none of
  them

#### Scenario: Neither surface invents the other's data
- **WHEN** one panel is available and the other is not
- **THEN** the available surface renders normally and the unavailable one renders its honest absent
  marker with no fabricated rows

#### Scenario: The quest book lists every stored record
- **WHEN** the quest book renders
- **THEN** it lists every stored record

#### Scenario: The counter carries counter business and never re-lists quests
- **WHEN** the guild counter renders
- **THEN** it carries registration, the quest board for accepting new quests, and guild rank with the
  promotion examination, and does not re-list the holder's accepted quest records, so no quest is presented
  twice in one drawer

### Requirement: Counter-only quest actions appear on a book row only when the counter offers them

Abandon and turn-in SHALL be rendered on a quest book row only when the `services` panel's guild
section carries a quest row with the same `quest_id` and that action is enabled there. Matching by
`quest_id` SHALL be the only join between the two panels.

#### Scenario: Away from a clerk only tracking is offered
- **WHEN** the quest book renders with no guild section available
- **THEN** each in-progress row offers tracking, and no row offers abandon or turn-in

#### Scenario: At the counter the row gains its counter actions
- **WHEN** the same rows render with the guild section available
- **THEN** an in-progress row additionally offers abandon and a completed unclaimed row additionally
  offers turn-in, each dispatching the counter-side descriptor's exact action and payload

#### Scenario: A disabled counter action is not enabled by the book
- **WHEN** the counter-side turn-in descriptor is disabled with an already-claimed reason
- **THEN** the book row renders that disabled state and its reason rather than an enabled control

#### Scenario: A book row with no counter-side match offers no counter actions
- **WHEN** a private commission's row renders while a guild clerk is present
- **THEN** it offers tracking only, because the guild section carries no row with that quest ID

#### Scenario: Tracking comes from the book row's own descriptor
- **WHEN** a quest book row renders its tracking control
- **THEN** tracking is rendered from the `quest_log` row's own descriptor and is available regardless of any
  host, because `guild.quest_track` is host-independent by contract

#### Scenario: The book never invents counter descriptors
- **WHEN** the book renders a row whose counter side has no enabled abandon or turn-in descriptor
- **THEN** the book synthesizes no abandon or turn-in descriptor and enables none whose counter-side descriptor
  is disabled

### Requirement: The quest book discloses each quest's commissioner and settlement

Each quest book row SHALL render the issuer label from its `quest_log` row and SHALL indicate whether
the quest settles at a counter or on completion, so a player can tell a guild commission from a
private one and knows whether a return trip is required. The row SHALL render the reward line when
the panel carries one and SHALL render nothing in its place when the panel carries `null`.

#### Scenario: A guild quest shows its counter requirement
- **WHEN** a row whose settlement is `counter` renders
- **THEN** it shows the issuing guild label and indicates the reward is claimed at the counter

#### Scenario: A private commission shows automatic settlement
- **WHEN** a row whose settlement is `auto` renders
- **THEN** it shows the commissioner's label and indicates the reward settles on completion

#### Scenario: A missing reward line renders nothing rather than a placeholder
- **WHEN** a row's `reward_line` is `null`
- **THEN** no reward text and no placeholder appears on that row
