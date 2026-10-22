# Spec Delta

## ADDED Requirements

### Requirement: Recent deeds use a frozen inclusive two-day world window
An admitted request SHALL freeze world tick T and select committed deeds from max(0, T minus two canonical world days) through T inclusive. Future records SHALL be excluded. Selection SHALL NOT consume deeds or resize the window with fatigue balance. Time filtering SHALL precede aggregation.

#### Scenario: Inclusive bounds
- **WHEN** records exist at the lower bound, one tick earlier, T and T plus one
- **THEN** only the lower bound and T records qualify

#### Scenario: Canonical duration and zero clamp
- **WHEN** T is less than two configured world days
- **THEN** the lower bound is zero and the duration derives from clock configuration, currently 172800 game seconds

#### Scenario: Expired repetitions do not count
- **WHEN** matching repeated actions straddle the window boundary
- **THEN** counts include only retained committed occurrences and a later request can reuse still-current deeds

### Requirement: Recent deed eligibility is closed and personally authorized
Nomination SHALL accept only deterministic adapters for completed quests, passed exams, completed combat, settled skills, adult acts and actual adult milestones. It SHALL require personal involvement and authorized knowledge per field before grouping. Generated statements, self-reports, routine activities and protection classifications SHALL be excluded.

#### Scenario: Closed evidence set
- **WHEN** supported deeds and narrator prose, model statements, movement, waiting, commerce, conversation and encounter_protection coexist
- **THEN** only authorized supported deterministic deeds enter the stream

#### Scenario: Field privacy precedes counts
- **WHEN** a participant record contains another character's private or unknown state
- **THEN** those fields influence neither rendered facts nor aggregate counts and summaries

#### Scenario: Malformed record fails closed
- **WHEN** one eligible source is malformed beside a usable record
- **THEN** only the malformed source is omitted with a diagnostic; no substitute facts are manufactured

### Requirement: Recent deed groups retain outcomes and stable provenance
The feed SHALL group encounter actions with their outcome and combine one action's effects and milestones. Consecutive eligible repeats SHALL combine only with matching action type, participant identities/roles and encounter context. Distinct results and milestones SHALL remain traceable to immutable source IDs. Counts SHALL represent retained committed occurrences.

#### Scenario: Context boundaries stop repetition
- **WHEN** consecutive actions change roles, participants, action type or encounter
- **THEN** a new repetition group starts and different encounters never merge

#### Scenario: Action milestones do not double count
- **WHEN** one action has effects and a milestone
- **THEN** the group retains both with required source IDs and counts that action once

#### Scenario: No invented aggregate identity
- **WHEN** several sources support one group
- **THEN** the group lists immutable supporting IDs and claims no new persisted aggregate event ID

### Requirement: Recent deed rendering has complete bounded groups
Groups SHALL sort by latest included tick descending and stable source identity ascending, retaining at most eight. Event JSON, envelope and references SHALL fit 8000 Unicode code points by dropping older complete groups. Oversized singleton groups SHALL be omitted. Claims SHALL retain their outcomes and supporting IDs; empty rendering SHALL mean empty material.

#### Scenario: Deterministic tie and cap
- **WHEN** more than eight groups share several latest ticks
- **THEN** the newest eight follow stable source tie order

#### Scenario: Unicode and oversized groups
- **WHEN** non-ASCII groups and their references exceed the budget or one group cannot fit alone
- **THEN** complete groups are omitted until valid complete JSON fits, with no clipped outcome or unsupported claim

#### Scenario: No renderable evidence
- **WHEN** every eligible group is too large
- **THEN** the feed is empty and cannot justify generation

