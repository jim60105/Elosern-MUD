## MODIFIED Requirements

### Requirement: The occupant spawn path exposes a post-commit portrait-eligibility seam with unchanged atomicity
`world/quests/scene_builder.py`'s occupant spawn path SHALL apply the characterization carried by
`StageSpawnRequirement` (display name, paired canonical adult ages, and the named portrait
`stable_key` from `blueprint-portrait-policy`) when present: `db.display_name`, `db.age` /
`db.apparent_age` (declared values, or the deterministic adult baseline 25 when a portrait policy
is declared and the ages are absent), and `db.portrait_policy = {"mode": "named",
"stable_key": ...}`. After materialization, the spawn path SHALL, inside the same atomic
materialization, schedule a portrait ensure through `transaction.on_commit` for any occupant that
carries that explicit named portrait policy, so the schedule fires only after the materialization
transaction commits and an art failure can never roll back a materialized scene. A rolled-back
materialization SHALL emit no post-commit portrait job, and the existing full rollback behavior
SHALL be unchanged. A generic role-based occupant without characterization carries no policy and
schedules nothing.

#### Scenario: A generic role-based occupant schedules no portrait
- **WHEN** an occupant carries no portrait policy
- **THEN** no post-commit portrait job is scheduled, matching the pre-change behavior

#### Scenario: A characterized named occupant schedules exactly one portrait
- **WHEN** an occupant carrying an applied named portrait policy is materialized and the transaction
  commits
- **THEN** exactly one post-commit portrait ensure is scheduled for that occupant's subject, and
  no other scheduling path exists

#### Scenario: A rolled-back materialization emits no portrait job
- **WHEN** the materialization transaction rolls back after occupants were created
- **THEN** no post-commit portrait job is emitted and the existing full rollback behavior is
  unchanged

#### Scenario: The portrait apply writes the full policy dict
- **WHEN** a characterized occupant is spawned
- **THEN** `db.portrait_policy` is exactly `{"mode": "named", "stable_key": ...}` and canonical
  adult ages are present before the policy is set
