# Design

## Context

Observed owners and nearby test targets: exploration_actions.py validate_move_payload/_move_adapter and publication-group data; movement_settlement.py settle_movement/MovementSnapshot; new travel_interrupts.py/test_travel_interrupts.py; existing test_exploration_actions/test_move_and_look.py and dispatcher data-slot tests.

## Goals / Non-Goals

Attach stateless commit-qualified interrupt flags to wilderness moves. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Allow existing exact explore.move {exit_ref,current_node} or that plus exact walk:{pace,stop_at_night}, using planner enums/bool validation. Omitted walk remains legal. Store no walk context/session/queue state. Freeze immutable before facts immediately before traversal using actual source coordinates before pooled room mutation; after facts must describe a committed successful wilderness step. Include current cell/tick, exact landmark membership and valid lit set, distant internal source keys, live hostile observation keys and source-present traveller fatigue/postures. Use authorized PlayerCharacter knowledge owner under possession.

Flags and semantics: landmark_reached on exact arrival at any district landmark, including repeat; district_lit only after-minus-before lit set; landmark_sighted only new distant source key; hostile_in_sight only new live hostile observation key; member_asleep only awake->voluntary/forced transition of a traveller. With walk, pace_threshold applies to cautious/standard when a member crosses the threshold or was already at/beyond it before this legal step; this implements the planner's first-legal-step initial-state stop. Forced never raises it. With walk.stop_at_night=true, nightfall raises for a positive charged interval crossing night entry, not endpoint-phase comparison; flight-waived zero-charge steps cannot cross time boundaries. Without walk the natural landmark/district/sighting/hostile/sleep flags still apply, while pace/nightfall do not. Stable unique output order landmark_reached,district_lit,landmark_sighted,hostile_in_sight,pace_threshold,nightfall,member_asleep.

Successful wilderness result data has interrupts:[...] (empty legal). Preserve/compose any other existing data keys through shared exact validation rather than replacing a slot wholesale. Non-wilderness result shape unchanged. Refused/stale/failed/rolled-back movement has no interrupt data and unchanged refusal codes/messages. The actual mutation owner is movement_settlement.py::settle_movement, whose transaction and MovementSnapshot compensate failures observed inside that owner. PublicationReceipt is not a movement rollback owner.

Use a new ephemeral capture_movement_observation(actor) context manager in movement_settlement.py, backed by a ContextVar collector bound only around _move_adapter's exit.at_traverse call. The collector stores immutable before facts captured before traversal and a candidate after snapshot only after settle_movement's successful canonical-coordinate change. It carries no game writes. Nested NPC movements cannot replace the collector's actor/step. Before capture or comparison failures set the collector's empty-flag disposition and log; real traversal exceptions still follow existing rejection handling. After successful movement, the collector exposes the frozen comparison result to _move_adapter instead of relying on an invented existing movement receipt.

The adapter constructs the usual success dictionary from the collector after at_traverse returns and canonical success is confirmed. Release the success result through an on_publication_commit callback under the already captured publication group; use the existing dispatcher Deferred adapter path to return the dictionary only when that callback runs. In a normal production UI request, settle_movement is the database transaction owner and the commit callback can complete immediately. Tests capture/execute commit callbacks using their existing test transaction harness. A rollback inside settle_movement restores its snapshot and produces the unchanged refusal/error path. If a caller explicitly wraps the adapter in its own application transaction, success completion stays deferred and rollback discards the callback; that external caller owns its existing cached-state compensation and error completion. This change makes no new guarantee that arbitrary Django atomic wrappers restore caches after settle_movement has already returned. Such a generic transaction-journal redesign is outside the approved sight design, which requires the movement-owned rollback guarantee.

Capture/compare failure logs travel_interrupts_failed with char/tick/step and yields empty flags for an otherwise successful movement, as detailed design §9 specifies; this guard must not swallow traversal/preflight/settlement failure. No new retry/fallback policy. Tests independently raise/suppress all flags, combine stable ordering, exercise pooled same-room-object coordinate changes, prospective-to-materialized identity, optional walk validation, exact-zero sleep, failure after knowledge write while still inside the movement-owned transaction and injected comparison failure without movement failure. Separately test an external transaction discards the deferred success callback, without claiming automatic external cache compensation. Extend Python/JS result data validation and frozen audits where needed; verify adoption detaches incoming data. Document stateless walk/results in existing synchronization/map protocol docs. No browser queue/HUD/camp work.

## Review dispositions and task boundary

B3 is adopted with the paired test_initial_pace_state_matches_move_interrupt shared with the planner. B4 is adopted through the full webclient-exploration-menu MODIFIED block; retain all original scenarios and add exact optional-walk validation cases. B5 is adopted by specifying the new collector, actual mutation owner and commit handoff, and removing the unsupported extra promise about arbitrary caller-owned rollback. This changes no approved sight behavior. Suggested evidence is test_move_owned_failure_restores_observation, test_outer_rollback_discards_deferred_interrupt_result and test_collector_ignores_nested_other_actor_movement.

One-day breakdown is 1.5h validator/pure comparison, 2h collector/Deferred handoff, 2h focused failure/protocol tests, 1h docs/traceability and 1.5h integration allowance. The evidence mapping is this design section, using existing exploration payload/movement-settlement canonical requirements before the new IDs are produced.

## Dependency contracts

- [wilderness-travel-planning](../wilderness-travel-planning/design.md) must land first.

## Planning and implementation boundaries

This artifact set covers sub-project1 only. Read the [blueprint](../../../docs/superpowers/specs/2026-10-30-wilderness-travel-mode-blueprint-design.md) §7.1, the [detailed sight design](../../../docs/superpowers/specs/2026-10-30-wilderness-sight-and-fog-reveal-design.md) and [engine architecture](../../../docs/superpowers/specs/2026-07-29-ai-mud-engine-design.md) §§2/3/6.5/10. Preserve single-writer ownership and server exploration mode. No travel HUD/input queue/log/tint, camping/dream/art changes, authored geography/landmark-content changes, new roads, migrations or compatibility paths. Generated elevation and the approved sight rulebook are explicitly allowed.

Implementation will be performed by gpt-luna-level workers. Follow the named owners and exact contracts; read each prerequisite design first. Do not invent downstream stubs or leave unresolved behavior to a worker. Each change is capped at one workday including focused evidence/docs. Independent roots can run concurrently only with one owner integrating shared test-manifest/doc edits.

## Evidence and requirement shape

Use synthetic documents, policies and parties with independent expected results. Do not pin shipped data, text, markup or counts. Appearance/wording judgments are human-reviewed against the approved detailed design, outside SHALL requirements. For each requirement implement a discoverable test named from its mechanism, covering every delta scenario and both raising/non-raising cases. Test paths are named in Context. New package-local server tests join exactly one shard in .github/evennia-shards.json; avoid new modules when an existing test file is sufficient.

Requirement IDs must come from tools.spec_traceability list on the equivalent merged spec tree, never hand-composed. Before sync associate only the nearest current canonical requirement and report the temporary mapping per docs/development/spec-test-traceability.md. Sync remounts to the generated IDs with no uncovered requirements or waiver. Modified requirements retain identity except an explicit RENAMED window title. Mechanism tests must exist before that sync.

## Risks / Trade-offs

[Read side effects] -> Pure projections and object/Attribute/clock snapshots in integration tests. [Shared files] -> Serialize shard-manifest, schema and documentation changes even when roots are independent. [Data echo tests] -> Assert mechanics on synthetic fixtures and treat visual review separately. No new permanent lighting or walking state is allowed.

## Rollout / Rollback

Apply only after dependencies land. Development database reset is needed for the schema2 cutover; never automate deleting the user's database. No migration or dual decoder is added. Rollback is source reversal and a deliberate development reset where applicable. This proposal task does not start apply, sync or archive.
