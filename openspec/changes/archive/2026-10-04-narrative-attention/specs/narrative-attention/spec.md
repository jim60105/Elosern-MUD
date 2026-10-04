## Purpose

Ranks executable invested-story candidates deterministically before director generation, while reserving unrelated new stories for explicitly confirmed requests.

## ADDED Requirements

### Requirement: Eligibility precedes attention scoring

Automatic candidates SHALL derive from existing experiences, relationships, clues, correspondence and invested threads. Knowledge, location, scheduling and executable feasibility SHALL filter before scoring. Unrelated new stories SHALL require an explicitly confirmed valid creative request. Attention SHALL call no model.

#### Scenario: Unrelated automatic candidate
- **WHEN** a candidate has high salience but no invested source or confirmed request
- **THEN** it is ineligible before ranking

#### Scenario: Unavailable candidate
- **WHEN** a candidate violates location/schedule/executable constraints
- **THEN** it is excluded regardless of its score

#### Scenario: Confirmed unrelated direction
- **WHEN** a valid explicitly confirmed request proposes an unrelated story
- **THEN** it is eligible as player-originated direction, not automatic history

### Requirement: Observable engagement and calibrated focus bound selection

Ranking SHALL use unresolved stakes, observable engagement, relationships, deadlines, location relevance, repetition and cooldown with deterministic ties and calibrated weights/focus limits. Passive receipt alone SHALL NOT count as high engagement. Selection SHALL preserve existing threads, limiting only the candidates supplied to the director.

#### Scenario: Visit and correspondence outweigh passive receipt
- **WHEN** one thread has initiated visits/questions/sustained exchange and another only passive receipt
- **THEN** the measured engagement component reflects the active behavior

#### Scenario: Identical ranking inputs
- **WHEN** the same eligible candidates/revisions/configuration are ranked twice offline
- **THEN** the bounded order and reason data are identical and unselected state is not deleted

