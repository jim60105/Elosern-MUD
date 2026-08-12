# affinity-friendly-fire Specification

## Purpose

Define the deterministic friendly-fire penalty contract: a player combat action that damages an
ally-side companion NPC applies one per-hit `friendly_fire` negative delta through the sole
affinity writer, atomically with the round, with per-round membership snapshots and the party
auto-leave integration.

## Requirements

### Requirement: Player combat actions that damage companion NPCs apply a per-hit affinity penalty
The player combat session SHALL scan each resolved player action round for damage events caused by
that player action against ally-side companion NPCs (participants that are NPCs in
`player.db.party` and present on the battlefield). Each qualifying hit SHALL call the sole affinity
writer with the `friendly_fire` source and a penalty of `friendly_fire_penalty_per_hit` (rulebook,
default 1) — one call per hit, with no per-battle cap. The penalty SHALL apply exactly as a
negative delta through the writer: never resetting or restoring the daily budget, applying
unclamped downward (floor 0), and running the party auto-leave recheck. Damage that is not caused
by a player action — companion-vs-companion damage, enemy behavior, and buff-tick damage — SHALL
never trigger the penalty. A hit against a participant that is not a companion NPC SHALL write
nothing and create no record, including when that participant has no affinity record at all.

#### Scenario: An AREA skill hitting two companions applies two penalties
- **WHEN** a player action with an AREA target hits two companion NPCs in one round
- **THEN** each companion's affinity value decreases by 1, for two separate `friendly_fire` calls,
  and neither daily counter changes

#### Scenario: A self-selected single-target misfire still penalizes
- **WHEN** the player explicitly selects a companion NPC as a single target and the action damages
  it
- **THEN** the companion's affinity decreases by 1, because the criterion is player action damage
  to the NPC, not intent

#### Scenario: Non-player-action damage never penalizes
- **WHEN** a companion takes damage from another companion's action, an enemy action, or a buff
  tick during the same round
- **THEN** no affinity write occurs for any participant

#### Scenario: A non-companion target writes nothing
- **WHEN** a player action damages an NPC that is not in `player.db.party`
- **THEN** no affinity record is created or modified for that NPC

#### Scenario: A recordless non-companion gains no record
- **WHEN** a player action damages an NPC with no `relations_data` entry that is not a companion
- **THEN** the NPC still has no affinity entry after the round, proving the scan never calls the
  writer for non-companions

#### Scenario: A knockout hit still qualifies
- **WHEN** a player action's damage brings a companion NPC to 0 HP (nonlethal knockout) in the
  same round
- **THEN** the hit still applies one penalty, because the qualifying event is the damage the
  player action caused, not the target's survival

#### Scenario: The penalty value comes from the rulebook
- **WHEN** `rulebook/affinity.yaml` sets `friendly_fire_penalty_per_hit` to a value other than 1
- **THEN** the per-hit penalty equals that value, and loading rejects a missing, non-integer, or
  non-positive value

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

### Requirement: Friendly-fire penalties below the invite threshold end the companion party
The auto-leave recheck hook SHALL run for every friendly-fire penalty exactly as for any other
negative delta: when the affected NPC is a bound companion and its affinity toward the player drops
below the invite threshold (70), the party binding SHALL be removed with
`reason="affinity_below_threshold"` inside the same transaction, a failed leave SHALL roll back the
penalty, and the caller SHALL notify the player only after the transaction commits.

#### Scenario: A drop below 70 triggers auto-leave with notification
- **WHEN** a friendly-fire penalty drops a bound companion from 70 to 69
- **THEN** the binding is removed with the auto-leave reason and the player receives the
  notification after the write commits

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
