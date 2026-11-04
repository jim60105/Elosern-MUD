# Monster Field Behaviour: Developer Review and Evidence

This document is the human review and evidence surface for the monster
field-behaviour proposal set. Tests establish state, identity, legality and
timing rather than shipped copy, balance tables or coordinates.

## Movement Edge History

`movement-edge-history` owns the last completed player physical edge, its
read-only legality/pricing discovery, and the committed passage interval. The
implementation is `world/rules/movement_edges.py` plus integration seams in
`world/rules/movement_settlement.py`, `world/rules/travel_cost.py` and
`typeclasses/exits.py`.

### Stable locator contract

- `LocationRef` is a frozen tagged value and its strict JSON shape is exactly
  `{"kind": "wilderness", "map": str, "x": int, "y": int}` or
  `{"kind": "room", "id": int}`. Integers exclude `bool`; extra or missing keys
  are rejected. `encode_location_ref` / `decode_location_ref` are the codecs.
- `PhysicalEdge(source, destination, route)` serializes as exactly
  `{"source": LocationRef, "destination": LocationRef, "route": str}`. A
  wilderness source uses `direction:<normalized direction>`; an authored-room
  source uses `exit:<positive dbref>`. A gate stays its actual registered
  crossing.
- A room locator is legal only for a persistent authored room (`Room` or
  `GridRoom`). A pooled `TerrainRoom` is named by map + cell coordinates and is
  never a room locator; ephemeral `InstanceRoom`s and a body with no stable
  position raise `LocationRefError`.
- Discovery sorts edges by canonical serialized source/destination/route.
  `legal_edges` for a wilderness cell enumerates the eight canonical
  directions through the shared `find_gateway`/`wilderness_neighbor` rule; for
  an authored room it enumerates the room's real exits through their
  `traverse` access.

### Discovery, quoting and execution

`quote_edge` delegates to the canonical `travel_cost.resolve_traversal_cost`
(and therefore `plan_traversal` / `wilderness_step_cost` /
`gate_approach_cost` / `settlement_edge_cost`) and returns the existing
`TraversalResolution`. A recycled wilderness source is represented by a
read-only locator adapter (`movement_layer == "wilderness"`) so no pooled room
is fabricated. Detached `TravellerState` values price projected physiology via
their existing `detached()` adapters.

A stale edge (changed destination, locked exit, vanished room) is
`UNRESOLVED`. A legitimate refusal (sleeping party, pre-destination depletion)
raises `MovementPreflightRefused`. A named topology/physiology error (for
example half-written fatigue state) propagates rather than becoming an
unroutable edge. Discovery and quoting create no rooms, tick no gauge, advance
no clock and write no attribute.

`typeclasses/exits.py` no longer duplicates the gateway/neighbour rule: the
gate entry and both wilderness-return branches consume `resolve_exit_edge` /
`resolve_direction_edge`, keep the existing `preflight_movement_cost` record so
`charge_movement` still consumes exactly the preflight price, and pass the
completed `route`, `cost_key` and (for an ordinary step) the target cell into
the settlement.

### Retained history and invalidation

The only retained record is `body.db.previous_traversal` (attribute
`previous_traversal`), written by
`world.rules.movement_edges.record_completed_edge`:

- `settle_movement` captures the source locator before any relocation and, for
  a settled player-driven traversal, records the completed edge inside the
  owning transaction after the whole edge, its costs and following succeed. A
  non-traversal player-driven settlement (a direct `NPC.move_to`, including a
  possessed control body) invalidates instead.
- Every physically transported source-present party body that ended at the
  destination records the same edge (the traverser plus the follow set,
  including the commander's body under possession). A remote party body keeps
  its unchanged record. A follower left behind keeps its old record.
- `settle_relocation` (operator teleport) invalidates the moved body and every
  present party body that arrived with it.
- `PlayerCharacter.at_post_move` -> `note_direct_move_end` invalidates a
  successful direct move no settlement owns.
- `read_previous_edge` returns `None` for absent history and for a record whose
  destination no longer equals the body's current logical position; malformed
  history raises `MovementHistoryError` rather than silently resetting.

`previous_traversal` is part of `_TRAVERSER_SURFACES`, so the movement
settlement's full-window registry restores the old record on a rollback
together with contents, attributes, clock tick and wilderness bookkeeping.

### Passage visibility

`world.rules.movement_settlement.TraversalScope` is the immutable
`(member_ids, source, destination, departure_tick, arrival_tick)` bound before
the stock relocation, inside the causal publication group. `field_presence(body,
tick)` is `False` for a member during the half-open interval
`[departure_tick, arrival_tick)` and `True` at and after `arrival_tick`; a body
with no active scope is present at its actual location. The arrival tick is the
exact committed clock interval `charge_movement` advances (the preflight cost,
the authored non-distance default, or zero under the authorized flight waiver).
No browser timer authors this scope.

### Observability

Named facade imports only (`from world.observability import log_info, log_warn`).
Both catalog rows were added to the approved observability design:

- `movement_edge_completed` (`body`, `commander`, `source`, `destination`,
  `route`, `tick`) is deferred until the owning transaction commits.
- `movement_history_invalidated` (`body`, `commander`, `tick`, `reason`) is
  emitted only when a stored record was actually removed, also on commit.

A rolled-back settlement emits neither success event.

### Evidence map

Canonical synced requirement ID (generated with
`uv run --locked python -m tools.spec_traceability list` against the synced
`openspec/specs/movement-edge-history/spec.md`):
`movement-edge-history::completed-physical-edges-retain-stable-player-history`.
The listed tests carry that literal ID through `covers_requirement`.

| Scenario | Substantive test assertions |
| --- | --- |
| Recycled wilderness source | `world.rules.tests.test_movement_edges.MovementHistoryTests.test_pooled_source_recycles_and_reload_preserves_locators` (source cell frozen before the pooled room moves; cold attribute re-read returns the same locators); `LocationRefTests.test_pooled_terrain_room_locator_is_coordinates_not_room_id` |
| Failure and teleport | `MovementHistoryTests.test_failed_traversal_retains_the_previous_record` (clock failure restores source and keeps the old edge); `test_teleport_invalidates_the_record`; `test_fault_after_history_write_restores_source_history_and_tick` (injected post-history fault restores source, history, contents, Attribute cache and tick with no success event); `test_malformed_history_raises_and_stale_destination_is_none` |
| Possessed party | `PossessedMovementHistoryTests.test_transported_party_records_the_same_edge_and_remote_unchanged` (puppet, commander body and present companion share the edge; remote companion unchanged); `LegalEdgeTests.test_locked_exit_is_not_a_legal_edge` (reverse candidates consult current access) |
| Shared quote and passage | `QuotedExecutionAgreementTests.test_quote_matches_the_committed_gate_and_reverse_costs` and `test_quote_matches_the_committed_ordinary_step_cost` (quote seconds equal the actual charged tick delta both ways); `test_exact_zero_arrival_is_affordable_and_one_unit_less_refuses`; `test_partial_physiology_refuses_instead_of_pricing`; `LegalEdgeTests.test_approach_cell_routes_the_registered_gateway_and_no_wall_entrance` and `test_discovery_and_quote_are_read_only`; `PassageVisibilityTests.test_half_open_interval_has_no_idle_endpoint_presence` and `test_committed_wilderness_step_interval_ends_at_the_accepted_tick` |
| Serialization | `EdgeCodecTests` (exact tagged shapes, bool rejection, route/source-kind consistency, exact edge keys) |

Existing modules extended for the new baseline behaviors:
`world.rules.tests.test_movement_settlement` (blocked-corner patch now targets
the shared discovery; refused/failed gate entry compares bookkeeping with the
pre-traversal baseline because the landed regional population seeds the
wilderness script), `world.rules.tests.test_party_follow_possession`,
`typeclasses.tests.test_exit_movement_cost`, `world.rules.tests.test_movement`
and `web.webclient.presentation.tests.test_movement_alignment`.

### Focused verification run

```text
uv run --locked --env-file=.test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_movement_edges
uv run --locked --env-file=.test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_movement_settlement
uv run --locked --env-file=.test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_party_follow_possession
uv run --locked --env-file=.test.env evennia test --settings test_settings.py --keepdb typeclasses.tests.test_exit_movement_cost
uv run --locked --env-file=.test.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_movement
uv run --locked --env-file=.test.env evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_movement_alignment
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.contract_gate
uv run --locked openspec validate movement-edge-history --strict
```

`world.rules.tests.test_movement_edges` is registered exactly once in
`.github/evennia-shards.json` (`rules-12`, beside the movement-settlement
module). Full managed-browser and complete traceability evidence remain
CI-owned.

### Spec deviations

None. Presentation/copy/balance judgments are not asserted by shipped strings
or counts.

### Review dispositions

An independent rubber-duck review of the implementation produced these
dispositions:

- **Relocation mistaken for completion (blocking):** fixed. The success tail
  (`after_successful_movement`) now emits an explicit completion marker
  (`note_traversal_completed`), and history is written only when the settlement
  consumes that marker and observed a settled relocation. A stock `move_to`
  that relocates and then swallows a failing receive/post hook returns falsy
  without running the tail, so it records nothing. Regression:
  `MovementHistoryTests.test_relocated_falsy_plain_exit_records_no_completion`.
- **Discovery/quoting omitted receive and direction access (blocking):** fixed
  for the authored hard gate and materialized direction exits.
  `LimboRoom.refuses_arrival` is the pure read-only half of the hard gate used
  by discovery/quoting (no message, no NAttribute), and a materialized
  wilderness direction exit's real `traverse` lock is consulted. The generic
  `at_pre_move` combat veto is deliberately not applied: later escape/retreat
  consumers need lawful edges while a player is in combat, and the design
  treats that veto as execution admission, not physical topology. Regression:
  `LocationRefTests.test_limbo_receive_gate_is_consulted_read_only`.
- **Flight-waived quote was positive (blocking):** fixed. `quote_edge` applies
  the canonical `flight_waives_wilderness_charge` decision to the committed
  duration, matching `charge_movement` and the passage interval. Regression:
  `QuotedExecutionAgreementTests.test_flight_waived_step_quotes_zero_and_charges_zero`.
- **Unsupported endpoints left transported followers stale (blocking):** fixed.
  The settlement identifies actually moved party bodies from the pre-move
  location/registration and invalidates exactly that set when no edge can be
  retained; teleport invalidation likewise only touches moved bodies (a refused
  follower keeps its record).
- **Follower passage visibility (non-blocking, deferred):** the contract binds
  the source-present following set before the clock advance, which necessarily
  precedes the follow step; a follower later refused at the destination is
  hidden during passage as the design's committed interval requires. Later
  field-contact integration reads actual room contents at arrival, so this is
  not a defect in this change.
- **Event provenance (non-blocking):** fixed. Completion/invalidation resolve
  the bound commander for transported companions, and invalidation records the
  removed edge's source/destination/route when decodable.
- **Strict history validation (non-blocking):** fixed. Route patterns use
  full-string matching (a trailing newline is malformed), and a present null
  `previous_traversal` raises `MovementHistoryError` instead of reading as
  absence.

## Monster Field Activity: Authoring Schema and Review

This document records the authored field-activity layer published by the
`monster-activity-authoring` change. It is the human review surface for the
authored bindings; tests establish state, identity, legality and timing rather
than shipped wording, coordinates or counts.

### Declaration schema

`world/lore/monster_activity.py` publishes three frozen slotted row types and
two immutable registries:

```python
ActivityArea(key, region_key, rectangles, home_radius)
AggressionCondition(kind, area_key, dayparts)
MonsterActivity(key, policy, area_key, decision_interval, aggression)
```

- Policies are closed: `stationary`, `solitary_roaming`, `cohesive_group`.
- Aggression kinds are closed: `passive`, `contact`, `defended_area`.
- `ActivityArea` authors exactly one geometry form:
  - region intersection: a known wilderness `region_key` plus non-empty
    inclusive `(x_min, x_max, y_min, y_max)` rectangles and no `home_radius`;
  - home distance: a nonnegative `home_radius` and no region or rectangles.
- `resolve_activity_area(area, *, home, candidate_world)` returns the
  deduplicated, canonically sorted legal-cell locators. The home/result
  locator is exactly `{"kind": "wilderness", "map": str, "x": int, "y": int}`
  or `{"kind": "room", "id": int}`. A room home is legal only at radius zero
  and contains that room alone. Home distance is inclusive Chebyshev distance.
- Empty `dayparts` means all times; every nonempty value must be a clock
  rulebook daypart. `defended_area` requires an `area_key`; other kinds forbid
  one.
- Decision intervals are positive integer game ticks, including for
  stationary bindings.

`world/lore/monster_placement.py` adds required `activity_key` to
`EncounterComposition` and to `MonsterSite`. The site override wins only for
that site's own movement declaration; there is no variant fallback and exactly
one complete binding. `solitary_roaming` requires every permitted composition
outcome to total one individual (`sum(member.maximum) == 1`), checked at
publication for the composition binding and again for a site override. A
sampled singleton never authorizes a wider possible outcome. A
`cohesive_group` declaration is legal only as a complete composition binding.

### Candidate publication

The lore import validates the shipped declarations before publishing the
read-only registries. `world.maps.geography.build_geography` (reached from the
candidate bundle in `world.maps.runtime.compose`) then validates the same
declarations against the candidate's own regions and frame, and every site
binding against its complete composition. Any defect rejects the whole
candidate and leaves the previously published snapshot untouched.

Activity geometry is independent of birth geometry. Settlement birth buffers
are never consulted as movement barriers, and no birth exclusion participates
in `resolve_activity_area`.

### Authored binding review

Each ecology zone has one region extent matching its authored birth rectangle.
The three manual sites keep a region extent for their complete composition and
a zero-radius home extent for their own stationary override.

| Kind | Authored choice |
| --- | --- |
| Single-variant ecology compositions | `solitary_roaming`, 60-tick decisions |
| Mixed ecology compositions | `cohesive_group`, 90-tick decisions |
| Manual sites | `stationary`, passive, 120-tick decisions |
| Predators and wardens | `contact` or `defended_area` |
| Non-aggressive foragers | `passive` |
| Highland trail hunter | `contact` at dawn and dusk only |

These are authored declarations, not policy inferred from a species name or
from ecology prose. Exam opponents and GM/quest construction gain their
explicit activity input at the consuming runtime changes' deterministic
placement boundaries; this slice validates published quest/site references and
does not add runtime writers.

### Evidence map

Canonical requirement ID (generated with
`uv run --locked python -m tools.spec_traceability list` against the synced
`openspec/specs/monster-field-activity/spec.md`):
`monster-field-activity::activity-declarations-publish-complete-validated-bindings`.
The listed tests carry that literal ID through `covers_requirement`.

| Scenario | Substantive test assertions |
| --- | --- |
| Complete forms | `world.lore.tests.test_monster_activity.GeometryResolutionTests` (region enumeration, home radius, canonical sort, room zero); `PublishedActivityRegistryTests.test_every_shipped_reference_resolves` |
| Atomic rejection | `DeclarationValidationTests` (bad forms, unknown refs/dayparts, bool/nonpositive timing, duplicate keys, no mutation on failure); `CandidateAreaValidationTests` (unknown region, outside frame, no legal cell); `world.maps.tests.test_geography_source.ActivityCandidatePublicationTests` (whole candidate rejects, prior snapshot retained) |
| Separate topology | `GeometryResolutionTests.test_settlement_buffers_never_participate_in_activity_geometry`; `PublishedActivityRegistryTests.test_the_module_offers_no_execution_callable` |
| Every solitary outcome is valid | `BindingValidationTests.test_solitary_binding_rejects_any_multi_individual_outcome`; `world.lore.tests.test_monster_placement` site-override tests |

### Focused verification run

```text
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_activity
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_placement
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_geography_source
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_sites
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_population_geometry
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population_recovery
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_sync world.lore.tests.test_registry_index_contract world.lore.tests.test_registry_refs
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.quests.tests.test_compile_registration world.quests.tests.test_definitions world.quests.tests.test_site_clear_out_acceptance
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.tests.test_synthetic_data
uv run --locked python -m tools.contract_gate
uv run --locked openspec validate monster-activity-authoring --strict
```

## Mapped Monster Escape: Durable Departure and Journey

`mapped-monster-escape` replaces the location-preserving mapped flee with an
atomic legal departure and a durable journey. The owner is
`world/maps/monster_activity.py` (strict group/journey/receipt codecs, the
sole `wilderness.db.monster_activity` writer, chronological arrival and
protected-arrival waiting), the pure planner is
`world/rules/world_escape.py`, and the resolver seam is
`world/rules/disengage.py::_handle_disengage` with
`combat_session/battlefield.py::_context_for` supplying the explicit world or
abstract escape context.

Construction owners create the one initial group per occurrence:
`commit_population_wave` (retained `composition_key`/`activity_key` on
`PopulationPlacement`), `monster_sites._populate`, GM/quest explicit
registration (`STAGED_STATIONARY_ACTIVITY`), and staged exams. Per-member
`member_time` cursors mark admission, every completed round, departure and
terminal settlement. `population_lifecycle` merges journey arrival/retry
boundaries and snapshots the activity owner.

The scenario-to-test map for this change, with the canonical requirement IDs
the sync produced (`uv run --locked python -m tools.spec_traceability list`):

| Requirement | Scenario | Test assertions |
| --- | --- | --- |
| `monster-journeys::mapped-individual-escape-commits-a-real-adjacent-departure` | Real resolver departure | `world.maps.tests.test_monster_journeys.MappedFleeIntegrationTests.test_a_two_enemy_rounds_flee_departs_and_reengages_the_same_identity` (only the chosen enemy leaves `itemcoordinates`/room, keeps group ownership, journey starts at the round offset, remainder continues); `test_departure_removes_presence_and_replays_from_the_receipt` |
| `monster-journeys::mapped-individual-escape-commits-a-real-adjacent-departure` | Route or reserve failure | `world.rules.tests.test_world_escape.WorldEscapeTests.test_no_lawful_route_returns_no_plan_even_without_a_pursuer`; `test_a_missing_escape_context_is_a_named_rejection`; `test_partial_physiology_is_a_named_rejection_not_a_skip` |
| `monster-journeys::mapped-individual-escape-commits-a-real-adjacent-departure` | Outside normal range | `WorldEscapeTests.test_an_out_of_bounds_refuge_is_still_a_legal_escape` |
| `monster-journeys::mapped-individual-escape-commits-a-real-adjacent-departure` | Explicit abstract calculation | `WorldEscapeTests.test_an_abstract_context_changes_eligibility_only` |
| `monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence` | Unobserved partition and restart | `WorldEscapeTests.test_equal_partitions_and_a_reload_preserve_resources_and_progress`; `test_inactive_arrival_creates_no_room_and_preserves_identity` |
| `monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence` | Protected arrival | `WorldEscapeTests.test_a_protected_arrival_waits_without_a_second_travel_charge` |
| `monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence` | Deferred combat physiology transfers once | `MappedFleeIntegrationTests...` (reserve equals one 12-second combat prediction) and `WorldEscapeTests.test_two_deferred_combat_rounds_pay_twelve_seconds_once` |
| `monster-journeys::journey-operations-restore-complete-state-on-failure-and-replay` | Retained binding / group ownership | `test_monster_journeys.GroupConstructionTests.test_identical_member_rows_keep_their_own_selected_binding`; `test_a_group_collision_refuses_instead_of_absorbing_identities`; `ActivityRecordTests.test_missing_and_malformed_state_refuse_without_reset` |
| `wilderness-population-view::population-reads-report-actual-living-registrations` | Transit is not endpoint presence | `MappedPresenceConsumerTests.test_population_view_and_gm_inspection_never_show_transit_at_either_endpoint` (population view, hostile facts, room contents/name search, GM journey row; presence returns after arrival) |
| `monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence` | Equal partitions and restart | `WorldEscapeTests.test_the_population_lifecycle_settles_a_journey_in_equal_partitions`; `test_equal_partitions_and_a_reload_preserve_resources_and_progress` |
| `monster-journeys::journey-operations-restore-complete-state-on-failure-and-replay` | Late failure restores the whole operation | `WorldEscapeTests.test_a_late_lifecycle_failure_restores_the_whole_journey` (clock failure after arrival restores activity state, body location and reserve) |

Command docs (`docs/game/commands.md`,
`docs/game/command-reference.md`) describe the real mapped enemy departure and
its transit/arrival behaviour. GM inspection reports a travelling
individual's journey separately (`web/gm/readers/monsters.py`).

### Presence consumers

`population_view`, `travel_interrupts.live_hostile_facts`, room contents and a
room's name search are built from the actual coordinate registration and room
attachment, so an in-transit individual is absent from both endpoints by
construction. GM `placement_section` adds a separate `旅程` fact and omits
`所在房間` while the journey is open. After arrival the coordinate fact returns
and the journey row disappears. No quest consumer resolves an exact bound
target ID to a position: site clear-out acceptance binds living owned IDs and
defeat credit matches the same IDs, so departure and arrival change neither
`objective_target_ids` nor kill credit.

### Observability catalog

Outer-commit named-facade events (all success rows are scheduled only when the
enclosing durable transaction commits):

| Event | Context |
| --- | --- |
| `monster_departed` | `operation`, `group`, `individual`, `source`, `destination`, `journey`, `tick` |
| `monster_arrived` | `journey`, `group`, `individual`, `source`, `destination`, `tick` |
| `monster_arrival_deferred` | `journey`, `individual`, `destination`, `tick`, `retry_tick` |
| `monster_escape_resolved` | `operation`, `group`, `individual`, `source`, `destination`, `journey`, `tick` |
| `monster_escape_failed` | `session`, `operation`, `individual`, `group`, `source`, `destination`, `tick` (warn; emitted before the enclosing commit restores every surface) |

A rolled-back departure emits none of the success rows.

### Review dispositions

An independent rubber-duck review of the implementation produced these
dispositions:

- **Idle physiology discarded (blocking):** fixed. Admission now pays the
  member's idle prefix through the canonical fatigue writer at the session
  start before it becomes combat-owned (`begin_member_combat`). Regression:
  `WorldEscapeTests.test_admission_pays_the_idle_prefix_before_combat_ownership`.
- **Successful protected-arrival retry lost its waiting interval
  (blocking):** fixed. Every due boundary pays newly elapsed travel and
  ordinary waiting before it arrives or defers; the successful retry assertion
  is now exact (`test_a_protected_arrival_waits_without_a_second_travel_charge`).
- **Real authored-room battles used abstract escape (blocking):** fixed. A
  hostile session carries a world context at its durable room locator, and
  completed-round/terminal combat ownership now follows the real hostile mode
  instead of the wilderness cell. Staged exams remain explicitly abstract.
  Regression: `test_a_real_authored_room_session_has_world_escape_authority`.
- **Arrival did not revalidate route access (blocking):** fixed. Arrival
  re-resolves the committed edge read-only (topology, traverse access and
  destination refusal) without repricing; a temporary obstruction defers with
  the same positive retry, and a vanished authored source room raises.
  Regression: `test_a_locked_room_exit_defers_arrival_and_retries_without_repricing`.
- **Quest exact-destination scope (non-blocking):** the current quest read
  surface uses authored site/habitat guidance and matches bound target IDs; no
  supported objective family resolves an ID to a live position. That clause is
  therefore position-independent in this tree: bound IDs and defeat credit are
  unchanged by departure/arrival, and the actual view excludes transit. This is
  recorded as an applicability disposition, not claimed as new wiring.
- **Sleep-receipt rollback coverage (non-blocking, follow-up):** the activity
  snapshot now includes `SLEEP_RECEIPT_SURFACES`, and both rollback tests
  assert the pre-operation state of the member and journey. A behavioural
  forced-sleep-threshold receipt mutation is not constructed here; the global
  monster-activity slice introduces owner-settled idle physiology and owns that
  deeper receipt transition test. This is a test-depth follow-up, not a
  deferred correctness fix.

### Focused verification run

```text
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_world_escape
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_journeys
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_disengage world.rules.tests.test_disengage_integration world.maps.tests.test_wilderness_population
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population world.maps.tests.test_monster_sites
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_combat_session_persistence world.rules.tests.test_disengage world.rules.tests.test_disengage_integration world.rules.tests.test_companion_field_opening
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_combat_initiation
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_combat_session_flow
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb tests.test_command_docs
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_bootstrap_sync
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.contract_gate
uv run --locked openspec validate mapped-monster-escape --strict
```

`world.maps.tests.test_monster_journeys` is registered exactly once in
`.github/evennia-shards.json` (`maps-34`) and
`world.rules.tests.test_world_escape` exactly once in `rules-12`. The
bootstrap module's fixed-dbref assertion depends on a pristine test database;
on a reused database its object sequence is advanced and the assertion fails
identically on the untouched baseline, while a fresh test database passes all
20. `world.rules.tests.test_guild_exams` retains its baseline-only
`test_incoherent_cold_start_fails_once_and_restores_the_host` failure
(identical on the untouched parent).
