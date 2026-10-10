# Spec Delta

## MODIFIED Requirements

### Requirement: Completing a quest rewards each then-in-party companion with affinity
Quest reward settlement SHALL grant the declared quest-completion affinity (source `quest_completion`, exempt from the daily cap) to every companion in the player's party at turn-in, through the sole-writer affinity API (`world/rules/affinity.py`), committed atomically with the reward transaction. Companions SHALL receive no XP, items, or merit.

#### Scenario: Turn-in rewards the party with affinity
- **WHEN** a player turns in a completed quest with two bound companions in the party
- **THEN** each companion's affinity value rises by the declared quest-completion gain, alongside the ordinary reward surfaces, in
  one committed operation

#### Scenario: Only then-in-party companions earn the bonus
- **WHEN** a player turns in a quest while one bound companion is in the party and another is not
- **THEN** only the in-party companion's affinity rises by the declared quest-completion gain

#### Scenario: A quest-completion gain bypasses the daily cap
- **WHEN** a companion's interaction budget is exhausted for the day and a turn-in grants the bonus
- **THEN** the the declared quest-completion applies and the daily interaction counter is unchanged

#### Scenario: A failed reward write restores every surface
- **WHEN** any reward or affinity write is fault-injected after preceding writes
- **THEN** wallet, inventory, merit, quest log, claims, and every companion's affinity record ;  and
  their in-process caches ;  equal their pre-turn-in values

#### Scenario: Every reward surface commits in one transaction
- **WHEN** a quest turn-in commits
- **THEN** wallet, inventory, merit, ACQUIRE progress, claims, and every affected companion's affinity record commit together in the one atomic reward transaction

#### Scenario: Independently known cap-order fixture
- **WHEN** a synthetic quest rule grants 2 to value 99 and raises cap to 150
- **THEN** the committed value is 101, whereas a failed reward commit restores both value 99 and cap 99; this does not pin the production quest gain

