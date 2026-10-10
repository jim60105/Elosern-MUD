# Spec Delta

## MODIFIED Requirements

### Requirement: Reward payout is one atomic copper, item, merit, acquisition, claim, and affinity transaction
Turn-in SHALL commit wallet, inventory, `guild_merit`, quest log, claims, and every affected
companion's affinity record (values and caps) in one database transaction and restore every
Evennia cache ;  including the affinity records ;  if any write fails. The completed quest record
itself SHALL remain `COMPLETED` history.

#### Scenario: Reward grants all configured surfaces
- **WHEN** a reward has copper 50, two healing potions, and merit 25
- **THEN** wallet increases by 50, two item keys are appended, merit increases by the declared quest-completion gain5, and the claim is
  recorded in the same successful operation

#### Scenario: Reward item advances another ACQUIRE quest atomically
- **WHEN** a claimed potion reward satisfies another active quest's current ACQUIRE objective
- **THEN** that quest progress and every reward surface commit together

#### Scenario: Turn-in rewards each then-in-party companion
- **WHEN** a turn-in succeeds with two bound companions in the party
- **THEN** each companion's affinity rises by the declared quest-completion gain in the same transaction as the reward surfaces, and
  a companion outside the party gains nothing

#### Scenario: A matching cap_breaks entry raises companion caps in the same transaction
- **WHEN** a turn-in completes a milestone quest with matching in-party companions
- **THEN** the matching companions' caps rise to the entry's `new_cap` in the same transaction as
  the reward, the the declared quest-completion gains, and the claim

#### Scenario: A cap break at the old cap does not lose the the declared quest-completion gain
- **WHEN** a matching companion's record sits at value 99 with cap 99 at turn-in
- **THEN** the cap rises first and the the declared quest-completion applies after, leaving value 99 plus the declared gain (clamped to the raised cap) under the raised cap

#### Scenario: Fault at every write position restores all surfaces
- **WHEN** each reward, affinity, or cap write is fault-injected to raise after any preceding
  writes
- **THEN** database and in-process wallet, inventory, merit, quest log, claims, and every
  companion's affinity record (values and caps) all equal their pre-turn-in values

#### Scenario: Turn-in precomputes every settlement value before committing
- **WHEN** turn-in prepares the settlement
- **THEN** it precomputes non-negative integer wallet and merit values, repeated-key item
  additions, ACQUIRE progress for other active quests, the replacement claims list, and the declared quest-completion
  affinity (`quest_completion` source, exempt from the daily cap) for every companion in the
  player's party at turn-in through the sole-writer affinity API (`world/rules/affinity.py`)

#### Scenario: A cap_breaks entry precomputes cap raises applied before the the declared quest-completion gains
- **WHEN** the completed quest has a `cap_breaks` entry
- **THEN** turn-in also precomputes `raise_affinity_cap` calls for every then-in-party companion
  matching the entry's `npc_key` or role and applies them before the `quest_completion` gains, so
  a record at the old cap cannot clamp the the declared quest-completion

#### Scenario: Independently known cap-order fixture
- **WHEN** a synthetic quest rule grants 2 to value 99 and raises cap to 150
- **THEN** the committed value is 101, whereas a failed reward commit restores both value 99 and cap 99; this does not pin the production quest gain

