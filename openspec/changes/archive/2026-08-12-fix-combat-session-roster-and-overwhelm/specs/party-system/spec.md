## ADDED Requirements

### Requirement: Combat settlement includes companions in the regen scope

The terminal settlement of a combat session SHALL apply the combat-time gauge regen to every living, non-fled roster member, including bound companions, so a knocked-out companion can recover above the nonlethal HP floor and rejoin later engagements.

#### Scenario: Knocked-out companion recovers through combat settlement

- **WHEN** a session with a companion floored at 1 HP reaches a terminal outcome whose accumulated combat seconds exceed what its regen needs to rise above 1
- **THEN** the companion's HP rises above 1 and the companion is eligible for a later engagement
