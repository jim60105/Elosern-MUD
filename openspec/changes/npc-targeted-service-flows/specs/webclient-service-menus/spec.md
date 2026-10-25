# Spec Delta

## ADDED Requirements

### Requirement: Opening selected-provider services is read-only and correlated
A service opening SHALL identify the selected NPC explicitly and return only its current supported surfaces. Opening SHALL perform no gameplay mutation, retain target correlation, and reject a stale or unauthorized provider without substituting another NPC.

#### Scenario: Two merchants
- **WHEN** a player opens the second of two present merchants
- **THEN** the read shows that merchant and purchases retain its explicit identity

#### Scenario: Late response
- **WHEN** a read response arrives after actor/transport/card/provider changes
- **THEN** the client discards it without reopening stale UI

#### Scenario: Examination reception only
- **WHEN** a selected NPC carries reception without guild staff
- **THEN** the independent rank surface remains discoverable and targets that reception while qualification selects the real adventurer

## MODIFIED Requirements

### Requirement: The services panel is an exact read-only exploration-mode panel

The production presentation registry SHALL register `services` schema version 8. Its available payload SHALL
contain exactly `schema_version`, `available`, `kind`, `host`, `player`, `guild`, `rank`, `shop`, and
`pagination`; `available` SHALL be true, `kind` SHALL be `services`, and `schema_version` SHALL be integer 8.
Personal inventory SHALL NOT appear; the `party_inventory` panel owns it.
The presenter SHALL strictly read canonical records and registries through the no-mutation service read model.

#### Scenario: Exploration snapshot carries the full services panel
- **WHEN** a puppeted WebClient in exploration mode receives a full snapshot
- **THEN** `services` reports the display-only host, wallet/rank/merit summary, and available guild and shop sections, subject to the possession omission below, and pagination totals equal shipped row counts without mutating canonical state

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
- **THEN** the shop surface is unavailable with a stable reason while guild and narrative still render, subject to the possession omission below

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
- **THEN** `guild` and `shop` are each null or an exact section object; while possessed the guild section is null and omitted from the UI, while the shop retains its ordinary availability

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

#### Scenario: Possession omits only guild services in exploration
- **WHEN** a player possesses a companion outside combat beside an available local merchant
- **THEN** `player` is built from the owner, `guild` is null with `board_total` and `quest_total` zero and no guild unavailable reason, `host` names the merchant, and `shop` has the normal viewed-member rows and stock/sellable totals

#### Scenario: Combat suppression takes precedence
- **WHEN** the services read model sees an active combat session, including an actor carrying a possession binding
- **THEN** host, guild and shop remain null with all four pagination totals zero, while the canonical player summary remains available

#### Scenario: Exact selected-provider snapshot
- **WHEN** services.open reads a visible co-present selected NPC
- **THEN** schema 8 reports only that provider's guild/shop/rank sections with their provider_id, leaves unsupported sections null, preserves all existing row limits and eligibility, and writes no state

Service reads SHALL support exact selected-provider views and retain implicit room discovery only for untargeted summaries. A targeted read SHALL use only the selected visible co-present NPC. Player summary, combat suppression, possession rules and per-surface failure isolation SHALL remain unchanged.

#### Scenario: Guild hall resolves one guild host and its examiner
- **WHEN** a targeted NPC carries staff and reception
- **THEN** guild and independent top-level rank use that same selected provider

#### Scenario: General store resolves one merchant
- **WHEN** a merchant is selected while another merchant is nearby
- **THEN** only selected stock/shop identity is returned

#### Scenario: Co-located different service classes stay independent
- **WHEN** a selected NPC lacks a different capability present on another NPC
- **THEN** the missing selected surface remains null without substitution

#### Scenario: Ambiguous hosts close only the affected surface
- **WHEN** an untargeted room summary sees two staff and one merchant
- **THEN** staff discovery remains ambiguous while targeted staff and the merchant resolve independently

#### Scenario: Possession omits only guild services
- **WHEN** a lawful possessed body selects a merchant
- **THEN** merchant/member/purse semantics remain while guild/reception are suppressed

#### Scenario: Player summary derives only from canonical sources
- **WHEN** a disguised registered player opens services
- **THEN** wallet/rank/merit remain canonical true values, independent of displayed disguise

#### Scenario: Host is metadata, never authority or payload field
- **WHEN** top-level host metadata is present
- **THEN** it remains display-only; mutations use their explicit validated npc_id

### Requirement: The guild surface covers registration, board, quest log, and rank examination
The guild section SHALL retain its existing branch/registration/board/quests fields plus required provider_id; rank SHALL be an independent nullable top-level section with its own provider_id, local GuildStaff gate and read-only ownership. Quest rows SHALL accept invalidated and add nullable bounded terminal_reason; invalidated rows SHALL have disabled abandon/turn-in. Private escort abandonment is a separate host-independent quest_log descriptor using the same action ID, and SHALL not make a guild section available without staff.

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
- **THEN** `rank` reports the exact next rank E and enables `exam_request` with payload {npc_id: selected_reception_id, target_rank: "E"}, and no other rank can be selected

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
  containing exactly `definition_key`, `display_name`, `category`, `rank`, `objective_summary`, `objective_note`,
  `deadline_line`, `rationale`, `flavor`, `reward`, and `accept`, and no `reward_summary`

#### Scenario: Board accept gates on eligibility and no active record
- **WHEN** a board offer row's `accept` descriptor is computed
- **THEN** it is enabled only while that offer is board-eligible and the actor has no active record for it

#### Scenario: Quest rows carry their exact fields in record order
- **WHEN** the services quests list ships
- **THEN** the existing bounded ordered row shape, including tracked, adds terminal_reason; state accepts in_progress/completed/failed/invalidated, detail stays canonical, and invalidated reasons are present with no enabled terminal mutation

#### Scenario: Abandon enables only for an in-progress record at a staff host
- **WHEN** a guild-section quest row abandon descriptor is computed
- **THEN** the existing guild counter descriptor retains its active-record/local-staff gate; private escort quest_log descriptors separately require owned active escort state and no staff

#### Scenario: Turn-in requires an unclaimed completed record at a staff host
- **WHEN** a guild quest row turnin descriptor is computed
- **THEN** the existing local staff, completed and unclaimed gates remain, grouped records additionally require selected-winner entitlement, and invalidated records never enable turn-in

#### Scenario: Rank section presence and exact fields
- **WHEN** the `rank` section is computed
- **THEN** it is present only when exactly one local examination counter (the `GuildExamReception` counter of the
  hall) resolves, whether or not the qualified persistent host is present, and contains exactly `rank`, `merit`,
  `next_rank`, `next_threshold`, `merit_qualified`, `exam_request` and provider_id

#### Scenario: Exam start requires every condition and the next-rank payload
- **WHEN** `exam_request` is computed
- **THEN** it is enabled only when the actor is registered at the counter's branch, an exact next rank exists,
  and the local counter passes its service and schedule gates; merit and host presence never disable it, and its
  action payload carries exactly npc_id and the next-rank key

#### Scenario: Unregistered and top-rank actors receive stable target reasons
- **WHEN** the actor is unregistered or already holds the top rank
- **THEN** `exam_request` is disabled with the stable `unregistered` or `top_rank` reason and never with a merit
  reason

#### Scenario: Exact selected-provider snapshot
- **WHEN** services.open reads a visible co-present selected NPC
- **THEN** schema 8 reports only that provider's guild/shop/rank sections with their provider_id, leaves unsupported sections null, preserves all existing row limits and eligibility, and writes no state

### Requirement: The shop surface covers stock, quantity, buy, sell, and sellable inventory
The `shop` section SHALL contain exactly `open`, `member_id`, `stock`, `sellable` and provider_id and SHALL be present only in
exploration mode when the exact selected Merchant resolves (or implicit room discovery resolves one for the untargeted summary). `member_id` SHALL be the viewed member (else the
commander), the default recipient and seller. Prices SHALL be exact integer copper, buy-only on stock rows and
sell-only on sellable rows, and `buy`/`sell` SHALL be enabled only when the shop is open and the trade is legal,
else carrying a stable disabled reason.

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
- **WHEN** a version-8 services payload is built
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

#### Scenario: Exact selected-provider snapshot
- **WHEN** services.open reads a visible co-present selected NPC
- **THEN** schema 8 reports only that provider's guild/shop/rank sections with their provider_id, leaves unsupported sections null, preserves all existing row limits and eligibility, and writes no state

### Requirement: Service actions are exact, allowlisted, and server-authoritative
The existing service action allowlist and exact bounded payloads SHALL remain. Party member references SHALL appear only in the exact member-scoped fields their owning capabilities define, reauthorized by the rules and never replaced by the commander. `guild.quest_abandon` SHALL revalidate the authenticated owner and record; private escort abandonment needs no host, while ordinary guild actions retain their gates. Only services.open is added as a private read; six provider-dependent actions SHALL require npc_id. Other action schemas and member ownership SHALL remain unchanged.

#### Scenario: Existing registration reaches its deterministic API once
- **WHEN** an unregistered actor submits guild.register with exactly npc_id at the local guild hall
- **THEN** the adapter resolves only the explicitly selected staff host and calls `register_adventurer`, and the snapshot thereafter reports rank F with the recorded branch

#### Scenario: Repeated registration is idempotent
- **WHEN** a registered actor submits guild.register with exactly npc_id again after a state change between render and submit
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
- **THEN** exact validation or the coordinator rejects before any exam creation and only npc_id plus the exact next-rank key is accepted

#### Scenario: Existing buy and sell submit only item and quantity
- **WHEN** a client submits `shop.buy` with item key, quantity, recipient_id and npc_id only
- **THEN** the adapter re-resolves and rechecks the local merchant and reauthorizes the recipient before calling deterministic economy settlement

#### Scenario: Inventory use submits only item key
- **WHEN** a client submits `inventory.use` with one item key and the user's `actor_id`
- **THEN** the adapter reauthorizes the member, resolves current mode and delegates to the matching deterministic item-use facade exactly once

#### Scenario: Inventory toggle submits only item key
- **WHEN** a client submits `inventory.toggle_equip` with one item key and the member's `actor_id`
- **THEN** the adapter reauthorizes the member and delegates to deterministic equipment toggle without accepting a client-selected slot

#### Scenario: Authority-like fields can never be supplied
- **WHEN** any service or inventory action contains an actor-like field outside its exact member reference, or a host, session, effect, or slot-like field
- **THEN** exact-schema validation rejects before adapter invocation

#### Scenario: Below merit request stays enabled
- **WHEN** a registered next-rank member below true merit threshold stands at a functioning guild counter and the qualified host is absent
- **THEN** merit_qualified is false, exam_request is enabled and dispatch returns exam_schedule without mutation

#### Scenario: Payload schemas are exact and bounded
- **WHEN** any service action payload is validated
- **THEN** `guild.register` accepts exactly npc_id, guild.quest_accept, guild.quest_turnin and guild.exam_request add required npc_id to their existing bounded identifiers; guild.quest_abandon stays host-independent, `guild.quest_track` accepts exactly `quest_id` (the shared bounded quest identifier) and
  boolean `tracked`, `shop.buy` accepts exactly bounded `item_key`, integer quantity, recipient_id and npc_id, and `shop.sell` accepts exactly bounded `item_key`, integer quantity, seller_id and npc_id

#### Scenario: Registration idempotency is retained
- **WHEN** registration is submitted again after the actor is already registered
- **THEN** `guild.register` retains its current idempotency

#### Scenario: Inventory actions carry only a bounded item key
- **WHEN** an `inventory.use` or `inventory.toggle_equip` payload is validated
- **THEN** its `item_key` is a 1..64-character non-empty string, `inventory.toggle_equip` accepts exactly `actor_id` and `item_key`, and `inventory.use` accepts exactly `actor_id`, `item_key` and an optional `target_key`

#### Scenario: Adapters are session-scoped and re-resolve everything
- **WHEN** a service adapter runs
- **THEN** it resolves the authenticated actor and referenced canonical state, resolves local hosts where the action requires them, and delegates to the existing public owner; private escort abandonment needs no guild staff

#### Scenario: Inventory payloads reject every authority field
- **WHEN** an inventory payload carries any of host, branch, session, effect, consumable, quantity,
  slot, HP, combat, price, stock, or wallet fields, or any member reference other than its exact `actor_id`
- **THEN** exact-schema validation rejects it

#### Scenario: Adapters never write canonical state directly
- **WHEN** any adapter settles
- **THEN** no adapter assigns `.db`, traits, registration, rank, merit, quest log, wallet, inventory, equipment,
  merchant stock, location, combat, or clock state directly

#### Scenario: Actions never route through the text parser
- **WHEN** any service or inventory action is dispatched
- **THEN** no action routes an action ID or payload through the text command parser

#### Scenario: Host-independent escort abandonment uses the existing action
- **WHEN** a holder confirms guild.quest_abandon for an active owned private escort away from a counter
- **THEN** the unchanged quest_id payload invokes compensated abandonment once, releases only that record's sources and refreshes committed quest/party/dialogue state

#### Scenario: Forged terminal or foreign abandonment is refused
- **WHEN** a stale, invalidated, non-owned or foreign quest ID is submitted as a private escort abandonment
- **THEN** current domain authorization refuses without control, membership, quest or reward mutation

#### Scenario: Targeted stale submission never substitutes
- **WHEN** a selected provider leaves, loses capability or fails binding/control after render while another valid provider remains
- **THEN** the action rejects without state changes and never chooses the other provider
