## ADDED Requirements

### Requirement: Out-of-combat casts settle resolution and world-time cost in one outer transaction

The out-of-combat cast command path SHALL route every cast through `world/rules/cast_settlement.settle_out_of_combat_cast(request)`, which SHALL snapshot all action- and clock-touched objects before resolution, open one outer `transaction.atomic()`, run `ActionResolver.resolve(request)` and — only on success — `WorldClock.advance(result.time_cost_seconds, AdvanceSource.COMMAND, [request.actor])` as nested operations inside it, and return only after the outer transaction commits. The snapshot SHALL cover, merged by object identity before the transaction opens: the merged advance-snapshot registry (per the world-clock advance-surface seam), the actor's and every request target's entity surfaces and quest logs, the battlefield's fled/knocked-out sets when the request context carries one, and the clock tick. Success rendering and EventLog presentation SHALL occur only after the outer transaction commits. A rejected resolution SHALL advance nothing and SHALL leave every snapshotted surface untouched.

#### Scenario: A successful status_disguise cast commits disguise, practice, and tick together
- **WHEN** a player casts `status_disguise` out of combat and the settlement succeeds with `time_cost_seconds == 6`
- **THEN** after the settlement returns, `db.disguised_stats` is durably materialized (or re-persisted), `db.skill_proficiency["status_disguise"]` increased by the race-scaled practice award, and `get_world_clock().tick` increased by exactly 6 — all visible in a fresh read after the outer commit, and the EventLog is rendered only after that commit

#### Scenario: A successful buff-applying out-of-combat cast commits the buff and tick together
- **WHEN** a player casts a buff-applying spell registered `usable_out_of_combat=True` with an empty cost (for example a test-registered `self_buff_apply` skill) and the settlement succeeds
- **THEN** the actor's `db.buffs` contains the applied buff and the clock tick increased by the reported `time_cost_seconds`, both visible after the outer commit

#### Scenario: A rejected out-of-combat cast advances nothing and touches no surface
- **WHEN** `ActionResolver.resolve` rejects the request (for example an unowned skill)
- **THEN** the settlement returns the rejection without advancing the clock and without materializing or persisting any disguise, buff, practice, quest, or tick state

#### Scenario: The in-combat session cast path does not use the settlement API
- **WHEN** a player casts during an active persistent combat session
- **THEN** `_cast_in_session` delegates to combat-session orchestration exactly as before and never calls `settle_out_of_combat_cast` or `WorldClock.advance`

### Requirement: A failed out-of-combat settlement restores every touched Evennia cache before the failure surfaces

When the clock callback, the final clock persistence, or the outer commit fails after a successful resolution, the settlement SHALL restore, before propagating the failure, the pre-action state of every snapshotted surface — actor and target Evennia Attributes (`traits`, `disguised_stats`, `sexual_traits`, `virgin`, `experience_types`, `buffs`, `skill_grants`, `magic_xp`, `skill_proficiency`, `quest_log`), the battlefield's fled/knocked-out sets when present, every callback-owned advance surface, and the clock tick — because Django rollback reverts only durable rows while Evennia's in-process caches keep the uncommitted values. Restore SHALL run in a fixed deterministic order after the rollback, SHALL be best-effort per step with a logged diagnostic on failure, and SHALL NOT mask or replace the original failure. The world-clock tick SHALL be restored from its pre-action snapshot, not from any post-action or post-advance value.

#### Scenario: A clock-callback failure rolls back a status_disguise cast completely
- **WHEN** a player casts `status_disguise` out of combat with `db.disguised_stats` absent and no proficiency entry, and a registered clock boundary-stage source raises during the advance
- **THEN** the failure propagates, `db.disguised_stats` is not materialized (or is restored to its pre-action value when it already existed), `db.skill_proficiency` has no new `status_disguise` entry, and `get_world_clock().tick` is unchanged — in the in-process objects and in the raw Attribute rows

#### Scenario: A final clock-persistence failure rolls back a status_disguise cast completely
- **WHEN** a player casts `status_disguise` out of combat and the clock tick's final persist raises after all stages ran
- **THEN** the failure propagates and the disguise, practice, and tick state all equal their pre-action values in cache and storage

#### Scenario: A clock-callback failure rolls back a buff-applying cast
- **WHEN** a player casts a buff-applying out-of-combat spell and a clock boundary-stage source raises during the advance
- **THEN** the actor's `db.buffs` attribute equals its pre-action value, the trait cache refreshes to the rolled-back storage, and the tick is unchanged

#### Scenario: A rolled-back outer commit reconciles durable rows and in-process caches to the pre-action state
- **WHEN** the outer settlement transaction fails at commit
- **THEN** the durable rows revert to the pre-action state and a fresh read of the in-process objects shows the same pre-action state across every snapshotted surface and the clock tick (verified deterministically by invoking the settlement's restore against a deliberately constructed divergent in-process state, since Django test cases wrap every transaction so commit failure cannot occur at the boundary level in tests)

#### Scenario: The settlement snapshot covers every ACTIVE out-of-combat catalog skill's effect entities
- **WHEN** the seven ACTIVE skills marked `usable_out_of_combat=True` (`status_disguise`, `dominion_art`, `divine_sexual_arts`, `divine_time_dilation`, `divine_space_distortion`, `divine_matter_transmutation`, `divine_life_extension`) are inspected
- **THEN** each skill's effect handlers write only entities within the settlement's declared snapshot superset — the actor, the request targets, and the merged advance registry — so no rolled-back cast can leave an unsnapshotted write behind
