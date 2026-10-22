# Spec Delta

## ADDED Requirements

### Requirement: Settled deeds retain readable location snapshots
Every supported recent-deed producer SHALL persist a bounded location reference with its immutable occurrence, using the source's actual settlement location. The reference SHALL contain a durable identity and a readable label sufficient for later rendering. Unknown location SHALL remain explicitly unknown rather than be inferred at read time.

#### Scenario: Quest and action facts carry their settled locations
- **WHEN** a quest completion and a skill or adult action commit in distinct rooms
- **THEN** each fact retains its own location identity and readable label without consulting a mutable live room at selection time

#### Scenario: Compressed occurrence keeps the right location
- **WHEN** consecutive matching occurrences happen in different locations
- **THEN** retained occurrence context preserves each occurrence's own location instead of assigning the first location to all of them
