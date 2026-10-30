# Spec Delta

## Purpose

Calculate ground sight and transient distant sightings from validated policy. This capability owns its observable mechanism and rejection boundaries.

## ADDED Requirements

### Requirement: Ground sight derives from phase and observer inputs
Sight SHALL derive the current ground disc from validated light policy, observer terrain, prominence and vantage without changing gameplay state.

#### Scenario: Boundaries and overrides
- **WHEN** an injected policy is evaluated at every phase boundary, tier and canopy/vantage combination
- **THEN** starting phases, max/override rules and independently known radius0/8 disc edges match

#### Scenario: Policy consumption
- **WHEN** one synthetic radius or hour changes
- **THEN** only corresponding derived results change without a duplicate shipped table

### Requirement: Distant sightings disclose approximate current observations
Sight SHALL emit only currently visible non-hidden sources outside ground sight as bearing, rounded distance and silhouette, naming them only for a lit district.

#### Scenario: Visibility and rounding
- **WHEN** synthetic sources cross phase/range/disc/sector/distance-tie boundaries and canopy
- **THEN** visibility and rounding follow design.md, canopy yields none, night yields lights only and hidden sources never appear

#### Scenario: Name and source privacy
- **WHEN** a visible source district lights or a landmark references a settlement
- **THEN** only the permitted name changes, duplicate sources merge and no target coordinates or registry keys serialize

#### Scenario: Automatic settlement silhouette is anonymous
- **WHEN** an unlit non-hidden settlement has identifying name/description but no authored landmark silhouette
- **THEN** its marker selects the validated kind/phase silhouette policy and never substitutes identifying location text; missing kind coverage rejects policy loading
