## Purpose

Define the deterministic outer settlement boundary for out-of-combat skill casts: the skill effect,
practice award, planner writes, and the command-time charge commit together in one transaction, and a
failed settlement restores every touched Evennia cache to its pre-action state before the failure
surfaces.

## Requirements

### Requirement: Out-of-combat casts settle resolution and world-time cost in one outer transaction
The out-of-combat cast command path SHALL route every cast that is not a field-combat initiation through
`world/rules/cast_settlement.settle_out_of_combat_cast(request)`, which SHALL snapshot all action- and
clock-touched objects before resolution and open one outer `transaction.atomic()`.

#### Scenario: A successful status_disguise cast commits disguise, practice, and tick together
- **WHEN** a player casts `status_disguise` out of combat and the settlement succeeds with
  `time_cost_seconds == 6`
- **THEN** after the settlement returns, `db.disguised_stats` is durably materialized (or re-persisted),
  `db.skill_proficiency["status_disguise"]` increased by the race-scaled practice award, and
  `get_world_clock().tick` increased by exactly 6 — all visible in a fresh read after the outer commit,
  and the EventLog is rendered only after that commit

#### Scenario: Resolution and clock advance run nested and the call returns only after commit

- **WHEN** the settlement runs inside its outer transaction
- **THEN** it runs `ActionResolver.resolve(request)` and — only on success — `WorldClock.advance(result.time_cost_seconds, AdvanceSource.COMMAND, [request.actor])` as nested operations inside the outer transaction, and returns only after the outer transaction commits

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

#### Scenario: The settlement snapshot covers every ACTIVE out-of-combat catalog skill's effect entities
- **WHEN** every ACTIVE catalog skill marked `usable_out_of_combat=True` is inspected
- **THEN** each skill's effect handlers write only entities within the settlement's declared snapshot
  superset — the actor, the request targets, and the merged advance registry — so no rolled-back cast can
  leave an unsnapshotted write behind

#### Scenario: A field-combat initiation defers its time cost to the combat session

- **WHEN** a cast is aimed at a living co-located `Monster`, making it a field-combat initiation routed through `world/rules/combat_initiation.initiate_field_combat()`
- **THEN** its time cost is accumulated by the combat session and charged as combat time by its terminal settlement rather than as `AdvanceSource.COMMAND` time in the out-of-combat settlement

#### Scenario: The settlement snapshot covers the declared surfaces merged by object identity

- **WHEN** the settlement builds its pre-resolution snapshot
- **THEN** the snapshot covers, merged by object identity before the transaction opens: the merged advance-snapshot registry (per the world-clock advance-surface seam), the actor's and every request target's entity surfaces and quest logs, the battlefield's fled/knocked-out sets when the request context carries one, and the clock tick

#### Scenario: Success rendering and EventLog presentation are post-commit only

- **WHEN** an out-of-combat cast resolves successfully
- **THEN** success rendering and EventLog presentation occur only after the outer transaction commits

#### Scenario: A rejected resolution leaves every snapshotted surface untouched

- **WHEN** `ActionResolver.resolve` rejects the request inside the settlement
- **THEN** the settlement advances nothing and leaves every snapshotted surface untouched

### Requirement: A failed out-of-combat settlement restores every touched Evennia cache before the failure surfaces
When the clock callback, the final clock persistence, or the outer commit fails after a successful
resolution, the settlement SHALL restore, before propagating the failure, the pre-action state of every
snapshotted surface — because Django rollback reverts only durable rows while Evennia's in-process
caches keep the uncommitted values.

#### Scenario: A clock-callback failure rolls back a status_disguise cast completely
- **WHEN** a player casts `status_disguise` out of combat with `db.disguised_stats` absent and no
  proficiency entry, and a registered clock boundary-stage source raises during the advance
- **THEN** the failure propagates, `db.disguised_stats` is not materialized (or is restored to its
  pre-action value when it already existed), `db.skill_proficiency` has no new `status_disguise` entry,
  and `get_world_clock().tick` is unchanged — in the in-process objects and in the raw Attribute rows

#### Scenario: A final clock-persistence failure rolls back a status_disguise cast completely
- **WHEN** a player casts `status_disguise` out of combat and the clock tick's final persist raises after
  all stages ran
- **THEN** the failure propagates and the disguise, practice, and tick state all equal their pre-action
  values in cache and storage

#### Scenario: A clock-callback failure rolls back a buff-applying cast
- **WHEN** a player casts a buff-applying out-of-combat spell and a clock boundary-stage source raises
  during the advance
- **THEN** the actor's `db.buffs` attribute equals its pre-action value, the trait cache refreshes to the
  rolled-back storage, and the tick is unchanged

#### Scenario: A rolled-back outer commit reconciles durable rows and in-process caches to the pre-action state
- **WHEN** the outer settlement transaction fails at commit
- **THEN** the durable rows revert to the pre-action state and a fresh read of the in-process objects
  shows the same pre-action state across every snapshotted surface and the clock tick (verified
  deterministically by invoking the settlement's restore against a deliberately constructed divergent
  in-process state, since Django test cases wrap every transaction so commit failure cannot occur at the
  boundary level in tests)

#### Scenario: The settlement snapshot covers every ACTIVE out-of-combat catalog skill's effect entities
- **WHEN** the seven ACTIVE skills marked `usable_out_of_combat=True` (`status_disguise`, `dominion_art`,
  `divine_sexual_arts`, `divine_time_dilation`, `divine_space_distortion`, `divine_matter_transmutation`,
  `divine_life_extension`) are inspected
- **THEN** each skill's effect handlers write only entities within the settlement's declared snapshot
  superset — the actor, the request targets, and the merged advance registry — so no rolled-back cast can
  leave an unsnapshotted write behind

#### Scenario: A rolled-back holy-rite cast restores the church ledger byte-identically
- **WHEN** a player casts `rite_martial_blessing` out of combat with an existing ledger and the
  outer settlement commit fails after the buff mount and the `blessing_last_tick` stamp applied
- **THEN** the failure propagates, `db.buffs`, `db.church` (merit, daily block, and any
  `blessing_last_tick` key), the trait cache, and the clock tick all equal their pre-action values
  in cache and storage, and no `rite_cast` event is emitted

#### Scenario: The restore covers every enumerated snapshotted surface

- **WHEN** the settlement restores after a failed out-of-combat settlement
- **THEN** it restores the pre-action state of the actor and target Evennia Attributes (`traits`, `disguised_stats`, `sexual_traits`, `virgin`, `experience_types`, `buffs`, `skill_grants`, `skill_proficiency`, `quest_log`, `church`), the battlefield's fled/knocked-out sets when present, every callback-owned advance surface, and the clock tick

#### Scenario: Restore execution is ordered, best-effort, and non-masking

- **WHEN** the settlement's restore runs after the rollback
- **THEN** it runs in a fixed deterministic order, is best-effort per step with a logged diagnostic on failure, and does not mask or replace the original failure

#### Scenario: The world-clock tick is restored from its pre-action snapshot

- **WHEN** the settlement restores the world-clock tick
- **THEN** the tick is restored from its pre-action snapshot, not from any post-action or post-advance value
