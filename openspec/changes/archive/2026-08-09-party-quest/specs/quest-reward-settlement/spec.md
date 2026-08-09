## RENAMED Requirements

- FROM: `### Requirement: Reward payout is one atomic copper, item, merit, acquisition, and claim transaction`
- TO: `### Requirement: Reward payout is one atomic copper, item, merit, acquisition, claim, and affinity transaction`

## MODIFIED Requirements

### Requirement: Reward payout is one atomic copper, item, merit, acquisition, claim, and affinity transaction
Turn-in SHALL precompute non-negative integer wallet and merit values, repeated-key item additions,
ACQUIRE progress for other active quests, the replacement claims list, and +2 affinity
(`quest_completion` source, exempt from the daily cap) for every companion in the player's party at
turn-in through the sole-writer affinity API (`world/rules/affinity.py`). It SHALL commit wallet,
inventory, `guild_merit`, quest log, claims, and every affected companion's affinity record in one
database transaction and restore every Evennia cache — including the affinity records — if any
write fails. The completed quest record itself SHALL remain `COMPLETED` history.

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

#### Scenario: Fault at every write position restores all surfaces
- **WHEN** each reward or affinity write is fault-injected to raise after any preceding writes
- **THEN** database and in-process wallet, inventory, merit, quest log, claims, and every
  companion's affinity record all equal their pre-turn-in values
