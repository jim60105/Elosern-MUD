# Spec Delta

## Purpose

Generate deterministic physical elevation and prominence offline. This capability owns its observable mechanism and rejection boundaries.

## ADDED Requirements

### Requirement: Elevation generation is deterministic and physically constrained
The offline generator SHALL derive identical band and prominence rasters from identical terrain, ordered shapes and versioned configuration while preserving physical constraints.

#### Scenario: Physical synthetic frame
- **WHEN** a fixed frame contains sea, ridge, waterways, canopy and overlapping shapes
- **THEN** repeat bytes match, sea is zero, ridge exceeds adjacent lowlands, rivers do not exceed banks, shape order applies and canopy/no_prominence tiers are zero

#### Scenario: Prominence and noise mechanisms
- **WHEN** synthetic ring thresholds, tiny components and fixed residual noise are evaluated
- **THEN** tier transitions and minimum-area suppression match known results and directional autocorrelation meets design.md limits
