## Purpose

Change 22 wires the named-NPC portrait lifecycle into the real validated spawn path. The SceneBuilder
occupant spawn gains a portrait-eligibility seam: a spawned occupant carrying an explicit named
portrait policy schedules its unique-portrait ensure after the spawn transaction commits, while
today's role-based scene NPCs and monsters carry no policy and resolve to no portrait. The
materialization's atomicity, idempotency, and anti-hallucination contract are unchanged.

## ADDED Requirements

### Requirement: The occupant spawn path exposes a post-commit portrait-eligibility seam with unchanged atomicity
`world/quests/scene_builder.py` SHALL, after spawning and registering occupants inside the same outer
atomic materialization, schedule a portrait ensure through `transaction.on_commit` for any occupant
that carries an explicit `{"mode": "named", "stable_key": ...}` portrait policy, so the schedule fires
only after the materialization commits and an art failure can never roll back a materialized scene. An
occupant with no policy (every role-based scene NPC and monster spawned today) SHALL schedule nothing.
The existing atomicity, idempotency, and lore-derived-stat behavior of `materialize_stage` SHALL be
unchanged.

#### Scenario: A generic role-based occupant schedules no portrait
- **WHEN** a scene with role-based NPCs and monsters is materialized
- **THEN** none of the occupants carries a portrait policy and no post-commit portrait job is scheduled

#### Scenario: A named-policy occupant schedules after commit only
- **WHEN** an occupant carrying an explicit named portrait policy is materialized and the transaction
  commits
- **THEN** exactly one post-commit portrait ensure is scheduled for that occupant's subject, and no
  artwork failure can roll back the materialization

#### Scenario: A rolled-back materialization emits no portrait job
- **WHEN** an occupant spawn fails after an earlier occupant was spawned and the outer transaction
  rolls back
- **THEN** no post-commit portrait job is emitted and the existing full rollback behavior is unchanged
