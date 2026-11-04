# Design

## Context

mental_time.next_skip_boundary combines physiology with next_registered_boundary. Population's current query reports maintenance boundaries, including distant recovery. continue_sleep and continue_owner_sleep already persist accepted intervals and continuation authorization. The predecessor supplies admission, sleep interruption and real enemy-only rounds.

## Goals / Non-Goals

Read-only forecast finds the first relevant contact during wait/rest/sleep. No second clock, mutating simulation, room creation, saved random draws or nearest-current-monster shortcut. Committed movement stays indivisible.

## Decisions

### One shared deterministic transition planner

Extract the real activity writer's transition planning into pure `project_activity_window(snapshot: ActivitySnapshot, *, start_tick: int, end_tick: int, observers: tuple[FieldObserver,...]) -> ContactForecast`. Snapshot contains detached group/journey records, actual PopulationPresence, site/population seeds/sequences and recovery due state, protection intervals, condition-time boundaries, optional physiology and observer logical positions. `FieldObserver(commander_id: int, location: LocationRef, traversing_until: int | None)` and `ContactForecast(first_tick: int | None, contact_sources: tuple[str,...])` are frozen Python values, never persisted.

Projection enumerates the same due facts and newly created facts in the writer's order. Adapt existing pure wave/composition/group planners to accept detached projected counts/state without constructing future entities. Prospective occurrence tokens are internal forecast values, never public monster identities or targets. Do not call constructors, settlements or sessions; do not use database rollback as simulation or maintain a shadow authoritative world.

At each projected tick process completed arrivals, site/regional births, condition changes, contact and then idle departure. Continue through distant maintenance until the first contact for a relevant present player-controlled party or end_tick. Include birth/departure within the interval and later arrival, with the same deterministic selection and pricing as commit. Public next_population_lifecycle_boundary(start_tick:int,end_tick:int)->int|None returns interactive contact ticks only; internal _next_population_boundary still advances all maintenance. Present contacts are handled by preflight at zero time, never a zero-time next-boundary loop.

### Exact detached projection values

Frozen `ActivitySnapshot(groups: tuple[ActivityGroupSnapshot,...], journeys: tuple[JourneySnapshot,...], presence: tuple[tuple[int|str,PopulationPresence],...], zones: tuple[ProjectedZone,...], sites: tuple[ProjectedSite,...], protection: tuple[PopulationProtection,...], room_protection: tuple[RoomProtectionSnapshot,...], physiology: tuple[tuple[int|str,TravellerState],...], condition_ticks: tuple[int,...])`. ActivityGroupSnapshot and JourneySnapshot are deep-frozen validated records with exactly the predecessor's persisted keys, including member_time and the committed plan; use tuples for sequence values and immutable mappings for named keys. They contain no live Evennia objects.

Frozen `ProjectedZone(key: str, seed: int, generation_sequence: int, recovery_due_tick: int | None, settled_through_tick: int)` retains existing initialized-zone state; immutable zone declarations/birth geometry are read-only planner inputs. Frozen `ProjectedSite(key: str, seed: int, generation_sequence: int, member_ids: tuple[int|str,...], populated: bool, cleared: bool, cleared_at_tick: int | None, recovery_due_tick: int | None, composition_key: str, activity_key: str)` retains the site's complete lifecycle and selected binding. Prospective individual tokens are canonical strings `forecast:<owner-kind>:<owner-key>:<generation-sequence>:<member-ordinal>`, internal to this function; actual persistent IDs remain ints. The token format is not a requirement ID or public entity ID.

RoomProtectionSnapshot is the immutable predecessor room_protection record with exact session_id/location/start_tick/end_tick fields. All projection entry values are captured at start_tick through the real owner’s pure read snapshot. Each planned occurrence returns an immutable replacement snapshot plus ordered facts; the writer consumes the same fact planner with actual constructor/registration adapters at commit. Retained PopulationPlacement composition_key/activity_key feeds projected and real group formation identically, never variant-row inference. No global mutable simulation cache or authored balance copy is introduced.

### Accepted interval and receipt behavior

Integrate advance_wait, continue_sleep, continue_owner_sleep, study and camping shared boundaries. planned_seconds uses the minimum physiological/contact boundary; settle recovery only through that tick then atomically admit contact at the endpoint. Distant events remain internal. Preserve ScheduledEvent.interactive and SkipResult requested/elapsed distinction; a contact is interactive only for involved parties. Forced sleeper retains receipt/threshold; voluntary interruption invokes the predecessor's sleep owner and revokes continuation. Discard unused requested time. Subsequent enemy-only rounds are separately paid combat operations, absent from skip elapsed/recovery receipts.

For movement and retreat use indivisible completion and traversal scope, never clip an edge with planned_seconds. Complete costs, then evaluate arrival contact and stop browser walking before another edge. Publish one final mode frame; browser timers own no simulation. Update existing text time/arrival messages and server-authoritative browser presentation plus both command documents.

### Atomicity and logging

Forecast preserves object/room counts, Attributes, clocks, seeds, sequence and sessions. Extend clock snapshot registry with affected observer session/receipt/skip-safety plus all globally written map surfaces, so failure after admission restores the accepted interval too. Reuse field_contact_admitted, clock_advance and sleep boundaries through named facade imports. Add catalog event field_contact_interrupted with operation/sleep ID, requested/accepted ticks and session. Commit-only success; operational errors re-raise; no credentials or prose.

## Risks / Trade-offs

Forecasting only existing journeys misses future birth/departure contact. Shared pure planners and saved deterministic inputs are required for forecast/commit equivalence and equal-time partitioning.

## Verification

Register new `world.rules.tests.test_field_contact_boundaries` in evennia-shards. Synthetic birth110, departure120, arrival140 during [100,1000], with distant maintenance105, must forecast140 without mutation and stop the actual wait at140. Compare interval partitions for routes/resources/receipts/session. Cover rest, voluntary/forced sleep, owner auto-continuation, dawn condition and companion control, then real separately billed enemy rounds. A physical edge crosses140 but arrives150, pays through150 and admits at150 only. Failure after movement/sleep/session writes restores reload and live state. Add actual text and authoritative browser action tests, registering any new browser module/method in browser-shards; full managed browser evidence remains CI-owned.

## Implementation evidence contract

Canonical IDs copied from traceability list output for the equivalent merged tree:

- `hostile-field-contact::contact-forecasts-stop-interruptible-time-at-actual-interaction`, tasks1.1-3.1, test_field_contact_boundaries.
- `time-skip-commands::interruptible-skips-stop-at-the-earliest-relevant-boundary`, task2.1, accepted wait/sleep/owner-continuation controls.
- `wilderness-travel-interrupts::arrival-combat-stops-walking-before-the-next-edge`, task3.1, authoritative movement/browser controls.

Create `/tmp/mud-field-tests.env` containing `MUD_TEST_SETTINGS=1` outside tracked source. Run one focused method/class at a time using the guarded command shown below; never concatenate the inventory or exceed 100 discovered tests. Register every new Python test module exactly once in `.github/evennia-shards.json`; new managed browser modules/methods belong exactly once in `.github/browser-shards.json`. Full managed-browser and complete traceability evidence remain CI-owned.

`uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <named-label>`

Use canonical identifiers generated by `uv run --locked python -m tools.spec_traceability list`, never by concatenating names. For added/removed requirements, generate the equivalent merged specification tree outside Git and run the same tool with `--repo-root`; use its output before updating annotations. Preserve substantive assertion roles; delete retired claims without forwarding decorators, copy/data pin tests or waivers. Record requirement/scenario-to-test assertions and exercised evidence in `docs/development/monster-field-behaviour.md`. Human ecology/wording/visual judgment is reviewed there rather than asserted by shipped strings or counts.

At implementation handoff run focused tests, `uv run --locked python -m tools.observability_lint check` alongside changed-logging tests, the existing command-doc contract whenever command docs change, `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. These are future worker checks, not feature verification during proposal creation. Failure restores every owning durable/live surface and emits no committed success. No compatibility readers, migrations, hidden initialization of an existing save or reset-on-load.
