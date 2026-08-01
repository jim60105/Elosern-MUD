## ADDED Requirements

### Requirement: Quest deadline settlement is registered from the server startup composition root
`world/quests/bootstrap.py::sync_quest_runtime()` SHALL register
`settle_quest_deadlines` through `register_event_source("quest_deadlines", ...)`. The server
`at_server_start()` hook SHALL call quest synchronization after lore and map synchronization on every
start and reload. `world/maps/bootstrap.py` SHALL NOT import `world.quests` to perform this registration.

#### Scenario: Server start activates deadline settlement
- **WHEN** `at_server_start()` completes
- **THEN** advancing `WorldClock` across a due quest deadline invokes quest settlement without a manual
  registration or settlement call

#### Scenario: Repeated startup registration is idempotent
- **WHEN** quest synchronization runs more than once in one process
- **THEN** one event source and one event-effect planner are active, with no duplicate deadline event or
  duplicate quest progress

### Requirement: Due active quests fail and release their current instance pin
`settle_quest_deadlines(start_tick, end_tick)` SHALL transition every valid `IN_PROGRESS` record whose
non-`None` `deadline_tick <= end_tick` to `FAILED` with reason `deadline_expired`, release and clear its
runtime bindings, and return one JSON-safe `ScheduledEvent` containing character ID, quest ID, and
definition key. It SHALL ignore terminal and no-deadline records.

#### Scenario: Due quest fails
- **WHEN** clock settlement ends at or after an active quest's deadline
- **THEN** the record is failed once with reason `deadline_expired` and a JSON-safe scheduled event is
  returned

#### Scenario: No-deadline quest never expires
- **WHEN** an active record has `deadline_tick=None`
- **THEN** deadline settlement leaves it unchanged for every end tick

#### Scenario: Deadline releases bound instance
- **WHEN** a due quest owns a current-stage instance pin
- **THEN** failure removes that exact pin and clears the record's binding in the same transition

#### Scenario: Malformed data cannot partially settle the owning character
- **WHEN** one character's quest log contains malformed data
- **THEN** settlement records a diagnostic, leaves that character's complete quest log and pins
  unchanged, and continues settling other characters

### Requirement: Deadline failure precedes instance reclamation in one clock advance
This change SHALL NOT modify `_STAGE_ORDER`. Because `quest_deadlines` already precedes
`instance_reclamation`, a room whose quest deadline and TTL are due in the same clock advance SHALL be
unpinned by quest settlement before map-instance evaluates it.

#### Scenario: Due room is resolved in one advance
- **WHEN** a quest deadline and its bound room's TTL fall within one `WorldClock.advance()` window
- **THEN** the quest fails and map-instance reclaims or promotes the now-unpinned room before that single
  advance returns

### Requirement: Defeat of an exact protected entity fails its active quests atomically
The quest action event-effect planner SHALL compare each `target_defeated.data["target_id"]` against
active records' `protected_entity_ids`. Every exact match SHALL stage a failure with reason
`protected_entity_defeated` and release that quest's instance pin in the same action commit. It SHALL
not compare display keys, monster tiers, or `objective_target_ids` for this failure condition.

#### Scenario: Protected NPC death fails an escort quest
- **WHEN** a hostile action lethally damages the exact NPC dbref protected by an active escort quest
- **THEN** the damage, quest failure, and pin release commit together

#### Scenario: Same display key does not create a false failure
- **WHEN** another NPC shares the protected NPC's display key but has a different dbref and is defeated
- **THEN** the quest remains active

#### Scenario: Objective target death cannot trigger protected failure
- **WHEN** a DEFEAT stage's `objective_target_ids` target is killed and that ID is absent from
  `protected_entity_ids`
- **THEN** it may advance DEFEAT progress but cannot fail the quest

#### Scenario: Commit fault rolls back death and quest failure together
- **WHEN** a staged pin or quest-log write raises during protected-entity failure commit
- **THEN** target HP, the quest record, and the room pin list all equal their pre-action state
