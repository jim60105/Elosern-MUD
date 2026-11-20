## Purpose

Define lore-derived player starting-stat allocation and bounded starting magic rolls.

## Requirements

### Requirement: Player starting profiles are derived from immutable lore bands
The deterministic creation service SHALL resolve custom-player bounds for `hp`, `mp`, `sp`, `atk_phys`, `agility`, and `defense` from the selected `RaceProfile` and, where applicable, the compatible `Subrace`. The bounds-plus-allocation-plus-modifier computation SHALL have exactly one implementation, exposed as the pure function `resolve_preset_values(preset)` in `world/rules/character_creation.py`.

#### Scenario: A foxkin profile uses its MP override
- **WHEN** a player selects `race="beastfolk"` and `subrace="foxkin"`
- **THEN** its allocable MP bounds are the foxkin vital override rather than the beastfolk race MP band

#### Scenario: A catkin profile applies its physical modifier after allocation
- **WHEN** a player selects `race="beastfolk"`, `subrace="catkin"`, and a valid raw physical allocation
- **THEN** the final physical trait values equal the allocated race values with catkin's documented static modifiers applied once

#### Scenario: One resolver owns the computation
- **WHEN** `resolve_preset_values` is called for a shipped preset and that same preset is activated as a player character
- **THEN** the resolver's returned values equal the trait values activation persists, axis for axis

#### Scenario: The resolver is pure
- **WHEN** `resolve_preset_values` is called with only a preset
- **THEN** it returns the value map without touching an account, a character, the database, or the world clock

#### Scenario: Vital overrides and static modifiers follow normal trait construction
- **WHEN** a resolved profile carries subrace vital overrides and static modifiers
- **THEN** the overrides replace their race vital band, and static modifiers are applied after allocation in the same order and `round(value * (1 + modifier))` behavior used by normal trait construction

#### Scenario: No hardcoded race or subrace constants in the service
- **WHEN** the creation service is searched for balance data
- **THEN** it contains no hardcoded stat bound or balance constant for a specific race or subrace

#### Scenario: Every preset consumer shares one implementation
- **WHEN** player activation preflight today, or any later non-player consumer of the same card, needs a preset's final values
- **THEN** each derives identical numbers from one implementation and cannot drift

### Requirement: Custom starting stats require one exact finite allocation budget
Custom and preset allocations SHALL contain exactly the seven allocation keys with integer points within their profile caps and SHALL sum to the exact profile budget. Both paths SHALL use the same race-specific allocation policy. Non-elf profiles SHALL retain the raw-increment policy.

#### Scenario: Raw increments are unchanged
- **WHEN** a non-elf custom or preset profile resolves
- **THEN** each axis accepts zero through its lore span, the budget is the floor of half the sum of spans, and each pre-modifier value is its lore floor plus its allocated points

#### Scenario: Invalid allocations are rejected
- **WHEN** an axis is missing or unexpected, a point value is non-integer or outside its cap, or the total differs from the exact budget
- **THEN** activation is rejected before character state changes

#### Scenario: A balanced allocation is accepted
- **WHEN** all seven allocations are in range and sum to the profile budget
- **THEN** activation accepts the allocation and uses the selected profile's conversion

#### Scenario: An all-maximum allocation is rejected
- **WHEN** the player submits each axis at its maximum and their sum exceeds the budget
- **THEN** activation is rejected before any character state changes

#### Scenario: An underpowered allocation is rejected
- **WHEN** the allocations sum to less than the exact budget
- **THEN** activation is rejected before any character state changes

#### Scenario: Skill multipliers cannot be allocated or stored
- **WHEN** starting allocation is resolved
- **THEN** allocated values remain base traits, with no input or write path for skill multipliers

### Requirement: Custom elf allocation converts points to starting stats
The elf policy SHALL use the sum of physical spans as the exact budget and SHALL interpolate magic power to the configured creation cap before existing subrace modifiers apply. The same policy SHALL govern elf presets, including their use as starting companions.

#### Scenario: Both custom-elf endpoints are reachable
- **WHEN** a custom elf spends everything on magic or fills only the physical axes
- **THEN** fixed gauges accept zero points, each physical axis accepts zero through its span and magic accepts zero through the budget
- **AND** before modifiers, the former allocation yields the creation magic cap with physical floors and the latter yields the lore magic floor with all physical axes at their maxima

#### Scenario: Mixed allocations are deterministic
- **WHEN** a valid allocation includes both magic and physical points
- **THEN** each physical value is its lore floor plus allocated points and magic is its lore floor plus the nearest integer to `(creation_cap - lore_floor) * magic_points / budget`
- **AND** an exact half rounds upward and existing subrace modifiers apply once after conversion

#### Scenario: An elf preset uses the same conversion as a custom elf
- **WHEN** an elf preset and a custom elf of the same subrace have identical allocations
- **THEN** both resolve to the same starting base values, and a newly constructed starting companion based on that preset uses those same values

### Requirement: Creation surfaces use the selected allocation policy
WebClient and text creation SHALL expose the selected profile's budget and point bounds. WebClient SHALL preview the resulting values from server policy data and SHALL NOT interpret point caps as raw stat spans. Previously saved custom-elf drafts using the superseded policy SHALL require fresh allocation without losing non-allocation data or draft portrait state.

#### Scenario: A saved custom-elf draft predates the policy
- **WHEN** a player resumes a superseded draft with saved allocations
- **THEN** the player must allocate again and cannot activate with those saved points, while identity, prose and portrait remain

#### Scenario: Preview uses the custom policy
- **WHEN** a complete custom allocation is previewed
- **THEN** the resulting values match activation at the pre-modifier stage
