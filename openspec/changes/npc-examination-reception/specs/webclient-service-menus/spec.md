# Spec Delta

## MODIFIED Requirements

### Requirement: Service presentation resolves hosts per service class and a stable player summary

Outside combat each available service surface SHALL resolve its local host independently from the actor's current room under the same deterministic rule as commands. Guild and rank use their normal staff and examination-counter classes; shop uses a merchant. Zero or multiple hosts SHALL make only that surface unavailable. While possessed, guild and rank SHALL be omitted without resolving their services; the merchant SHALL still resolve normally and supply host metadata.

#### Scenario: Guild hall resolves one guild host and its examiner
- **WHEN** an unpossessed actor stands in a room containing exactly one `GuildStaff` host that also carries `GuildExamReception`
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
- **THEN** they create no cross-class ambiguity, and the co-location of `GuildStaff` with `GuildExamReception` makes
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

### Requirement: The guild surface covers registration, board, quest log, and rank examination
The guild section SHALL retain its existing exact branch/rank/registration/board/quests/exam shape, local GuildStaff gate and read-only ownership. Quest rows SHALL accept invalidated and add nullable bounded terminal_reason; invalidated rows SHALL have disabled abandon/turn-in. Private escort abandonment is a separate host-independent quest_log descriptor using the same action ID, and SHALL not make a guild section available without staff.

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
