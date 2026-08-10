## MODIFIED Requirements

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
