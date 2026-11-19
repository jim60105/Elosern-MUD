## MODIFIED Requirements

### Requirement: Custom creation mode explains its prompts
The custom text flow SHALL explain races, compatible subraces, each allocation axis, point caps and the exact total, and SHALL collect an optional bounded background through a dedicated prompt.

#### Scenario: Custom prompts carry explanations
- **WHEN** a pending player runs `character create`
- **THEN** race options and each allocation axis are explained

#### Scenario: The subrace prompt lists every available subrace
- **WHEN** the player selects a race
- **THEN** the wizard lists every compatible subrace with its display name and specialty and offers no empty selection

#### Scenario: The allocation briefing precedes the allocation step
- **WHEN** the player is about to enter allocations
- **THEN** the wizard explains the seven-axis input, selected budget, per-axis point caps, exact sum, and any conversion that differs from one point per stat unit

#### Scenario: The custom flow collects an optional background
- **WHEN** the player finishes allocating
- **THEN** the wizard prompts for bounded optional background text and carries accepted input into activation
