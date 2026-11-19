## MODIFIED Requirements

### Requirement: Custom starting stats require one exact finite allocation budget
All seven allocation keys SHALL be present with integer points within their profile caps and SHALL sum to the exact budget. For non-elf custom creation, the budget remains `floor(sum(axis_max - axis_min) / 2)` and the pre-modifier value remains the lore floor plus allocated points. For custom elves, fixed gauges SHALL receive zero points, the budget SHALL equal the sum of the three physical spans, each physical point SHALL add one to its stat, and magic SHALL accept up to the whole budget. Magic power SHALL be the lore floor plus the nearest integer to `(creation_cap - lore_floor) * magic_points / budget`, with ties rounded upward. The initial creation cap SHALL be 200. Preset resolution SHALL retain its existing raw-increment policy.

#### Scenario: Both custom-elf endpoints are reachable
- **WHEN** a custom elf spends everything on magic or fills only the physical axes
- **THEN** the former starts at the creation magic cap with physical floors, and the latter starts at the lore magic floor with all physical axes at their maxima

#### Scenario: Mixed allocations are deterministic
- **WHEN** a valid custom-elf allocation includes both magic and physical points
- **THEN** the resolved values follow the selected profile's interpolation and physical increments, identically in preview and activation

#### Scenario: Invalid allocations are rejected
- **WHEN** any axis is missing, non-integer, outside its cap, or the total differs from the exact budget
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

### Requirement: Creation surfaces use the selected allocation policy
WebClient and text creation SHALL expose the selected profile's budget and point bounds. WebClient SHALL preview the resulting values from server policy data and SHALL NOT interpret point caps as raw stat spans. Previously saved custom-elf drafts using the superseded policy SHALL require fresh allocation without losing non-allocation data or draft portrait state.

#### Scenario: A saved custom-elf draft predates the policy
- **WHEN** a player resumes a superseded draft with saved allocations
- **THEN** the player must allocate again and cannot activate with those saved points, while identity, prose and portrait remain
