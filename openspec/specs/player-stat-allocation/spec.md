## Purpose

Define lore-derived player starting-stat allocation and bounded starting magic rolls.

## Requirements

### Requirement: Player starting profiles are derived from immutable lore bands
The deterministic creation service SHALL resolve custom-player bounds for `hp`, `mp`, `sp`, `atk_phys`, `agility`, and `defense` from the selected `RaceProfile` and, where applicable, the compatible `Subrace`. Vital overrides shall replace their race vital band; static modifiers SHALL be applied after allocation in the same order and `round(value * (1 + modifier))` behavior used by normal trait construction. The service SHALL not contain a hardcoded stat bound or balance constant for a specific race or subrace.

#### Scenario: A foxkin profile uses its MP override
- **WHEN** a player selects `race="beastfolk"` and `subrace="foxkin"`
- **THEN** its allocable MP bounds are the foxkin vital override rather than the beastfolk race MP band

#### Scenario: A catkin profile applies its physical modifier after allocation
- **WHEN** a player selects `race="beastfolk"`, `subrace="catkin"`, and a valid raw physical allocation
- **THEN** the final physical trait values equal the allocated race values with catkin's documented static modifiers applied once

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
