## ADDED Requirements

### Requirement: Shipped content provides reachable friendly-fire triggers

The shipped skill set SHALL provide AREA and single-target damage paths that can hit companion NPCs, so the penalty and auto-leave contracts are reachable through ordinary player actions.

#### Scenario: AREA friendly fire is playable with shipped skills

- **WHEN** a player with a bound companion uses a shipped AREA damage skill against a group that includes the companion
- **THEN** the companion takes damage and receives one `friendly_fire` penalty per hit, with the auto-leave recheck applied

#### Scenario: Single-target misfire is playable with shipped skills

- **WHEN** a player explicitly selects a bound companion with a shipped single-target damage skill
- **THEN** the companion takes damage and receives the penalty

### Requirement: The friendly-fire scan commits with the round transaction

The damage scan, every penalty write, and any auto-leave SHALL run inside the player action round's transaction boundary (the outer round transaction introduced by the combat-settlement change), so the round's damage cannot commit with partial penalties.

#### Scenario: Penalty failure rolls back the round's damage

- **WHEN** an auto-leave write fails after the round's damage events were applied
- **THEN** the damage, penalties, and party state all roll back together

### Requirement: Healing allies or foes carries no penalty

No affinity write or penalty SHALL result from recovery skills targeting allies, companions, or enemies; the friendly-fire contract applies only to player-action damage against companion NPCs.

#### Scenario: Healing a foe is a permitted choice

- **WHEN** a player casts a recovery skill on an enemy or an ally
- **THEN** the skill resolves and no affinity record is created or modified
