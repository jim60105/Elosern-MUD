## MODIFIED Requirements

### Requirement: The services panel is an exact read-only exploration-mode panel
The production presentation registry SHALL register `services` schema version 5. Its available payload SHALL contain exactly `schema_version`, `available`, `kind`, `host`, `player`, `guild`, `shop`, `inventory`, and `pagination`; `available` SHALL be true and `kind` SHALL be `services`. `schema_version` SHALL be integer 5. `host` SHALL be null or contain exactly `identity` (1..64 opaque ASCII characters) and `display_name` (1..256 Unicode code points) and SHALL be display-only reconciliation metadata that never enters a `ui_action` payload. `pagination` SHALL contain exactly `board_total`, `quest_total`, `stock_total`, `sellable_total`, and `inventory_total`, each a non-negative JavaScript-safe integer no greater than its surface's row ceiling and equal to the number of rows shipped in that surface (zero when the surface is null). `player` SHALL contain exactly `wallet`, `guild_registered`, `guild_rank`, `guild_merit`, `next_rank`, and `next_threshold`: wallet SHALL be a non-negative JavaScript-safe integer, `guild_registered` a boolean, `guild_rank` null or a 1..8-character rank key, `guild_merit` a non-negative safe integer, and `next_rank`/`next_threshold` null when the actor holds the top rank, otherwise the next rank key and its positive catalog merit threshold. `guild`, `shop`, and `inventory` SHALL each be null or an exact section object. In exploration mode all sections SHALL retain their ordinary availability. In active combat `host`, `guild`, and `shop` SHALL be null, their pagination totals SHALL be zero, and canonical `player` plus `inventory` SHALL remain available so personal item actions expose no remote service. The presenter SHALL strictly read canonical records and registries through the no-mutation service read model, SHALL emit no live object reference and no filesystem path, and SHALL NOT mutate registration, quests, wallet, inventory, equipment, merchant stock, rank, merit, traits, location, combat, or world time. The whole panel SHALL use the registered common unavailable form only when a global prerequisite fails — the actor is creation-pending or the actor/player/inventory summary cannot be read without mutation; a failure confined to one exploration surface SHALL make only that surface unavailable with a stable reason while the other surfaces and narrative stay healthy.

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
Guild and shop SHALL retain independent local GuildStaff/Merchant resolution through resolve_local_service_host. Rank requests SHALL resolve canonical branch/target qualification through the functioning local counter or qualified direct-host access; an absent target examiner SHALL NOT make request service unavailable. Several differently qualified local examiners SHALL NOT create generic-host ambiguity. Different host classes present in the same room SHALL NOT create cross-class ambiguity, and the co-location of `GuildStaff` with `GuildExaminer` SHALL make both the guild and rank surfaces available. The top-level `host` SHALL be the display-only reconciliation identity of the resolved single local `GuildStaff` host when exactly one exists, else the resolved single local `Merchant` host when exactly one exists, else null; it SHALL NOT be the availability authority for any surface and SHALL NEVER be submitted in an action payload. The `player` summary SHALL derive from canonical wallet, parsed guild registration, canonical `guild_rank`, the true `guild_merit` counter, and the catalog's merit thresholds; it SHALL NEVER read `disguised_stats` or registration snapshot values for wallet, rank, merit, or eligibility.

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
The `guild` section SHALL contain exactly `registration`, `board`, `quests`, and `rank` and SHALL be present only when exactly one local `GuildStaff` host resolves. `registration` SHALL contain exactly `registered` (boolean) and `register` (an action descriptor); `register` SHALL be enabled only for an unregistered actor with one local `GuildStaff` host and otherwise carry a stable disabled reason. `board` SHALL be a bounded list of at most 12 offer rows in the deterministic rank/key order returned by the board API, each containing exactly `definition_key`, `display_name`, `objective_summary`, `reward_summary`, `rank`, and `accept`; each `objective_summary`/`reward_summary` SHALL be server-rendered from immutable quest values, and `accept` SHALL be enabled only while that offer is board-eligible and the actor has no active record for it. `quests` SHALL be a bounded list of at most 12 quest-log rows in deterministic record order, each containing exactly `quest_id`, `definition_key`, `display_name`, `state`, `stage_index`, `stage_progress`, `objective_summary`, `deadline_line`, `detail`, `abandon`, and `turnin`; `state` SHALL be one of `in_progress`, `completed`, or `failed`; `detail` SHALL be the server-rendered full quest detail; `abandon` SHALL be enabled only for an `in_progress` record with one local `GuildStaff` host; and `turnin` SHALL be enabled only for a `completed` record with one local `GuildStaff` host and the quest ID absent from the actor's reward claims. `rank` SHALL contain exactly `rank`, `merit`, `next_rank`, `next_threshold`, `merit_qualified`, and `exam_request`. True-merit qualification SHALL be independent of attendance. `exam_request.enabled` SHALL require valid registered next target and local functioning request service, independent of merit and host presence. No equality constraint between merit_qualified and enabled SHALL remain. The action SHALL be `guild.exam_request`, label 「預約升等考核」 and payload exactly target_rank. Unregistered/S actors SHALL receive stable registration/no-next-target reasons. Unrelated board/quest fields and bounds SHALL remain unchanged.

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
- **THEN** it is present only when exactly one local `GuildExaminer` host resolves and contains exactly `rank`,
  `merit`, `next_rank`, `next_threshold`, `eligible`, and `exam_start`

#### Scenario: Exam start requires every condition and the next-rank payload
- **WHEN** `exam_start` is computed
- **THEN** it is enabled only when the actor is registered, a local `GuildExaminer` host exists, an exact next
  rank exists, true merit meets its threshold, and no active combat or examination exists, and its action payload
  carries exactly the next-rank key

### Requirement: Service actions are exact, allowlisted, and server-authoritative
The production action registry SHALL retain every existing combat, service, creation, exploration, and options action and SHALL add exactly `inventory.use`, `inventory.toggle_equip`, and `guild.quest_track`. The service action set SHALL therefore contain `guild.register`, `guild.quest_accept`, `guild.quest_abandon`, `guild.quest_turnin`, `guild.quest_track`, `guild.exam_request`, `shop.buy`, `shop.sell`, `inventory.use`, and `inventory.toggle_equip`. `guild.register` SHALL accept exactly an empty payload and retain its current idempotency. Guild quest and exam actions SHALL retain their exact bounded identifiers; `guild.quest_track` SHALL accept exactly `quest_id` (the shared bounded quest identifier) and boolean `tracked`; `shop.buy` and `shop.sell` SHALL retain exactly bounded `item_key` and integer `quantity`. Each inventory action SHALL accept exactly `item_key` as a 1..64-character non-empty string. Every adapter SHALL obtain the actor from the authenticated session, re-resolve every local host and referenced quest, definition, item, rank, mechanic, and current condition, and invoke only its listed public deterministic API. No inventory payload SHALL accept actor, host, branch, session, effect, consumable, quantity, target, slot, HP, combat, price, stock, or wallet fields. No adapter SHALL assign `.db`, traits, registration, rank, merit, quest log, wallet, inventory, equipment, merchant stock, location, combat, or clock state directly. No action SHALL route an action ID or payload through the text command parser.

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

### Requirement: Service action completion updates canonical panels and preserves narrative
After an admitted service or inventory action settles, the server SHALL emit every returned message through the ordinary escaped text output path and SHALL publish canonical panel replacements at one newer revision before sending the matching safe `ui_action_result`. Existing guild, quest, and shop actions SHALL retain their established affected-panel sets. `inventory.use` and `inventory.toggle_equip` SHALL publish a full snapshot because they may change inventory, contained mirrors, status, character equipment, clock-derived state, combat/context state, terminal mode, and art. Entering combat SHALL unload exploration service menus and their local forms, but services v5 SHALL retain personal player/inventory data and the combat UI SHALL own a separate inventory affordance; guild and shop actions SHALL remain absent in combat. Every success or domain-rejection message SHALL be emitted as text and never parsed by the browser to update panel state.

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
- **THEN** exploration service menus and their local forms are unloaded, services v3 retains personal
  player/inventory data, the combat UI owns a separate inventory affordance, and guild and shop actions remain
  absent in combat

#### Scenario: Prose never drives panel state
- **WHEN** any success or domain-rejection message is produced
- **THEN** it is emitted as text and never parsed by the browser to update panel state

