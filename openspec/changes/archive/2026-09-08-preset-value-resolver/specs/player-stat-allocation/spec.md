# player-stat-allocation delta

## MODIFIED Requirements

### Requirement: Player starting profiles are derived from immutable lore bands
The deterministic creation service SHALL resolve custom-player bounds for `hp`, `mp`, `sp`, `atk_phys`, `agility`, and `defense` from the selected `RaceProfile` and, where applicable, the compatible `Subrace`. Vital overrides shall replace their race vital band; static modifiers SHALL be applied after allocation in the same order and `round(value * (1 + modifier))` behavior used by normal trait construction. The service SHALL not contain a hardcoded stat bound or balance constant for a specific race or subrace. The bounds-plus-allocation-plus-modifier computation SHALL have exactly one implementation, exposed as the pure function `resolve_preset_values(preset)` in `world/rules/character_creation.py`, which takes no account and no character and performs no write, so every consumer of a preset's final values — player activation preflight today, and any later non-player consumer of the same card — derives identical numbers from one implementation and cannot drift.

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
