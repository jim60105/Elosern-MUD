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

### Requirement: Service presentation resolves hosts per service class and a stable player summary

Outside combat each available service surface SHALL resolve its local host independently from the actor's current room under the same deterministic rule as commands. Guild and rank use their normal staff and examination-counter classes; shop uses a merchant. Zero or multiple hosts SHALL make only that surface unavailable. While possessed, guild and rank SHALL be omitted without resolving their services; the merchant SHALL still resolve normally and supply host metadata.

#### Scenario: Guild hall resolves one guild host and its examiner
- **WHEN** an unpossessed actor stands in a room containing exactly one `GuildStaff` host that also carries `GuildExaminer`
- **THEN** `host` names that host, `guild` and `rank` surfaces are present, and `shop` is null

#### Scenario: General store resolves one merchant
- **WHEN** the actor stands in a room containing exactly one `Merchant` host and no `GuildStaff`
- **THEN** `host` names that merchant, `shop` is present, and `guild` is null

#### Scenario: Co-located different service classes stay independent
- **WHEN** an unpossessed actor's room contains exactly one `GuildStaff` and exactly one `Merchant`
- **THEN** both the guild and shop surfaces render their own host data and neither availability is affected by the other class

#### Scenario: Ambiguous hosts close only the affected surface
- **WHEN** an unpossessed actor's room contains two `GuildStaff` hosts and one `Merchant`
- **THEN** the guild surface is unavailable with a stable reason while the shop surface remains available, and no adapter can address either guild host

#### Scenario: Unregistered summary is honest
- **WHEN** an unpossessed actor has no `guild_registration`
- **THEN** `player` reports `guild_registered` false, `guild_rank` null, and the board section renders no offers while the registration surface offers the register action

#### Scenario: Disguised elf does not distort the summary
- **WHEN** an elf with true rank F and true merit 0 holds a disguise
- **THEN** `player` reports rank F, merit 0, and no displayed-stat value, and no surface derives eligibility from the disguise

#### Scenario: Below merit request stays enabled
- **WHEN** an unpossessed registered next-rank member below true merit threshold stands at a functioning guild counter and the qualified host is absent
- **THEN** merit_qualified is false, exam_request is enabled and dispatch returns exam_schedule without mutation

#### Scenario: Different host classes never create cross-class ambiguity
- **WHEN** different host classes are present in the same room for an unpossessed actor
- **THEN** they create no cross-class ambiguity, and the co-location of `GuildStaff` with `GuildExaminer` makes
  both the guild and rank surfaces available

#### Scenario: Top-level host follows the guild-then-merchant preference
- **WHEN** the top-level `host` field is computed outside combat for an unpossessed actor
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
  snapshot values for wallet, rank, merit, or eligibility; while possessed these sources belong to the owner

#### Scenario: A possessed actor ignores a co-located guild host
- **WHEN** a possessed companion stands beside both guild staff and a merchant outside combat
- **THEN** `host` names only the merchant and the normal shop renders, while guild and rank service sections and guild navigation remain absent

#### Scenario: A possessed actor with no merchant has no service host
- **WHEN** a possessed companion stands beside guild staff with no merchant
- **THEN** `host`, `guild` and `shop` are null, all service pagination totals are zero, and no guild failure reason is invented
