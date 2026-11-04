# Design

## Context

`_handle_disengage` currently stages only `battlefield.fled.add(stable_actor_id(actor))` as a PendingEffect. `_finalize_resolved_round` records occurrence offsets; `CombatSessionRecord.started_tick` and `population_cell` already protect deferred combat time. `population_lifecycle.register_regional_population` owns the existing final `monster_site_lifecycle` source and snapshot contract. `population_counts` already counts living home owners without a current position. The deleted provisioning module is not an attachment point.

## Goals / Non-Goals

Ship actual resolver-driven enemy escape and a globally settled journey, without ordinary wandering or proactive admission. All normal mapped combat receives a world context. Pure calculations opt into an abstract context explicitly. Shared route/history declarations from the two prerequisites are available before this change starts.

## Decisions

### Map-owned records and creation

Create `world/maps/monster_activity.py` as the sole writer of `wilderness.db.monster_activity = {"groups":dict[str,dict],"journeys":dict[str,dict],"receipts":dict[str,dict],"settled_through_tick":int}`. Explicit fresh provisioning initializes it once inside `sync_wilderness`'s existing compensated initialization. Missing or malformed state in an existing provisioned world refuses by `monster_activity_state_invalid`; no automatic legacy initialization, hidden reset or online migration.

Group JSON shape is `{"member_ids":list[int],"home_owner":{"kind":str,"key":str},"activity_key":str,"home":LocationRef,"position":LocationRef|None,"journey_id":str|None,"next_decision_tick":int,"sequence":int,"seed":int}`. Owner kinds are `zone`, `site`, `quest`, `explicit`; ownership references do not transfer quest or site authority. Group IDs derive from the placing operation ID and sampled composition ordinal; IDs and numeric member ordering are durable. A group is either idle at position or in one journey. Only construction owners create initial groups: hook `commit_population_wave`, `monster_sites._populate`, GM and quest explicit placement with complete activity binding, and staged exams with stationary binding. All use the saved population seed and current occurrence. These integrations assign group membership but enable no ordinary decisions yet.

Journey JSON shape is `{"group_id":str,"member_ids":list[int],"source":LocationRef,"destination":LocationRef,"depart_tick":int,"arrival_tick":int,"settled_through_tick":int,"retry_tick":int|None,"edge":PhysicalEdge-json,"plan":dict}`. Plan stores canonical traversal duration, segment fractions as integer numerator/denominator pairs and per-member initial validated optional fatigue state plus committed activity/waiver; use strict codecs, never pickle live objects. The elapsed cursor may advance beyond arrival while waiting, but physical plan progress clamps at arrival. Reuse the existing physiology writers and apply only the newly elapsed interval. Waiting after route completion uses ordinary posture activity, never a second travel charge. Absent optional physiology follows existing travel rules; partial/malformed halves refuse by name.

### Rules-owned escape and effect journal

Create `world/rules/world_escape.py` with frozen `WorldEscapeContext(session_id: str, occurred_tick: int, source: LocationRef, operation_id: str)` and explicit `AbstractEscapeContext()`. Context builders provide `event_context["escape_context"]` for every flee-capable BattlefieldActionContext. `_context_for` passes logical action-end time `started_tick + (rounds_elapsed + 1)*6`; there is no extra round per enemy. Standalone combat and manual campaign constructors explicitly provide abstract context. Missing mapped context is `EFFECT_RESOLUTION_FAILED`, never location-preserving fallback.

Public contract `plan_individual_escape(actor: Any, battlefield: Battlefield, context: WorldEscapeContext) -> EscapePlan | None` returns no route for legitimate blocked/unaffordable neighbors, propagates corrupt state, and quotes canonical execution edges after the actor's accumulated combat-activity contribution through occurred_tick. This is read-only projection of the same posture segments used by terminal settlement; factor one shared projector out of settlement, do not invent reserve arithmetic. World eligibility retains existing action and fastest-pursuer agility predicates. No pursuer skips only the roll, never route/energy checks. Choose among stable legal affordable neighbors using execution-scope deterministic state, independent from ordinary bounds or monster presence. Active encounter destination cells are ineligible. Failed route/contest leaves fled/location/group untouched, apart from normal action costs/upkeep/time.

`commit_monster_departure(wilderness: Any, plan: EscapePlan) -> str` belongs to the map owner and atomically records fled state through the resolver effect, detaches the single member into its own group, removes source coordinate/room attachment and creates one journey. Capture before/after PopulationPresence with alive True and no transit position at occurred_tick. Retain home_ecology_zone/site_key and bound quest IDs. Extend the effect's declared surfaces and actual action/round undo journals to include population timeline, activity record, coordinates, locations, room contents and physiology; database rollback alone is insufficient. Roster identity remains present-but-fled in the old Battlefield; reconstruction permits departed fled entities while requiring actual location for non-fled ones.

### Clock integration and protection

Extend `population_lifecycle`'s existing merged chronological loop with exact departure/arrival/retry boundaries; never register a second scheduler or recursively advance from a monster action. `settle_monster_activity_at(wilderness: Any, tick: int) -> list[ScheduledEvent]`, `next_monster_activity_boundary(wilderness: Any, after: int, end: int) -> int | None` and `snapshot_monster_activity_surfaces(start: int,end: int) -> dict[int,SurfaceSnapshot]` are the map-owner interfaces. Arrival preserves IDs/resources, registers destination coordinates and attaches only to an existing room. Room destinations use durable actual authored room identity. Unobserved wilderness destinations create no room.

Use existing historical cell protection for foreign entries and persist departure occurrence evidence so catch-up cannot wander or attach a departed actor retroactively before its departure tick. A lawful own escape can leave its protected source at occurred_tick. If a destination became protected, retain the same journey outside both endpoints, set retry_tick to tick + positive decision_interval and settle waiting physiology. Revalidate access at arrival; lawful temporary obstruction waits under the same positive retry policy, corrupt route state raises. New facts are consumed in the same advance chronologically. Partition/restart must not duplicate passage charges.

### Presence, quests and logging

Keep the registered upcoming population query conservative at this stage: include the next journey arrival/retry in its maintenance minimum. This lets the later hostile-admission slice stop existing interruptible callers safely before contact forecasting replaces maintenance returns.

Update actual-view/GM inspection to report journey separately, never a target at either endpoint. `population_view` continues projecting registrations, not plans. Exact entity quest destinations and stale text/browser target resolution use current actual presence, without changing objective_target_ids or defeat credit. The player can follow and voluntarily engage the same ID immediately after actual arrival; add no cooldown or last-opponent blacklist.

Add catalog rows `monster_departed`, `monster_arrived`, `monster_arrival_deferred`, `monster_escape_resolved` with outer-commit named-facade logging of owner/group/individual/source/destination/session/occurred tick and journey ID. Errors log an operational event and re-raise after whole-operation restoration; rolled-back success logs are discarded.

## Risks / Trade-offs

Most complexity is existing owner integration, not a new time authority. PendingEffects must remain side-effect-free until apply. Retrying the same operation uses saved deterministic candidates and returns the same receipt; receipts retain sufficient operation identity for the existing action/session replay lifetime, without an unbounded event transcript.

## Verification

New `world.maps.tests.test_monster_journeys` and `world.rules.tests.test_world_escape` register in evennia-shards; extend existing disengage integration and session persistence tests. Use real construction/registration and normal ActionResolver with two remaining enemies. Assert one member departs at round offset, remainder continues, transit appears at neither endpoint, partition/restart charges elapsed reserve once, later arrival preserves IDs and re-engagement succeeds. Exercise locked/corner/energy failure, no pursuer with no route, explicit abstract context, malformed physiology and faults after effect/registration/physiology/session writes. View/GM/quest tests establish actual presence without data/copy pinning. Both command docs describe actual enemy flee and re-engagement.

## Implementation evidence contract

Canonical IDs copied from traceability list output for the equivalent merged tree:

- `monster-journeys::mapped-individual-escape-commits-a-real-adjacent-departure`, tasks1.1-3.1, test_world_escape and test_disengage_integration.
- `monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence`, task4.1, test_monster_journeys.
- `monster-journeys::journey-operations-restore-complete-state-on-failure-and-replay`, tasks3.1-4.1, journey/session fault and replay controls.
- `disengage-action::a-successful-flee-adds-the-fleeing-entity-s-key-to-battlefield-fled-a-failed-attempt`, task3.1, actual resolver controls.
- `wilderness-population-view::population-reads-report-actual-living-registrations`, task4.1, view/quest/stale-target controls.

Create `/tmp/mud-field-tests.env` containing `MUD_TEST_SETTINGS=1` outside tracked source. Run one focused method/class at a time using the guarded command shown below; never concatenate the inventory or exceed 100 discovered tests. Register every new Python test module exactly once in `.github/evennia-shards.json`; new managed browser modules/methods belong exactly once in `.github/browser-shards.json`. Full managed-browser and complete traceability evidence remain CI-owned.

`uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb <named-label>`

Use canonical identifiers generated by `uv run --locked python -m tools.spec_traceability list`, never by concatenating names. For added/removed requirements, generate the equivalent merged specification tree outside Git and run the same tool with `--repo-root`; use its output before updating annotations. Preserve substantive assertion roles; delete retired claims without forwarding decorators, copy/data pin tests or waivers. Record requirement/scenario-to-test assertions and exercised evidence in `docs/development/monster-field-behaviour.md`. Human ecology/wording/visual judgment is reviewed there rather than asserted by shipped strings or counts.

At implementation handoff run focused tests, `uv run --locked python -m tools.observability_lint check` alongside changed-logging tests, the existing command-doc contract whenever command docs change, `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. These are future worker checks, not feature verification during proposal creation. Failure restores every owning durable/live surface and emits no committed success. No compatibility readers, migrations, hidden initialization of an existing save or reset-on-load.
