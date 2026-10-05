## MODIFIED Requirements

### Requirement: QuestRecord is JSON-safe persisted state with three stored states
`world/quests/runtime.py` SHALL define `QuestState` values `IN_PROGRESS`, `COMPLETED`, and `FAILED`, and a
frozen `QuestRecord` containing `quest_id`, `definition_key`, `issuer_key`, `state`, `stage_index`,
`stage_progress`, `deadline_tick`, `accepted_tick`, `stage_room_id`, `objective_target_ids`,
`protected_entity_ids`, `failure_reason`, `tracked`, and `counted_defeat_ids` — a JSON-safe tuple of
the integer persistent identities this record has already credited for its current DEFEAT objective,
defaulting to empty and cleared on stage transition together with the existing runtime bindings (a new
objective therefore counts its own identities from empty, so counted-set residue can never cap later
stages).
`issuer_key` SHALL be a required non-empty
string naming the commission the record was accepted under, and the strict reader SHALL validate it
against the shared issuer-key grammar and reject a missing or malformed value rather than defaulting
it — a record must always say which issuance governs its reward and settlement. `tracked` SHALL be a
boolean defaulting to false — a stored entry whose dict carries no `tracked` key SHALL load as
`tracked=False` — and accepting a quest SHALL never set it; a stored entry with no
`counted_defeat_ids` key SHALL likewise load as empty without rewriting the stored entry. Records SHALL be stored as plain
JSON-safe dicts in `PlayerCharacter.db.quest_log`. Unaccepted SHALL be represented by absence, and
abandonment SHALL use `FAILED` with reason `abandoned`.

#### Scenario: A record round-trips through JSON
- **WHEN** a record containing integer dbrefs and tuple bindings is serialized to its storage dict,
  passed through JSON serialization, and reconstructed
- **THEN** every field equals the original, including `issuer_key` and `counted_defeat_ids`, and the stored value contains no
  live entity reference

#### Scenario: Unaccepted definition has no record
- **WHEN** a definition is registered but never accepted by a character
- **THEN** that character's quest log has no record for the definition

#### Scenario: Accepting never tracks
- **WHEN** a character accepts a definition
- **THEN** the created record carries `tracked` false and an empty counted-identity tuple

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
