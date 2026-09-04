# Delta spec: quest-lifecycle (webclient-align-06-quest-tracking-contract)

## MODIFIED Requirements

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

#### Scenario: Accepting never tracks
- **WHEN** a character accepts a definition
- **THEN** the created record carries `tracked` false

#### Scenario: A legacy-shaped entry without the key loads untracked
- **WHEN** a stored quest-log entry dict carries every other field but no `tracked` key
- **THEN** the record loader returns `tracked=False` without rewriting the stored entry

## ADDED Requirements

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
