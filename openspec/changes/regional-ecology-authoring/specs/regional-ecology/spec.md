# Spec Delta

## Purpose

Define immutable bounded monster habitats and complete birth compositions with validated settlement exclusions and recoverable individual-density budgets.

## ADDED Requirements

### Requirement: Ecology declarations publish only complete valid bounded habitats
Ecology publication SHALL atomically validate keyed bounded zones, weighted complete compositions and habitat-compatible variant references before exposing an immutable registry.

#### Scenario: Composition forms
- **WHEN** synthetic solitary, repeated-variant and mixed-variant compositions are declared
- **THEN** each resolves its explicit inclusive member ranges and positive pool weights without inferring counts from prose

#### Scenario: Invalid declarations
- **WHEN** a candidate contains unknown references, habitat mismatch, invalid geometry, overlapping zones, invalid counts, bool numerics or nonpositive timing/weight/capacity
- **THEN** publication rejects the entire candidate and retains the preceding snapshot

#### Scenario: Unconfigured ground
- **WHEN** a valid map cell belongs to no authored zone
- **THEN** it is outside automatic birth geometry and creates no implicit species source

### Requirement: Eligible birth area excludes inhabited settlement surroundings
Ordinary birth eligibility SHALL intersect bounded zone geometry, its parent region and shared wilderness validity, excluding each inhabited settlement's authored Chebyshev buffer of at least one neighboring cell.

#### Scenario: Footprint and point settlements
- **WHEN** a capital, a noncapital footprint town and a point village have birth policy
- **THEN** distance is measured from every footprint cell or the point anchor respectively, excluding the complete exterior neighboring ring and any larger buffer

#### Scenario: Nonsettlement and exceptions
- **WHEN** a dungeon anchor or explicit lawful manual placement is evaluated
- **THEN** the dungeon gets no settlement exclusion and explicit placement bypasses automatic birth exclusions and density without bypassing shared placement validity

#### Scenario: Candidate publication
- **WHEN** new published settlement geometry changes a birth area
- **THEN** eligibility is validated from that same candidate world and never stale previously published footprints

### Requirement: Density intervals permit complete unobstructed recovery
Enabled ecology zones SHALL derive positive usable individual bounds with integer ceiling and floor over eligible birth cells and admit complete compositions that can recover unobstructed sub-lower populations within every ordinary limit.

#### Scenario: Integer sparse bounds
- **WHEN** E=25 and lower/upper densities are 5/12 individuals per hundred cells
- **THEN** the bounds are 2 and 3; density zero, inverted, at least 100 or yielding no positive usable interval rejects

#### Scenario: Unsplit recoverability
- **WHEN** group minima, cell capacity, wave budget or remaining upper headroom leave an unobstructed below-lower population unable to reach its band
- **THEN** the authoring candidate rejects rather than truncating groups or accepting an unreachable recovery target

#### Scenario: Single-source tuning
- **WHEN** valid production density or composition tuning changes
- **THEN** generic validation reads declarations and legal relationships without a duplicate approval-value table

