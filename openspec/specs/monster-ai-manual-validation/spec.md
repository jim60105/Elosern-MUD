# monster-ai-manual-validation Specification

## Purpose
Provide isolated manual encounter, paired-selector and whole-policy performance evidence outside default tests. This capability defines observable behavior at the monster decision boundary.

## Requirements

### Requirement: Manual campaign has the approved finite allocation
Manual acceptance SHALL use six archetypes, six synthetic situations, two documented seeds and intelligence 10/90, totaling 24 encounters per archetype and 144 utility encounters. Intelligence SHALL be the only paired variant difference. Encounters SHALL use real production settlement and committed reload.

#### Scenario: Six distinct situations
- **WHEN** each archetype campaign executes
- **THEN** finishing, area versus single, resource exhaustion, mandatory targeting, support/focus and long lifecycle are each exercised twice at both intelligence values

#### Scenario: Bounded outcome
- **WHEN** an encounter terminates or reaches 30 actual rounds
- **THEN** terminal win/loss is reported; the bound is labeled capped/unresolved and never counted as terminal; illegal action or simulator bug fails the batch

#### Scenario: Isolated operations
- **WHEN** one named campaign is invoked
- **THEN** only its 24 encounters run with empty memory, isolated scratch database, stable scenario/archetype seed encoding and recorded decision/combat seeds; live and retained test databases remain untouched

### Requirement: Paired selector evidence measures a fixed utility gap
A standalone manual selector check SHALL compare exactly two legal candidates with utility gap 0.5 using the same 128 documented injected seeds at intelligence 10/90. High-intelligence highest-utility frequency SHALL exceed low by at least 15 percentage points. Counts, paired difference and Wilson intervals SHALL be reported.

#### Scenario: Selector replay
- **WHEN** the manual check is repeated with identical input, seeds and configuration
- **THEN** every chosen candidate repeats; the operation runs no encounters and reports no win-rate conclusion

### Requirement: Performance evidence measures the complete policy
Manual performance SHALL time snapshot, legality, estimation, scoring, sampling and configured trace overhead using monotonic wall clock and actual ORM queries. The reference envelope SHALL use 16 live participants, up to 16 owned active skills and 256 candidate budget. Warm utility p95 SHALL be at most 50 ms on the recorded host.

#### Scenario: Warm and cold comparison
- **WHEN** legacy and utility performance are measured on fixed snapshot state
- **THEN** each has a separate cold first call, five warm-ups and 50 measurements; report p50/p95, examined/accepted/omitted candidates, queries and isolated dice state

#### Scenario: Candidate query scaling
- **WHEN** candidate count varies on identical actor/participant data
- **THEN** query work can scale with initial participants/skills, never their subsequent target plans; failure requires profiling without reducing the timed boundary or silently increasing the limit

### Requirement: Manual reports preserve evidence and uncertainty
Reports SHALL provide machine-readable JSON and compact Markdown interpretation with baseline commit, algorithm/config fingerprints, versions, host/clock, scenarios, seeds, initial memory, intelligence, raw paired results, approximation flags, omissions and unresolved outcomes. Detailed traces SHALL be opt-in and exclude hidden intent.

#### Scenario: Encounter metrics
- **WHEN** an archetype report completes
- **THEN** win/loss/capped counts, mean-round denominators, highest-utility fraction, skill distribution, target concentration, candidate rejections, selected-illegal count and no-action counts distinguish legal restriction, estimator exclusion and budget omission

#### Scenario: Small sample interpretation
- **WHEN** paired encounter outcomes differ
- **THEN** interpretation states uncertainty and does not claim balance certification or monotonically increasing win rates; replay includes initial observation data

### Requirement: Manual operations remain separate from default verification
Manual selector, one named archetype and performance operations SHALL be explicit and independent. They SHALL NOT execute in startup, default test discovery, CI or contract gates. Ordinary and overwhelm production smoke SHALL separately verify real context and internal round/slot identity.

#### Scenario: Discovery isolation
- **WHEN** default permanent tests and contract gates run
- **THEN** the manual campaign is not discovered or invoked; small deterministic tests cover numerical replay, legal settlement and tool/report boundaries

#### Scenario: Short local operations
- **WHEN** a campaign operation is expected to exceed ten minutes
- **THEN** named scenario batches are used before execution, preserving the total allocation without running full CI shards or browser suites
