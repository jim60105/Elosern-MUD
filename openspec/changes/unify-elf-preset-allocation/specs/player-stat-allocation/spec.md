## MODIFIED Requirements

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
