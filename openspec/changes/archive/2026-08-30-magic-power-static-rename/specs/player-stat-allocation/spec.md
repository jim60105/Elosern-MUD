## MODIFIED Requirements

### Requirement: Custom starting stats require one exact finite allocation budget
For a resolved profile, the service SHALL calculate an exact allocation budget of `floor(sum(axis_max - axis_min) / 2)` across the seven allocable axes (the four static axes plus the three gauges). Each allocation SHALL be an integer from zero through that axis's inclusive span, and all seven allocations SHALL sum exactly to the profile budget. The service SHALL set each pre-modifier trait value to its lower bound plus its allocation.

#### Scenario: A balanced allocation is accepted
- **WHEN** a custom player provides seven in-range allocations whose sum exactly equals the resolved profile budget
- **THEN** activation accepts the allocation and uses those values as the profile's pre-modifier starting stats

#### Scenario: An all-maximum allocation is rejected
- **WHEN** a custom player allocates more than the exact profile budget across the seven axes
- **THEN** activation is rejected before any character state is changed

#### Scenario: An underpowered allocation is rejected
- **WHEN** a custom player allocates fewer than the exact profile budget across the seven axes
- **THEN** activation is rejected before any character state is changed

#### Scenario: Skill multipliers cannot be allocated or stored
- **WHEN** custom creation is inspected or invoked with its allowed stat input
- **THEN** it has no input or write path for ×10, ×100, or ×1000 skill multipliers, and all stored values remain base traits

## REMOVED Requirements

### Requirement: Starting magic level is sampled from a race-owned average band
**Reason**: `RaceProfile.starting_magic_level` and the magic cap are deleted;
`magic_power` is an ordinary allocable static axis, so there is no magic-only sampler
left to own a starting value.
**Migration**: custom creation allocates `magic_power` through the exact-budget static
path (seventh axis), and presets fix it as a literal. The sampler helper, its
validation, and its injection seam are deleted outright.
