## Purpose

Complete production utility attack dispatch with independent sampling, real execution identity and diagnostics. This capability defines observable behavior at the monster decision boundary.

## ADDED Requirements

### Requirement: Utility attack score reflects continuous intelligence
Attack utility SHALL equal w_damage*damage + w_preference*preference + i*(w_kill*finishing - w_cost*cost - w_waste*waste), with i=intelligence/100. Preference SHALL combine configured target, owned-skill and area bias as bounded stable ranks with shared ranks for ties.

#### Scenario: Intelligence does not grant power
- **WHEN** identical registered variants differ only in intelligence
- **THEN** stats, proficiency, ownership and legal actions remain identical; tactical terms scale continuously and win rates need not increase

#### Scenario: Six preferences
- **WHEN** all six archetypes evaluate the same synthetic options
- **THEN** instinctive simple attacks, pack_hunter weak prey/focus, brute strong-enemy pressure, tactical_caster spell efficiency, apex_predator finishing/coverage and ambush_predator single-target opening remain distinct soft preferences

### Requirement: Selection uses stable independent softmax
Selection SHALL sort by canonical skill, normalized targets and scale and sample stable softmax using maximum-score subtraction and T=1.25-1.17*i. Selection RNG SHALL be independent of combat dice and injectable. Equal scores SHALL sample uniformly; invalid scores or non-positive/non-finite temperatures SHALL fail explicitly.

#### Scenario: Reproducible independent sampling
- **WHEN** the same candidates, state, observation inputs, tuning and execution scope are replayed
- **THEN** selected requests repeat; combat hit, damage and initiative RNG state is unchanged

#### Scenario: Empty and extreme values
- **WHEN** candidates are empty, scores are large but finite, or scores/temperature are invalid
- **THEN** empty returns None, finite large values remain numerically stable, invalid numeric input is diagnosed

### Requirement: Actual execution identity distinguishes every decision
Production selection seeds SHALL use versioned SHA-256 encoding of session ID, actual round, stable actor ID, actual action-slot index and configuration fingerprint. Scope SHALL restore on return and exception while preserving two-argument providers. Inspection without scope SHALL use canonical identities and read-only snapshot fingerprint with slot zero.

#### Scenario: Multiple slots and overwhelm
- **WHEN** one actor receives multiple actions and overwhelm executes several internal rounds
- **THEN** each real slot and internal round has its distinct scope; initiative and resolution formulas remain unchanged

#### Scenario: Inspection has no hidden counter
- **WHEN** the same direct two-argument inspection repeats without state changes
- **THEN** it repeats the same selection and neither advances hidden counters nor uses wall clock, object address, display name, Python hash or unordered iteration

### Requirement: Production adapters preserve decision semantics
The session adapter SHALL construct the normal or overwhelm settlement context before selection. Selected requests SHALL retain targets including recognized shorthands and authored non-default scale. Every actual action SHALL settle through the existing resolver.

#### Scenario: End to end attack
- **WHEN** a synthetic utility monster selects a scaled AREA request through the normal adapter and separately overwhelm
- **THEN** real settlement affects only legal recipients, reload shows actual resource/effect changes, and the shorthand remains a string

#### Scenario: Rollback after action writes
- **WHEN** a fault occurs after resource or effect writes but before outer commit
- **THEN** persistent state rolls back with the existing journals and no AI path applies independent effects

### Requirement: Invalid state fallback is narrow and observable
Malformed startup tuning SHALL fail. A typed invalid runtime AI state SHALL emit a facade warning with identifiers and exception context and use configured legacy fallback or diagnostic None. Empty legal sets, unsupported individual candidates, late rejection, database errors and programming exceptions SHALL retain their normal boundaries.

#### Scenario: Failure taxonomy
- **WHEN** invalid identity and separately empty candidates, resolver rejection, DB error or unexpected exception occur
- **THEN** only typed AI invalid state receives AI fallback; other failures are not suppressed or relabeled

#### Scenario: Opt in trace
- **WHEN** detailed debugging or a manual report is requested
- **THEN** trace includes scope, algorithm/config, intelligence, seed, candidate/rejection/omission counts, feature contributions, estimation limits, normalized plans and selected request; ordinary facade context has only a bounded summary

