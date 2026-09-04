# Delta spec: webclient-service-menus (webclient-align-06-quest-tracking-contract)

## MODIFIED Requirements

### Requirement: The services panel is an exact read-only exploration-mode panel
The production presentation registry SHALL register `services` schema version 4. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `host`, `player`, `guild`, `shop`, `inventory`, and `pagination`; `available` SHALL be true and `kind` SHALL be `services`. `schema_version` SHALL be integer 4. `host` SHALL be null or contain exactly `identity` (1..64 opaque ASCII characters) and `display_name` (1..256 Unicode code points) and SHALL be display-only reconciliation metadata that never enters a `ui_action` payload. `pagination` SHALL contain exactly `board_total`, `quest_total`, `stock_total`, `sellable_total`, and `inventory_total`, each a non-negative JavaScript-safe integer no greater than its surface's row ceiling and equal to the number of rows shipped in that surface (zero when the surface is null). `player` SHALL contain exactly `wallet`, `guild_registered`, `guild_rank`, `guild_merit`, `next_rank`, and `next_threshold`: wallet SHALL be a non-negative JavaScript-safe integer, `guild_registered` a boolean, `guild_rank` null or a 1..8-character rank key, `guild_merit` a non-negative safe integer, and `next_rank`/`next_threshold` null when the actor holds the top rank, otherwise the next rank key and its positive catalog merit threshold. `guild`, `shop`, and `inventory` SHALL each be null or an exact section object. In exploration mode all sections SHALL retain their ordinary availability. In active combat `host`, `guild`, and `shop` SHALL be null, their pagination totals SHALL be zero, and canonical `player` plus `inventory` SHALL remain available so personal item actions expose no remote service. The presenter SHALL strictly read canonical records and registries through the no-mutation service read model, SHALL emit no live object reference and no filesystem path, and SHALL NOT mutate registration, quests, wallet, inventory, equipment, merchant stock, rank, merit, traits, location, combat, or world time. The whole panel SHALL use the registered common unavailable form only when a global prerequisite fails — the actor is creation-pending or the actor/player/inventory summary cannot be read without mutation; a failure confined to one exploration surface SHALL make only that surface unavailable with a stable reason while the other surfaces and narrative stay healthy.

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

### Requirement: The guild surface covers registration, board, quest log, and rank examination
The `guild` section SHALL contain exactly `registration`, `board`, `quests`, and `rank` and SHALL be present only when exactly one local `GuildStaff` host resolves. `registration` SHALL contain exactly `registered` (boolean) and `register` (an action descriptor); `register` SHALL be enabled only for an unregistered actor with one local `GuildStaff` host and otherwise carry a stable disabled reason. `board` SHALL be a bounded list of at most 12 offer rows in the deterministic rank/key order returned by the board API, each containing exactly `definition_key`, `display_name`, `objective_summary`, `reward_summary`, `rank`, and `accept`; each `objective_summary`/`reward_summary` SHALL be server-rendered from immutable quest values, and `accept` SHALL be enabled only while that offer is board-eligible and the actor has no active record for it. `quests` SHALL be a bounded list of at most 12 quest-log rows in deterministic record order, each containing exactly `quest_id`, `definition_key`, `display_name`, `state`, `stage_index`, `stage_progress`, `objective_summary`, `deadline_line`, `detail`, `abandon`, `turnin`, and `tracked`; `state` SHALL be one of `in_progress`, `completed`, or `failed`; `tracked` SHALL be a boolean equal to the record's committed tracking state; `detail` SHALL be the server-rendered full quest detail; `abandon` SHALL be enabled only for an `in_progress` record with one local `GuildStaff` host; and `turnin` SHALL be enabled only for a `completed` record with one local `GuildStaff` host and the quest ID absent from the actor's reward claims. `rank` SHALL be present only when exactly one local `GuildExaminer` host resolves and SHALL contain exactly `rank`, `merit`, `next_rank`, `next_threshold`, `eligible`, and `exam_start`: `exam_start` SHALL be enabled only when the actor is registered, a local `GuildExaminer` host exists, an exact next rank exists, true merit meets its threshold, and no active combat or examination exists, and its action payload SHALL carry exactly the next-rank key.

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
- **THEN** `rank` reports the exact next rank E and enables `exam_start` with payload `{target_rank: "E"}`, and no other rank can be selected

#### Scenario: Guild surface stays read-only
- **WHEN** the guild section is built for an actor with registration, an active quest, and eligible exam state
- **THEN** registration, quest log, merit, rank, wallet, and exam records are byte-for-byte unchanged

### Requirement: Service actions are exact, allowlisted, and server-authoritative
The production action registry SHALL retain every existing combat, service, creation, exploration, and options action and SHALL add exactly `inventory.use`, `inventory.toggle_equip`, and `guild.quest_track`. The service action set SHALL therefore contain `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.quest_track`, `guild.exam_start`, `shop.buy`, `shop.sell`, `inventory.use`, and `inventory.toggle_equip`. `guild.register` SHALL accept exactly an empty payload and retain its current idempotency. Guild quest and exam actions SHALL retain their exact bounded identifiers; `guild.quest_track` SHALL accept exactly `quest_id` (the shared bounded quest identifier) and boolean `tracked`; `shop.buy` and `shop.sell` SHALL retain exactly bounded `item_key` and integer `quantity`. Each inventory action SHALL accept exactly `item_key` as a 1..64-character non-empty string. Every adapter SHALL obtain the actor from the authenticated session, re-resolve every local host and referenced quest, definition, item, rank, mechanic, and current condition, and invoke only its listed public deterministic API. The `guild.quest_track` adapter SHALL NOT require a local `GuildStaff` host and SHALL invoke only the quest lifecycle tracking operation, surfacing its transition error (including the tracking-cap refusal) as a bounded rejected message without mutation. No inventory payload SHALL accept actor, host, branch, session, effect, consumable, quantity, target, slot, HP, combat, price, stock, or wallet fields. No adapter SHALL assign `.db`, traits, registration, rank, merit, quest log, wallet, inventory, equipment, merchant stock, location, combat, or clock state directly. No action SHALL route an action ID or payload through the text command parser.

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
