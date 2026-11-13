# Spec Delta

## MODIFIED Requirements

### Requirement: Eligible birth area excludes inhabited settlement surroundings
Ordinary birth eligibility SHALL intersect bounded zone geometry, its parent region and shared wilderness validity, excluding each inhabited settlement's authored Chebyshev buffer of at least one neighboring cell.

#### Scenario: Footprint and point settlements
- **WHEN** a capital, a noncapital footprint town and a point village have birth policy
- **THEN** distance is measured from every footprint cell or the point anchor respectively, excluding the complete exterior neighboring ring and any larger buffer

#### Scenario: Village and hamlet categories
- **WHEN** a synthetic village location and a synthetic hamlet location, each with a published cell and no settlement document, lie inside a zone
- **THEN** each excludes its own cell and the complete neighboring ring, as an inhabited settlement of any other category with the same geometry does

#### Scenario: Nonsettlement and exceptions
- **WHEN** a dungeon anchor or explicit lawful manual placement is evaluated
- **THEN** the dungeon gets no settlement exclusion and explicit placement bypasses automatic birth exclusions and density without bypassing shared placement validity

#### Scenario: Candidate publication
- **WHEN** new published settlement geometry changes a birth area
- **THEN** eligibility is validated from that same candidate world and never stale previously published footprints
