## MODIFIED Requirements

### Requirement: Out-of-combat casts settle resolution and world-time cost in one outer transaction
The out-of-combat cast command path SHALL route every cast that is not a field-combat initiation
through
`world/rules/cast_settlement.settle_out_of_combat_cast(request)`, which SHALL snapshot all action- and
clock-touched objects before resolution, open one outer `transaction.atomic()`, run
`ActionResolver.resolve(request)` and — only on success —
`WorldClock.advance(result.time_cost_seconds, AdvanceSource.COMMAND, [request.actor])` as nested
operations inside it, and return only after the outer transaction commits. A cast aimed at a living
co-located `Monster` is a field-combat initiation and SHALL instead route through
`world/rules/combat_initiation.initiate_field_combat()`, whose time cost is accumulated by the combat
session and charged as combat time by its terminal settlement rather than as `AdvanceSource.COMMAND`
time here. The snapshot SHALL cover,
merged by object identity before the transaction opens: the merged advance-snapshot registry (per the
world-clock advance-surface seam), the actor's and every request target's entity surfaces and quest
logs, the battlefield's fled/knocked-out sets when the request context carries one, and the clock tick.
Success rendering and EventLog presentation SHALL occur only after the outer transaction commits. A
rejected resolution SHALL advance nothing and SHALL leave every snapshotted surface untouched.

#### Scenario: A successful status_disguise cast commits disguise, practice, and tick together
- **WHEN** a player casts `status_disguise` out of combat and the settlement succeeds with
  `time_cost_seconds == 6`
- **THEN** after the settlement returns, `db.disguised_stats` is durably materialized (or re-persisted),
  `db.skill_proficiency["status_disguise"]` increased by the race-scaled practice award, and
  `get_world_clock().tick` increased by exactly 6 — all visible in a fresh read after the outer commit,
  and the EventLog is rendered only after that commit

#### Scenario: A successful buff-applying out-of-combat cast commits the buff and tick together
- **WHEN** a player casts a buff-applying spell registered `usable_out_of_combat=True` with an empty
  cost (for example a test-registered `self_buff_apply` skill) and the settlement succeeds
- **THEN** the actor's `db.buffs` contains the applied buff and the clock tick increased by the reported
  `time_cost_seconds`, both visible after the outer commit

#### Scenario: A rejected out-of-combat cast advances nothing and touches no surface
- **WHEN** `ActionResolver.resolve` rejects the request (for example an unowned skill)
- **THEN** the settlement returns the rejection without advancing the clock and without materializing or
  persisting any disguise, buff, practice, quest, or tick state

#### Scenario: The in-combat session cast path does not use the settlement API
- **WHEN** a player casts during an active persistent combat session
- **THEN** `_cast_in_session` delegates to combat-session orchestration exactly as before and never
  calls `settle_out_of_combat_cast` or `WorldClock.advance`

#### Scenario: A monster-targeted exploration cast does not use the settlement API
- **WHEN** a player casts from exploration at a living co-located `Monster`
- **THEN** the command routes to `initiate_field_combat()` and never calls
  `settle_out_of_combat_cast` or charges `AdvanceSource.COMMAND` time for that cast

#### Scenario: A non-monster-targeted exploration cast still uses the settlement API unchanged
- **WHEN** a player casts a non-damaging skill from exploration at an NPC, at itself, or with no
  target
- **THEN** the cast routes through `settle_out_of_combat_cast` and every snapshot, transaction, and
  command-time behaviour is identical to before this change
