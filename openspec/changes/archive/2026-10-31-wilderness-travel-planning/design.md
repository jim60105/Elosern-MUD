# Design

## Context

Observed owners and nearby test targets: world/rules/travel_cost.py wilderness_step_cost/plan_traversal/source_present_members and fatigue.py pure prediction; new travel_plan.py; web/webclient/actions/map_actions.py read precedent, registry.py ActionSpec and dispatcher.py _publish_completion; new test_travel_plan.py/test_travel_actions.py and existing movement tests.

## Goals / Non-Goals

Expose bounded read-only travel.plan with sequential settlement prediction. Keep the named slice complete and independently runnable after prerequisites; dependent behavior is owned elsewhere.

## Decisions

Add pure plan_travel(snapshot,destination,pace,stop_at_night), narrow actions/travel_actions.py and production registry entry travel.plan. Exact payload {destination:{x:int,y:int},pace:cautious|standard|forced,stop_at_night:bool}. Require current wilderness exploration actor and existing auth/admission. Re-resolve current cell, source-present travellers, clock and revealed window at query time. Domain errors only plan_destination_outside_window, plan_destination_unrevealed, plan_unreachable, plan_too_long, plan_party_cannot_travel. Normal malformed/auth/mode dispatcher refusals retain existing codes. Unexpected domain failure logs then returns plan_unreachable, never exceptions to client.

Window is inclusive current+/-20, clipped to frame. Reveal/passability use the owners, not map payload trust. Eight directions with two-orthogonal diagonal rule; both crossed orthogonals must be revealed/passable. Settlement footprints/grid gate entry are not routes; ordinary adjacent settlement entry remains its existing move descriptor. A same-cell destination yields empty steps/null indices/zero total/destination_reached, but sleepers still refuse. Search connectivity before the60-step bound so no path is unreachable and a valid selected weighted path>60 is too_long, never truncated.

Routing choice explicitly resolves an unspecified algorithm detail: A* with zero admissible heuristic (Dijkstra), initial snapshot fatigue frozen for candidate-edge pricing, using canonical wilderness_step_cost predicted durations. Stable n,ne,e,se,s,sw,w,nw neighbour order and heap(cost,steps,y,x) ties. This chooses a bounded duration-weighted route; it does not claim global fatigue-dependent optimality. Existing road terrain naturally wins if the canonical cost exposes it; no invented roads. If initial-state edge preflight refuses, obtain a routing-only weight from pure distance/terrain at that initial fatigue speed, factoring a read-only estimator beside current cost helpers. This never authorizes execution. Actual admission below exclusively uses existing preflight. Keep routing policy explicit in docs and tests rather than a worker guessing a reserve-state search.

Sequential replay first calls wilderness_step_cost/plan_traversal using detached predicted member states for each edge. Distinguish physical admission duration from charged duration. Extract the existing charge_movement flight-waiver decision into a pure canonical helper reused by execution and planning: only an owned, currently allowed flight effect on the actual traverser waives wilderness charge; flash_step alone does not. Ordinary sleeping/depletion preflight runs before the waiver. An admitted waived edge has charged seconds0, unchanged calendar/reserves/posture and no fatigue/night-entry transition. Otherwise apply the existing pure FOOT_TRAVEL fatigue prediction over that edge's rounded charged seconds and carry end reserves/postures. A single ceil over all legs is forbidden. Real entities, object preparation, population, quest state, Attributes and clock never change. First-edge refusal/asleep party gives plan_party_cannot_travel. Later refusal returns admitted prefix and preflight_refused. Exact-zero reserve arrival is admitted and ends prediction with member_asleep; no fabricated post-sleep steps.

Success data exact {origin:{x,y},destination:{x,y},steps:[{cell:{x,y},seconds,fatigue_stage}],total_seconds,nightfall_index,stop_index,stop_reason}. Indexes zero-based, nullable on empty. Nonnegative integer charged seconds, worst after-step fatigue among present travellers, max60 steps. Keep admitted preview steps beyond voluntary stops, but never beyond a refused/post-sleep edge. total_seconds sums through stop_index. nightfall_index is first positive charged interval containing night entry, using absolute calendar boundaries rather than only comparing endpoint phases. Cautious stops after first crossing into light-or-worse, standard moderate-or-worse, forced no voluntary threshold. Already at/beyond configured threshold stops after first legal step, including a zero-charge flight step; the move interrupt uses the same initial-state rule. stop_at_night selects earlier nightfall. For simultaneous stops use member_asleep, preflight_refused, pace_threshold, nightfall, destination_reached order. Preflight_refused points to last admitted step, not refused index.

Return standard action outcome/code/message and bounded data slot, with internal no_presentation:true on success/domain rejection. dispatcher.py::_publish_completion already supports this serialized result-only path and strips the private flag in _normalize_result. Do not infer behavior from an empty affected tuple. Extend exact data validators only where needed. No new panel, browser queue or walking state. Test all five domain errors, policy stops, rounding/diagonal/heterogeneous parties, and predicted admitted-prefix duration/stages equal actual transactional one-by-one moves. Benchmark synthetic20000 visits with warmup and20 samples, median<=100ms on recorded development hardware. Update existing protocol documentation.

## Dependency contracts

## Review dispositions and concrete evidence

B1 is adopted. Add test_allowed_flight_has_zero_charge_and_matches_real_steps, test_restricted_flight_and_flash_step_use_foot_cost and test_flight_does_not_bypass_sleep_or_depletion in test_travel_plan.py and the existing movement suite. Route selection still uses physical predicted weights; charge waivers affect sequential replay and stops only. These tests use synthetic ownership/restriction facts and compare real settlement.

B3 uses the shared first-legal-step stop when already fatigued. Add test_initial_pace_state_matches_the_committed_first_step for light/moderate/severe states under all paces; it compares this query's first-legal-step decision with the identical departure's real committed after-step stage against the same threshold table (the move-interrupt flag itself is owned by the later slice — see the initial-pace note under the requirement-to-test mapping).

The frozen-weight suggestion is adopted. Add test_frozen_route_choice_is_separate_from_sequential_replay with two synthetic paths whose initially cheaper edge-weight sum differs from the sum after fatigue replay; assert the selected frozen-weight path and then independently assert its committed per-step predictions.

The requirement-to-test mapping belongs in this design's evidence section. Existing canonical targets are movement-cost-charging requirements for admission/waiver and webclient-area-map for read-only query state. Obtain their exact IDs with the tool; remount to the two new capability requirements on the equivalent merged tree. Do not hand-compose IDs.

### Requirement-to-test mapping (pre-sync)

The delta's ADDED requirements have no canonical ID before archive sync, so
each mechanism test currently annotates the nearest current canonical
requirement exactly as `docs/development/spec-test-traceability.md` requires.
The planned remount targets were produced by running
`tools.spec_traceability list --repo-root <equivalent merged spec tree>`
(the delta merged as the capability's `openspec/specs/wilderness-travel-planning/spec.md`),
never hand-composed:

- `wilderness-travel-planning::travel-queries-route-within-revealed-wilderness`
- `wilderness-travel-planning::travel-prediction-matches-sequential-admitted-steps`

| Test (`world/rules/tests/test_travel_plan.py` unless noted) | Scenario it establishes | Current canonical annotation | Remount target |
| --- | --- | --- | --- |
| `test_route_goes_around_water_and_prefers_the_lower_canonical_duration` | Routing and errors | `movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed` | travel-queries… |
| `test_a_diagonal_needs_both_crossed_orthogonals_passable_and_revealed` | Routing and errors | same | travel-queries… |
| `test_a_registered_gateway_direction_is_never_an_ordinary_route` | Routing and errors | `wilderness-gateway::wildernessreturnexit-routes-every-registered-approach-cell-and-direction-pair-back-to-the-grid` | travel-queries… |
| `test_each_domain_error_keeps_its_stable_code` | Routing and errors | `movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed` | travel-queries… |
| `test_same_cell_destination_is_an_empty_arrival_but_sleepers_refuse` | Stops and refusal | `movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion` | travel-queries… |
| `test_an_absent_physiology_traveller_is_admitted_at_base_speed` | Committed equivalence | `movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed` | travel-prediction… |
| `test_the_snapshot_matches_its_canonical_owners_and_writes_nothing` | Read isolation and publication | `wilderness-ground-reveal::permanent-reveal-is-a-bounded-read-projection` + `webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay` | travel-queries… |
| `test_malformed_physiology_is_party_cannot_travel_not_an_internal_error` | Stops and refusal | `movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion` | travel-prediction… |
| `test_predicted_prefix_matches_real_transactional_steps` | Committed equivalence | `movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance` | travel-prediction… |
| `test_allowed_flight_has_zero_charge_and_matches_real_steps` | Flight charge follows execution | `movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function` | travel-prediction… |
| `test_restricted_flight_and_flash_step_use_foot_cost` | Flight charge follows execution | same | travel-prediction… |
| `test_flight_does_not_bypass_sleep_or_depletion` | Flight charge follows execution | `movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function` + `movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion` | travel-prediction… |
| `test_initial_pace_state_matches_the_committed_first_step` | Initial pace state agrees with move interruption | `movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance` | travel-prediction… |
| `test_first_refusal_is_party_cannot_travel_and_a_later_one_keeps_the_prefix` | Stops and refusal | `movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion` | travel-prediction… |
| `test_exact_zero_arrival_is_admitted_and_ends_with_member_asleep` | Committed equivalence / Stops and refusal | `movement-cost-charging::sparse-edge-admission-refuses-pre-destination-depletion` | travel-prediction… |
| `test_preview_steps_continue_past_a_voluntary_stop` | Stops and refusal | `movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance` | travel-prediction… |
| `test_each_pace_stops_at_the_first_step_at_or_beyond_its_threshold` | Stops and refusal | `movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed` | travel-prediction… |
| `test_heterogeneous_party_pays_the_slowest_member_and_reports_the_worst_stage` | Committed equivalence | `movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed` | travel-prediction… |
| `test_a_waived_plan_charges_zero_and_keeps_every_reserve_and_the_calendar` | Flight charge follows execution | `movement-cost-charging::charge-movement-is-the-single-shared-movement-cost-charging-function` | travel-prediction… |
| `test_nightfall_index_uses_absolute_calendar_boundaries` | Stops and refusal | `movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance` | travel-prediction… |
| `test_night_entry_transitions_cover_starts_ends_and_later_nights` | Stops and refusal | `movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance` | travel-prediction… |
| `test_the_earlier_stop_wins_and_a_tie_uses_the_design_priority` | Stops and refusal | `movement-cost-charging::terrain-and-the-slowest-eligible-traveller-determine-speed` | travel-prediction… |
| `test_frozen_route_choice_is_separate_from_sequential_replay` | Frozen route selection is distinct from replay | `movement-cost-charging::traversal-integrates-fatigue-over-remaining-distance` | travel-prediction… |
| `test_warmed_plan_with_twenty_thousand_visits_is_within_one_hundred_ms` | Read isolation and publication (bound) | `wilderness-ground-reveal::permanent-reveal-is-a-bounded-read-projection` | travel-queries… |
| `test_an_absent_clock_is_read_as_zero_and_is_never_created` (`test_travel_plan.py`) | Read isolation and publication | `webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay` | travel-queries… |
| `test_the_exact_payload_is_normalized_and_every_deviation_is_rejected` (`web/webclient/actions/tests/test_travel_actions.py`) | Read isolation and publication | `webclient-action-dispatch::action-registries-are-allowlisted-and-duplicate-safe` | travel-queries… |
| `test_the_production_registry_binds_the_travel_plan_spec` (`test_travel_actions.py`) | Read isolation and publication | same | travel-queries… |
| `test_success_is_a_result_only_plan_and_a_mode_refusal_keeps_its_code` (`test_travel_actions.py`) | Read isolation and publication | `webclient-area-map::map-view-requests-publish-the-requested-area-without-changing-gameplay` | travel-queries… |
| `test_every_domain_refusal_maps_to_its_stable_code_and_message` (`test_travel_actions.py`) | Routing and errors | same | travel-queries… |
| `test_an_unexpected_failure_is_logged_and_answers_plan_unreachable` (`test_travel_actions.py`) | Read isolation and publication | same | travel-queries… |
| `test_a_mode_read_failure_is_result_only_and_never_re_snapshots` (`test_travel_actions.py`) | Read isolation and publication | same | travel-queries… |
| `test_dispatch_publishes_only_the_correlated_result_and_writes_nothing` (`test_travel_actions.py`) | Read isolation and publication | same | travel-queries… |
| `test_a_domain_refusal_publishes_no_presentation_and_keeps_state` (`test_travel_actions.py`) | Read isolation and publication | same | travel-queries… |

No waiver test is attached to
`movement-cost-charging::flight-required-exits-pass-only-for-flight-flash-step-owners`:
that requirement governs exit admission, not the wilderness charge waiver; the
charge tests attach to the charge/admission requirements instead. The
cross-slice "move interruption" half of the initial-pace scenario is owned by
the later `wilderness-travel-interrupts` change (its `pace_threshold` flag is
not implemented in this tree), so
`test_initial_pace_state_matches_the_committed_first_step` compares the query's
first-legal-step decision with the identical departure's real committed
after-step stage and the shared threshold table that slice must reuse; it does
not claim the flag surface exists here.

### Remount completed at archive

The archive sync created both canonical IDs above. Every mapping row's test now
annotates its remount target instead of the pre-sync neighbour, and
`tools.spec_traceability check` reports 2655 requirements, 2655 covered, 0
uncovered, 0 errors on the synced tree. `test_warmed_plan_with_twenty_thousand_visits_is_within_one_hundred_ms`
kept its pre-sync `wilderness-ground-reveal::permanent-reveal-is-a-bounded-read-projection`
association rather than gaining a remounted one, because it is skipped unless
`MUD_TRAVEL_PLAN_BENCHMARK=1` and would not establish coverage on its own; the
requirement's bounded-read clause is carried by the non-skipped routing and
publication tests above.

### Post-implementation review dispositions

The final review raised two blocking items; both are addressed on the branch.

1. *Mode admission escaped the failure boundary.* `travel_plan_adapter` now
   reads `actor.location` and `in_exploration_mode` inside its guarded
   operation, so an unexpected stored-mode read failure logs
   `travel_plan_failed` and answers `plan_unreachable` through the same
   result-only path; `test_a_mode_read_failure_is_result_only_and_never_re_snapshots`
   proves no update/snapshot, no revision change and the logged event. Ordinary
   mode refusals keep the existing `not_exploring` code.
2. *The frozen-route test did not compare complete routes.* It now compares two
   complete legal routes to the same destination (14, 10): route A is nine road
   edges (three diagonal) plus one mountain edge, route B is four mountain
   edges, and the initial reserve puts the normal→light boundary exactly at the
   end of A's first 800 s road edge. The test asserts the strict inversion the
   delta names: frozen sum A < frozen sum B, while cumulative replay A > replay
   B; the planner selects A (the frozen winner); and every returned step equals
   an independent canonical cost/prediction replay built from a local probe,
   not the planner's traveller type. The initial reserve and the first step's
   price are derived from the live policy and the canonical cost owner, and a
   registered gateway direction blocks the diagonal shortcut that would
   otherwise bypass the intended route.

Non-blocking review items were also closed: night-entry detection now tracks
phase transitions across the whole interval (start, exact end boundary,
night→day→night), a night-start interval no longer suppresses a later entry;
the committed-equivalence test now compares every emitted `fatigue_stage` with
the canonical worst stage of the committed members; the exact-zero test walks a
route with a further unperformed edge; stop-priority and earlier-stop ties have
direct tests; the read-isolation tests compare persisted attribute values, the
clock tick, location and revision (success and refusal) and pin the
non-creating clock accessor with an absent-clock case; and all fatigue fixtures
derive their reserves and per-step seconds from the live policy/rulebook rather
than calibration literals. The shipped-gateway probe keeps the repository's
established live-registry idiom (unique-match assertion) used by the existing
movement-settlement tests, because the wilderness contrib identity is a
production fixture there.

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
