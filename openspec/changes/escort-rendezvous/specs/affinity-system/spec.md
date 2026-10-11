# Spec Delta

## MODIFIED Requirements

### Requirement: The party auto-leave recheck hook runs after negative affinity deltas
Every negative affinity delta SHALL run the canonical party recheck. A valid active exact escort reason SHALL suppress automatic departure while relationship changes and lawful damage remain. General-only companions SHALL retain existing threshold departure, possession handback, notification and rollback behavior. Invalid/stale reasons SHALL grant no exemption.

#### Scenario: The hook is invoked on negative deltas
- **WHEN** a negative delta is applied through the sole-writer API
- **THEN** the auto-leave recheck hook runs once with the affected NPC and player

#### Scenario: A below-threshold drop ends a companion party
- **WHEN** a general-only companion with no valid escort reason crosses below the ordinary threshold
- **THEN** ordinary departure and its transactional returned notification remain; a valid escort instead preserves membership while the affinity delta commits

#### Scenario: A failed auto-leave rolls back the affinity write
- **WHEN** the leave write fails after the affinity value was lowered below the threshold
- **THEN** the affinity value and both party attributes return to their pre-delta values and no
  notification is emitted

#### Scenario: A non-companion negative delta changes nothing
- **WHEN** a negative delta applies to an NPC that is not a companion
- **THEN** the hook runs, no party call occurs, and no notification is emitted

#### Scenario: The writer returns the notification line but never sends it
- **WHEN** an auto-leave fires during a negative-delta write
- **THEN** the write API returns the auto-leave notification line, which the caller SHALL send to the player only after its own transaction commits — the writer never sends it

#### Scenario: A drop that stays at or above the threshold keeps the party
- **WHEN** a bound companion's affinity drops by a negative delta but stays at or above 70
- **THEN** the party is not ended

#### Scenario: The hook is deterministic
- **WHEN** the same negative delta and companion state are replayed
- **THEN** the hook produces the same recheck outcome, and it is side-effect free for non-companions

#### Scenario: Valid escort survives friendly fire and low affinity
- **WHEN** a lawful friendly-fire hit damages a temporary or dual member and its penalty crosses below the ordinary threshold
- **THEN** damage and affinity penalty commit through current owners without automatic departure or possession handback while a valid escort reason remains
