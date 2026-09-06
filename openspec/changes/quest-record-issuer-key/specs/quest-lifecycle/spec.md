# Delta spec: quest-lifecycle (quest-record-issuer-key)

## MODIFIED Requirements

### Requirement: QuestRecord is JSON-safe persisted state with three stored states
`world/quests/runtime.py` SHALL define `QuestState` values `IN_PROGRESS`, `COMPLETED`, and `FAILED`, and a
frozen `QuestRecord` containing `quest_id`, `definition_key`, `issuer_key`, `state`, `stage_index`,
`stage_progress`, `deadline_tick`, `accepted_tick`, `stage_room_id`, `objective_target_ids`,
`protected_entity_ids`, `failure_reason`, and `tracked`. `issuer_key` SHALL be a required non-empty
string naming the commission the record was accepted under, and the strict reader SHALL validate it
against the shared issuer-key grammar and reject a missing or malformed value rather than defaulting
it — a record must always say which issuance governs its reward and settlement. `tracked` SHALL be a
boolean defaulting to false — a stored entry whose dict carries no `tracked` key SHALL load as
`tracked=False` — and accepting a quest SHALL never set it. Records SHALL be stored as plain
JSON-safe dicts in `PlayerCharacter.db.quest_log`. Unaccepted SHALL be represented by absence, and
abandonment SHALL use `FAILED` with reason `abandoned`.

#### Scenario: A record round-trips through JSON
- **WHEN** a record containing integer dbrefs and tuple bindings is serialized to its storage dict,
  passed through JSON serialization, and reconstructed
- **THEN** every field equals the original, including `issuer_key`, and the stored value contains no
  live entity reference

#### Scenario: Unaccepted definition has no record
- **WHEN** a definition is registered but never accepted by a character
- **THEN** that character's quest log has no record for the definition

#### Scenario: Accepting never tracks
- **WHEN** a character accepts a definition
- **THEN** the created record carries `tracked` false

#### Scenario: A legacy-shaped entry without the key loads untracked
- **WHEN** a stored quest-log entry dict carries every other field but no `tracked` key
- **THEN** the record loader returns `tracked=False` without rewriting the stored entry

#### Scenario: An entry missing the issuer key is rejected, not defaulted
- **WHEN** a stored quest-log entry dict carries every other field but no `issuer_key` key
- **THEN** the strict reader raises `QuestDataError` and no lifecycle operation proceeds

#### Scenario: An entry with a malformed issuer key is rejected
- **WHEN** a stored entry carries an `issuer_key` that does not parse under the shared grammar
- **THEN** the strict reader raises `QuestDataError` and the stored value is neither rewritten nor
  coerced

### Requirement: accept_quest creates one deterministic active record
`accept_quest(actor, definition_key, issuer_key)` SHALL reject an unknown definition, reject when the
actor already has an active record for that definition, and reject when
`resolve_issuance(definition_key, issuer_key)` returns no issuance — a record SHALL never be created
pointing at a commission that does not exist. Otherwise it SHALL create an `IN_PROGRESS` stage-zero
record carrying the supplied `issuer_key`, whose deterministic `quest_id` uses the definition key and
that character's next acceptance number, whose `accepted_tick` is the current world tick, and whose
`deadline_tick` is either `None` or the accepted tick plus the definition's positive hours converted
with `CLOCK_YAML`.

#### Scenario: First acceptance succeeds
- **WHEN** a character accepts a known definition under a registered issuance with no previous record
  for it
- **THEN** one stage-zero `IN_PROGRESS` record is stored with quest ID `<definition-key>:1` and the
  supplied issuer key

#### Scenario: Duplicate active acceptance is rejected
- **WHEN** the character accepts a definition for which an `IN_PROGRESS` record already exists
- **THEN** `QuestAlreadyActive` is raised and the quest log is unchanged

#### Scenario: Acceptance under an unregistered issuance is rejected
- **WHEN** a character accepts a known definition naming an issuer key with no registered issuance
- **THEN** acceptance raises a named error and the quest log is unchanged

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

#### Scenario: The same definition can be held twice under different issuers
- **WHEN** a character completes a definition issued by a guild branch and later accepts the same
  definition from a private commissioner
- **THEN** the new record carries the private issuer key while the terminal record retains the guild
  issuer key
