## MODIFIED Requirements

### Requirement: The services panel is an exact read-only exploration-mode panel

The production presentation registry SHALL register `services` schema version 6. Its available payload SHALL
contain exactly `schema_version`, `available`, `kind`, `host`, `player`, `guild`, `shop`, `inventory`, and
`pagination`; `available` SHALL be true, `kind` SHALL be `services`, and `schema_version` SHALL be integer 6.
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

### Requirement: The guild surface covers registration, board, quest log, and rank examination

The `guild` section SHALL contain exactly `branch_label`, `rank_ladder`, `registration`, `board`, `quests`, and
`rank` and SHALL be present only when exactly one local `GuildStaff` host resolves. `branch_label` SHALL be the
resolved host's branch display name, the issuer label of every board offer. `rank_ladder` SHALL list every guild
rank key in ascending rank order. `board` and `quests` SHALL be bounded lists of at most 12
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
  containing exactly `definition_key`, `display_name`, `category`, `rank`, `objective_summary`, `objective_note`,
  `deadline_line`, `rationale`, `flavor`, `reward`, and `accept`, and no `reward_summary`

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

## ADDED Requirements

### Requirement: Board offers carry structured facts from the canonical seams

Each board row SHALL describe its offer through the quest log's seams and vocabularies: the closed `category`
keys, an objective line and note composing to `describe_objective`, the offer-deadline seam, verbatim authored
`rationale` and `flavor`, and the quest log's non-null `reward` shape. The board SHALL never disagree with the
quest book.

#### Scenario: A species-hunt offer splits its variant clause
- **WHEN** the board lists a regional species-hunt offer
- **THEN** `objective_summary` names the region, quantity, and species, `objective_note` carries the counted-variant clause, and the two compose to `describe_objective`

#### Scenario: An offer with a deadline discloses it before acceptance
- **WHEN** the board lists an offer whose definition carries a 72-hour deadline
- **THEN** its `deadline_line` reads 接取後 3 日, and an offer with no deadline carries null

#### Scenario: The board reward matches the accepted quest's reward
- **WHEN** a player accepts a board offer and the quest log row for the new record is built
- **THEN** the board row's `reward` and the quest log row's `reward` are equal

#### Scenario: Authored prose reaches the board verbatim
- **WHEN** a definition carries a rating rationale and background flavor
- **THEN** the board row's `rationale` and `flavor` equal them exactly, and a definition without them yields null

#### Scenario: The branch label names the issuing guild
- **WHEN** the guild section is built at a branch's counter
- **THEN** `branch_label` equals the label the quest log renders as the issuer of a quest accepted from that board

#### Scenario: The board never carries offers above the holder's rank
- **WHEN** a registered E-rank holder's board is built in a hall that also holds D offers
- **THEN** no board row's `rank` sits above E in `rank_ladder`

#### Scenario: The rank ladder lists every rank in order
- **WHEN** the guild section is built
- **THEN** `rank_ladder` lists every registered guild rank key exactly once, ordered from the lowest rank to the highest, and every board row's `rank` and the rank block's `rank` and `next_rank` appear in it

#### Scenario: The client mirror rejects a stale board row
- **WHEN** a board row carrying `reward_summary`, an unknown category, or a ninth reward item reaches the client validator
- **THEN** the client rejects the services payload rather than rendering it

### Requirement: The guild counter renders the structured board offer

The guild counter's board SHALL render each offer's reward from its `reward` object (copper, merit when
non-zero, and each item with its quantity) under one reward label, SHALL render `objective_note` and
`deadline_line` when present, and SHALL add no prefix or text the payload does not carry.

#### Scenario: An offer shows its reward once
- **WHEN** a board row with copper 120 and merit 45 renders
- **THEN** the counter shows both figures under a single reward label

#### Scenario: Null optional facts render nothing
- **WHEN** a board row's `objective_note`, `deadline_line`, `rationale`, and `flavor` are null
- **THEN** the counter renders no placeholder for any of them
