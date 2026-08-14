## Why

A malformed persisted combat record blocks hostile play forever. For `active_combat = {"not": "a valid record"}`,
`dict(raw)` succeeds and `from_storage` raises `CombatSessionError(MALFORMED_SESSION)`, but
`restore_active_session` parses the record (`read_session` at `combat_session.py:1260`) *before* its
recovery `try` block, so startup recovery never clears or quarantines the payload — `restore_persisted_sessions`
(`guild_economy.py:157-169`) only logs the propagated exception. `is_in_active_session` then reports no
session, producing exploration mode, while hostile `engage` and `combat forfeit` keep rejecting without
clearing the record; ordinary `TypeError`/`ValueError` conversion failures are not even normalized to a
`CombatSessionError`. The block only lifts if an unrelated guild examination happens to overwrite the record.

## What Changes

- `read_session` normalizes raw-conversion and strict-parsing failures (`TypeError`/`ValueError` from
  `dict(raw)` and parsing) into `CombatSessionError(SessionReason.MALFORMED_SESSION)`; `CombatSessionError`
  itself is re-raised untouched.
- `restore_active_session` moves strict parsing inside the recovery boundary: an unparseable record is
  diagnostically cleared (durable record, `action_context`, transient battlefield registration for the
  actor) WITHOUT deriving time settlement or participant effects from untrusted fields, and without
  advancing world time.
- Well-formed records with missing/deleted/moved/duplicated participant references keep the existing
  diagnostic termination (defeat / exam FAIL settlement), and the `settled_tick` fast path is unchanged.
- Unrelated restoration or settlement exceptions no longer clear or re-settle a valid session: the record
  stays intact for retry and the exception propagates to the startup logger.
- Regression tests using exactly `{"not": "a valid record"}` verify startup clears it and a subsequent
  hostile engagement succeeds.

## Capabilities

### New Capabilities
<!-- None: the changed behavior belongs to the existing player-combat-session capability. -->

### Modified Capabilities
- `player-combat-session`: the startup-recovery requirement extends to unparseable persisted records
  (cleared without settlement) alongside the existing invalid-participant diagnostic termination, plus a
  new requirement for fail-closed normalization of malformed payloads in active-session queries.

## Impact

- `world/rules/combat_session.py`: `read_session` normalization; `restore_active_session` recovery
  restructure and docstring update. `is_in_active_session`, `engage`, `forfeit`, and
  `restore_persisted_sessions` keep their contracts unchanged (the wrapper's log-and-continue already
  isolates per-player failures).
- Tests in `world/rules/tests/test_combat_session.py` (regression plus normalization coverage); existing
  restore/settlement tests in `test_combat_session.py` and `test_guild_exams.py` must stay green.
- No player-command surface change; `docs/game/commands.md` and `docs/game/command-reference.md` are
  untouched. No schema or data migration (0 released users).
