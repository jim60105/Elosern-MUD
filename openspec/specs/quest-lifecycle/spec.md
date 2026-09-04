# quest-lifecycle Specification

## Purpose
Persistent deterministic per-character quest records and their lifecycle operations — accept, abandon,
stage binding, completion, and failure — with every multi-attribute write atomic and cache-consistent.

## Requirements
### Requirement: QuestRecord is JSON-safe persisted state with three stored states
`world/quests/runtime.py` SHALL define `QuestState` values `IN_PROGRESS`, `COMPLETED`, and `FAILED`, and a
frozen `QuestRecord` containing `quest_id`, `definition_key`, `state`, `stage_index`, `stage_progress`,
`deadline_tick`, `accepted_tick`, `stage_room_id`, `objective_target_ids`, `protected_entity_ids`,
`failure_reason`, and `tracked`. `tracked` SHALL be a boolean defaulting to false — a stored entry
whose dict carries no `tracked` key SHALL load as `tracked=False` — and accepting a quest SHALL
never set it. Records SHALL be stored as plain JSON-safe dicts in `PlayerCharacter.db.quest_log`.
Unaccepted SHALL be represented by absence, and abandonment SHALL use `FAILED` with reason `abandoned`.

#### Scenario: A record round-trips through JSON
- **WHEN** a record containing integer dbrefs and tuple bindings is serialized to its storage dict,
  passed through JSON serialization, and reconstructed
- **THEN** every field equals the original and the stored value contains no live entity reference

#### Scenario: Unaccepted definition has no record
- **WHEN** a definition is registered but never accepted by a character
- **THEN** that character's quest log has no record for the definition

#### Scenario: Accepting never tracks
- **WHEN** a character accepts a definition
- **THEN** the created record carries `tracked` false

#### Scenario: A legacy-shaped entry without the key loads untracked
- **WHEN** a stored quest-log entry dict carries every other field but no `tracked` key
- **THEN** the record loader returns `tracked=False` without rewriting the stored entry

### Requirement: Tracking state is bounded deterministic quest state
`world/quests/runtime.py` SHALL provide a tracking operation that sets `tracked` on exactly one
record of a character's quest log, validating the whole log through the shared validate-before-
replace lifecycle discipline before any write. Tracking true SHALL be rejected when the target
record is not `in_progress`, and rejected when the character already carries three tracked
`in_progress` records and the target is not already tracked; untracking SHALL always be permitted
for an existing record. A rejected operation SHALL raise the module's transition error and leave
the quest log byte-for-byte unchanged. No caller outside the quest lifecycle module and the
deterministic core SHALL assign `tracked`.

#### Scenario: Tracking up to the cap succeeds
- **WHEN** a holder with two tracked active quests tracks a third active record
- **THEN** exactly that record's `tracked` becomes true and the log round-trips through storage

#### Scenario: The fourth tracked quest is refused
- **WHEN** a holder with three tracked active quests attempts to track a fourth active record
- **THEN** the operation raises the transition error and no record's tracked state changes

#### Scenario: Terminal records cannot be tracked
- **WHEN** tracking true is attempted on a completed or failed record
- **THEN** the operation raises the transition error before any write

#### Scenario: Untracking is always permitted
- **WHEN** a holder untracks a tracked record or untracks an already-untracked record
- **THEN** the operation succeeds idempotently and only that record's state is affected

### Requirement: Every lifecycle operation validates before replacing the quest log
Every public lifecycle operation SHALL parse and validate every quest-log entry it touches before any
write. A malformed record, unknown active definition, stale stage, out-of-range stage index, progress
exceeding the objective quantity, or invalid state transition SHALL raise a named `QuestDataError` or
`QuestTransitionError` and SHALL leave the complete quest log and all instance pins unchanged. An active
record SHALL reference a known definition whose stage index is in range and still matches, and SHALL
carry progress within the current objective's quantity. A terminal record SHALL be final: no runtime
bindings may remain, and a `FAILED` record SHALL carry its reason. A successful operation SHALL persist
one replacement quest-log list rather than mutating a nested dict in place.

#### Scenario: Malformed persisted data fails without a partial write
- **WHEN** a quest log contains one malformed dict and an operation targets a different valid record
- **THEN** the operation raises `QuestDataError` and neither record nor any pin is modified

#### Scenario: Missing definition is reported
- **WHEN** an active record references a definition absent from `QUEST_DEFINITION_REGISTRY`
- **THEN** lifecycle access raises `QuestDataError` naming the missing key instead of silently skipping
  or reinterpreting the record

#### Scenario: Duplicate quest ids are rejected
- **WHEN** a quest log contains two records with the same deterministic quest ID
- **THEN** every lifecycle operation raises `QuestDataError` before it mutates any record or pin

### Requirement: accept_quest creates one deterministic active record
`accept_quest(actor, definition_key)` SHALL reject an unknown definition and reject when the actor
already has an active record for that definition. Otherwise it SHALL create an `IN_PROGRESS` stage-zero
record whose deterministic `quest_id` uses the definition key and that character's next acceptance
number, whose `accepted_tick` is the current world tick, and whose `deadline_tick` is either `None` or
the accepted tick plus the definition's positive hours converted with `CLOCK_YAML`.

#### Scenario: First acceptance succeeds
- **WHEN** a character accepts a known definition with no previous record for it
- **THEN** one stage-zero `IN_PROGRESS` record is stored with quest ID `<definition-key>:1`

#### Scenario: Duplicate active acceptance is rejected
- **WHEN** the character accepts a definition for which an `IN_PROGRESS` record already exists
- **THEN** `QuestAlreadyActive` is raised and the quest log is unchanged

#### Scenario: Terminal quest may be retried deterministically
- **WHEN** the previous record for a definition is `COMPLETED` or `FAILED` and the character accepts it
  again
- **THEN** a new active record is stored with the next acceptance number and the terminal history is
  retained

#### Scenario: Explicit deadline is converted to ticks
- **WHEN** a definition with `deadline_hours=72` is accepted at tick T
- **THEN** its deadline is `T + 72 * CLOCK_YAML["seconds_per_hour"]`

#### Scenario: No-deadline definition remains without a deadline
- **WHEN** a definition with `deadline_hours=None` is accepted
- **THEN** the record's `deadline_tick` is `None`

### Requirement: abandon_quest fails only an active quest and releases its runtime binding
`abandon_quest(actor, quest_id)` SHALL transition an active record to `FAILED` with
`failure_reason="abandoned"`, clear its runtime bindings, and release its current stage's instance pin.
Calling it again for the same terminal record SHALL be an idempotent no-op returning that record. An
unknown quest ID SHALL raise `QuestNotFound` without mutation.

#### Scenario: Abandonment records failure and releases a pin
- **WHEN** an active bound-instance quest is abandoned
- **THEN** it is failed with reason `abandoned`, its bindings are cleared, and its exact quest pin is
  absent from the room in the same operation

#### Scenario: Repeated abandonment is harmless
- **WHEN** `abandon_quest()` is called twice for the same quest ID
- **THEN** the second call makes no additional state change and does not fail on the already-removed pin

### Requirement: bind_stage_runtime attaches only current-stage instance and entity identities
`bind_stage_runtime(actor, quest_id, *, room=None, objective_targets=(), protected_entities=())` SHALL
accept only an active current stage. A supplied room SHALL be an existing `InstanceRoom`; supplied
entities SHALL be live `LivingEntity` objects. It SHALL persist integer dbrefs, keep objective targets
separate from protected entities, reject any dbref present in both sets, and pin the room with
`quest:<character-id>:<quest-id>:stage:<stage-index>`. Repeating an identical binding SHALL be
idempotent; replacing any existing binding SHALL raise before mutation.

#### Scenario: Runtime binding stores identities and pins the instance
- **WHEN** a current stage is bound to one instance room, two objective targets, and one protected NPC
- **THEN** the record stores the three entity dbrefs in their respective fields and the room contains
  exactly the stage's quest pin

#### Scenario: Objective and protected identities remain distinct
- **WHEN** a stage is bound with the same call's objective targets and protected entities
- **THEN** defeating an objective target cannot match the protected-entity failure set

#### Scenario: Overlapping objective and protected binding is rejected
- **WHEN** the same entity dbref is supplied in `objective_targets` and `protected_entities`
- **THEN** `QuestTransitionError` is raised before the quest log or room pin changes

#### Scenario: Persisted overlapping identity sets are invalid
- **WHEN** strict record parsing finds one dbref in both identity fields
- **THEN** it raises `QuestDataError` and no lifecycle operation mutates that record or its pin

#### Scenario: Conflicting rebind is rejected atomically
- **WHEN** a bound stage is rebound to a different room or entity set
- **THEN** `QuestTransitionError` is raised and the old record and pin remain unchanged

### Requirement: Multi-attribute lifecycle writes are atomic and cache-consistent
Operations that update both a quest log and an instance pin SHALL preflight the complete transition,
perform both writes in one `transaction.atomic()` block, and restore pre-operation Evennia attribute
values if any write raises. No successful exception path SHALL leave only one side changed.

#### Scenario: Pin failure rolls back acceptance or binding
- **WHEN** pin persistence is fault-injected to raise during a runtime binding
- **THEN** the quest record, room pin list, and their in-process attribute values equal their
  pre-operation state

#### Scenario: Quest-log failure restores an already-written pin
- **WHEN** quest-log persistence raises after a pin write
- **THEN** database state and cached room attributes both contain the original pin list

### Requirement: Generated quest definitions resolve after a server restart
The system SHALL restore all generated quest definitions, offers, and spawn requirements from the durable store at startup, before any player quest-log read, so persisted records referencing generated definitions resolve normally.

#### Scenario: Accepted generated quest remains readable after restart
- **WHEN** the server restarts after a player accepted a generated `ai_*` quest
- **THEN** `guild log` and all other quest-log reads succeed and list the accepted quest

#### Scenario: Accepted generated quest remains abandonable after restart
- **WHEN** the server restarts after a player accepted a generated `ai_*` quest
- **THEN** the player can abandon that quest without error

#### Scenario: Restore is idempotent across repeated restarts
- **WHEN** the server restarts multiple times with generated quests in the store
- **THEN** each generated quest is registered exactly once and quest-log reads succeed

### Requirement: Quest lifecycle transitions emit boundary events

Every successful quest lifecycle transition (accept, stage transition,
abandon, complete, fail) SHALL emit one `quest_transition` info event
through the `world.observability` facade at the transition's durable
commit point, with `char`, `quest`, `stage_from`, and `stage_to` context.
Rolled-back lifecycle operations MUST NOT emit the event, and best-effort
quest-log restore failures SHALL surface as `rollback_restore_failed` warn
events instead of silent passes. Lifecycle atomicity and validation
semantics MUST NOT change.

#### Scenario: A stage transition leaves one boundary event

- **WHEN** a quest stage transition commits durably
- **THEN** exactly one `quest_transition` event is logged with the quest key
  and the from/to stage identities

#### Scenario: A rolled-back transition emits no event

- **WHEN** a lifecycle operation fails after staging and rolls back
- **THEN** no `quest_transition` event is logged for that attempt, and any
  swallowed quest-log restore failure appears as a `rollback_restore_failed`
  warn event
