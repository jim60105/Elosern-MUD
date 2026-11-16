# Proposal

## Why

`PopulationDrainScript` repeats every `POPULATION_DRAIN_INTERVAL_SECONDS` real seconds whether or not a player is acting. Evennia runs one reactor thread, so a player command that arrives while a drain run is settling waits for the run to finish. The live log showed a move committed at 23:33:41 whose presentation was only sent at 23:33:46, after a drain run.

The drain exists to pay debt while the player is reading or idle. It has no signal that says whether a player is idle.

## What Changes

- The server records the monotonic time of the last player input. Input means a non-idle text command, or a WebClient UI action sent by a session with a puppet. An idle keepalive and a `ui_sync` request are not input.
- `PopulationDrainScript.at_repeat` performs no drain run while the last input is more recent than a new setting, `POPULATION_DRAIN_IDLE_SECONDS` (default 5 real seconds, positive integer, environment override of the same name). With no input recorded since the process started, the repeat drains as before.
- A skipped repeat is silent: it emits no event and reads no population record.
- The synchronous catch-up (`ensure_population_current` and its entry points) is not changed and does not consult the idle signal. A lagging unit is still settled before the action that needs it.
- `drain_population_backlog` itself is not gated: a shell or a test that calls it directly still drains.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `population-settlement-units`: the periodic drain yields to recent player input.

## Impact

- New `world/rules/player_input.py`; edits to `server/conf/inputfuncs.py`, `world/maps/population_drain.py`, `server/conf/settings.py`, `server/conf/test_settings.py`, `.env.example`.
- Tests: new `world/rules/tests/test_player_input.py`; edits to `server/conf/tests/test_inputfuncs.py`, `world/maps/tests/test_population_drain.py`, `server/conf/tests/test_env_overrides/_support.py`.
- Documentation: `docs/development/settings-and-environment.md`, `docs/development/regional-monster-population.md` (section "The periodic caller").
- No stored data changes. No settlement outcome changes: only the real time at which a drain run happens moves.
- Human-reviewed: none. Every behaviour of this change is established by tests.

## Batch:

- depends-on: none
- This change does not require commit `c0736d44` (`fix/population-group-units-memo`).
- conflicts: `population-drain-batched-runs` edits `PopulationDrainScript.at_repeat` and the same documentation section; it is ordered after this change. `server/conf/settings.py`, `server/conf/test_settings.py`, `.env.example`, `server/conf/tests/test_env_overrides/_support.py` and `docs/development/settings-and-environment.md` are edited by both; each adds its own setting line.
- parallel with: `monster-activity-record-parts`, `population-snapshot-part-scoping` (no shared file).
