# Spec Delta

## MODIFIED Requirements

### Requirement: Living winning violators depart the room, quest-bound monsters retained
At defeat settlement, every living foe-team monster carrying the wilderness
ownership marker `db.population_key` SHALL be logically departed inside the
settlement transaction: its marker is cleared and it is dropped from the
wilderness script's `itemcoordinates`.

#### Scenario: Population winner despawns at defeat settlement
- **WHEN** a player loses to a wilderness population monster carrying `population_key`
- **THEN** the monster is absent from `itemcoordinates` as part of the committed settlement and, after the post-commit departure callback completes, its object is deleted; no coordinate activation reconciles a fresh monster, because later ordinary births belong only to the regional owner's game-time recovery contract

#### Scenario: Post-commit deletion failure reverts the departure
- **WHEN** the physical object deletion fails after the settlement committed
- **THEN** the marker and the `itemcoordinates` entry are restored, the monster remains a normal live population monster, and the failure is logged at error level

#### Scenario: Quest-bound winner is retained
- **WHEN** a player loses to a monster whose pk is listed in a persisted quest record's `objective_target_ids`
- **THEN** the monster remains in the room and the quest record is unchanged

#### Scenario: Quest binding outranks the population marker
- **WHEN** a monster carries both `population_key` and a `quest_log` `objective_target_ids` binding
- **THEN** it is retained, never despawned

#### Scenario: Physical deletion is deferred to after the outermost commit
- **WHEN** a logical departure is committed
- **THEN** the physical Evennia-object deletion is scheduled only after the outermost transaction
  commits (through `transaction.on_commit`), because a deleted idmapper instance cannot be
  restored on rollback

#### Scenario: A crash in the post-commit window is the accepted residual risk
- **WHEN** the process crashes in the post-commit window between commit and physical deletion
- **THEN** only that crash may leave a marker-less live monster — the parent design's accepted
  restart-refresh risk

#### Scenario: Foreign monsters are left untouched
- **WHEN** a living foe-team monster has no `db.population_key` marker and no quest binding
- **THEN** defeat settlement leaves it untouched
