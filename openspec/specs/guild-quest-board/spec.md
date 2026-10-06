# guild-quest-board Specification

## Purpose

Define deterministic guild quest offers and their player-facing board workflow.

## Requirements

### Requirement: GuildQuestOffer is immutable and validated against quest, guild, item, and branch registries
The guild offer registry SHALL accept only frozen `GuildQuestOffer` values containing a known
`definition_key`, known issuer branch, and deeply immutable `QuestReward`. Registration SHALL reject
unknown references, negative copper or merit, non-positive item quantities, duplicate reward item keys,
and copper outside the referenced quest rank's `GUILD_RANK_REGISTRY` reward band. Equal duplicate
registration SHALL be idempotent and conflicting registration SHALL preserve the original. Hand-written
offer reward values SHALL load from `guild_economy.yaml` rather than duplicate tunable numbers in Python.

#### Scenario: Valid hand-written offer registers
- **WHEN** an offer references the introductory quest, its Altoria issuer, known reward items, and copper
  inside that quest rank's band
- **THEN** the exact immutable offer is available from the registry

#### Scenario: Out-of-band reward is rejected
- **WHEN** an F-rank quest offer declares copper above the F-rank maximum
- **THEN** registration raises before changing the offer registry

#### Scenario: S-rank open upper bound is honored
- **WHEN** an S-rank offer declares integer copper at or above the S-rank minimum
- **THEN** validation does not invent an upper cap

### Requirement: Guild boards expose only local rank-eligible offers
`list_guild_offers(actor, staff)` SHALL require valid registration and local GuildStaff. It SHALL return
only offers issued by that staff's branch whose quest-rank order is less than or equal to the actor's
canonical `guild_rank` order, in stable rank/key order. It SHALL never read registration snapshot values
or `disguised_stats` for eligibility. A bound clear-out over an authored site SHALL additionally be
offered only while its site can currently supply the objective's quantity of living individuals, read
through the same quest-layer read the acceptance-time guarantee uses, so the board never advertises work
that acceptance would refuse; a cleared one-shot site's clear-out is therefore absent from the board, and
a recoverable site's clear-out returns once its authored in-game condition has matured and it has
repopulated. A site the world has not yet populated SHALL be treated the same way: its clear-out is absent
until the world clock's own settlement populates the site, and no quest, board read, or acceptance ever
populates one. The availability rule SHALL narrow the listing only: it SHALL NOT change the acceptance
precheck, and it SHALL be independent of rank eligibility, of the objective-summary rendering, and of the
ordering key: a board listed with summaries and without them returns the same offers in the same order.

#### Scenario: F member sees only local F offers
- **WHEN** an F member lists a board containing local F/E offers and a remote F offer
- **THEN** only the local F offer is returned

#### Scenario: True exceptional power does not bypass rank
- **WHEN** a true-stat elf registered at F lists the board
- **THEN** offers above F remain hidden despite the elf's combat power

#### Scenario: A cleared one-shot site's clear-out leaves the board
- **WHEN** a one-shot site's individuals are defeated and the site is declared cleared, then the board is listed again
- **THEN** its clear-out is not offered, and no other offer's eligibility or order changed

#### Scenario: A recovered site's clear-out returns to the board
- **WHEN** a cleared recoverable site's authored condition matures and it repopulates with fresh individuals
- **THEN** its clear-out is offered again, and acceptance binds those fresh individuals rather than any previously defeated one

#### Scenario: An unpopulated site's clear-out is absent until the world settles it
- **WHEN** the board is listed before any world-clock advance has populated a site
- **THEN** that site's clear-out is absent, and no individual is created for it by listing or accepting

#### Scenario: Availability never reorders the board
- **WHEN** a board containing clear-outs and species hunts is listed with and without objective summaries
- **THEN** the returned offers and their order are identical, and only the rendered rows differ

### Requirement: Board acceptance and abandonment delegate to quest lifecycle
`accept_guild_offer()` SHALL validate board eligibility and then invoke change 15's `accept_quest()` for
the offer's definition, naming the issuing branch as the issuer key in the canonical
`guild:<branch_key>` form derived from the resolved `GuildStaff` host's `branch_key`. The guild layer
SHALL NOT construct that key by string concatenation; it SHALL use the shared issuer-key
constructor, so the board path and the read seam can never disagree about the key's spelling. A
successful acceptance SHALL additionally grant +1 affinity (`guild` source)
with the issuing GuildStaff host through the sole-writer affinity API (`world/rules/affinity.py`),
committed in one all-or-nothing operation with the quest record creation: the acceptance SHALL
snapshot the actor's quest-log surface plus the host's affinity record (acceptance creates no
instance pins — a stage's instance binding is made at stage advance, and a site clear-out's stage-zero
target binding is made at acceptance without an instance pin), apply the quest
record and the gain inside one transaction, and restore every surface on failure so a failed
affinity write rolls back the acceptance; abandonment SHALL grant no affinity.
When `accept_quest()` refuses an offer because the hunt cannot be legally satisfied (the
target-availability guarantee fails) — a regional species hunt whose region cannot supply the count, or a
bound clear-out whose site cannot supply its living individuals — the board path SHALL surface that named
refusal as an ordinary rejection: no quest record, no affinity gain, and no partial provisioning,
population, or binding left behind.
The acceptance precheck SHALL remain the issuing branch plus the actor's rank alone: the availability rule
narrows what the board lists, never what acceptance will attempt, so a player who names an offer's key
directly or who accepts a listing taken before the site changed state receives the lifecycle's named
refusal instead of a generic eligibility error.
`abandon_guild_quest()` SHALL invoke `abandon_quest()` for the exact quest ID.
The guild layer SHALL NOT construct, mutate, or reinterpret quest-record dicts itself.

#### Scenario: Eligible offer creates a normal quest record
- **WHEN** a registered member accepts a visible offer
- **THEN** the resulting record is exactly the record `accept_quest()` creates, its issuer key is
  `guild:<the issuing host's branch key>`, no reward is paid, and the issuing host's affinity value
  rises by 1

#### Scenario: Over-rank acceptance is rejected before quest mutation
- **WHEN** an F member directly names an E offer key
- **THEN** no quest record is created and no affinity is granted

#### Scenario: A failed acceptance restores every surface
- **WHEN** persistence is fault-injected after the quest record is written and before the
  affinity gain commits
- **THEN** the quest log and the host's affinity record — and their in-process caches — equal
  their pre-acceptance values

#### Scenario: A legally unsatisfiable hunt offer is refused cleanly
- **WHEN** a member accepts a species-hunt offer whose ordinary-eligible target guarantee cannot be met
- **THEN** the refusal names the reason, and the quest log, affinity record, and every individual owned by the ambient/site managers equal their pre-acceptance values

#### Scenario: A legally unsatisfiable clear-out offer is refused cleanly
- **WHEN** a member accepts a bound clear-out whose site can no longer supply its living individuals
- **THEN** the refusal names the site-cleared or site-short reason, no quest record and no affinity gain exist, and the site's durable state and its individuals are unchanged

#### Scenario: A state change between listing and acceptance is reported by name
- **WHEN** a site's individuals are defeated after the board was listed and the member then accepts the now-unsatisfiable offer from that listing or by naming its key directly
- **THEN** the lifecycle's named refusal reaches the member, and the board precheck does not present it as an unknown or ineligible offer

#### Scenario: Abandonment preserves quest-runtime semantics
- **WHEN** a member abandons an active offered quest
- **THEN** the quest runtime records `FAILED` with reason `abandoned`, the guild layer adds no second
  abandonment state, and no affinity is granted

#### Scenario: Two branches offering one definition produce distinguishable records
- **WHEN** the same definition is accepted at one branch, completed, and later accepted at a second
  branch offering it
- **THEN** the two records carry that branch's own issuer key, and each resolves to its own branch's
  registered reward

### Requirement: Player-facing guild commands resolve one local service host
The character cmdset SHALL provide commands for guild registration, offer listing, acceptance,
quest-log listing, detail viewing, abandonment, and turn-in. Every guild service command
(registration, board listing, acceptance, abandonment, turn-in) SHALL search only the caller's room
and SHALL reject absent or ambiguous matching hosts with Traditional Chinese output. Read-only
personal quest-log commands (`guild log` and `guild show`) SHALL operate on the caller's own
persisted quest log and SHALL NOT require a local `GuildStaff` host. The guild staff dialogue SHALL
provide the turn-in surface in addition to the commands: `talk <guild-staff> 回報` SHALL list, in
deterministic `(accepted_tick, quest_id)` order, every quest record that is `COMPLETED`, whose
definition has a registered offer at the staff's branch, and whose quest id is absent from the
caller's reward claims, or answer that nothing is reportable; `talk <guild-staff> 回報 <quest_id>`
SHALL turn in exactly that quest through the same deterministic `turn_in_quest` API used by
`guild turnin`, with identical atomic settlement and rejection semantics. Both dialogue forms SHALL
apply the same local-host rule: the talked-to NPC SHALL be the sole `GuildStaff` host in the
caller's room, and the turn-in SHALL never accept a remote host or bypass `turn_in_quest`.

#### Scenario: Guild workflow is reachable from commands
- **WHEN** a player enters the Altoria guild hall and invokes the documented guild commands
- **THEN** the same deterministic registration, board, lifecycle, and turn-in APIs used by tests are called

#### Scenario: Guild command cannot address a remote dbref
- **WHEN** a player supplies the dbref of GuildStaff in another room
- **THEN** the command rejects rather than performing a remote operation

#### Scenario: Read-only quest-log commands work without a service host
- **WHEN** a player runs `guild log` or `guild show` in a room with no `GuildStaff` host
- **THEN** the command renders the caller's own quest log or quest detail instead of reporting an
  absent service host

#### Scenario: Completed quests are reportable through guild-staff dialogue
- **WHEN** a registered player with a `COMPLETED`, unclaimed quest whose offer is registered at the
  staff's branch talks to the local guild staff with `回報 <quest_id>`
- **THEN** the deterministic settlement commits exactly once, the reward matches the offer, and the
  listing afterwards no longer includes the quest

#### Scenario: Multiple completed quests list in deterministic order
- **WHEN** a player with several completed, unclaimed quests talks to the guild staff with `回報`
- **THEN** the staff lists exactly those quests ordered by accepted tick then quest id, and turning
  one in never affects the reportability of the others

#### Scenario: Dialogue turn-in never bypasses the settlement contract
- **WHEN** a player talks to the guild staff with `回報` naming an unknown, in-progress, failed,
  already-claimed, or offer-less quest id
- **THEN** the dialogue answers with the standard turn-in rejection and no reward state changes

#### Scenario: 回報 outside a guild hall yields no turn-in
- **WHEN** a player talks to an NPC that is not the local `GuildStaff` host with the keyword `回報`
- **THEN** the host answers with the no-understanding line and no state changes

#### Scenario: 回報 on a host reusing the guild_staff table without the staff component stays a plain keyword
- **WHEN** a player talks to a dialogue host carrying the `guild_staff` table but no `GuildStaff`
  component, with `回報 <quest_id>`
- **THEN** the host answers with the no-understanding line, no turn-in is attempted, and no reward
  state changes

#### Scenario: 回報 with ambiguous guild staff is rejected
- **WHEN** a player talks to a guild staff NPC with `回報` while more than one `GuildStaff` host
  occupies the room
- **THEN** both the listing and any turn-in attempt answer with the standard ambiguous-host
  rejection line and no quest, wallet, inventory, merit, or claim state changes

### Requirement: Board listing and quest log surface objective guidance
`guild list` SHALL render each eligible offer with a one-line Traditional
Chinese summary of the offered definition's first objective, in addition to the
existing key, display name, and reward; a regional species hunt SHALL render as one
deterministic line naming the region, species, and count. `guild log` SHALL render a hint that
`guild show <quest_id>` reveals full objective detail. Both SHALL be read-only
presentation over existing registries and records, and SHALL NOT change board
eligibility or quest state.

#### Scenario: Board rows show a first-objective one-liner
- **WHEN** an F member lists a board containing the `introductory_hunt` offer
- **THEN** the row shows the offered definition's first objective summary (for
  example a DEFEAT goal) alongside the name and reward

#### Scenario: A species-hunt offer renders its one-liner
- **WHEN** a board contains a species-hunt offer
- **THEN** its row shows region, species, and required count in one deterministic Traditional Chinese line

#### Scenario: Quest log hints at the detail command
- **WHEN** a player with at least one quest record runs `guild log`
- **THEN** the output points the player to `guild show` for full objective
  detail

#### Scenario: Objective summaries never affect eligibility
- **WHEN** a board is listed with objective summaries enabled
- **THEN** rank-eligible filtering and ordering are byte-for-byte identical to
  the behavior without summaries

### Requirement: Generated guild offers survive a server restart
The system SHALL re-register the guild offers of all generated quests held in the durable store at startup, so the guild board lists them again and they can be accepted.

#### Scenario: Generated offer visible on the board after restart
- **WHEN** the server restarts while a generated quest offer exists in the durable store and has not been accepted
- **THEN** the guild board lists the generated offer and it can be accepted

#### Scenario: Accepted generated offer is not double-registered
- **WHEN** the server restarts after the generated offer was accepted
- **THEN** the offer is not listed again on the board and no duplicate offer record is created
