# Spec Delta

## ADDED Requirements

### Requirement: Released control preserves owner physiology and rederives the view
Possession release SHALL leave the owner's accepted sleep/posture intact and grant no ordinary sleeping-body action authority. After verified release, a still-sleeping owner with no companion possession SHALL receive the dream question regardless of other companions' sleep. An already-awake owner SHALL return to ordinary play without that question. Release SHALL add no time.

#### Scenario: Early release
- **WHEN** owner sleep is followed by companion possession then explicit release before the owner's wake target
- **THEN** the owner remains asleep, ordinary actions reject, and owner-bound optional dream entry is asked even with an awake companion present

#### Scenario: Late release
- **WHEN** the owner has passively awakened while the player possesses a companion and the player releases
- **THEN** ordinary owner control returns without a dream question or a second wake

#### Scenario: Sleeping companion chain
- **WHEN** controlled companions sleep in sequence and the player releases the final possession while the owner still sleeps
- **THEN** no companion becomes dream owner and the resulting released view asks about the owner's dream

#### Scenario: Transfer fault
- **WHEN** release or companion-to-companion handoff fails after session, lock, cmdset or mirrored-control writes
- **THEN** all touched persisted/cache/control/location surfaces restore, no new view claims transfer success and tick is unchanged

#### Scenario: Reconnect and lifecycle cleanup
- **WHEN** disconnect cleanup releases a companion and the authenticated player reconnects onto a still-sleeping owner
- **THEN** no wall-clock recovery occurs and the canonical released view restores its existing receipt and decision without replaying sleep entry or transfer
