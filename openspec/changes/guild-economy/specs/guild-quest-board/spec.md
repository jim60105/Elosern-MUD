## ADDED Requirements

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
or `disguised_stats` for eligibility.

#### Scenario: F member sees only local F offers
- **WHEN** an F member lists a board containing local F/E offers and a remote F offer
- **THEN** only the local F offer is returned

#### Scenario: True exceptional power does not bypass rank
- **WHEN** a true-stat elf registered at F lists the board
- **THEN** offers above F remain hidden despite the elf's combat power

### Requirement: Board acceptance and abandonment delegate to quest lifecycle
`accept_guild_offer()` SHALL validate board eligibility and then invoke change 15's `accept_quest()` for
the offer's definition. `abandon_guild_quest()` SHALL invoke `abandon_quest()` for the exact quest ID.
The guild layer SHALL NOT construct, mutate, or reinterpret quest-record dicts itself.

#### Scenario: Eligible offer creates a normal quest record
- **WHEN** a registered member accepts a visible offer
- **THEN** the resulting record is exactly the record `accept_quest()` creates and no reward is paid

#### Scenario: Over-rank acceptance is rejected before quest mutation
- **WHEN** an F member directly names an E offer key
- **THEN** no quest record is created

#### Scenario: Abandonment preserves quest-runtime semantics
- **WHEN** a member abandons an active offered quest
- **THEN** the quest runtime records `FAILED` with reason `abandoned` and the guild layer adds no second
  abandonment state

### Requirement: Player-facing guild commands resolve one local service host
The character cmdset SHALL provide commands for guild registration, offer listing, acceptance, quest-log
listing, abandonment, and turn-in. Every service command SHALL search only the caller's room and SHALL
reject absent or ambiguous matching hosts with Traditional Chinese output.

#### Scenario: Guild workflow is reachable from commands
- **WHEN** a player enters the Altoria guild hall and invokes the documented guild commands
- **THEN** the same deterministic registration, board, lifecycle, and turn-in APIs used by tests are called

#### Scenario: Guild command cannot address a remote dbref
- **WHEN** a player supplies the dbref of GuildStaff in another room
- **THEN** the command rejects rather than performing a remote operation
