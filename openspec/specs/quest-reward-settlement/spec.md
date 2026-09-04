# quest-reward-settlement Specification

## Purpose

Define atomic guild-quest reward claims and inventory-backed acquisition.

## Requirements

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

### Requirement: Reward payout is one atomic copper, item, merit, acquisition, claim, and affinity transaction
Turn-in SHALL precompute non-negative integer wallet and merit values, repeated-key item additions,
ACQUIRE progress for other active quests, the replacement claims list, and +2 affinity
(`quest_completion` source, exempt from the daily cap) for every companion in the player's party at
turn-in through the sole-writer affinity API (`world/rules/affinity.py`). When the completed quest
has a `cap_breaks` entry, turn-in SHALL also precompute `raise_affinity_cap` calls for every
then-in-party companion matching the entry's `npc_key` or role and SHALL apply them before the
`quest_completion` gains, so a record at the old cap cannot clamp the +2. It SHALL commit wallet,
inventory, `guild_merit`, quest log, claims, and every affected companion's affinity record (values
and caps) in one database transaction and restore every Evennia cache — including the affinity
records — if any write fails. The completed quest record itself SHALL remain `COMPLETED` history.

#### Scenario: Reward grants all configured surfaces
- **WHEN** a reward has copper 50, two healing potions, and merit 25
- **THEN** wallet increases by 50, two item keys are appended, merit increases by 25, and the claim is
  recorded in the same successful operation

#### Scenario: Reward item advances another ACQUIRE quest atomically
- **WHEN** a claimed potion reward satisfies another active quest's current ACQUIRE objective
- **THEN** that quest progress and every reward surface commit together

#### Scenario: Turn-in rewards each then-in-party companion
- **WHEN** a turn-in succeeds with two bound companions in the party
- **THEN** each companion's affinity rises by 2 in the same transaction as the reward surfaces, and
  a companion outside the party gains nothing

#### Scenario: A matching cap_breaks entry raises companion caps in the same transaction
- **WHEN** a turn-in completes a milestone quest with matching in-party companions
- **THEN** the matching companions' caps rise to the entry's `new_cap` in the same transaction as
  the reward, the +2 gains, and the claim

#### Scenario: A cap break at the old cap does not lose the +2 gain
- **WHEN** a matching companion's record sits at value 99 with cap 99 at turn-in
- **THEN** the cap rises first and the +2 applies after, leaving value 101 under the raised cap

#### Scenario: Fault at every write position restores all surfaces
- **WHEN** each reward, affinity, or cap write is fault-injected to raise after any preceding
  writes
- **THEN** database and in-process wallet, inventory, merit, quest log, claims, and every
  companion's affinity record (values and caps) all equal their pre-turn-in values

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

### Requirement: The first-ever reward claim grants the starter epithet atomically
`turn_in_quest` SHALL detect, before appending this claim's quest ID, that the
actor's `guild_reward_claims` list is empty — the actor's first-ever reward
claim for any quest definition (never keyed to a particular `definition_key`) —
and inside that same all-or-nothing claim transaction call
`world/rules/titles.py::grant_first_quest_epithet`, which banks the starter
epithet 「南門新客」 (`origin_quote` from `world/lore/titles.py`'s
`STARTER_EPITHET`) through the regular `bank_epithet` writer, auto-equipping an
empty epithet slot. The grant notification 「獲得異名：南門新客」 SHALL merge
into the claim response payload (`title_notifications`) and every claim surface
(CLI turn-in, the turn-in dialogue keyword, the webclient claim action) SHALL
echo those lines with the reward summary. The title attributes SHALL join the
claim transaction's snapshot set: a rolled-back claim removes the epithet.
`bank_epithet` display dedupe is the second guard — any later claim, replay, or
repeated invocation is an inert no-op granting nothing and notifying nothing.

#### Scenario: First completed claim grants the epithet
- **WHEN** a registered member with an empty claims list turns in any completed quest for the first time
- **THEN** the epithet 「南門新客」 is banked and auto-equipped in the same commit as the reward, and the response carries 「獲得異名：南門新客」 for every claim surface to echo

#### Scenario: Later claims never re-grant
- **WHEN** the same member turns in any further completed quest, including a second acceptance of the same definition
- **THEN** the reward pays normally, `title_collection` is unchanged, and no epithet notification line appears in the response

#### Scenario: A rolled-back first claim revokes the epithet
- **WHEN** any write in the first claim's transaction fails after the epithet was banked
- **THEN** wallet, inventory, merit, quest log, claims, and both title attributes equal their pre-turn-in values

#### Scenario: The grant is definition-independent
- **WHEN** the first-ever claim completes a quest whose `definition_key` is not `introductory_hunt`
- **THEN** the epithet grants exactly as for any other first claim
