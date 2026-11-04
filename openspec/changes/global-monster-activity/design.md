# Design

## Context

The prerequisite provides complete group formation and individual flee journeys under the real population source. `population_counts` already distinguishes local/home ownership; `site_living_members` resolves saved IDs independent of position. No redesign of either landed mechanism belongs here.

## Goals / Non-Goals

Enable ordinary seeded decisions for every actual group globally. Reuse the journey owner and physiology cursors without pursuit, replacement monsters, wall-clock simulation or new rooms.

## Decisions

### Deterministic ordinary decisions

Extend `monster_activity.py` with frozen `ActivityDecision(group_id: str, tick: int, expected_sequence: int, edge: PhysicalEdge | None, reason: str)`, read-only `plan_group_decision(wilderness: Any, group_id: str, *, tick: int) -> ActivityDecision` and `commit_group_decision(wilderness: Any, plan: ActivityDecision) -> None`. Commit revalidates membership, sequence, position and canonical execution pricing. Use saved seed/group/sequence/tick/purpose through the population owner's SHA-256/rejection-sampling discipline; sort canonical edges and include staying as a candidate. One committed stay or departure increments sequence once; schedule at a positive interval. Reads, reload and reconnect never redraw.

Ordinary edges remain inside resolved activity bounds and use shared topology, actual access and movement capabilities. Settlement birth buffers never filter movement. Stationary policies maintain elapsed posture without departures. Cohesive groups quote all required self-moving living members together at slowest speed and commit one journey. Any blocked, sleeping or unaffordable member makes the group stay; never move a subset. Active participants cannot depart, and no outside group can begin a route into a protected encounter cell.

A singly escaped member outside its ordinary bounds prefers only legal adjacent steps directly back inside the original area. With none, wait and retry at the positive decision interval. Do not invent a new exploration policy, teleport, delete or replace the member. Normal bounds resume on return. Successful escape itself can cross the bounds.

### Global chronological settlement

Extend `_settle_population_at` and `_next_population_boundary` in population_lifecycle to process newly generated facts in the same advance. Same tick applies lawful completed arrivals, existing site-before-regional births, contact phase, then idle departures. Until hostile-field-admission lands there is no contact policy; add no unimplemented callback. Equal facts sort owner/group/member IDs. Recompute local density after position changes and keep current recovery episode semantics. Movement records alive-before/alive-after presence, retaining home/site markers, with no kill or site-clear credit. Visitors consume local headroom and home owners in transit consume their home ceiling once.

Every group, including stationary groups, settles ordinary elapsed posture under existing physiology owners using its saved cursor; passage uses the journey cursor. Discover all groups globally, independent of the clock caller's scope. Exclude activity-owned bodies from duplicate generic physiology for the same interval while retaining other stages. Optional absent physiology keeps the current exemption, partial/malformed state fails closed. Work follows due facts, never per-second/per-cell room scans.

Extend snapshot_population_lifecycle_surfaces for group state and every written existing body, including new groups produced by births within the interval. The population owner already tracks newly constructed IDs; later clock failure must restore the full advance and live caches. Startup source registration remains before session restoration; only fresh provisioning creates the new owner record. No existing-save reinterpretation.

### Presentation and observability

Actual view, GM and travel logs consume real departures/arrivals. Add `monster_activity_decided` to the approved observability event catalog for committed stays/departures with group, sequence, tick and reason; reuse journey events and named facade imports. Reads emit no mutation event. Both command docs explain wandering; human ecology/wording review lives in the developer document.

## Risks / Trade-offs

One planner and saved decision/cursor state are required for equal-time partitioning. Avoid a visible-groups-only cache. The existing regional owner already implements both birth ceilings; prove actual journeys consume them rather than introducing another budget. The world-clock delta makes explicit that registered population-owner intervals are separate from ordinary caller-scoped stages. Factor/reuse the canonical clock gauge/physiology interval writers for owner-settled bodies; do not merely omit generic regen or apply it twice. Monster idle/combat/journey handoffs use the member_time contract from mapped-monster-escape.

## Verification

New `world.maps.tests.test_monster_activity` registers in evennia-shards. Extend journey/recovery/site/view tests. An unobserved mixed group moves without rooms and at the slowest speed; one blocked member prevents the whole step. Verify seeded stay/restart, corner and locked gate, movement through birth buffers, outside-bound return, home ceiling during repeated departures, visitors blocking local births, and no false site clearing. [100,160] and [100,125]+[125,160] produce identical resources/positions/schedule. Historical battle protection and a late fault after a new birth/departure restore both DB and live caches.

## Implementation evidence contract

Canonical IDs copied from traceability list output for the equivalent merged tree:

- `monster-field-activity::due-activity-moves-bounded-complete-groups-globally`, tasks1.1-3.1, test_monster_activity.
- `monster-journeys::activity-ordering-protects-encounters-across-deferred-time`, tasks2.1-3.1, activity/journey/protection controls.
- `regional-population::population-lifecycle-replays-loss-and-site-boundaries-chronologically`, task2.1, test_regional_population_recovery.
- `wilderness-monster-population::runtime-population-uses-authored-regions-without-implicit-fallback`, task2.1, unobserved actual-owner integration.
- `world-clock::advance-settles-exactly-the-entities-its-caller-supplies-never-a-global-registry`, task2.1, explicit registered-owner versus ordinary caller-scope controls.

Create `/tmp/mud-field-tests.env` containing `MUD_TEST_SETTINGS=1` outside tracked source. Run one focused method/class at a time using the guarded command shown below; never concatenate the inventory or exceed 100 discovered tests. Register every new Python test module exactly once in `.github/evennia-shards.json`; new managed browser modules/methods belong exactly once in `.github/browser-shards.json`. Full managed-browser and complete traceability evidence remain CI-owned.

`uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <named-label>`

Use canonical identifiers generated by `uv run --locked python -m tools.spec_traceability list`, never by concatenating names. For added/removed requirements, generate the equivalent merged specification tree outside Git and run the same tool with `--repo-root`; use its output before updating annotations. Preserve substantive assertion roles; delete retired claims without forwarding decorators, copy/data pin tests or waivers. Record requirement/scenario-to-test assertions and exercised evidence in `docs/development/monster-field-behaviour.md`. Human ecology/wording/visual judgment is reviewed there rather than asserted by shipped strings or counts.

At implementation handoff run focused tests, `uv run --locked python -m tools.observability_lint check` alongside changed-logging tests, the existing command-doc contract whenever command docs change, `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. These are future worker checks, not feature verification during proposal creation. Failure restores every owning durable/live surface and emits no committed success. No compatibility readers, migrations, hidden initialization of an existing save or reset-on-load.
