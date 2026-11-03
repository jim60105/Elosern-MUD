# Design

## Context

`WorldClock.advance` snapshots registered owner surfaces before its transaction and restores mutable caches on failure. `register_event_source(kind, source, surfaces, *, next_boundary=None)` is the current seam. Combat time remains terminal-only; `_finalize_resolved_round` knows the completed-round ordinal, while `settle_combat_result` advances all accumulated seconds at battle end. Its regional-population capability is introduced by the required predecessor and becomes the authoritative target before this dependent change archives.

## Goals / Non-Goals

Deliver this proposal's bounded regional-population prerequisite or cutover, using existing deterministic owners and real runnable operations. Do not implement adjacent field movement/aggression/escape or independent monster content. No compatibility paths or save conversion.

## Decisions

### Recovery API and state extension
Extend `regional_population.py` with `record_population_loss(wilderness, individual_id: int, *, occurred_tick: int, source_id: str) -> None`, `settle_regional_population(start_tick: int, end_tick: int) -> list[ScheduledEvent]`, `next_population_boundary(start_tick: int, end_tick: int) -> int | None`, and `register_regional_population() -> None`. Registration uses kind `regional_monster_population` with the existing owner snapshot function and pure next-boundary query; registration must be idempotent. No new worker or time source. The final cutover calls registration before session restoration.

Extend durable per-zone state with `pending_losses: list[dict]`; each entry has `individual_id: int`, `occurred_tick: int`, `source_id: str`, `cell: tuple[int,int] | None`. Entries describe committed losses whose occurrence is ahead of clock-settlement progress. A uniqueness check on source_id/individual_id makes round replay idempotent. Count all local Monster losses, including foreign-owned ones, without transferring their owner. Pass `at_tick` to count/planning reads during historical settlement: a dead ID whose committed loss is later than the evaluated tick still counts until its occurrence. Retain necessary cell/home facts until settlement passes them, then discard settled pending entries. This avoids an earlier pending wave using headroom from a later combat death. Do not resurrect an object or show historical-presence facts in public views.

### Combat occurrence contract
Add required `started_tick: int` to newly written `CombatSessionRecord` values and strict storage serialization, set once on engagement/candidate creation. No current-tick fallback or old-record reader. In `_finalize_resolved_round`, after committed round effects and before terminal catch-up, compare recorded round HP before/after for newly defeated Monster IDs, including upkeep defeats, and call the population owner inside that same rollback boundary. `occurred_tick = started_tick + completed_round * COMBAT_YAML round duration` (the existing six seconds). `source_id` derives from existing engagement/round provenance plus the exact individual ID. No parsing of log prose or pre-battle tick backdating. On noninteractive mapped losses, use the action owner's actual occurrence timestamp; abstract pure combat has no map notification. Do not notify for flee, knockout, absence or a simulated guild exam restoration.

Use future pending-loss facts while live clock is frozen. Example: battle starts 100, death in round 3 occurs 118, delay 10 gives earliest due 128 even if battle ends at 124. An older pending wave at 110 cannot count that future death as free headroom. Store start/protection evidence on the session and include active/historical encounter cell intervals in population planning during terminal catch-up, so closing a session never permits a retroactive birth in its cell. This protection context is scoped to population settlement only; no movement system is introduced.

### Episode state machine
First committed below-L state at occurrence T sets due=T+delay if no episode is pending. Further losses do not move due. Initialization that cannot reach L records a deficit at its initialization tick. At each due tick recompute effective local and home populations first. If local>=L clear due without construction, draws or sequence increment. Otherwise run at most wave_budget individuals using complete fitting compositions; after success or blockage, if still below L set next_due=due_tick+replenishment_interval, otherwise clear. Blocked waves leave generation_sequence unchanged and emit one bounded commit-qualified `monster_population_recovery_blocked` decision with reason. Returning/manual individuals restore local count and can cancel a pending episode; home-full blockage never bypasses caps. All due times are positive-progress, processed in tick then zone-key order, including newly scheduled waves within the interval. Repeated/overlapping settlement never processes an already settled boundary.

For equal external facts and saved seed, advance [100,160] and [100,125],[125,160] produce identical births, due/sequence/progress and IDs modulo separately allocated test databases. Compare planned variant/count/cell and retained-ID relationships, not cross-database numeric pk equality. Clock rollback must restore every wave in an advance, pending losses, schedule state, seed/sequence, registrations, rooms and event callbacks, even after a later stage fails. Read-only next-boundary queries consume no draws and change no state.

### Scope and documentation
Own regional_population, `combat_session/{records,lifecycle,battlefield,rounds,settlement}.py`, combat candidate record builders, clock snapshot/stage integration and tests. Do not tick fatigue in live rounds, change terminal-only clock, add aggression/arrival contacts or field movement. Document occurrence timestamps, source IDs, state and stage ordering in the population developer document. Existing site stage stays site-owned; when both are due, settle site lifecycle before ordinary regional births so explicit site arrivals count toward local headroom at the shared tick.

## Risks / Trade-offs

The existing display-name, coordinate-slot and supply contracts have broad callers. Complete the named semantic caller cutover within this slice; do not add a parallel legacy path. Candidate-world validation and mutable Evennia cache restoration are part of correctness. Use synthetic independently known mechanism outcomes and real-owner integration controls instead of production data-echo tests.

## Verification and requirement traceability

During implementation, create an environment file outside tracked source containing `MUD_TEST_SETTINGS=1`. Focused command: `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb LABELS`. Replace LABELS with this slice's labels below, keeping the single-token env-file form. Use fixed synthetic inputs and independently known outputs. Production checks establish references, ownership/topology and profile obligations without copying shipped values or prose. New nonbrowser modules require exact ownership in `.github/evennia-shards.json`; browser methods, if added, require `.github/browser-shards.json` ownership. Run observability lint alongside focused tests when logging changes. Full managed browser and complete evidence verification remain CI-owned.

Before changing annotations, record each affected assertion's synthetic-mechanism, registry-contract or representative-smoke role and substantive replacement in `docs/development/regional-monster-population.md`. Canonical IDs below came from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/regional-population-requirements.json`. ADDED requirements have no current IDs; never fabricate one. Before archive, use the tool on an equivalent merged spec tree, then replace provisional nearest-current claims with generated IDs. Retain no retired, empty or skipped claims. Each delta scenario maps to tasks.md test modules and must assert behavior rather than echo data.

After the completed slice run `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. This gate does not establish coverage of unarchived deltas; the assertion-role ledger and focused evidence remain required. The runtime slice owns the cross-system real smoke; each earlier slice still owns real-owner integration and reload/fault controls.

## Deployment and rollback boundary

No migrations, legacy readers, aliases, implicit reset or compatibility setting are authorized. New ordinary runtime activates only at regional-population-runtime-cutover; earlier APIs are fully implemented and independently exercised through real owners. Operation failures restore durable and live surfaces through deterministic owner compensation. An incompatible development save requires documented explicit GM save/repair/reset procedures, never startup mutation. A source/code rollback requires its matching explicitly saved development state, with no incompatible-record reinterpretation.

### Nearest current canonical anchors

- `player-combat-session::combat-time-settles-once-at-terminal-session-outcome`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `monster-site-placement::one-shot-sites-stay-cleared-and-recoverable-sites-recover-only-on-approved-conditions`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.

### Focused implementation labels

`world.maps.tests.test_regional_population_recovery world.rules.tests.test_combat_session_persistence`
