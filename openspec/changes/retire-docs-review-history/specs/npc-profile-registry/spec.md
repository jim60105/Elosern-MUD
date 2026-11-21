# Spec Delta

## MODIFIED Requirements

### Requirement: Authored host dialogue preserves service semantics
Every shipped host dialogue SHALL retain its declared service interactions, bounded in-character greeting/responses and individual voice without fixed prices, stock counts or live availability prose. Prose SHALL remain editable without literal-text tests, and tests SHALL establish coverage and behavior rather than editorial quality. Editorial judgement stays with the owning change and is not a committed Docsify ledger.

#### Scenario: Registry-derived rewrite coverage
- **WHEN** the authored dialogue corpus is reviewed
- **THEN** every live host/table is covered, including newly added sources; keyword actions and service behavior remain verified

#### Scenario: Editorial evidence has complete source coverage
- **WHEN** an editorial review is recorded for a characterization change
- **THEN** it covers every affected live source in the owning change's artifacts, and no committed Docsify ledger is required

#### Scenario: Rewording
- **WHEN** a valid greeting, response or misunderstanding line is reworded
- **THEN** behavior and coverage tests pass without updating expected prose; no command/mechanic/UI term or shared placeholder is accepted

#### Scenario: Shared service labels
- **WHEN** two hosts legitimately expose the same keyword labels
- **THEN** valid individual cards and voice are accepted without requiring globally unique keyword sets
