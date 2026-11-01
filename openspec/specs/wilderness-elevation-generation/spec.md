# wilderness-elevation-generation Specification

## Purpose
Generate deterministic physical elevation and prominence offline. This capability owns its observable mechanism and rejection boundaries.

## Requirements

### Requirement: Elevation generation is deterministic and physically constrained
The offline generator SHALL derive identical band and prominence rasters from identical terrain, ordered shapes and versioned configuration, using the maximum active stem-or-arm ridge rise while preserving physical constraints.

#### Scenario: Physical synthetic frame
- **WHEN** a fixed frame contains sea, ridge, waterways, canopy and overlapping shapes
- **THEN** repeat bytes match, sea is zero, ridge exceeds adjacent lowlands, rivers do not exceed banks, shape order applies and canopy/no_prominence tiers are zero

#### Scenario: Prominence and noise mechanisms
- **WHEN** synthetic ring thresholds, tiny components and fixed residual noise are evaluated
- **THEN** tier transitions and minimum-area suppression match known results and directional autocorrelation meets the established design limits

#### Scenario: Fork relief uses maximum
- **WHEN** synthetic active stem and arm profiles overlap at the crotch or in their shoulders
- **THEN** the mountain contribution equals the greatest profile contribution, never their sum; both arm centres rise above the no-ridge control and inactive rows get no rise from that crest

#### Scenario: Forest arms retain canopy
- **WHEN** arms lie inside synthetic deep forest
- **THEN** their elevation rises without changing region classification or producing a nonzero forest prominence tier

#### Scenario: Zero-width relief keeps centre semantics
- **WHEN** a synthetic zero-half-width crest bends across adjacent columns
- **THEN** its pre-clamp ridge contribution raises active centres and leaves non-centre bend-closure cells at zero contribution, while all physical span cells still block traversal and sea remains band zero
