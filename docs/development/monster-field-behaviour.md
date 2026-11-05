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

`world/lore/monster_activity.py` publishes frozen slotted row types, the
`MovementUnit` formation value, the pure `movement_units` helper, and two
immutable registries:

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
one complete binding. Publication only resolves that binding: it checks that
the composition and the site override each name a published activity, and it
never lets a member count select or reject a policy. A binding's policy instead
decides group formation at construction
(`monster_activity.movement_units`), so a `solitary_roaming` binding of a
composition whose legal outcomes exceed one individual is lawful and disperses
its members into one-member groups. See "Activity Group Formation" below.

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
| Every solitary outcome is valid | `MovementUnitTests` (a solitary row of three becomes three units, cohesive rows stay one unit); `world.lore.tests.test_monster_placement` site-override tests |

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

## Global Monster Activity: Seeded Global Decisions

`global-monster-activity` lets every real group take saved bounded decisions on
game time through the existing population clock source, including groups in
unobserved cells. The owner remains `world/maps/monster_activity.py` (strict
`ActivityDecision` plans, atomic group departures/arrivals, per-member
`member_time` cursors, and the one activity draw); the coordinator remains
`world/maps/population_lifecycle.py`. There is no second scheduler and no
monster action ever calls `WorldClock.advance`.

### Decision contract

`ActivityDecision(group_id, tick, expected_sequence, edge, reason)` is the
immutable plan. `plan_group_decision` is a pure read: it resolves the group's
published activity area, intersects every living member's real
`legal_edges` discovery, keeps only unprotected destinations directly inside
that area, prices each surviving edge through the canonical `quote_edge`
resolver at the whole group's slowest actual speed, and samples from
`[stay] + edges` through `regional_population.draw_index` with the saved
`seed/group/sequence/tick/purpose`. A group outside its bounds has no stay
candidate and may only step directly back inside; with no such edge it waits.
Reads, reconnects and reloads recompute the same decision and consume nothing.

`commit_group_decision` revalidates sequence, idle position, living membership,
per-member access, area membership, destination protection and canonical
pricing before any write. A stay increments the sequence once and schedules a
positive interval. A departure moves every living member in one atomic group
journey; a residual group of non-moving (dead) identities keeps the original
id. Closing the owning one whole-group departure carries `old sequence + 1`;
a split child starts at sequence `0`, exactly like the predecessor's
single-member escape. Both the departure and its physiology settle inside the
owner's snapshot/restore boundary.

Physiology uses the existing cursors and the canonical fatigue and gauge
writers: idle posture is paid in interruptible segments at the fatigue
owner's own boundaries (so arbitrary advance partitions agree), journey
traffic pays foot travel, waiting pays the member's posture, and each cursor
advances monotonically. `activity_member_mode` lets the clock's caller-scoped
mental/gauge stages skip an activity-owned body, so a supplied body and an
unobserved one settle the identical interval under their owner exactly once.

### Same-tick ordering and recovery

`_settle_population_at` now runs lawful arrivals/retries, then zone boundary
refresh, site births, regional births, idle departures, the same-tick
zero-duration arrival, and a final boundary refresh before consuming the
timeline. A departure that creates a local deficit therefore starts its
recovery episode at the departure tick rather than a later unrelated one.
Historical combat participants whose cursor is already ahead of a decision
tick stay, and protected destinations are never entered.

### Observability catalog

| Event | Context |
| --- | --- |
| `monster_activity_decided` | `group`, `sequence`, `tick`, `reason` (outer commit only; reads emit no mutation event) |

### Evidence map

Canonical IDs below are generated with
`uv run --locked python -m tools.spec_traceability --repo-root /tmp/os-merged
list` against an equivalent merged specification tree built outside Git by
running `openspec archive global-monster-activity --yes` on a copy. Those two
delta IDs are **not yet synced**, so no test carries them; tests use only
already-synced IDs, and the mapping is recorded here until archive.

New (not yet synced) requirement IDs:

- `monster-field-activity::due-activity-moves-bounded-complete-groups-globally`
- `monster-journeys::activity-ordering-protects-encounters-across-deferred-time`

| Requirement | Scenario | Substantive test assertions |
| --- | --- | --- |
| `monster-field-activity::due-activity-moves-bounded-complete-groups-globally` | Unobserved and restart | `world.maps.tests.test_monster_activity.SeededDecisionTests.test_saved_decision_is_stable_across_reads_and_reload` (a stay seed and a departure seed reproduce after an attribute-cache reload; a replay is stale; departure removes source registration); `test_departure_is_atomic_and_arrival_is_one_unit` (all three identities leave and arrive together, no room is created, the full persisted record reloads) |
| `monster-field-activity::due-activity-moves-bounded-complete-groups-globally` | Slowest member and topology | `test_mixed_group_travels_at_the_slowest_member_price` (committed seconds equal the canonical all-member quote and are never faster than the fast member alone); `test_sleeping_member_keeps_the_whole_group`; `test_unaffordable_member_keeps_the_whole_group`; `test_commit_revalidates_every_members_access`; `test_bounds_corner_and_locked_gates_hold`; `test_birth_exclusions_never_block_lawful_travel` |
| `monster-field-activity::due-activity-moves-bounded-complete-groups-globally` | Stationary bindings | `test_stationary_group_never_moves_or_restores_identity` (position, member IDs and home owner unchanged across a long advance; the sequence still advances as scheduled stays) |
| `monster-field-activity::due-activity-moves-bounded-complete-groups-globally` | Return after escape | `test_outside_bounds_member_returns_or_waits` (only an inside destination is chosen; a sealed outside cell waits) |
| `monster-journeys::activity-ordering-protects-encounters-across-deferred-time` | Same tick contact precedence | `world.maps.tests.test_monster_activity.ChronologicalSettlementTests.test_same_tick_phases_run_arrivals_births_then_departures` (phase order arrival → site → regional → departure) |
| `monster-journeys::activity-ordering-protects-encounters-across-deferred-time` | Historical protection | `test_combat_owned_and_historical_members_never_wander` (combat ownership and a cursor already settled past the tick both stay); `test_protected_destination_prevents_departure` (a protected neighbour is never entered) |
| `monster-journeys::activity-ordering-protects-encounters-across-deferred-time` | Newly due facts | `test_advance_processes_decision_arrival_then_next_decision` (one advance processes the 60-tick decision, the later arrival and a strictly later decision); `test_newly_created_group_is_due_within_one_advance`; `test_equal_partitions_preserve_resources_and_schedule` (equal partitions produce identical positions, sequences, schedules, reserves and cursors, and a repeated endpoint is a no-op) |
| `world-clock::advance-settles-exactly-the-entities-its-caller-supplies-never-a-global-registry` | Explicit activity-owned interval | `test_supplied_activity_member_settles_once_under_its_owner` (a supplied member and an unobserved twin end with equal reserve, gauge and cursor after one advance) |
| `world-clock::a-rolled-back-advance-restores-every-callback-owned-surface-not-just-caller-entities` | Forced-sleep receipt depth (carried follow-up) | `test_forced_sleep_receipt_rolls_back_with_a_late_source_fault` (the owner's idle settlement crosses the forced-sleep threshold and creates a threshold receipt; a late source fault restores the activity record, reserve, cursor, trait store and receipt cache; a retry then commits the same receipt and 12 seconds of sleep recovery) |
| `world-clock::a-rolled-back-advance-restores-every-callback-owned-surface-not-just-caller-entities` | Newly born group inside a failed advance | `test_a_birth_and_departure_in_one_advance_roll_back_completely` (a group created at a boundary departs inside the advance; a late fault removes the row and its group, restores the tick, and a deterministic retry recreates and moves it) |
| `monster-journeys::journey-passage-preserves-elapsed-resources-and-actual-presence` | Unobserved partition and restart | `test_unobserved_wandering_waits_for_a_live_encounter_then_reloads` (a real unobserved group departs, waits outside the live protected destination, reloads its journey, then arrives with no room created at either cell); `test_equal_partitions_preserve_resources_and_schedule` (departure, arrival and a later decision across one advance versus two partitions, including gauges) |
| `monster-journeys::journey-operations-restore-complete-state-on-failure-and-replay` | Death in transit | `test_a_member_killed_in_transit_is_not_resurrected` (no physiology or gauge is paid for a dead member; the recorded arrival fact is `alive=False` and no destination registration is minted) |
| `world-clock::advance-settles-exactly-the-entities-its-caller-supplies-never-a-global-registry` | Combat prefix gauge ownership | `test_combat_prefix_regenerates_gauges_before_ownership_release` (the combat owner pays the exact gauge interval once, then releases the cursor; a replay is a no-op) |

### Changed-logging evidence

`monster_activity_decided` is scheduled only inside the owning transaction via
`transaction.on_commit`; a rolled-back advance emits no success row. The
forced-sleep rollback test exercises that path along with the restored
receipt. Reads (`plan_group_decision`, read-model inspection) emit nothing.

### Review dispositions

An independent plan review produced these blocking findings and their
resolutions before implementation:

- **Historical participants could depart before their battle ended:** fixed.
  A member whose `member_time` cursor is already ahead of the decision tick
  stays with `member_settled_ahead`; idle settlement never regresses a cursor.
  Regression: `test_combat_owned_and_historical_members_never_wander`.
- **A departure-created deficit missed the same-tick recovery episode:** fixed.
  The coordinator refreshes each zone's boundary dates after departures and
  before consuming the timeline; no second birth phase runs.
- **A zero-duration departure scheduled an unreachable same-tick arrival:**
  fixed. The coordinator settles due journeys again after departures, inside
  the same clock advance and without recursion.
  Regression: `test_zero_duration_departure_arrives_at_the_same_tick`.
- **A departing group reset its sequence:** fixed for a complete ordinary
  departure (`old sequence + 1`); only a split child starts at zero, matching
  the predecessor's escape contract.
- **Commit did not revalidate every member's access:** fixed. Commit repeats
  the per-member legal-edge intersection. Regression:
  `test_commit_revalidates_every_members_access`.
- **Gauge physiology stayed caller-scoped:** fixed. The owner settles gauges
  through the canonical `settle_gauge_regeneration` writer for idle and
  journey intervals, and the clock skips exactly those bodies; the activity
  snapshot now includes the durable `traits` surface.
- **The public commit had no explicit transaction/restore boundary:** fixed.
  Both stay and departure commits snapshot the activity, timeline and member
  surfaces and restore them when the enclosing savepoint fails.
- **Planner and lifecycle could evaluate different physiology:** fixed. The
  pure planner projects the unpaid idle prefix with the same interruptible
  segmentation the commit later settles, so the read-only decision agrees with
  the committed one.
- **Coverage gaps:** the unobserved/live-encounter, partition, same-tick
  ordering and forced-sleep receipt tests above close them.

The final independent review of the complete diff added these dispositions:

- **Combat survivors lost their gauge interval (blocking):** fixed. The
  combat owner now pays the combat prefix's gauge regeneration through
  `settle_gauge_regeneration` before releasing the cursor, and admission pays
  the idle prefix's gauge; the clock skips every activity-owned body for
  gauges so the owner is the only payer. Regression:
  `ChokepointLifecycleTests.test_combat_prefix_regenerates_gauges_before_ownership_release`.
- **A released participant could wander at the terminal boundary
  (blocking):** fixed. Planning and commit consult the persisted active
  hostile session's non-fled enemy IDs and keep such a member in place, even
  when terminal settlement has already paid its prefix and released it to
  idle. Regression:
  `SeededDecisionTests.test_active_combat_participant_never_wanders_even_when_released`.
- **Immediate posture transitions were projected but not committed
  (blocking):** fixed. A zero-length depletion/wake is now committed through
  the sole fatigue writer before the next segment, so the persisted state and
  the projection cannot disagree. Regression:
  `test_immediate_posture_transitions_are_committed` (both immediate depletion
  and immediate wake).
- **A dead journey member could be regenerated into life (blocking):** fixed.
  Journey settlement pays nothing for a dead member, arrival records its
  truthful `alive=False` presence, and it is never registered or attached at
  the destination. Regression:
  `test_a_member_killed_in_transit_is_not_resurrected`.
- **Partition evidence was too shallow (non-blocking):** fixed. The test now
  runs a departure, arrival and later decision across one advance versus two
  partitions, compares positions, sequences, schedules, cursors, reserves and
  gauges, and checks a repeated endpoint on the same world.
- **Newly born group rollback and the two population budgets were untested
  (non-blocking):** fixed. `test_a_birth_and_departure_in_one_advance_roll_back_completely`
  creates a group inside the failed advance and verifies the row, owner record
  and tick are restored before a deterministic retry; the departure test now
  asserts retained home ceiling for emigrants and a foreign visitor consuming
  local headroom.

### Focused verification run

```text
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_activity
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_journeys
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_world_escape
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population_recovery
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_clock
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_sites
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb web.gm.tests.test_reader_monsters
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb tests.test_command_docs
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.contract_gate
uv run --locked openspec validate global-monster-activity --strict
```

`world.maps.tests.test_monster_activity` is registered exactly once in
`.github/evennia-shards.json` (`maps-34`). The predecessor's recorded
baseline-only failures remain identical on the untouched parent and are not
claimed as this change's evidence:
`world.maps.tests.test_regional_population_recovery` keeps six pre-existing
errors (duplicate explicit registration of a zone-born member, and
`_reset`'s replayed `wave:` group id), and `world.rules.tests.test_clock`
keeps four pre-existing settlement-map/quest-registration errors.

### Spec deviations

None. The synced `wilderness-monster-population` Purpose was amended in this
slice to include explicitly bound activity as required by task 3.1; its
requirement text is updated by the delta at archive.

## Incapacitated Hostile Rounds: Real Paid Enemy Rounds

### Human review of the player-facing wording

The two command documents no longer claim that an all-forced-sleep opening
enters zero-round defeat. `docs/game/commands.md` and
`docs/game/command-reference.md` now state the actual contract: ordinary
interactive rounds still defer combat time, while a party with no actionable
member receives normal enemy-only rounds; each real round pays six seconds and
actual physiology, a forced sleeper wakes only at the authored threshold inside
those paid rounds, any unpaid interactive prefix is paid once when continuation
starts, and terminal settlement pays only the remaining suffix. The examination
FAIL policy, the voluntary sleep gates and the requested-retreat no-acting-ally
defeat are stated explicitly, so no player reads the old zero-round story. An
ecology/wording reviewer should confirm the Traditional Chinese sentence rhythm
and that no sentence promises a new ability or a proactive contact path (this
change adds neither).

### Requirement traceability (delta not yet synced)

The new `player-combat-session` requirement
`incapacitated-hostile-parties-receive-normal-enemy-rounds` is defined only in
`openspec/changes/incapacitated-hostile-rounds/specs/`. Because the delta is
not merged into `openspec/specs/` yet, every substantive test is annotated with
currently reported IDs only, and this table records the pending mapping; after
archive sync the same test identities should also annotate the new requirement.

| Test identity | Pending delta requirement | Current IDs that also cover it |
| --- | --- | --- |
| `world.rules.tests.test_hostile_incapacitated_rounds.PaidRoundTests.test_one_paid_round_reaches_the_threshold_and_returns_choice` | `player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds` | `player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits`, `mental-reserve::posture-and-forced-sleep-hysteresis-are-body-scoped` |
| `...PaidRoundTests.test_sleep_alone_never_declares_defeat` | same | `player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits` |
| `...PaidRoundTests.test_a_waking_companion_ends_automatic_play_under_normal_authority` | same | `player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits` |
| `...PaidRoundTests.test_the_existing_cap_still_terminates_an_all_sleep_party` | same | `player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits` |
| `...BlockingContinuationTests.test_a_confirmed_round_applies_a_blocking_effect_then_continues` | same | `player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits` |
| `...BlockingContinuationTests.test_a_late_failure_restores_the_round_and_the_retry_pays_once` | same | `player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits` |
| `...MappedPaidCursorTests.test_the_paid_endpoint_advances_the_map_cursor_once` | same | `player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits` |
| `world.rules.tests.test_guild_exams.ExamSettlementRecoveryTests.test_all_forced_sleep_candidate_enters_exam_fail_without_a_round` | same (examination scenario retained) | `player-combat-session::combat-time-settles-once-at-terminal-session-outcome`, `player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits`, `guild-rank-exams::exam-settlement-is-idempotent-and-promotes-only-a-passing-candidate` |
| `world.rules.tests.test_combat_party.ForcedSleepOpeningTests.test_opening_runs_real_rounds_until_the_existing_cap` | same | `player-combat-session::combat-time-settles-once-at-terminal-session-outcome`, `player-combat-session::no-eligible-actors-leaves-command-collection-paused-with-explicit-party-exits` |

The old `player-combat-session::all-forced-sleep-engagement-enters-ordinary-zero-round-defeat`
requirement is retired by the delta, but it remains a main-spec requirement
until archive synchronization. Its only remaining annotation is on the
examination FAIL control, which still establishes the requirement's retained
examination clause; no test asserts sleep-caused hostile defeat any more. The
annotation and this mapping are removed/repointed at archive.

### Scenario evidence

- **One real wake round:** a forced sleeper at 71928 receives exactly one
  enemy-only six-second round and reaches 72000/AWAKE; the paid cursor is 1/1,
  the clock advanced six seconds and the next normal player command resolves.
- **Temporary incapacity and terminal outcome:** a real confirmed self-cast
  applies the rulebook `paralysis` (20 s) to the last actionable ally; three
  automatic enemy rounds plus ordinary upkeep expire it, the committed
  `combat_incapacitated_continued` event is registered once and choice returns.
  A party that stays asleep runs to the existing 100-round cap; a lethal enemy
  deals a defeat through real attacks over at least one paid round, never from
  sleep alone.
- **Paid automatic prefix:** one wake round is paid, two interactive rounds stay
  deferred, and forfeit advances only twelve combat seconds (lifetime eighteen),
  consuming only the two unpaid awake rounds.
- **Reload equivalence:** after a paid wake and one deferred awake round,
  `restore_active_session` runs no round and no time; terminal settlement
  charges the deferred round at its actual awake rate, not as pre-payment sleep.
- **Failure and retry:** a fault injected on the durable cursor write after the
  clock/physiology writes rolls back the round unit, the cursor, the clock and
  the blocking buff; a retry pays every accepted round exactly once.
- **Mapped cursor:** a mapped enemy paid through `settle_monster_combat_through`
  at the six-second endpoint is re-marked combat-owned at that exact cursor; the
  terminal settlement charges no second interval. The dead/fled exclusion is
  enforced in the writer (and the dead-enemy interval recorder) but is not
  separately exercised by a multi-round mapped test in this slice.
- **Examination and invalid request:** the exam-only zero-round FAIL helper is
  the sole surviving forced-opening terminal path; a malformed/remote target
  still rejects before any round or time.
- **World time:** a guard raises if `WorldClock.advance` runs while a combatant
  action is on the stack; the wake scenario passes, proving the enemy action
  itself never advances the clock.

### Review dispositions

The plan review's blocking findings were incorporated before implementation:
the unpaid prefix now replays recorded posture segments (not the live posture);
payment-induced posture changes are reconciled into the durable boundary
evidence with the cursor; rollback ownership moved to the enclosing admission
and round operations with a maximal continuation snapshot horizon; automatic
round journals and practice dedupe join the owner's compensation; admission only
re-registers a surviving session; the automatic loop's terminal round is never
paid twice; and focused tests cover both the cursor-write failure and a receipt-write
failure after a successful continuation, plus the text command consumer, the
browser `explore.engage` adapter, the waking-companion control path, the cap,
the clock guard, the preserved boundary-evidence transition, the
knocked-out no-wake rule and the mapped cursor.

### Focused verification run

```text
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_hostile_incapacitated_rounds
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_combat_session_persistence
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_combat_party.ForcedSleepOpeningTests
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_party_time_settlement
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb web.webclient.presentation.tests.test_settlement_alignment
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_action_preview
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.contract_gate
uv run --locked openspec validate incapacitated-hostile-rounds --strict
```

`world.rules.tests.test_hostile_incapacitated_rounds` is registered exactly once
in `.github/evennia-shards.json` (evennia shard 2). The managed browser suite is
CI-owned and was not executed here; only its fixture comment/docstring was
updated, so no browser evidence is claimed.

Known pre-existing baseline failures that remain identical on the untouched
parent (`master` at `dc7ac8d9`) and are not attributed to this change:
`world.rules.tests.test_clock` keeps its four settlement-map/quest-registration
errors, `world.rules.tests.test_guild_exams.ExamSettlementRecoveryTests` keeps
its three `examiner_engaged`/collision errors, and
`world.rules.tests.test_combat_session_recovery.OverwhelmDirectionTests.test_player_overwhelming_in_session_submission_never_dispatches`
keeps its `None != 'party'` classification failure.

## Hostile Field Admission: Authored Contact at Real Boundaries

### Human review of the player-facing wording

Both command documents state the actual contract: authored aggressive
monsters admit one ordinary whole-cell encounter at a real arrival, birth or
condition boundary with no grace round and no free opening attack. They also
state that look/preview/reconnect never admits, that a monster in passage is
not present, that re-co-location after an escape admits again with no
immunity, that voluntary sleep is interrupted with only its actual recovered
reserve while forced sleep keeps its posture and threshold, and that the
examination and staged-encounter policies are unchanged. An
ecology/wording reviewer should confirm the Traditional Chinese sentence
rhythm and that no sentence promises a new ability or stricter player
control.

### Requirement traceability (synced)

`hostile-field-admission` is archived: its requirements now live in
`openspec/specs/hostile-field-contact/spec.md`, and
`tools.spec_traceability list` reports the canonical IDs
`hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat`
and
`hostile-field-contact::hostile-sleep-interruption-preserves-accepted-body-state`.
The tests that previously carried only the pending mapping now annotate those
two IDs directly. The table below keeps each test identity next to the
neighbouring coverage it also exercises.

| Test identity | Pending delta requirement | Current IDs that also cover it |
| --- | --- | --- |
| `world.rules.tests.test_field_contact.WholeCellArrivalTests.test_an_arrival_admits_a_a_b_once_with_no_free_opening_attack` | `hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat` | `player-combat-session::engage-group-opens-one-session-against-several-co-located-hostile-targets`, `player-combat-session::combat-state-preserves-individual-identity-across-repeated-labels` |
| `...ConditionAuthorityTests.test_daypart_gated_contact_admits_only_in_its_declared_region` | same | `monster-field-activity::activity-declarations-publish-complete-validated-bindings` |
| `...ConditionAuthorityTests.test_defended_area_admits_only_inside_its_geometry` | same | same |
| `...WholeCellArrivalTests.test_a_read_preview_never_admits` | same | `field-combat-initiation::validation-runs-against-a-candidate-battlefield-that-is-never-persisted-under-a-combat-context` |
| `...ClockSourceAdmissionTests.test_source_admits_at_the_endpoint_and_returns_an_event` | same | `player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds` (delta, pending) |
| `...PreActionBoundaryTests.test_wait_admits_and_spends_no_time` | same | `skip-safety-gate::evaluate_skip_safety-rejects-a-skip-when-a-living-monster-shares-the-actor-s-location` |
| `...PreActionBoundaryTests.test_ordinary_cast_reports_the_admitted_encounter` | same | `field-combat-initiation::the-command-routes-an-exploration-cast-by-target-and-its-documentation-says-so` |
| `...SleepInterruptionTests.test_voluntary_receipt_interrupts_without_refill_or_resume` | `hostile-field-contact::hostile-sleep-interruption-preserves-accepted-body-state` | `mental-reserve::posture-and-forced-sleep-hysteresis-are-body-scoped` |
| `...SleepInterruptionTests.test_forced_receipt_keeps_its_posture_and_threshold` | same | same |
| `world.rules.tests.test_sleep_receipt.ContactSleepInterruptionTests.test_voluntary_receipt_pays_actual_sleep_then_interrupts_once` | same | `party-time-settlement::every-settled-sleeper-completes-its-own-accepted-wake-plan` |
| `...ContactSleepInterruptionTests.test_forced_receipt_keeps_posture_target_and_threshold` | same | `mental-reserve::posture-and-forced-sleep-hysteresis-are-body-scoped` |
| `...ContactSleepInterruptionTests.test_a_pending_owner_continuation_becomes_unresumable` | `hostile-field-contact::hostile-sleep-interruption-preserves-accepted-body-state` | `party-time-settlement::every-settled-sleeper-completes-its-own-accepted-wake-plan` |
| `...ForcedWakeThroughAdmissionTests.test_forced_71928_reaches_72000_after_one_real_enemy_round` | `hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat` | `player-combat-session::incapacitated-hostile-parties-receive-normal-enemy-rounds` (delta, pending), `mental-reserve::posture-and-forced-sleep-hysteresis-are-body-scoped` |
| `...ProtectionTests.test_active_session_protects_the_cell_and_history_blocks_catch_up` | `hostile-field-contact::authored-hostile-contact-admits-immediate-ordinary-combat` | `wilderness-monster-population::encounter-protection-blocks-birth-space` |
| `...FaultRestorationTests.test_session_write_failure_restores_the_interrupted_receipt` | same | `player-combat-session::combat-time-settles-once-at-terminal-session-outcome` |
| `...FaultRestorationTests.test_a_continuation_failure_rolls_back_the_whole_encounter` | same | `player-combat-session::combat-time-settles-once-at-terminal-session-outcome` |
| `...PreActionBoundaryTests.test_all_party_sleep_admits_before_its_safety_refusal` | same | `party-system::any-present-sleeper-makes-party-travel-stationary` |

These current IDs are recorded as neighbouring coverage only; the substantive
assertions are the new behavior above, and no ID is claimed to be a new
requirement before archive synchronization.

### Scenario evidence

- **A+A+B arrival:** a real `settle_movement` relocation into a cell with two
  same-named contact monsters and one passive monster admits one session whose
  `enemy_ids` are all three living locals in persistent-ID order, with one
  draft and no round, no enemy HP loss and no clock advance.
- **Birth/condition source:** a registered clock source admits at the accepted
  interval endpoint, returns an interactive `field_contact_admitted` event and
  leaves the clock unchanged; the owning action drains the predecessor
  continuation once the advance returned. Declared dayparts and defended
  areas admit only inside their authored condition; passive members never
  trigger.
- **Transit and reads:** an in-passage party and a read-only preview create no
  session.
- **Forced wake:** a forced sleeper at 71928 admits normally, receives exactly
  one real six-second enemy round and reaches 72000/AWAKE with the paid cursor
  at 1/1; the session survives and choice returns.
- **Voluntary receipt:** a real contact interrupts voluntary sleep, the
  receipt becomes `interrupted` at the occurrence tick, the reserve equals
  only the actual sleep-rate recovery (never a refill) and a repeated contact
  cannot advance it. A forced receipt keeps its posture, target and threshold.
- **Pre-action:** a co-located contact admits before wait/rest/sleep/camp,
  item use or an ordinary cast; the action spends no time, resource or effect
  and the existing safety refusal reports the encounter.
- **Protection and re-co-location:** an active mapped session protects its
  cell; the real terminal settlement leaves the historical interval blocking
  a catch-up birth, and a later co-location admits a fresh session with a new
  identity (no immunity).
- **Fault restoration:** a failure in the session write after the interruption
  restores the receipt, physiology and session surfaces, emits
  `field_contact_failed` and no success event.

### Spec deviations

None. The removal of hostile `settle_forced_sleep_opening` was already
completed by `incapacitated-hostile-rounds`, which left only the examination
helper; this slice verified that no hostile caller remains. The conservative
registered boundary query deliberately stops interruptible skips at every
next activity/arrival/birth/condition/daypart tick until the forecast
successor replaces it, as design.md requires.

### Focused verification run

```text
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_field_contact
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_sleep_receipt
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_hostile_incapacitated_rounds
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.contract_gate
uv run --locked openspec validate hostile-field-admission --strict
```

`world.rules.tests.test_field_contact` is registered exactly once in
`.github/evennia-shards.json` (evennia shard 2). The managed browser suite is
CI-owned and was not executed here; the text and browser surfaces share the
same rules entry points (`settle_movement`, `cast_in_field`, `use_item`,
`time_skip`), so no separate browser evidence is claimed.

## Interruptible Field Contact: Read-Only Contact Forecast

`interruptible-field-contact` makes wait, rest, sleep, study, camp and the
owner-targeted continuation stop at the first tick that really contacts the
party, instead of at every population maintenance tick. The owner is
`world/maps/population_forecast.py`; the committed writer stays
`world/maps/population_lifecycle.py`.

### Projection contract

`capture_activity_snapshot(start_tick=...)` reads every planning input at the
interval start through the owners' existing pure readers: detached
`ActivityGroupSnapshot`/`JourneySnapshot` records, the projected
`PopulationPresence` at that tick, `ProjectedZone`/`ProjectedSite` selection
state, protection intervals, sited room protection and the captured
wilderness name.

`project_activity_window(snapshot, *, start_tick, end_tick, observers)` replays
the coordinator's documented order over those detached records: completed
arrivals, zone boundary refresh, site decisions, zone recoveries, the contact
check, then idle decisions, then the same-tick arrival pass. It returns a
frozen `ContactForecast(first_tick, contact_sources)`.

Purity: the projection constructs no individual, room or session, moves
nothing, writes no attribute, consumes no draw or generation sequence, and
uses no database rollback as simulation. A prospective individual token is
`forecast:<owner-kind>:<owner-key>:<generation-sequence>:<ordinal>` and is
internal to the call; it is never returned as an identity, presence or target.

### Shared planning rules

The forecast never copies a formula:

| Decision | Shared pure rule |
| --- | --- |
| Regional birth wave | `regional_population.plan_population_wave_from` (the writer's own core; `plan_population_wave` is its committed-state adapter) |
| Zone local/home counts | `regional_population.counts_from_presence` (the same rule as `population_counts`) |
| Site occurrence | `monster_sites.site_occurrence_groups` (what `_populate` constructs) and `monster_sites.recovery_condition_matured` |
| Group idle decision | `monster_activity.plan_group_decision`, priced with `monster_activity.projected_member_states` + `quote_edge` + `world_escape.build_journey_plan` |
| Contact condition | `field_contact.contact_condition_admits` (dayparts and defended-area geometry), the committed evaluator's own rule |
| Daypart boundary | `clock.next_daypart_boundary` |

Both registered boundary queries —
`world.rules.field_contact.next_field_contact_boundary` and
`world.maps.population_lifecycle.next_population_lifecycle_boundary` — return
the same forecast tick, so the endpoint admission and the population stage
cannot disagree. `_next_population_boundary` still enumerates every
maintenance tick for the committed settlement; only the public interactive
query was narrowed.

### Projection bounds (disclosed)

1. Each existing group contributes at most its **next** idle decision, and a
   group a projected birth creates contributes none: a second decision needs
   committed selection state (sequence, settled member cursors) that a
   read-only pass must not invent. A later departure of the same group is
   therefore not projected.
2. After `MAX_PROJECTION_STEPS` (2,048) projected boundaries the forecast
   answers the next maintenance boundary, so a skip stops early rather than
   running past a contact the projection did not reach.

Both bounds can only make a skip stop *earlier* than the ideal forecast, never
later than a real contact, so they cannot let a contact go unobserved.

### Consumer integration

`mental_time.next_skip_boundary` already composes the registered boundary
query with each member's physiology; `time_skip.advance_wait` and
`continue_sleep` now bind `clock.advance_scope` around the interval query and
its advance, so the forecast discovers exactly the parties the skip settles
for and the endpoint admission admits for the same ones.
`continue_owner_sleep`, `continue_camp` and `sleep_control` inherit both
through `continue_sleep`.

Clock sources now declare interactivity explicitly
(`register_event_source(..., interactive=...)`): `shop_hours` stays
interactive, while the population coordinator settles many internal
maintenance ticks and marks only its accepted contact event, so distant
maintenance never reports `SkipResult.interrupted`.

### Observability

`field_contact_interrupted` (info, catalog section 4.2) is scheduled on
commit from `time_skip._log_contact_interruption` with `char`, `operation`,
`sleep`, `requested_seconds`, `elapsed_seconds`, `tick` and `session`. A
rolled-back interval leaves no row; distant maintenance produces none.

### Requirement traceability (delta not yet synced)

This change modifies `hostile-field-contact`, `time-skip-commands` and
`wilderness-travel-interrupts`.
`time-skip-commands::interruptible-skips-stop-at-the-earliest-relevant-boundary`
is already synced and its canonical ID is annotated on the wait, sleep,
owner-continuation and interruption-log tests. The added requirements are
defined only in `openspec/changes/interruptible-field-contact/specs/`, so no
annotation is added yet; the equivalent merged tree reports:

- `hostile-field-contact::contact-forecasts-stop-interruptible-time-at-actual-interaction`
- `wilderness-travel-interrupts::arrival-combat-stops-walking-before-the-next-edge`

| Test identity | Pending delta requirement |
| --- | --- |
| `test_field_contact_boundaries.ForecastPurityTests.test_the_first_contact_is_the_intermediate_arrivals_tick` | `hostile-field-contact::contact-forecasts-stop-interruptible-time-at-actual-interaction` |
| `...ForecastPurityTests.test_the_registered_query_reports_the_same_contact` | same |
| `...ForecastPurityTests.test_projection_preserves_every_owner_surface` | same |
| `...ForecastPurityTests.test_a_distant_group_decision_never_interrupts` | same |
| `...WaitBoundaryTests.test_a_distant_maintenance_fact_does_not_interrupt_the_wait` | same |
| `test_regional_population_recovery.RecoveryLifecycleTests.test_the_pure_boundary_projects_an_unpersisted_episode` | same |
| `...IndivisibleEdgeTests.test_an_edge_completes_once_and_admits_at_its_arrival` | `wilderness-travel-interrupts::arrival-combat-stops-walking-before-the-next-edge` |

### Scenario evidence

- **Intermediate journey contact:** a group at the neighbouring cell departs at
  its 120 decision and arrives later; a distant zone recovery (105) and a
  distant passive site birth (110) precede it. Repeated forecasts return the
  arrival tick with source `birth_or_arrival`, and the registered query reports
  the same tick while reporting nothing before it. Every owner surface
  (activity record, zone map, site map, presence timeline, monster rows,
  coordinate count) is identical after the forecast.
- **Intermediate birth contact:** a site recoverable at 110 on the party's own
  cell yields a forecast contact at 110; `continue_sleep` commits exactly ten
  seconds, the receipt becomes interrupted at 110 and the encounter starts
  there.
- **Forecast/settlement agreement:** the real `advance_wait` accepts exactly
  `arrival - 100` seconds and starts one session at the arrival tick with the
  arrived individual in the roster.
- **Distant maintenance is internal:** a wait that spans distant recoveries,
  births and lawful stays commits its whole request with
  `interrupted=False` and no session, while the zone's own generation sequence
  still advances inside the interval.
- **Receipt authority:** a voluntary sleeper keeps only the actual
  sleep-rate recovery, its receipt is interrupted at the contact tick, and the
  owner continuation ends without a resumable authorization. A forced receipt
  keeps `FORCED`, `forced_threshold` and its accepted cap; separately paid
  enemy rounds are outside the skip receipt.
- **Indivisible edge:** a committed edge pays its whole cost once, the party is
  in passage until the arrival tick, and the encounter is admitted at that
  arrival with one session.
- **Fault restoration:** a failure after the accepted interval and the
  admission restores the clock tick, the physiology surfaces and the zone
  state, and publishes no `field_contact_interrupted` row.

### Focused verification run

```text
cd /var/home/jim60105/repos/MUD/.worktrees/interruptible-field-contact
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_field_contact_boundaries
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_field_contact
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_time_skip
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_sleep_control world.rules.tests.test_sleep_receipt world.rules.tests.test_skip_safety world.rules.tests.test_skip_commands
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population_recovery.RecoveryLifecycleTests.test_the_pure_boundary_projects_an_unpersisted_episode
```

`world.rules.tests.test_field_contact_boundaries` is registered exactly once,
in `.github/evennia-shards.json` (rules-2). The managed browser suite remains
CI-owned; the browser walk stops on the same server-authoritative signal
(`mode` no longer `exploration` after the arrival publication), so no separate
browser evidence is claimed here.

## Paid Party Retreat: One Real Edge and Two Paid Intervals

`paid-party-retreat` makes a confirmed retreat execute a real adjacent
affordable edge. Success departs the whole present party (knocked-out
companions carried, remote companions untouched), pays the old encounter's
unpaid prefix plus the attempt round once, then pays the ordinary movement
traversal once through the shared movement settlement. No affordable legal
destination keeps the existing failed-retreat branch: one ordinary enemy round
at the source, no movement and no travel payment.

### Human review of the player-facing wording

`docs/game/commands.md` and `docs/game/command-reference.md` were read as a
player would. Both now state that confirmation first checks an affordable
adjacent route using the reserve left after the whole unpaid combat prefix and
the attempt round; the prompt-captured reverse of the last completed edge is
preferred when still legal and affordable, otherwise another lawful affordable
neighbour is used without a monster-free/safe preference. They state that a
successful party actually walks that edge with its knocked-out companions,
pays one attempt round plus the normal travel time and physiology once, gains
no exit heal or revival, and can be re-engaged immediately on arrival. They
state that a party with no affordable route stays at the source, spends all
allied actions and takes one ordinary enemy round without a movement charge.
The wording is Traditional Chinese (zh-TW), keeps the existing `flee` aliases,
and does not claim a client-chosen destination.

### Route, projection and scope

- `world_escape.plan_party_retreat` is read-only. It projects every present
  team member's unpaid prefix from `settled_rounds` and the recorded posture
  evidence, appends one six-second live-posture attempt, and prices the full
  route through `movement_edges.quote_edge`. A paid prefix is never counted
  again; `settled_rounds == rounds_elapsed` pays only the attempt.
- Present allies are the commander's current source team from the battlefield
  roster. Remote companions are outside `member_ids` and never price the
  route. A knocked-out present companion is in `member_ids`/`carried_ids` but
  never in `self_moving_ids`: it neither walks, prices speed nor triggers a
  sleep refusal. A non-knocked-out sleeper keeps the ordinary restriction and
  makes the route an ordinary unaffordable failure.
- Ordinary blocked/unaffordable neighbours produce `None`. A malformed fatigue
  pair, malformed saved history or broken authored geometry raises
  `WorldEscapeError` by name. The prompt binds the server-captured previous
  edge's identity fingerprint in the confirmation digest; execution revalidates
  the live source and route, and a gate that locks after the prompt still
  verifies the unchanged history and falls back to a lawful neighbour.

### One atomic exit and paid edge

- `rounds.resolve_party_retreat` establishes route viability before the
  agility contest. No acting ally keeps the existing defeat/exam-FAIL branch.
  No route runs `_failed_party_retreat` (empty allied provider, one ordinary
  enemy round, fresh nonterminal draft).
- On success the whole team is marked fled, and
  `settlement.settle_fled_combat_prefix` pays the allied mental intervals and
  advances the clock for exactly `[settled_rounds, rounds_elapsed + 1)` once.
  The durable cursor commits with the finalized round; the terminal settlement
  then pays zero remaining rounds and excludes the departed party from old
  encounter gauge regeneration. No exit heal or revival occurs.
- `movement_settlement.settle_party_retreat_traversal` executes the explicit
  rules-owned carry plan through the ordinary `settle_movement` boundary with
  the preflighted edge, charges the canonical traversal duration and
  physiology once, records the completed history, and admits authored arrival
  contact inside the same durable unit. It is not reachable from an exit, a
  command or a client.
- `confirm_party_exit` snapshots the full travel-window event surfaces, all
  present party attributes (history, receipts, dialogue, encounter sequence,
  sleep receipts) and the committed traversal handle; any late fault restores
  the complete original party/session/draft/history/clock and population
  surfaces. A committed old receipt replayed after arrival opened a new session
  reaches the receipt-only answer or is refused as a foreign session; it never
  mutates the new session.
- `party_retreat_resolved` is scheduled on the outermost commit with the
  outcome, reason, stable source/destination, member ids and attempt/arrival
  tick. A rolled-back unit emits nothing.

### Requirement traceability (delta not yet synced)

The four modified requirements keep their existing canonical ids (checked with
`uv run --locked python -m tools.spec_traceability list`); this change adds no
new requirement id, so no new annotation is created before archive sync.

| Requirement | Establishing tests |
| --- | --- |
| `player-combat-session::successful-retreat-carries-the-entire-present-party-and-counts-one-round` | `world.rules.tests.test_party_retreat_travel` (projection, carry scope, exact-zero, real edge, one combat plus one travel charge), `test_combat_party.PartyRetreatTests` (carried companion, replay) |
| `player-combat-session::retreat-contests-the-slowest-acting-ally-against-the-fastest-pursuer` | `test_party_retreat_travel` (unaffordable previous-edge fallback), unchanged `PartyRetreatTests` contest controls |
| `player-combat-session::failed-retreat-consumes-all-allied-actions-and-runs-one-ordinary-enemy-upkeep-round` | `test_party_retreat_travel` (post-attempt depletion, no movement/payment), `PartyRetreatTests` failed-round controls |
| `player-combat-session::party-exit-requires-a-commander-session-round-and-operation-bound-confirmation` | `test_confirmed_surrender` (malformed history by name, captured route, late lock fallback, new-session receipt replay) |
| `player-combat-session::combat-time-settles-once-at-terminal-session-outcome` | `test_party_retreat_travel` (clock delta `2×6 + travel`), `PartyRetreatTests` terminal-once controls |
| `guild-rank-exams::exam-settlement-is-idempotent-and-promotes-only-a-passing-candidate` | `test_guild_exams.ExamCombatTests.test_a_confirmed_retreat_fails_the_exam_over_a_real_edge` |

### Scenario evidence

- **Post-attempt affordability:** four unpaid awake-combat rounds project to
  `rounds_elapsed - settled_rounds` plus the attempt; a cursor already at the
  completed count projects only the attempt. Depleting before arrival is an
  ordinary `None` route, including with no living pursuer.
- **Exact zero:** the severe-band traveller is priced from 50% foot speed; the
  exact reserve for a one-cell edge is accepted and `TravellerState.advance`
  ends at zero with `FORCED` posture. One unit less after the attempt has no
  route at all.
- **Previous edge and fallback:** two adjacent edges with different canonical
  prices are separated by a reserve where the captured expensive edge is
  unaffordable; the planner returns a different lawful edge. In the authored
  room test, a gate locked after the prompt keeps the token valid and execution
  takes the other edge.
- **Carry, scope and no heal:** a present knocked-out companion is carried to
  the destination with its 1 HP unchanged; a remote companion is absent from
  the member list; only the self-moving member's state prices the route.
- **Exactly once:** the confirmed retreat advances the clock by one attempt
  round plus the canonical traversal duration; the terminal settlement adds no
  second combat charge. A committed receipt replay is idempotent; a replay
  after a new arrival session is refused as `unknown_session_id` and leaves the
  new session storage identical.
- **Exam edge:** a confirmed retreat from the examination room records
  `ExamState.FAILED`, restores the persistent host and moves the candidate over
  the examination room's real exit.

### Retained smoke

`tools/monster_field_behaviour_smoke.py::run` was executed against a fresh
disposable database. Because Evennia 6.1's `shell` has no `--plain` flag and a
freshly migrated disposable database has no superuser, the exact invocation is:

```text
MUD_SMOKE_DB=/tmp/mud-field-smoke.sqlite3 \
    uv run --locked evennia migrate \
    --settings monster_field_behaviour_smoke_settings --noinput
MUD_SMOKE_DB=/tmp/mud-field-smoke.sqlite3 \
    DJANGO_SETTINGS_MODULE=server.conf.monster_field_behaviour_smoke_settings \
    uv run --locked python -c "import django; django.setup(); from evennia.accounts.models import AccountDB; AccountDB.objects.create_superuser('smoke', '', 'smoke-pass')"
MUD_SMOKE_DB=/tmp/mud-field-smoke.sqlite3 \
    uv run --locked evennia shell \
    --settings monster_field_behaviour_smoke_settings -i python \
    -c "from tools.monster_field_behaviour_smoke import run; run()"
```

Observed report (real owners, no network/LLM, no mocked tested boundary):

```json
{
  "probe": [500, 700],
  "neighbour": [501, 700],
  "clean_wait": {"requested": 60, "elapsed": 60},
  "group_move": {"group": "smoke:move#0", "from": "501,700", "to": "500,700", "reason": "depart"},
  "interrupted_wait": {"requested": 60, "elapsed": 0, "refusal": "SkipRefused", "session": "hostile:2:60"},
  "failed_energy": {"route": null, "reserve": 10},
  "paid_retreat": {"outcome": "fled", "from": "500,700", "to": "501,700", "travel_seconds": 1200, "clock_delta": 1206, "companion_at_destination": true},
  "reengagement": {"session": "hostile:2:1266", "old_session": "hostile:2:60", "different": true, "enemies": [24]},
  "enemy_journey": {"journey": "journey:smoke:flee", "arrived": "500,701", "tick": 1698},
  "committed_reload": {"session": "hostile:2:1266", "enemies": [24]}
}
```

The `clock_delta` of 1206 is exactly the six-second attempt plus the canonical
1200-second traversal; the destination contact admitted a different session;
the enemy flee journey committed and arrived; and a fresh object reload read
the same committed session.

### Focused verification run

```text
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_party_retreat_travel world.rules.tests.test_combat_party world.rules.tests.test_confirmed_surrender
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_movement_settlement world.rules.tests.test_world_escape
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_guild_exams.ExamCombatTests web.webclient.actions.tests.test_combat_actions.CombatCommandAdapterTests world.rules.tests.test_rules_observability
uv run --locked python -m unittest tests.test_evennia_test_optimization_contract
uv run --locked python -m unittest tests.test_command_docs
uv run --locked python -m tools.observability_lint check
uv run --locked python -m tools.contract_gate
uv run --locked openspec validate paid-party-retreat --strict
```

`world.rules.tests.test_party_retreat_travel` is registered exactly once in
`.github/evennia-shards.json` (rules-2, beside `test_combat_party`). The managed
browser suite is CI-owned; the server-side browser adapter suite was extended
and run, but no full browser run is claimed.

Known pre-existing baseline failure, identical on the untouched parent
`master` at `10a44481`: 
`world.rules.tests.test_confirmed_surrender.AlliedFleeRemovalTests.test_enemy_disengagement_still_resolves_through_the_action_pipeline`
reports `round != victory` because the kept test database has no provisioned
wilderness world for a mapped individual escape. It is not attributed to this
change.

### Spec deviations

None. The command documents' design invocation `--plain` is unsupported by
Evennia 6.1's `shell`; the equivalent `-i python` invocation and the disposable
settings module are recorded above.

### Review dispositions

The blocking plan review and the blocking final review were both requested
through the available rubber-duck provider. Both invocations failed with the
exact provider status `usage_limit_reached` (`Codex error event: The usage
limit has been reached (code=usage_limit_reached)`), so no review finding is
claimed as disposed and no review output is fabricated. The implementation
evidence above and the focused/gate runs are the accepted substitute for this
change, exactly as the assignment's provider-failure clause permits.

## Activity Group Formation

`activity-group-formation` makes one pure rule decide how a placement's sampled
individuals become movement groups, and shares it between both writers and the
read-only forecast. The rule is
`world.lore.monster_activity.movement_units(row_counts, row_bindings, *,
activities=None)`; it returns immutable `MovementUnit(activity_key,
member_indices)` values in the placement's flattened construction order.

### The rule

- Every slot of a `cohesive_group` binding sharing one key joins exactly one
  unit, even when those rows are separated by other rows or share no variant.
- Every `solitary_roaming` or `stationary` slot is a unit of its own.
- Units are ordered by their smallest member slot; slot numbers start at zero
  and follow the sampled row order, which is exactly the order a writer
  constructs its individuals.
- A zero-count row contributes no slot, but its binding is still validated.
- Length mismatch, a non-integer (including `bool`) or negative count, and an
  unknown or empty binding raise `MonsterActivityRegistryError`. An explicitly
  supplied empty activity mapping therefore rejects every binding.

The rule deliberately does not add a policy value: `solitary_roaming` keeps its
movement semantics and simply disperses a multi-member composition instead of
forbidding it.

### Removed solitary-total check

Publication no longer requires a `solitary_roaming` binding's every legal
outcome to total one individual. `validate_activity_binding` and its
`__all__` entry are gone, and `world.lore.monster_placement` keeps only the
key-presence and unknown-reference checks for a composition binding and a site
override. Capacity, geometry, timing, aggression and unknown-reference
validation is unchanged. A solitary site override of a two-member composition
now publishes and disperses at construction.

### Writers

- **Zone waves.** `commit_population_wave` keeps constructing in
  `placement.groups` order, then creates one group per unit with
  `wave:<zone>:<sequence>#<ordinal>`, each member list from that unit's slots.
  The groups, zone state and event stay inside the existing transaction and
  surface snapshot/restore.
- **Manual sites.** `monster_sites._populate` constructs every row of the
  sampled occurrence (stamping `db.site_key`), then registers one group per
  unit through the new `regional_population.register_explicit_group`, keyed
  `site:<site>:<sequence>#<ordinal>`. A cohesive override therefore creates one
  multi-member group owned by the site; a stationary or solitary override
  creates one group per individual. The old `explicit:<x>:<y>:<pk>` prefix is no
  longer used for site groups and no compatibility reader was added.
  `register_explicit_individual` remains the single-individual entry point for
  GM, quest and staged placements and delegates with
  `explicit:<x>:<y>:<pk>#0` and presence evidence `source_id`
  `explicit:<x>:<y>:<pk>`, so every existing caller assertion is unchanged.
- **Registration contract.** `register_explicit_group` validates the cell and
  every individual before its first write, refuses an empty or duplicate list
  with `ExplicitPlacementRefused`, writes each coordinate and room attachment,
  creates exactly one group, records one `PopulationTransition` per individual
  and emits one `monster_population_individual_registered` event per
  individual. It opens no transaction and compensates nothing by itself.

### Writer/forecast parity

`world.maps.population_forecast` computes the same `movement_units` from the
same rows and binding and calls `_place` once per unit for a projected zone
birth (`zone:<zone>:<sequence>#<ordinal>`) and a projected matured site
recovery (`site:<site>:<sequence>#<ordinal>`), with
`count=len(unit.member_indices)` and the unit's own decision interval. Group
ids are not compared between the two paths (the committed zone prefix is
`wave:`); their group count and member counts are. Projected groups still
contribute no idle decision and still create no durable state.

### Traceability hand-off

The added requirement lives only in this change's delta
(`openspec/changes/activity-group-formation/specs/monster-field-activity/spec.md`)
and has no canonical ID until archive sync. Following the repository rule, the
tests written for it carry **no** `covers_requirement` annotation: a closest
current requirement, borrowed ID or hand-built slug would be a false claim. The
table below is the implementation-stage hand-off; the archive stage adds the
tool-generated annotation after the sync. This branch predates the traceability
gate's `--change` variant, so the handoff gate runs as
`uv run --locked python -m tools.contract_gate` and os-archive forwards the
change name after rebasing. Pre-existing annotations on tests this change did
not add are unchanged; the one existing canonical claim kept on a new test is
the wave's real due decision, which establishes
`monster-field-activity::due-activity-moves-bounded-complete-groups-globally`.

### Evidence map

Scenarios below are from the delta requirement "Placements form movement groups
from their binding policy".

| Scenario | Substantive test assertions |
| --- | --- |
| Solitary birth disperses | `world.maps.tests.test_regional_population.RegionalPopulationTests.test_a_solitary_binding_disperses_the_birth_and_one_group_may_leave` (three one-member groups at the birth cell; one later due decision departs while the other two keep position, members and sequence) |
| Cohesive birth stays whole | `RegionalPopulationTests.test_a_cohesive_binding_keeps_the_whole_birth_in_one_group` (exactly one group holds every constructed member) |
| Manual site formation | `world.maps.tests.test_monster_sites.MonsterSiteLifecycleTests.test_a_cohesive_site_binding_forms_one_group_owned_by_the_site`; `test_a_stationary_site_binding_forms_one_group_per_member` (three groups, all owned by the site) |
| Forecast agreement | `world.rules.tests.test_field_contact_boundaries.GroupFormationForecastParityTests.test_a_solitary_zone_birth_projects_the_committed_dispersal`; `test_a_matured_cohesive_site_recovery_projects_the_committed_group` (projected member counts equal the committed writer's for the same saved seed and sequence) |
| Failure leaves no partial grouping | `RegionalPopulationTests.test_a_failed_group_write_restores_every_surface_and_a_retry_commits` (fault on the second `create_group`: individuals, groups, zone state, coordinates and room contents restored, retry commits the same selection); `MonsterSiteLifecycleTests.test_a_failed_second_unit_restores_the_site_and_every_member` (same for the site writer) |
| Every possible solitary outcome is valid (modified requirement) | `world.lore.tests.test_monster_activity.MovementUnitTests`; `world.lore.tests.test_monster_placement.PlacementValidationTests.test_a_solitary_site_override_accepts_a_multi_member_composition` |
| Single registration keeps its identity | `MonsterSiteLifecycleTests.test_single_registration_keeps_its_explicit_identity_and_presence_evidence` (`explicit:<x>:<y>:<pk>#0` group and `explicit:<x>:<y>:<pk>` transition source) |

### Focused verification run

```text
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_activity world.lore.tests.test_monster_placement
  -> Ran 78 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population
  -> Ran 28 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --noinput world.maps.tests.test_regional_population_recovery
  -> Ran 24 tests, OK (fresh database; see the retained-database note below)
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_journeys
  -> Ran 12 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_sites
  -> Ran 39 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_field_contact_boundaries
  -> Ran 14 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_gm world.quests.tests.test_permanent_occupants
  -> Ran 19 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.quests.tests.test_site_clear_out_acceptance
  -> Ran 20 tests, OK
uv run --locked python -m tools.observability_lint check
  -> scanned=832 frozen=0 violations=0 exemptions=406
uv run --locked python -m tools.map_reference_context --check
  -> content/map-reference-context.json is up to date
uv run --locked openspec validate activity-group-formation --strict
  -> Change 'activity-group-formation' is valid
uv run --locked python -m tools.contract_gate
  -> contract gate passed: reference-context, traceability, observability, test-data, manifests, contracts
```

No new test module was added, so `.github/evennia-shards.json` is unchanged.

The recovery suite reproduces the repository's known retained-database
`round != victory` symptom when the shared retained test database has drifted;
omitting `--keepdb` and running with `--noinput` against a freshly created
database is the recorded evidence above. An earlier retained-database run also
surfaced `monster_activity_group_exists` from the same drift. `_reset` in that
suite now clears the map-owned activity record with the rest of the population
state a fresh world starts without, and the real session fixture joins a
zone-born individual's own group instead of re-registering it.

## Site Member Activity Bindings

`site-member-activity-bindings` adds two authored facts on top of the group
formation rule above: a composition row may bind its own individuals, and a
site may name the one individual it designates.

### The binding rule

One pure resolver owns the precedence:
`world.lore.monster_placement.composition_row_bindings(composition, *, site=None)`
returns one effective activity key per composition member row, in member order.

- A site that declares `activity_key` governs **every** row of that site; no row
  binding is consulted. This is the unchanged behaviour of every shipped site,
  which pass their stationary override positionally.
- A site that declares no override (`activity_key=None`) lets each row resolve
  its own `CompositionMember.activity_key` when it declares one, else the
  composition's `activity_key`.
- Zone births have no site, so they always resolve row binding, else
  composition binding.
- `PopulationPlacement.activity_key` keeps retaining the composition binding for
  plan comparison; it is the fallback a row without its own binding resolves,
  not necessarily any one group's effective binding (a group whose row inherits
  the fallback legitimately carries it).

Rows are never filtered or reordered: the sampled `(variant_key, count)` rows
are the composition's rows in member order, so the resolver's tuple is parallel
to what `movement_units` consumes. A cohesive row therefore stays whole next to
an independent row inside one manual composition.

Publication rejects both beginnings and overrides that name no published
activity. A row error is a `MonsterPlacementRegistryError` naming the
composition, the row index and the key (an empty or non-string row binding
reports "declares no activity binding"); a site error names the site and the
unknown activity key. The row check runs even when a site override would mask
the row at construction, so an authored typo cannot hide behind an override. A
`None` site override is lawful.

### The designated-individual label

`MonsterSite.individual_label_zh` is optional. Publication accepts it only when
`composition_bounds(composition) == (1, 1)` — every legal outcome of the site's
composition is exactly one individual — and rejects an empty label or a label on
any wider composition. The site owner passes the label as
`construct_species_individual(..., key=label)`, i.e. the constructed object's
display key; `None` keeps the variant's display name. Species key, variant key,
the `db.site_key` ownership marker, group ownership and defeat credit are
unchanged, and a recovered labelled site's members are new persistent
identities carrying the same display label. No naming tradition, nickname
generator or shipped label lives in this change.

### Evidence map

Scenarios below are from the delta requirements "Composition rows resolve one
effective activity binding" and "A designated site individual carries an
authored display label".

| Scenario | Substantive test assertions |
| --- | --- |
| Mixed manual encounter | `world.maps.tests.test_monster_sites.MonsterSiteLifecycleTests.test_a_row_bound_site_forms_one_group_per_row_binding` (two site-owned groups sized 2 and 1, each binding's own decision interval, and a due solitary decision that leaves the cohesive sibling's position, members and sequence untouched) |
| Site override precedence | `MonsterSiteLifecycleTests.test_a_stationary_site_override_suppresses_every_row_binding` (three one-member stationary groups, each due decision `STAY_STATIONARY` with no edge and no journey, so no row binding moves a member) |
| Zone row bindings | `world.maps.tests.test_regional_population.RegionalPopulationTests.test_a_row_bound_birth_forms_each_rows_own_group` (unbound row keeps the cohesive composition binding, bound row stands alone, both zone-owned); `world.rules.tests.test_field_contact_boundaries.GroupFormationForecastParityTests.test_a_row_bound_zone_birth_projects_the_committed_groups` (projected shapes and bindings equal the committed writer's) |
| Unknown binding | `world.lore.tests.test_monster_placement.MemberActivityBindingTests.test_an_unknown_or_empty_row_binding_is_rejected` (both publication paths, including a masked row under a valid override, plus the diagnostic naming composition, row and key) |
| Label applied | `MonsterSiteLifecycleTests.test_a_labelled_site_names_its_individual_without_changing_identity` (display key equals the label while species, variant, site marker and site-owned group match the unlabelled site) |
| Recovered label keeps identity keys | `MonsterSiteLifecycleTests.test_a_recovered_labelled_individual_keeps_the_label_and_a_new_identity` (the recovered member has a new primary key, the same label, the same site marker and a fresh site-owned group) |
| Label on a group rejected | `MemberActivityBindingTests.test_a_label_requires_every_outcome_to_be_exactly_one_individual`; `test_an_empty_label_is_rejected` |
| Forecast agreement for a mixed site | `GroupFormationForecastParityTests.test_a_matured_mixed_row_site_projects_the_committed_groups` |

### Traceability hand-off

Both requirements are added by this change's delta
(`openspec/changes/site-member-activity-bindings/specs/monster-site-placement/spec.md`)
and have no canonical ID until archive sync, so the tests written for them carry
**no** `covers_requirement` annotation. The implementation report carries the
test → (delta requirement, scenario) table; os-archive adds the tool-generated
annotation after the sync. Pre-existing annotations on untouched tests are
unchanged.

### Focused verification run

```text
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_placement
  -> Ran 56 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_sites
  -> Ran 43 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population
  -> Ran 29 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_field_contact_boundaries
  -> Ran 16 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_registry_index_contract
  -> Ran 13 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_activity
  -> Ran 28 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_sync
  -> Ran 6 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.quests.tests.test_site_clear_out_acceptance
  -> Ran 20 tests, OK
uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --noinput world.maps.tests.test_regional_population_recovery
  -> Ran 24 tests, OK (fresh database)
uv run --locked python -m tools.map_reference_context --check
  -> content/map-reference-context.json is up to date
uv run --locked python -m tools.observability_lint check
  -> scanned=832 frozen=0 violations=0 exemptions=406
openspec validate site-member-activity-bindings --strict
  -> Change 'site-member-activity-bindings' is valid
uv run --locked python -m tools.contract_gate --change site-member-activity-bindings
  -> contract gate passed: reference-context, traceability, observability, test-data, manifests, contracts
```

No new test module was added, so `.github/evennia-shards.json` is unchanged, and
no data-contract module was added, so `tools/test_data_freeze.json` is unchanged.
Only the placement dataclass definitions, the resolver and the validators
changed: every shipped site and composition declaration is untouched.
