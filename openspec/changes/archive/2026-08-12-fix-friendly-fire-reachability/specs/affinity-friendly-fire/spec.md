## MODIFIED Requirements

### Requirement: The scan, penalties, and auto-leave commit atomically with the round
The damage scan, every penalty write, and any resulting auto-leave SHALL run inside the player
action round's transaction boundary, so a failure anywhere rolls the whole round's affinity effects
back and the round's damage result cannot commit with partial penalties. The scan SHALL run inside
the outer round transaction of the player action (the transaction that also persists the round's
damage and session metadata), so a penalty failure rolls back the round's damage together with the
penalties and party state. The auto-leave
notification SHALL be delivered to the player only after the transaction commits. Companion
membership for the round SHALL be snapshotted at scan time: a companion that leaves the party
because of an earlier hit in the same round still qualifies for every hit that round, so the
penalty count never depends on the iteration order of damage events.

#### Scenario: A mid-round leave does not cancel later hits
- **WHEN** the first hit of a player action drops a companion below the threshold (auto-leave
  fires) and the same action's later event hits that companion again
- **THEN** the later hit still applies its penalty, because the round's qualifying membership was
  snapshotted before the penalties began

#### Scenario: A compression is scanned once after it resolves
- **WHEN** a player action resolves through overwhelm compression (multiple raw rounds compressed
  into one resolved player action round)
- **THEN** the scan runs once over the compression's player-action damage events after the
  compression resolves, and the same per-hit penalty, snapshot, and auto-leave contracts hold

#### Scenario: A failure rolls back every penalty
- **WHEN** the leave write fails after an earlier hit of the same action already applied a penalty
- **THEN** every penalty of that round rolls back with the round's transaction and no notification
  is emitted

#### Scenario: Penalty failure rolls back the round's damage
- **WHEN** an auto-leave write fails after the round's damage events were applied
- **THEN** the damage, penalties, and party state all roll back together

## ADDED Requirements

### Requirement: Shipped content provides reachable friendly-fire triggers

The shipped skill set SHALL provide AREA and single-target damage paths that can hit companion NPCs, so the penalty and auto-leave contracts are reachable through ordinary player actions.

#### Scenario: AREA friendly fire is playable with shipped skills

- **WHEN** a player with a bound companion uses a shipped AREA damage skill against a group that includes the companion
- **THEN** the companion takes damage and receives one `friendly_fire` penalty per hit, with the auto-leave recheck applied

#### Scenario: Single-target misfire is playable with shipped skills

- **WHEN** a player explicitly selects a bound companion with a shipped single-target damage skill
- **THEN** the companion takes damage and receives the penalty

### Requirement: Healing allies or foes carries no penalty

No affinity write or penalty SHALL result from recovery skills targeting allies, companions, or enemies; the friendly-fire contract applies only to player-action damage against companion NPCs.

#### Scenario: Healing a foe is a permitted choice

- **WHEN** a player casts a recovery skill on an enemy or an ally
- **THEN** the skill resolves and no affinity record is created or modified
