## Purpose
The single predicate deciding who counts as a player actor for world clock advancement and trigger purposes.

## Requirements

### Requirement: One predicate decides player-driven entity status
`world/rules/player_control.py` SHALL provide `is_player_driven(entity) -> bool`, true exactly when the entity is a puppeted `PlayerCharacter` (the existing check, unchanged) OR an `NPC` whose `db.possessed_by` is non-null and which is currently puppeted (`entity.sessions.count() > 0`). It SHALL be the project's ONLY such predicate: movement charging, the room-entry action-options trigger, and any future player-actor gate SHALL import it rather than re-implementing the OR. An NPC whose `db.possessed_by` is stale (attribute set, no session puppet — the disconnect window before release lands) SHALL read NOT player-driven.

#### Scenario: A puppeted player character is player-driven
- **WHEN** `is_player_driven` is called on a session-puppeted `PlayerCharacter`
- **THEN** it returns true

#### Scenario: A possessed-and-puppeted NPC is player-driven
- **WHEN** it is called on an NPC with `db.possessed_by` set and a live puppet session
- **THEN** it returns true

#### Scenario: An ordinary NPC is not
- **WHEN** it is called on an unpossessed NPC, or a possessed-but-unpuppeted NPC
- **THEN** it returns false

#### Scenario: The predicate is the only such gate
- **WHEN** the repository is searched for inline `isinstance(... PlayerCharacter)` checks in movement or trigger code paths
- **THEN** only `player_control.py` carries that shape in those paths
