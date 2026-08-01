## ADDED Requirements

### Requirement: Completed guild quests may be claimed exactly once per quest ID
`turn_in_quest(actor, staff, quest_id)` SHALL require a parsed `COMPLETED` quest record, the matching
local issuer branch and registered offer, and a quest ID absent from the actor's JSON-safe
`guild_reward_claims` list. Success SHALL append that exact ID. A different acceptance number for the
same definition SHALL remain independently claimable after completion.

#### Scenario: First completed acceptance is paid once
- **WHEN** a completed `<definition>:1` record is turned in at its issuer
- **THEN** `<definition>:1` is appended once to reward claims and the configured reward is applied

#### Scenario: Duplicate turn-in pays nothing
- **WHEN** the same completed quest ID is turned in again
- **THEN** an already-claimed error is returned and wallet, inventory, merit, claims, and quest log remain
  unchanged

#### Scenario: Later acceptance has independent claim identity
- **WHEN** `<definition>:2` is completed after `<definition>:1` was claimed
- **THEN** the second ID can be claimed once without removing the first claim record

### Requirement: Reward payout is one atomic copper, item, merit, acquisition, and claim transaction
Turn-in SHALL precompute non-negative integer wallet and merit values, repeated-key item additions,
ACQUIRE progress for other active quests, and the replacement claims list. It SHALL commit wallet,
inventory, `guild_merit`, quest log, and claims in one database transaction and restore every Evennia
cache if any write fails. The completed quest record itself SHALL remain `COMPLETED` history.

#### Scenario: Reward grants all configured surfaces
- **WHEN** a reward has copper 50, two healing potions, and merit 25
- **THEN** wallet increases by 50, two item keys are appended, merit increases by 25, and the claim is
  recorded in the same successful operation

#### Scenario: Reward item advances another ACQUIRE quest atomically
- **WHEN** a claimed potion reward satisfies another active quest's current ACQUIRE objective
- **THEN** that quest progress and every reward surface commit together

#### Scenario: Fault at every write position restores all surfaces
- **WHEN** each reward write is fault-injected to raise after any preceding writes
- **THEN** database and in-process wallet, inventory, merit, quest log, and claims all equal their
  pre-turn-in values

### Requirement: ACQUIRE is a closed inventory-backed quest objective
Change 16 SHALL add `ObjectiveKind.ACQUIRE`. An ACQUIRE objective SHALL declare exactly one known
`item_key` and a positive quantity and SHALL reject destination, monster-tier, bound-target, and escort
fields. It SHALL progress only from positive additions in a successfully committed inventory plan.

#### Scenario: Valid ACQUIRE objective registers
- **WHEN** a quest stage declares a known item key and quantity 3 with no unrelated fields
- **THEN** the definition registers and starts at progress zero

#### Scenario: Caller assertion cannot forge acquisition
- **WHEN** code has an item key and quantity but no committed inventory plan
- **THEN** no public quest API accepts that assertion as ACQUIRE progress

#### Scenario: Removal does not reverse progress
- **WHEN** an acquired quest item is later sold or removed
- **THEN** existing stage progress remains unchanged

#### Scenario: One addition advances multiple quests without surplus carry
- **WHEN** one inventory addition matches multiple active current stages
- **THEN** each matching quest advances at most one stage and excess quantity is not carried to its next
  stage

### Requirement: Import population is not gameplay acquisition
The import loader SHALL continue populating initial raw inventory only during character construction and
SHALL NOT invoke ACQUIRE progress. Every post-construction deterministic item producer SHALL use the
inventory planning boundary.

#### Scenario: Imported items do not auto-complete a later quest
- **WHEN** a character is imported with three potions and later accepts an ACQUIRE-potion quest
- **THEN** its stage starts at zero until a gameplay inventory addition commits
