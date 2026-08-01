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
For a resolved profile, the service SHALL calculate an exact allocation budget of `floor(sum(axis_max - axis_min) / 2)` across the six allocable axes. Each allocation SHALL be an integer from zero through that axis's inclusive span, and all six allocations SHALL sum exactly to the profile budget. The service SHALL set each pre-modifier trait value to its lower bound plus its allocation.

#### Scenario: A balanced allocation is accepted
- **WHEN** a custom player provides six in-range allocations whose sum exactly equals the resolved profile budget
- **THEN** activation accepts the allocation and uses those values as the profile's pre-modifier starting stats

#### Scenario: An all-maximum allocation is rejected
- **WHEN** a custom player allocates more than the exact profile budget across the six axes
- **THEN** activation is rejected before any character state is changed

#### Scenario: An underpowered allocation is rejected
- **WHEN** a custom player allocates fewer than the exact profile budget across the six axes
- **THEN** activation is rejected before any character state is changed

#### Scenario: Skill multipliers cannot be allocated or stored
- **WHEN** custom creation is inspected or invoked with its allowed stat input
- **THEN** it has no input or write path for ×10, ×100, or ×1000 skill multipliers, and all stored values remain base traits

### Requirement: Starting magic level is sampled from a race-owned average band
`RaceProfile.starting_magic_level` SHALL be the sole source of a newly active player character's average starting magic level. After all other creation preflight succeeds, the service SHALL calculate `low = (average * 9 + 9) // 10` and `high = average * 11 // 10`, then sample one uniform integer in the inclusive `low..high` interval. It SHALL reject an invalid interval, non-integer sample, or a sample outside either `low..high` or the selected race's `0..magic_cap` range before assigning it to `traits.magic_level`. The command shall not accept a player-selected magic level, and preset activation SHALL use the same sampling rule.

#### Scenario: Human starting magic level stays within its ten-percent band
- **WHEN** a human player character is activated with an injected sampler returning either endpoint
- **THEN** its `magic_level` is respectively 27 or 33, within the human magic cap of 90

#### Scenario: Beastfolk and elf starting levels use their own race averages
- **WHEN** beastfolk and elf player characters are activated with injected endpoint samplers
- **THEN** their allowed ranges are respectively 9–11 and 270–330, never a human-derived range

#### Scenario: A rejected request cannot reroll magic level
- **WHEN** a request fails identity or allocation preflight
- **THEN** the injected sampler is not called and the character has no persisted magic-level value

#### Scenario: An invalid sampler result is rejected before persistence
- **WHEN** an injected sampler returns a non-integer, a value below `low`, or a cap-safe value above `high`
- **THEN** activation is rejected before any character state is changed
