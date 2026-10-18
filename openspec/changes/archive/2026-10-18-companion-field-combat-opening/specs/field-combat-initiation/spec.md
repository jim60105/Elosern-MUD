# Spec Delta

## ADDED Requirements

### Requirement: A companion initiator opens the commander's encounter
When `initiate_field_combat` is called with a present effective companion as the caster, the system SHALL key the session, candidate battlefield, active-session check and rollback snapshots on the resolved commander, list the commander and eligible co-located companions as the player side, record the caster as opening first actor, and seed the skill as the caster's opening draft entry.

#### Scenario: The session belongs to the commander
- **WHEN** companion 艾拉 initiates field combat against a room monster
- **THEN** the persisted session lists the commander and the present companions as the player side, the commander is the session's commander, and 艾拉's draft entry holds the opening skill

#### Scenario: A failed companion initiation leaves nothing behind
- **WHEN** session creation or the opening validation fails for a companion initiator
- **THEN** no session, draft entry, resource change, practice award or clock change remains, exactly as for a commander initiator

#### Scenario: Other initiation rules keep applying
- **WHEN** a companion initiation is validated and committed
- **THEN** availability, SINGLE/AREA engagement and combat-time rules apply as for a commander initiator, and the boundary event names both the commander and the caster
