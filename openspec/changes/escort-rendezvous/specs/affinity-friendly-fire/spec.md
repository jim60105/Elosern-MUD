# Spec Delta

## MODIFIED Requirements

### Requirement: Friendly-fire penalties below the invite threshold end the companion party
Every negative affinity delta SHALL run the canonical party recheck. A valid active exact escort reason SHALL suppress automatic departure while relationship changes and lawful damage remain. General-only companions SHALL retain existing threshold departure, possession handback, notification and rollback behavior. Invalid/stale reasons SHALL grant no exemption.

#### Scenario: A drop below 70 triggers auto-leave with notification
- **WHEN** friendly-fire damage lowers a general-only companion below the ordinary threshold with no valid escort source
- **THEN** ordinary departure notifies after commit; an escort control receives real damage/penalty but keeps membership

#### Scenario: A drop that stays at or above 70 keeps the party
- **WHEN** a friendly-fire penalty leaves the affinity at or above 70
- **THEN** the binding stays and no notification is emitted

#### Scenario: A failed auto-leave rolls back the penalty
- **WHEN** the leave write fails after a friendly-fire penalty lowered the affinity below the
  threshold
- **THEN** the affinity value and both party attributes return to their pre-round values

#### Scenario: A companion that left mid-round no longer qualifies in a later round
- **WHEN** a player action in a subsequent round damages an NPC that left the party in an earlier
  round
- **THEN** the later hit writes nothing, because membership is re-snapshotted per round

#### Scenario: Valid escort survives friendly fire and low affinity
- **WHEN** a lawful friendly-fire hit damages a temporary or dual member and its penalty crosses below the ordinary threshold
- **THEN** damage and affinity penalty commit through current owners without automatic departure or possession handback while a valid escort reason remains
