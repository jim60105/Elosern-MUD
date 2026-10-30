# Design

## Context

Observed owners and nearby test targets: world/rules/travel_cost.py wilderness_step_cost/plan_traversal/source_present_members and fatigue.py pure prediction; new travel_plan.py; web/webclient/actions/map_actions.py read precedent, registry.py ActionSpec and dispatcher.py _publish_completion; new test_travel_plan.py/test_travel_actions.py and existing movement tests.

## Goals / Non-Goals

Expose bounded read-only travel.plan with sequential settlement prediction. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Add pure plan_travel(snapshot,destination,pace,stop_at_night), narrow actions/travel_actions.py and production registry entry travel.plan. Exact payload {destination:{x:int,y:int},pace:cautious|standard|forced,stop_at_night:bool}. Require current wilderness exploration actor and existing auth/admission. Re-resolve current cell, source-present travellers, clock and revealed window at query time. Domain errors only plan_destination_outside_window, plan_destination_unrevealed, plan_unreachable, plan_too_long, plan_party_cannot_travel. Normal malformed/auth/mode dispatcher refusals retain existing codes. Unexpected domain failure logs then returns plan_unreachable, never exceptions to client.

Window is inclusive current+/-20, clipped to frame. Reveal/passability use the owners, not map payload trust. Eight directions with two-orthogonal diagonal rule; both crossed orthogonals must be revealed/passable. Settlement footprints/grid gate entry are not routes; ordinary adjacent settlement entry remains its existing move descriptor. A same-cell destination yields empty steps/null indices/zero total/destination_reached, but sleepers still refuse. Search connectivity before the60-step bound so no path is unreachable and a valid selected weighted path>60 is too_long, never truncated.

Routing choice explicitly resolves an unspecified algorithm detail: A* with zero admissible heuristic (Dijkstra), initial snapshot fatigue frozen for candidate-edge pricing, using canonical wilderness_step_cost predicted durations. Stable n,ne,e,se,s,sw,w,nw neighbour order and heap(cost,steps,y,x) ties. This chooses a bounded duration-weighted route; it does not claim global fatigue-dependent optimality. Existing road terrain naturally wins if the canonical cost exposes it; no invented roads. If initial-state edge preflight refuses, obtain a routing-only weight from pure distance/terrain at that initial fatigue speed, factoring a read-only estimator beside current cost helpers. This never authorizes execution. Actual admission below exclusively uses existing preflight. Keep routing policy explicit in docs and tests rather than a worker guessing a reserve-state search.

Sequential replay calls wilderness_step_cost/plan_traversal using detached predicted member states for each edge; apply the existing pure FOOT_TRAVEL fatigue prediction over that edge's committed rounded seconds and carry end reserves/postures. A single ceil over all legs is forbidden. Real entities, object preparation, population, quest state, Attributes and clock never change. First-edge refusal/asleep party gives plan_party_cannot_travel. Later refusal returns admitted prefix and preflight_refused. Exact-zero arrival is admitted and ends prediction with member_asleep; no fabricated post-sleep steps.

Success data exact {origin:{x,y},destination:{x,y},steps:[{cell:{x,y},seconds,fatigue_stage}],total_seconds,nightfall_index,stop_index,stop_reason}. Indexes zero-based, nullable on empty. Positive integer seconds, worst after-step fatigue among present travellers, max60 steps. Keep admitted preview steps beyond voluntary stops, but never beyond a refused/post-sleep edge. total_seconds sums through stop_index. nightfall_index is first interval containing night entry, using absolute calendar boundaries rather than only comparing endpoint phases. Cautious stops after first crossing into light-or-worse, standard moderate-or-worse, forced no voluntary threshold. Already at/beyond configured threshold stops after first legal step. stop_at_night selects earlier nightfall. For simultaneous stops use member_asleep, preflight_refused, pace_threshold, nightfall, destination_reached order. Preflight_refused points to last admitted step, not refused index.

Return standard action outcome/code/message and bounded data slot, with internal no_presentation:true on success/domain rejection. dispatcher.py::_publish_completion already supports this serialized result-only path and strips the private flag in _normalize_result. Do not infer behavior from an empty affected tuple. Extend exact data validators only where needed. No new panel, browser queue or walking state. Test all five domain errors, policy stops, rounding/diagonal/heterogeneous parties, and predicted admitted-prefix duration/stages equal actual transactional one-by-one moves. Benchmark synthetic20000 visits with warmup and20 samples, median<=100ms on recorded development hardware. Update existing protocol documentation.

## Dependency contracts

- [wilderness-area-map-reveal](../wilderness-area-map-reveal/design.md) must land first.

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
