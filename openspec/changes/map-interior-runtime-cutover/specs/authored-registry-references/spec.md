# Spec Delta

## MODIFIED Requirements

### Requirement: Cached bidirectional integrity model
Reference indexes SHALL expose source fields, inverse referrers and complete dangling-target diagnostics, reusing immutable results only within the owning registry snapshot and rebuilding after map publication.

#### Scenario: Bidirectional and cached results
- **WHEN** references from nested and repeated synthetic entries are indexed twice
- **THEN** forward and inverse maps agree, each referrer is attributable to its source and field path, and immutable results are reused without rescanning

#### Scenario: Invalid declarations and missing keys
- **WHEN** fixtures declare an absent target registry, duplicate inverse declarations into one target, or missing target keys
- **THEN** contracts reject invalid declarations and integrity diagnostics identify every missing key with the required five fields

#### Scenario: Shipped reference acceptance
- **WHEN** all first-batch shipped references are checked in CI
- **THEN** the dangling list is empty and non-map checks retain their CI-only contract; map adoption separately validates its authoritative closure

#### Scenario: Declaration validity rules
- **WHEN** reference declarations are registered
- **THEN** every declaration names an indexed registry, distinct reference declarations into the same target registry have distinct inverse names, and repeated instances of one declaration do not constitute inverse-name collisions

#### Scenario: Shipped data corrected before acceptance
- **WHEN** shipped data is checked for dangling references
- **THEN** the checks produce no dangling references, and any first-batch dangling data is corrected before acceptance

#### Scenario: Checks are CI contracts only
- **WHEN** the integrity checks run
- **THEN** non-map checks remain CI contracts, while map adoption validates its map-facing closure before publication

