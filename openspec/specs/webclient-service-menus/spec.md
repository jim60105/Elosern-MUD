## Purpose

The read-only version-1 `services` panel payload (host resolution, player summary, guild/quest/shop/inventory surfaces, pagination), the seven exact allowlisted service action adapters, the no-mutation service read model, the keyboard service dock with bounded quantity forms and an abandon confirmation, and the Node/browser acceptance boundary.

## Requirements


### Requirement: The services panel is an exact read-only exploration-mode panel
The production presentation registry SHALL register `services` schema version 1. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `host`, `player`, `guild`, `shop`, `inventory`, and `pagination`; `available` SHALL be true and `kind` SHALL be `services`. `schema_version` SHALL be integer 1. `host` SHALL be null or contain exactly `identity` (1..64 opaque ASCII characters) and `display_name` (1..256 Unicode code points) and SHALL be display-only reconciliation metadata that never enters a `ui_action` payload. `pagination` SHALL contain exactly `board_total`, `quest_total`, `stock_total`, `sellable_total`, and `inventory_total`, each a non-negative JavaScript-safe integer no greater than its surface's row ceiling and equal to the number of rows shipped in that surface (zero when the surface is null). `player` SHALL contain exactly `wallet`, `guild_registered`, `guild_rank`, `guild_merit`, `next_rank`, and `next_threshold`: wallet SHALL be a non-negative JavaScript-safe integer, `guild_registered` a boolean, `guild_rank` null or a 1..8-character rank key, `guild_merit` a non-negative safe integer, and `next_rank`/`next_threshold` null when the actor holds the top rank, otherwise the next rank key and its positive catalog merit threshold. `guild`, `shop`, and `inventory` SHALL each be null or an exact section object. The presenter SHALL strictly read canonical records and registries through the no-mutation service read model, SHALL emit no live object reference and no filesystem path, and SHALL NOT mutate registration, quests, wallet, inventory, merchant stock, rank, merit, traits, location, or world time. The whole panel SHALL use the registered common unavailable form only when a global prerequisite fails — the puppet is not in exploration mode or the actor/player summary cannot be read without mutation; a failure confined to one surface SHALL make only that surface unavailable with a stable reason while the other surfaces and narrative stay healthy.

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

### Requirement: Service presentation resolves hosts per service class and a stable player summary
Each service surface SHALL resolve its own local host independently from the actor's current room using the same deterministic rule as commands: `guild` and `rank` SHALL resolve a `GuildStaff` and `GuildExaminer` host respectively, and `shop` SHALL resolve a `Merchant` host, each through `resolve_local_service_host`; zero or multiple hosts of the host class a surface requires SHALL make that surface unavailable rather than letting the browser choose a remote or ambiguous host. Different host classes present in the same room SHALL NOT create cross-class ambiguity, and the co-location of `GuildStaff` with `GuildExaminer` SHALL make both the guild and rank surfaces available. The top-level `host` SHALL be the display-only reconciliation identity of the resolved single local `GuildStaff` host when exactly one exists, else the resolved single local `Merchant` host when exactly one exists, else null; it SHALL NOT be the availability authority for any surface and SHALL NEVER be submitted in an action payload. The `player` summary SHALL derive from canonical wallet, parsed guild registration, canonical `guild_rank`, the true `guild_merit` counter, and the catalog's merit thresholds; it SHALL NEVER read `disguised_stats` or registration snapshot values for wallet, rank, merit, or eligibility.

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

### Requirement: The guild surface covers registration, board, quest log, and rank examination
The `guild` section SHALL contain exactly `registration`, `board`, `quests`, and `rank` and SHALL be present only when exactly one local `GuildStaff` host resolves. `registration` SHALL contain exactly `registered` (boolean) and `register` (an action descriptor); `register` SHALL be enabled only for an unregistered actor with one local `GuildStaff` host and otherwise carry a stable disabled reason. `board` SHALL be a bounded list of at most 12 offer rows in the deterministic rank/key order returned by the board API, each containing exactly `definition_key`, `display_name`, `objective_summary`, `reward_summary`, `rank`, and `accept`; each `objective_summary`/`reward_summary` SHALL be server-rendered from immutable quest values, and `accept` SHALL be enabled only while that offer is board-eligible and the actor has no active record for it. `quests` SHALL be a bounded list of at most 12 quest-log rows in deterministic record order, each containing exactly `quest_id`, `definition_key`, `display_name`, `state`, `stage_index`, `stage_progress`, `objective_summary`, `deadline_line`, `detail`, `abandon`, and `turnin`; `state` SHALL be one of `in_progress`, `completed`, or `failed`; `detail` SHALL be the server-rendered full quest detail; `abandon` SHALL be enabled only for an `in_progress` record with one local `GuildStaff` host; and `turnin` SHALL be enabled only for a `completed` record with one local `GuildStaff` host and the quest ID absent from the actor's reward claims. `rank` SHALL be present only when exactly one local `GuildExaminer` host resolves and SHALL contain exactly `rank`, `merit`, `next_rank`, `next_threshold`, `eligible`, and `exam_start`: `exam_start` SHALL be enabled only when the actor is registered, a local `GuildExaminer` host exists, an exact next rank exists, true merit meets its threshold, and no active combat or examination exists, and its action payload SHALL carry exactly the next-rank key.

#### Scenario: Unregistered player can register
- **WHEN** an unregistered actor stands in the guild hall
- **THEN** `registration.register` is enabled with the `guild.register` action and `board` contains no offers

#### Scenario: F member sees only rank-eligible board offers
- **WHEN** a registered F member stands in a hall whose board contains an F offer and an E offer
- **THEN** `board` contains only the F offer row and its `accept` carries the offer's definition key

#### Scenario: Quest log rows carry full server-rendered detail
- **WHEN** the actor has one active `introductory_hunt` record
- **THEN** the row names the quest, reports `in_progress`, carries stage/progress, a deadline line when set, and a `detail` string identical to the deterministic detail renderer, with `abandon` enabled and `turnin` null-disabled

#### Scenario: Completed quest offers exactly-once turn-in preview
- **WHEN** the actor has a completed, unclaimed record at the local branch
- **THEN** the row's `turnin` is enabled with the `guild.quest_turnin` action and the quest ID, and after the claim is recorded the same row's `turnin` becomes disabled with a stable already-claimed reason

#### Scenario: Exam eligibility shows the exact next rank only
- **WHEN** a registered F member has merit at or above the E threshold and no active session
- **THEN** `rank` reports the exact next rank E and enables `exam_start` with payload `{target_rank: "E"}`, and no other rank can be selected

#### Scenario: Guild surface stays read-only
- **WHEN** the guild section is built for an actor with registration, an active quest, and eligible exam state
- **THEN** registration, quest log, merit, rank, wallet, and exam records are byte-for-byte unchanged

### Requirement: The shop surface covers stock, quantity, buy, sell, and sellable inventory
The `shop` section SHALL contain exactly `open`, `stock`, and `sellable` and SHALL be present only when exactly one local `Merchant` host resolves. `open` SHALL be the boolean derived from the world-clock opening computation with no redundant flag. `stock` SHALL be a bounded list of at most 12 rows in catalog offer order, each containing exactly `item_key`, `display_name`, `buy_copper`, `sell_copper`, `stock`, `max_stock`, and `buy`; every copper value SHALL be the exact integer catalog value. `buy` SHALL be enabled only when the shop is open, the item is known and offered, stock is positive, and the actor can afford at least one unit; otherwise it SHALL carry a stable disabled reason. `sellable` SHALL be a bounded list of at most 12 rows in deterministic order, each containing exactly `item_key`, `display_name`, `sell_copper`, `held`, and `sell`; `sell` SHALL be enabled only when the shop is open, the item is sellable and offered, the actor holds at least one, and the merchant's stock cap is not already at maximum. `inventory` SHALL be present in exploration mode and SHALL contain exactly `rows` and `wallet`, with at most 32 rows each containing exactly `item_key`, `display_name`, `held`, and `equipped`, preserving repeated item keys and showing aggregate quantities as presentation only. No row SHALL carry a use, consume, or equip action in this schema version.

#### Scenario: Open shop lists exact integer stock and prices
- **WHEN** the merchant is open during opening hours
- **THEN** `open` is true and each stock row reports the exact catalog `buy_copper`/`sell_copper`, live `stock`, and `max_stock` with no float and no local path

#### Scenario: Closed shop shows disabled purchases
- **WHEN** the merchant is outside opening hours
- **THEN** `open` is false and every `buy`/`sell` descriptor is disabled with a stable closed reason while stock rows still render

#### Scenario: Quantity descriptor advertises a bounded maximum
- **WHEN** a buy row has stock 3
- **THEN** its `buy` action carries `quantity` with minimum 1 and a server-advertised maximum no greater than 3, and no client value can authorize a larger purchase

#### Scenario: Inventory never offers use or equip
- **WHEN** the actor holds repeated `healing_potion` keys
- **THEN** the inventory rows aggregate the count as presentation, show equipped state from canonical equipment, and contain no use, consume, or equip action descriptor

### Requirement: Service actions are exact, allowlisted, and server-authoritative
The production action registry SHALL register exactly `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.exam_start`, `shop.buy`, and `shop.sell` for this delivery unit in addition to the three combat adapters and no unrelated gameplay adapter. `guild.register` SHALL accept exactly an empty payload and SHALL be idempotent: submitting it for an already-registered actor SHALL be a success that returns the canonical record without replacing its branch, tick, or displayed-stat snapshot. `guild.quest_accept` SHALL accept exactly `definition_key` (a 1..64-character non-empty string). `guild.quest_abandon` and `guild.quest_turnin` SHALL each accept exactly `quest_id` (a 1..64-character non-empty string). `guild.exam_start` SHALL accept exactly `target_rank` (a 1..8-character rank key that SHALL equal the exact next rank the server derives from canonical `guild_rank`). `shop.buy` and `shop.sell` SHALL each accept exactly `item_key` (a 1..64-character non-empty string) and `quantity` (an integer in 1..1000 excluding booleans). Every adapter SHALL obtain the actor from the authenticated session, re-resolve the local `GuildStaff`, `GuildExaminer`, or `Merchant` host using the same local-host rule as commands, re-resolve every referenced quest, definition, item, and rank against current canonical state, and invoke only the public deterministic APIs `register_adventurer`, `accept_guild_offer`, `abandon_guild_quest`, `turn_in_quest`, `start_guild_exam(requested_by="webclient")`, `economy.buy`, or `economy.sell`. An adapter SHALL NOT accept an actor, host, branch, session, price, stock, or wallet field and SHALL NOT assign `.db`, traits, registration, rank, merit, quest log, wallet, inventory, merchant stock, or location directly. No action SHALL route an action ID or payload through the text command parser.

#### Scenario: Registration reaches the deterministic API once
- **WHEN** an unregistered actor submits an empty `guild.register` at the local guild hall
- **THEN** the adapter resolves the local staff host and calls `register_adventurer`, and the snapshot thereafter reports rank F with the recorded branch

#### Scenario: Repeated registration is idempotent
- **WHEN** a registered actor submits an empty `guild.register` again after a state change between render and submit
- **THEN** the adapter returns the original record without replacing branch, tick, or snapshot, reports success, and refreshes the canonical services/status panels

#### Scenario: Quest accept is the board-gated acceptance
- **WHEN** a registered member submits `guild.quest_accept` with a visible definition key
- **THEN** the adapter revalidates board eligibility and delegates acceptance to the quest lifecycle, creating exactly the record `accept_quest` would create

#### Scenario: Exam start cannot choose an examiner or rank
- **WHEN** a client submits `guild.exam_start` with a rank other than the derived next rank, or includes a host or examiner identity field
- **THEN** the adapter rejects before `start_guild_exam`, no opponent, record, or session is created, and only the exact next-rank payload is ever accepted

#### Scenario: A host field can never be supplied
- **WHEN** any service action payload contains a host-like, branch-like, session-like, or actor-like unknown field
- **THEN** exact-schema validation rejects the request without invoking the adapter

#### Scenario: Buy and sell submit only item and quantity
- **WHEN** a client submits `shop.buy` with `item_key` and `quantity` only
- **THEN** the adapter re-resolves the local merchant, rechecks open state, price, funds, stock, and cap, and calls `economy.buy`, returning the committed copper result

### Requirement: Service actions reject stale, duplicate, and tampered input without mutation
Every service action SHALL pass the existing dispatcher's epoch, base revision, in-flight, and request-ID checks before adapter invocation; a `presentation_epoch` or `base_revision` that does not equal the newest values issued for the live session SHALL return the dispatcher's `stale` outcome with a fresh full snapshot and SHALL invoke no adapter. A duplicate live request ID SHALL return its cached result without re-executing. After those checks, commit-time domain revalidation is authoritative: a price, stock, rank, quest, or claim that changed between render and commit is handled by the deterministic API against current canonical state, and the returned snapshot displays the committed result; such a change is not a stale condition and SHALL NOT double-apply a reward, trade, or rank. A tampered `quest_id`, `definition_key`, `item_key`, or `target_rank` that fails current domain revalidation SHALL be rejected with a stable code and Traditional Chinese message, and no wallet, inventory, stock, quest, merit, rank, claim, or exam surface SHALL change. A host that disappeared or became ambiguous between render and submit SHALL close the action controls and return a current local-service snapshot without any mutation.

#### Scenario: Stale revision cannot pay a reward twice
- **WHEN** the actor's turn-in row was rendered at revision N and an older-revision `guild.quest_turnin` is submitted after a newer revision is active
- **THEN** the dispatcher returns outcome `stale`, calls no adapter, and emits a full snapshot without appending a reward claim

#### Scenario: Price change between render and commit is not stale
- **WHEN** a `shop.buy` passes the current epoch/revision checks but the deterministic API rechecks a changed price or stock at commit
- **THEN** the trade settles against current canonical state, no float or double-application occurs, and the refreshed snapshot reports the committed wallet and stock

#### Scenario: Duplicate buy request executes once
- **WHEN** the same live request ID for `shop.buy` is delivered twice
- **THEN** `economy.buy` runs once, wallet and stock change once, and the duplicate receives the cached first result

#### Scenario: Unknown quest cannot be turned in
- **WHEN** a tampered `quest_id` is submitted for `guild.quest_turnin`
- **THEN** the adapter rejects before the reward transaction and wallet, inventory, merit, quest log, and claims remain unchanged

#### Scenario: Removed host closes without mutation
- **WHEN** a merchant host disappears from the actor's room between render and a `shop.buy` submit
- **THEN** the adapter rejects with a stable reason, no trade surface changes, and the returned snapshot reports the current local-service state

### Requirement: Service action completion updates canonical panels and preserves narrative
After an admitted service action settles, the server SHALL emit every returned message through the ordinary escaped text output path and SHALL publish canonical panel replacements at one newer revision before sending the matching safe `ui_action_result`. `guild.register`, `guild.quest_turnin`, `shop.buy`, and `shop.sell` SHALL publish `status` and `services`; `guild.quest_accept` and `guild.quest_abandon` SHALL publish `services`; `guild.exam_start` SHALL publish `status`, `services`, and `context_actions` together with the mode change to `combat`, and the browser SHALL then render the ordinary combat menu. Every success or domain-rejection message SHALL be emitted as text and never parsed by the browser to update panel state.

#### Scenario: Turn-in updates wallet and merit panels together
- **WHEN** a completed quest is turned in successfully
- **THEN** narrative carries the reward message, `status` and `services` reflect the new wallet, merit, claim, and quest-log state at one newer revision, and the dock unlocks only after that revision is accepted

#### Scenario: Exam start hands off to the combat menu
- **WHEN** `guild.exam_start` succeeds for the exact next rank
- **THEN** the update carries mode `combat` and a `context_actions` combat payload, `services` becomes unavailable, and no additional service mutation is admitted in that mode

#### Scenario: Mode change tears down the exploration dock and its service submenus atomically
- **WHEN** the browser adopts a valid update or snapshot whose mode is `combat`
- **THEN** the exploration action dock — including the service submenus re-homed under its Interact/Quests/Inventory roots — synchronously unloads, unregisters its keyboard handlers, discards any local quantity, selection, confirmation, and speech state, and only the combat dock owns action-dock focus

#### Scenario: Rejected purchase emits no fabricated prose
- **WHEN** the economy API rejects for insufficient funds
- **THEN** no trade message is fabricated beyond the stable safe rejection, wallet and stock remain unchanged, and refreshed `services` state permits another legal choice

### Requirement: Reconnect rebuilds services without replaying intent
WebSocket loss SHALL preserve the last rendered services view under the foundation offline overlay and lock every service mutation. After reconnect, the first valid new-epoch snapshot SHALL rebuild host, player summary, guild, shop, and inventory sections from canonical persistence even when its revision is lower than the retired epoch. The browser SHALL discard old-epoch packets, SHALL NOT restore an unsubmitted quantity or selection as authority, and SHALL NOT resubmit an uncertain prior mutation. An action submitted but unconfirmed before transport loss SHALL be treated as unconfirmed with the approved notice, never retried.

#### Scenario: Reconnect restores a shop view
- **WHEN** the transport disconnects inside the shop quantity form and reconnects without another game action
- **THEN** the new snapshot renders the current stock, wallet, and inventory at the services root, discards the unsubmitted quantity, and sends no automatic replacement purchase

#### Scenario: Disconnect after submit never retries
- **WHEN** transport closes after sending `guild.quest_turnin` but before its result is observed
- **THEN** reconnect synchronizes canonical quest, wallet, merit, and claims state, shows the uncertain-result notice, and sends no automatic replacement turn-in

### Requirement: Service browser acceptance is keyboard-only, confirmation-protected, and desktop-bounded
The managed localhost Playwright suite SHALL exercise, using keyboard controls only at 1440x900 and 1280x720: registration success and idempotent re-registration, board list to detail to accept, active-quest abandon behind an explicit confirmation screen, completed-quest turn-in, merit/exam eligibility and the transition into the combat menu with the service dock torn down, shop open/closed status at fixed world times, buy and sell quantity validation with exact copper and stock outcomes, stale and duplicate submission behavior, repeated-inventory display, and reconnect retention. The service submenus SHALL be reached from the exploration dock's Interact/Quests/Inventory roots rather than a standalone Services root; the `services` panel payload and its seven `guild.*`/`shop.*` adapters are unchanged. Tests SHALL use deterministic fixtures, SHALL make no remote, LLM, or image-generation request, and SHALL assert that no use/equip control and no remote or ambiguous host control is rendered.

#### Scenario: Guild board journey completes in Chromium
- **WHEN** a seeded registered member uses arrows and Enter to open the exploration dock, open Quests, open Guild, open Board, and accept an eligible offer
- **THEN** the flow submits exactly `guild.quest_accept` once with the expected definition key and the refreshed quest log appears without typed input

#### Scenario: Abandon requires confirmation
- **WHEN** the player focuses an active quest's abandon action but has not confirmed
- **THEN** no mutation is sent and Escape returns exactly one menu level without abandoning

#### Scenario: Minimum viewport retains service essentials
- **WHEN** the services panel renders at 1280x720 with a disabled buy row focused
- **THEN** the player can read narrative, wallet, stock, the disabled reason, and the service controls without overlap preventing operation
