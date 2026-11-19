## MODIFIED Requirements

### Requirement: Custom starting stats require one exact finite allocation budget
Custom allocation SHALL contain exactly the seven allocation keys with integer points within their profile caps and SHALL sum to the exact profile budget. Non-elf custom creation and preset resolution SHALL retain the raw-increment policy.

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

## ADDED Requirements

### Requirement: Custom elf allocation converts points to starting stats
The custom elf policy SHALL use the sum of physical spans as the exact budget and SHALL interpolate magic power to the configured creation cap before existing subrace modifiers apply.

#### Scenario: Both custom-elf endpoints are reachable
- **WHEN** a custom elf spends everything on magic or fills only the physical axes
- **THEN** fixed gauges accept zero points, each physical axis accepts zero through its span and magic accepts zero through the budget
- **AND** before modifiers, the former allocation yields the creation magic cap with physical floors and the latter yields the lore magic floor with all physical axes at their maxima

#### Scenario: Mixed allocations are deterministic
- **WHEN** a valid allocation includes both magic and physical points
- **THEN** each physical value is its lore floor plus allocated points and magic is its lore floor plus the nearest integer to `(creation_cap - lore_floor) * magic_points / budget`
- **AND** an exact half rounds upward and existing subrace modifiers apply once after conversion

### Requirement: Creation surfaces use the selected allocation policy
WebClient and text creation SHALL expose the selected profile's budget and point bounds. WebClient SHALL preview the resulting values from server policy data and SHALL NOT interpret point caps as raw stat spans. Previously saved custom-elf drafts using the superseded policy SHALL require fresh allocation without losing non-allocation data or draft portrait state.

#### Scenario: A saved custom-elf draft predates the policy
- **WHEN** a player resumes a superseded draft with saved allocations
- **THEN** the player must allocate again and cannot activate with those saved points, while identity, prose and portrait remain

#### Scenario: Preview uses the custom policy
- **WHEN** a complete custom allocation is previewed
- **THEN** the resulting values match activation at the pre-modifier stage
