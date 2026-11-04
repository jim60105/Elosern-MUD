# Regional monster population: ecology authoring

This document describes the authored ecology layer added by the OpenSpec change
`regional-ecology-authoring` (the first subproject of
`docs/superpowers/specs/2026-11-03-regional-monster-population-design.md`).

The layer is **authoring and validation only**. It publishes bounded habitats,
complete encounter compositions and settlement birth-exclusion policy, and it
validates them against a candidate map world. No ambient population owner is
activated, nothing spawns, and the pre-existing `AmbientPlacementRule` rows stay
the live ambient source until their explicit final cutover
(`regional-population-runtime-cutover`). There is no alias, translation or
compatibility row from an old ambient rule to a zone.

## Ownership boundary

| Concern | Owner |
| --- | --- |
| Frozen declarations and their construction-time validation | `world/lore/monster_placement.py` |
| Candidate-world birth geometry, density bounds, recoverability proof | `world/maps/population_geometry.py` (pure) |
| Publication of a validated candidate world | `world/maps/geography.py` (`build_geography`) and `world/maps/runtime.py` |
| Population state, births, recovery, selection | later changes; not in this slice |

Lore never mutates or reads a database. The geometry module never reads a live
registry: callers hand it one candidate world and that candidate's composed
wilderness entries.

## Registry signatures

All declarations are `dataclass(frozen=True, slots=True)` values; every
published registry is a `MappingProxyType` keyed by the declaration's own key.

```python
CompositionMember(
    variant_key: str,   # ref("monster_variants", inverse="composition_members")
    minimum: int,       # inclusive, >= 1
    maximum: int,       # inclusive, >= minimum
)

EncounterComposition(
    key: str,
    members: tuple[CompositionMember, ...],   # non-empty, no repeated variant
)

WeightedComposition(
    composition_key: str,  # ref("encounter_compositions", inverse="ecology_zone_pools")
    weight: int,           # >= 1
)

EcologyZone(
    key: str,
    region_key: str,       # ref("wilderness_regions", inverse="ecology_zones")
    rectangles: tuple[tuple[int, int, int, int], ...],  # inclusive (x_min, x_max, y_min, y_max)
    pool: tuple[WeightedComposition, ...],   # non-empty, no repeated composition
    lower_density: int,    # individuals per 100 eligible cells
    upper_density: int,
    cell_capacity: int,
    recovery_delay: int,          # game-time seconds
    replenishment_interval: int,  # game-time seconds
    wave_budget: int,             # largest complete composition one wave may place
)

SettlementBirthPolicy(
    anchor_key: str,       # ref("anchors", inverse="settlement_birth_policies")
    buffer_cells: int,     # >= 1, Chebyshev cells beyond the settlement
)
```

Published registries: `ENCOUNTER_COMPOSITION_REGISTRY`, `ECOLOGY_ZONE_REGISTRY`,
`SETTLEMENT_BIRTH_POLICY_REGISTRY`.

Builder and validation surface in `world/lore/monster_placement.py`:

```python
build_encounter_composition_registry(declarations) -> dict[str, EncounterComposition]
build_ecology_zone_registry(declarations) -> dict[str, EcologyZone]
build_settlement_birth_policy_registry(declarations) -> dict[str, SettlementBirthPolicy]
composition_bounds(composition) -> tuple[int, int]   # (sum of minima, sum of maxima)
validate_ecology_registries(
    zones, compositions, policies, *,
    region_face=None, variant_face=None, species_face=None,
) -> None
```

`validate_ecology_registries` checks everything the declarations alone can
decide: key identity, keyed-builder uniqueness, unknown/non-variant references,
species ownership, habitat compatibility of every pooled member against the
zone's parent region, inclusive integer geometry, `1 <= lower <= upper < 100`,
positive capacities and timings, positive weights, `minimum <= maximum`, and
whether one complete composition fits the zone's `cell_capacity` and
`wave_budget`. It raises `MonsterPlacementRegistryError` and publishes nothing.

The geometry surface in `world/maps/population_geometry.py`:

```python
density_bounds(eligible_count, lower_density, upper_density) -> tuple[int, int]
eligible_birth_cells(zone, *, geography, entries, policies) -> tuple[tuple[int, int], ...]
validate_ecology_geometry(
    *, geography, entries, zones, compositions, policies,
) -> tuple[str, ...]
```

`validate_ecology_geometry` reports (never raises) every candidate-world defect
in deterministic zone-key order, because `build_geography` collects it with its
other join problems.

## Formulas and mechanism

### Density interval

For `E` eligible birth cells:

```text
L = (E * lower_density + 99) // 100      # ceiling of E*lower/100
U = (E * upper_density) // 100           # floor   of E*upper/100
```

Enabled zones require `E > 0`, `0 < lower_density <= upper_density < 100`, and
`1 <= L <= U`. An empty enabled zone rejects. Because `upper_density < 100`,
`U < E` for ordinary occupancy: a sparse zone always keeps empty eligible cells.
With `E = 1`, `U = floor(upper/100) = 0`, so a usable zone needs at least two
eligible cells.

### Eligible birth cells

A cell is eligible only when it is

1. inside one of the zone's authored rectangles,
2. classified into the zone's `region_key` by the candidate terrain,
3. valid wilderness ground under the shared rule
   (`elosern_map_core.terrain.is_valid_wilderness_cell`, given the candidate
   world's own anchor footprints), and
4. outside every inhabited settlement's birth buffer.

Rectangle cells are enumerated directly; nothing scans the frame, reads
materialized rooms, or relies on which rooms exist. Zones may not share any
parent-region cell, even one that current terrain or exclusions make unusable.

### Settlement birth exclusion

Inhabited settlement categories are `capital`, `city`, `town`, `port` and
`elven_village` (`AnchorKind`). For a footprint settlement the distance source
is every masked footprint cell; for a point-shaped or map-less settlement it is
the published anchor cell. A cell is excluded when its minimum Chebyshev
distance to any source cell is at most the effective buffer. The effective
buffer is `max(1, policy.buffer_cells)`; a policy may only enlarge the generic
one-cell ring and is rejected for an unknown anchor, a non-inhabited anchor, or
a buffer below one. `dungeon` anchors receive no automatic exclusion — their
footprint cells are removed only by the shared validity rule. Explicit manual
and quest placement does not consult this module at all (see the ledger note).

### Complete-composition recoverability

A composition's achievable totals are the whole interval between the sums of
its members' minima and maxima. A complete composition that fits the zone's
cell capacity and wave budget is itself a legal wave, so a wave model of "add
one composition per step" is not weaker than allowing several per wave. The
proof is a bounded dynamic program over reachable totals `0..U`: a total is
reachable when adding some achievable composition total stays within `U`. The
candidate rejects when any unobstructed population below `L` cannot reach a
total at least `L`. Recovery never requires landing exactly on `L`, never
truncates a member group below its minimum, and a pool whose only fitting
composition can never accumulate into the band rejects at authoring time rather
than retrying at runtime.

## Authoring review (human judgment)

The four authored zones take the species that already had region-wide ambient
coverage and give each a bounded rectangle inside its approved habitat, plus the
two approved mixed groups. The declarations, not this document, are the balance
authority: no coordinate, density, count or timing is repeated here, and tests
do not pin them.

Human reviewers should judge, in the declarations themselves:

- **Sparse local ecology.** `lower_density`/`upper_density` are individuals per
  hundred eligible cells, and the zone's `cell_capacity`, `wave_budget`,
  `recovery_delay` and `replenishment_interval` decide how a cleared area
  refills. Values chosen for one habitat are not a recommendation for another,
  and the validation limit (`upper_density < 100`) is a hard bound, not a
  target.
- **Settlement surroundings.** Every inhabited settlement keeps at least its
  immediately neighbouring cells free of automatic births. Zones far from a
  settlement make that ring irrelevant in practice; the intent is that a zone
  placed near a settlement must not be used to fill the ground immediately
  outside it with standard population. A larger maintained surroundings area
  needs an explicit `SettlementBirthPolicy` row.
- **Unconfigured ground.** Ground outside every authored rectangle has no
  automatic species source. Future content must author its own zone rather than
  inherit coverage; no placeholder species or unresolved reference may be added
  to reserve habitat.
- **Explicit placements.** Manual sites and quest placements may overlap a zone
  and are never subject to automatic density or these exclusions; they still
  need shared placement validity (walkable wilderness surface for a site,
  approved species and variants, lawful lifecycle).

## Assertion roles and requirement mapping

The delta requirements were synced into
`openspec/specs/regional-ecology/spec.md` when this change was archived, which
assigned the canonical IDs below. The table is the hand-off ledger, and every
listed behavior test now carries `covers_requirement` annotations for the
requirement it establishes; none of them pins shipped coordinates, densities,
counts or prose.

| Requirement | Canonical ID |
| --- | --- |
| Ecology declarations publish only complete valid bounded habitats | `regional-ecology::ecology-declarations-publish-only-complete-valid-bounded-habitats` |
| Eligible birth area excludes inhabited settlement surroundings | `regional-ecology::eligible-birth-area-excludes-inhabited-settlement-surroundings` |
| Density intervals permit complete unobstructed recovery | `regional-ecology::density-intervals-permit-complete-unobstructed-recovery` |

### Requirement: ecology declarations publish only complete valid bounded habitats

| Test | Role | Defect detected |
| --- | --- | --- |
| `EcologyDeclarationTests.test_composition_forms_resolve_their_explicit_ranges` | synthetic mechanism | inferred counts instead of declared inclusive ranges; weight loss |
| `EcologyDeclarationTests.test_unknown_and_non_variant_references_are_rejected` | synthetic mechanism | unknown variant or species key accepted as a member |
| `EcologyDeclarationTests.test_habitat_mismatch_is_rejected_for_a_pooled_member` | synthetic mechanism | habitat tag not enforced for a pooled member (both directions) |
| `EcologyDeclarationTests.test_duplicate_keys_are_rejected` | synthetic mechanism | duplicate composition/zone/policy keys, repeated variant, repeated pool row |
| `EcologyDeclarationTests.test_inverted_or_non_positive_counts_and_timings_are_rejected` | synthetic mechanism | bool/zero/negative counts, inverted densities, inverted member ranges |
| `EcologyDeclarationTests.test_pool_weights_must_be_positive_and_reference_known_compositions` | synthetic mechanism | zero weight or dangling pool reference |
| `EcologyDeclarationTests.test_bounded_geometry_must_be_inclusive_integer_rectangles` | synthetic mechanism | empty, malformed, inverted or non-integer geometry |
| `EcologyDeclarationTests.test_a_complete_group_must_fit_cell_capacity_and_wave_budget` | synthetic mechanism | pool accepted although a complete group cannot be placed |
| `EcologyDeclarationTests.test_policy_buffers_are_positive_and_keyed_by_their_anchor` | synthetic mechanism | policy key drift or sub-one buffer |
| `EcologyDeclarationTests.test_validation_is_pure_and_publishes_nothing` | synthetic mechanism | validation mutating inputs or published registries |
| `CandidatePublicationTests.test_overlapping_zones_are_rejected_even_before_exclusions` | synthetic mechanism | ordinary zones sharing parent-region ground |
| `CandidatePublicationTests.test_a_zone_outside_its_parent_region_is_rejected` | synthetic mechanism | zone whose rectangle never classifies into its parent |
| `EcologyCandidatePublicationTests.test_a_rejected_ecology_candidate_keeps_the_published_snapshot` | representative integration control | partial publication of a rejected candidate |
| `EcologyCandidatePublicationTests.test_overlapping_synthetic_zones_are_rejected` | representative integration control | overlap escaping candidate publication |

### Requirement: eligible birth area excludes inhabited settlement surroundings

| Test | Role | Defect detected |
| --- | --- | --- |
| `BirthGeometryTests.test_zone_geometry_is_exactly_its_bounded_rectangle` | synthetic mechanism | geometry leaking outside rectangles or inventing unconfigured cells |
| `BirthGeometryTests.test_a_rectangle_crossing_region_and_water_rules_keeps_only_its_region` | synthetic mechanism | parent-region or shared-validity filtering skipped |
| `BirthGeometryTests.test_intersecting_rectangles_are_deduplicated_within_a_zone` | synthetic mechanism | double-counted overlapping geometry |
| `BirthGeometryTests.test_a_footprint_settlement_excludes_its_exterior_ring` | synthetic mechanism | footprint distance measured from an anchor cell or ring skipped |
| `BirthGeometryTests.test_a_noncapital_and_a_capital_settlement_exclude_identically` | synthetic mechanism | capital-only exclusion |
| `BirthGeometryTests.test_a_point_settlement_uses_its_published_anchor_cell` | synthetic mechanism | point settlement measured from a wrong source |
| `BirthGeometryTests.test_a_dungeon_anchor_receives_no_settlement_buffer` | synthetic mechanism | dungeon treated as a safe settlement |
| `BirthGeometryTests.test_a_dungeon_footprint_is_removed_by_shared_validity_only` | synthetic mechanism | absent buffer confused with absent validity |
| `BirthGeometryTests.test_an_explicit_policy_enlarges_the_buffer` | synthetic mechanism | policy row ignored or shrinking the ring |
| `BirthGeometryTests.test_a_policy_below_the_generic_ring_is_rejected` | synthetic mechanism | sub-one buffer accepted |
| `BirthGeometryTests.test_a_policy_naming_a_nonsettlement_anchor_is_rejected` | synthetic mechanism | unknown or dungeon policy anchor accepted |
| `BirthGeometryTests.test_the_candidate_entries_decide_the_footprint` | synthetic mechanism | stale published footprint used instead of the candidate's |
| `BirthGeometryTests.test_a_map_less_settlement_uses_its_candidate_anchor_cell` | synthetic mechanism | stale published anchor cell used instead of the candidate's |
| `BirthGeometryTests.test_the_live_wilderness_registry_is_never_consulted` | synthetic mechanism | live registry read during pure geometry |
| `EcologyCandidatePublicationTests.test_eligibility_reads_the_candidate_settlement_geometry` | representative integration control | candidate accepted/rejected from previously published footprints |
| `ShippedEcologyContentTests.test_explicit_site_placement_never_reads_automatic_birth_geometry` | registry contract | explicit placement pulled into automatic birth geometry |

### Requirement: density intervals permit complete unobstructed recovery

| Test | Role | Defect detected |
| --- | --- | --- |
| `DensityBoundsTests.test_sparse_densities_round_the_interval_outward` | synthetic mechanism | wrong ceiling/floor (independently known products) |
| `DensityBoundsTests.test_invalid_densities_and_empty_domains_are_rejected` | synthetic mechanism | zero/inverted/at-100 densities, empty domain, no positive band |
| `CandidatePublicationTests.test_a_zone_with_no_eligible_cell_is_rejected` | synthetic mechanism | empty enabled zone accepted |
| `CandidatePublicationTests.test_a_pool_with_no_complete_recovery_path_is_rejected` | synthetic mechanism | unreachable band accepted for a sub-lower start |
| `CandidatePublicationTests.test_a_composition_above_the_upper_bound_is_rejected` | synthetic mechanism | complete outcome above `U` accepted |
| `CandidatePublicationTests.test_a_pool_recovers_over_repeated_waves_and_may_overshoot_the_lower_bound` | synthetic mechanism | single-wave-only or exact-`L` requirement |
| `CandidatePublicationTests.test_headroom_is_proven_by_fitting_compositions_not_by_one_fixed_size` | synthetic mechanism | pool rejected/truncated although a fitting composition exists; oversized-only pool accepted |
| `EcologyDeclarationTests.test_a_complete_group_must_fit_cell_capacity_and_wave_budget` | synthetic mechanism | per-cell or per-wave limit ignored |
| `ShippedEcologyContentTests.test_every_shipped_row_validates_against_the_shipped_vocabularies` | registry contract | a shipped declaration no longer validates |
| `ShippedEcologyContentTests.test_every_shipped_zone_is_keyed_sparse_and_bounded` | registry contract | empty/bounded/sparse invariants lost on an authored row |
| `ShippedEcologyContentTests.test_every_shipped_composition_declares_complete_positive_ranges` | registry contract | incomplete or negative shipped range |
| `ShippedEcologyContentTests.test_every_shipped_pooled_member_belongs_to_its_zone_habitat` | registry contract | habitat relation drifting on an authored row |
| `ShippedEcologyContentTests.test_every_shipped_composition_is_pooled_by_a_zone` | registry contract | unreferenced composition left behind |

Affected existing assertions (no new claim attached):

| Test | Change | Role |
| --- | --- | --- |
| `PublishedRegistryTests.test_the_public_callables_are_exactly_the_read_validate_set` | extended with the three builders, `composition_bounds` and `validate_ecology_registries` | registry contract |
| `PublishedRegistryTests.test_variant_species_key_reads_the_variant_registry` | removed a redundant function-local import | registry contract (unchanged claim) |
| `SnapshotIsolationTests._world` | builds its deliberately re-partitioned candidate worlds with no authored zones, since a different coastline lawfully invalidates the shipped rectangles | representative integration control |
| `ShippedPlacementContentTests.test_every_shipped_site_habitat_is_the_region_of_its_coordinates` | unchanged; still the shared-placement-validity control for explicit sites | representative integration control |

Deferred, with the concrete prerequisite: the design's "explicit lawful manual
placement bypasses automatic birth exclusions and density" scenario has no
behavioural consumer in this slice (no population owner exists yet). This
change establishes the boundary (the site owner never reads the ecology
geometry, and shared placement validity still applies) and leaves the
observable placement behaviour to `manual-monster-compositions` and
`regional-population-runtime-cutover`, which own the placement path.

## Verification evidence (this change)

Run from the worktree root with the single-token environment file
(`/tmp/mud-population-test.env` containing `MUD_TEST_SETTINGS=1`):

| Command | Result |
| --- | --- |
| `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_placement` | `Ran 48 tests ... OK` |
| `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_population_geometry` | `Ran 24 tests ... OK` |
| `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_geography_source` | `Ran 14 tests ... OK` |
| `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_registry_index_contract` | `Ran 13 tests ... OK` |
| `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb tests.test_evennia_test_optimization_contract` | `Ran 10 tests ... OK` |
| `uv run --locked python -m tools.observability_lint check` | `scanned=822 frozen=0 violations=0 exemptions=374` |
| `uv run --locked python -m tools.contract_gate` | `contract gate passed: reference-context, traceability, observability, test-data, manifests, contracts` |
| `openspec validate regional-ecology-authoring --strict` | `Change 'regional-ecology-authoring' is valid` |
| `scripts/openspec-gates.sh archive regional-ecology-authoring` (pre-archive) | traceability `2695 covered, 0 uncovered, 0 errors`; `openspec validate --all --strict` `444 passed, 0 failed` |
| `scripts/openspec-gates.sh post-archive regional-ecology-authoring` (after the CLI sync and annotation repair) | traceability `2698 covered, 0 uncovered, 0 errors`; `openspec validate --all --strict` `444 passed, 0 failed` |

No logging path changed in this slice; the observability lint was run because
the changed map composition root participates in the facade-adopter set. CI
shards, the full managed browser suite and `tools.spec_traceability verify
--evidence` remain CI-owned and were not claimed locally.

## Registry index and mirroring

`encounter_compositions` and `ecology_zones` are added to
`world/lore/registry_index.py` so the existing recursive reference model
traverses the declared `ref` metadata (variant members, pool composition keys
and the zone's parent region) and the shipped reference-integrity contract
covers them. `SETTLEMENT_BIRTH_POLICY_REGISTRY` ships empty and is not indexed:
the registry index contract requires every indexed registry to ship at least one
entry. `world/lore/sync.py` is untouched: the lore-startup-sync requirement
enumerates the specific registries it mirrors, and this change activates no
system that reads a mirrored row.

# Regional monster population: the persistent owner

`world/maps/regional_population.py` is the single writer of a wilderness
world's regional population, added by the OpenSpec change
`regional-population-owner`. It owns selection state, birth waves and explicit
placement registration. It is **not** a scheduler: no clock stage, ambient
branch or room-entry hook is registered in this slice, so nothing spawns until
`regional-population-runtime-cutover` activates the stage.

## Ownership boundary

| Concern | Owner |
| --- | --- |
| Durable per-zone selection state, shared world seed | `world/maps/regional_population.py` |
| Eligible birth cells, local band `[L, U]` | `world/maps/population_geometry.py` (already published; unchanged here) |
| Ordinary home ownership of a born individual | the born individual's `db.home_ecology_zone` Attribute |
| Actual wilderness position | the wilderness script's `db.itemcoordinates` |
| Explicit manual/quest placement registration | `register_explicit_individual`, called by the placing owner |
| Fixed-clock scheduling, recovery episodes, history | `regional-population-recovery` and later slices; not this one |

Nothing here invents a compatibility path. An existing development world whose
script has no saved seed **refuses** (`read_population_seed` raises
`population_seed_uninitialized`); repair it explicitly through the GM console
or reset the development world. There is no missing-seed default, no seed
reroll, no zone initialization on restart and no save conversion.

## Public interface (for the successor slices)

Durable shapes, all JSON-safe:

```python
wilderness.db.regional_population = {
    "<zone_key>": {
        "initialized": True,
        "seed": int,                  # the shared world seed it was initialized with
        "generation_sequence": int,   # one per committed wave
        "recovery_due_tick": int | None,   # reserved for the recovery slice
        "settled_through_tick": int,
    }
}
wilderness.db.regional_population_seed = int   # written exactly once
individual.db.home_ecology_zone = "<zone_key>" # ordinary home ownership only
```

```python
current_population_tick() -> int                      # 0 before any clock advance
initialize_population_seed(wilderness, *, seed, tick) -> int   # write-once, never rerolls
read_population_seed(wilderness) -> int                        # refuses when absent/malformed
zone_state(wilderness, zone_key) -> ZonePopulationState | None # None = uninitialized
population_counts(wilderness, zone_key) -> PopulationCounts     # pure read
plan_population_wave(wilderness, zone_key, *, tick) -> PopulationWavePlan   # pure read
commit_population_wave(wilderness, plan) -> tuple[int, ...]     # atomic
initialize_zone(wilderness, zone_key, *, seed, tick) -> tuple[int, ...]  # once, atomic
register_explicit_individual(wilderness, individual, coordinates, *, tick) -> None
wilderness_registration_target(room) -> (wilderness, cell) | None
snapshot_population_surfaces(wilderness) -> dict[id(obj), SurfaceSnapshot]
restore_population_surfaces(snapshot) -> None
snapshot_regional_population_surfaces(start_tick, end_tick) -> dict[int, SurfaceSnapshot]
```

Reading rules a later slice must preserve:

- **Local** = every living `Monster` whose registered cell is inside the zone's
  rectangles intersected with its parent terrain region. Excluded-buffer cells
  are included, and ambient, manual, site, quest and visitor individuals all
  count. **Home** = every living individual carrying this zone's
  `home_ecology_zone`, wherever it stands — a travelling, unregistered or
  detached owner keeps consuming home headroom while counting locally only
  where it actually is. **Per-cell** = living occupants of each local cell.
- Position is read from `db.itemcoordinates` first and only falls back to a
  room's active coordinates when that room belongs to the same wilderness and
  the entity has no registration.
- Stored HP decides living; no gauge is ticked. Every set deduplicates IDs, so
  registering the same individual twice counts once.

### Blocked plans versus refusals

`PopulationWavePlan.blocked_reason` is a lawful, temporary answer:
`uninitialized`, `local_satisfied`, `home_saturated`, `no_legal_space`. A
blocked plan creates nothing, deletes nothing and does not advance the
sequence; `commit_population_wave` on it is a no-op returning `()`.

An absent world (`world_unavailable`), an unknown zone (`unknown_zone`), a
malformed record (`malformed_state`), an unusable or missing seed
(`population_seed_uninitialized`), a seed mismatch (`population_seed_mismatch`),
a stale plan (`stale_plan`) and an invalid explicit placement
(`explicit_placement_refused`) are refusals that raise before any write.

### Selection

One wave places exactly one complete composition. Cell first (lexicographic
eligible cells that are unprotected and have room for the smallest feasible
group), then a weighted pool composition among those with a fitting outcome,
then a uniformly chosen fitting count vector. Every draw is
`SHA-256(seed, zone_key, generation_sequence, tick, placement_ordinal, purpose,
draw_ordinal)` with rejection sampling, so replaying the same occurrence inputs
reproduces the same plan and different inputs can differ. Composition weights
are conditional on the drawn cell: a composition that fits fewer cells occurs
less often in aggregate, which the position-first design intends.

## Atomicity and rollback contract

`commit_population_wave` and `initialize_zone` each open one
`transaction.atomic()` covering every construction, home marker, coordinate
registration, active-room attachment and the state write. Before the write they
snapshot the world's population state, seed and coordinate registry, so a
failure at any point restores the durable values and reconciles the engine
caches through the shared `world.rules.surfaces` seam:
`flush_orphan_instances` evicts the rows the write created and re-reads the
contents cache of every room that received one (Evennia's contents handler is
not transaction-aware), and a snapshot object whose own row the rollback
removed -- a freshly provisioned wilderness script -- goes through
`flush_instance`. No private copy of that reconciliation lives in this owner. A
rolled-back wave publishes no `monster_population_wave` event and leaves no
stray registration.

A **caller-owned** rollback (a later stage failing after a committed wave) uses
the same pair:

```python
surfaces = snapshot_population_surfaces(wilderness)   # before the caller's writes
try:
    with transaction.atomic():
        ...  # commit_population_wave / register_explicit_individual
        ...  # any later write that may fail
except Exception:
    restore_population_surfaces(surfaces)
    raise
```

`snapshot_regional_population_surfaces` is the clock advance-surface shape for
the future stage registration; it discovers the world the way the owner's
writes do and answers `{}` before the world exists. The generic clock restore
cannot clear a room contents cache, so the runtime-cutover stage must call
`restore_population_surfaces` with the same mapping on its own failure path.

## Events

All three are info-level facade events scheduled with `transaction.on_commit`,
so only a durable change emits one:

| event | context |
| --- | --- |
| `monster_population_seed_initialized` | `seed`, `tick` (only on the actual first write) |
| `monster_population_wave` | `zone`, `region`, `individual`, `species`, `variant`, `cell`, `tick`, `created`, `sequence` |
| `monster_population_individual_registered` | `individual`, `coordinate`, `species`, `variant`, `tick` |

Reads, blocked plans and unchanged operations emit nothing.

## Assertion roles and requirement hand-off

The delta requirements below are not synced yet, so these tests carry **no**
`covers_requirement` annotation (delta IDs exist only after the archive sync).
This table is the hand-off: each test name, its role, and the delta
requirement/scenario it establishes.

| Test | Role | Delta requirement and scenario |
| --- | --- | --- |
| `RegionalPopulationTests.test_a_complete_group_consumes_one_unit_of_each_measure` | synthetic mechanism | Automatic births satisfy local and home-owned individual ceilings — complete fitting groups |
| `RegionalPopulationTests.test_a_departed_home_owner_keeps_home_headroom_but_stops_counting_locally` | synthetic mechanism | …ceilings — local and home measures |
| `RegionalPopulationTests.test_duplicate_registration_is_counted_once_and_moves_the_one_identity` | synthetic mechanism | …ceilings — local and home measures (each ID once per measure) |
| `RegionalPopulationTests.test_manual_excess_above_the_band_blocks_births_without_modifying_it` | synthetic mechanism | …ceilings — manual excess |
| `RegionalPopulationTests.test_home_owned_excess_outside_the_zone_saturates_births` | synthetic mechanism | …ceilings — manual excess (home measure) |
| `RegionalPopulationTests.test_a_full_cell_ceiling_leaves_no_legal_space_and_keeps_the_occupants` | synthetic mechanism | …ceilings — manual excess (cell measure) |
| `RegionalPopulationTests.test_replaying_an_occurrence_reproduces_its_own_complete_plan` | synthetic mechanism | Birth occurrences retain deterministic persistent individual state — occurrence selection |
| `RegionalPopulationTests.test_no_composition_is_ever_split_below_its_minimum_or_above_the_budget` | synthetic mechanism | …ceilings — complete fitting groups (no truncated row) |
| `RegionalPopulationTests.test_a_failed_wave_leaves_no_partial_group_and_a_retry_selects_the_same_plan` | synthetic mechanism | Population wave commit is atomic across durable and live surfaces — failure after real writes |
| `RegionalPopulationTests.test_a_failure_during_the_state_write_restores_every_surface` | synthetic mechanism | …atomic — failure after real writes |
| `RegionalPopulationTests.test_a_failure_after_the_state_write_publishes_no_wave_event` | synthetic mechanism | …atomic — commit observability (no rolled-back event) |
| `RegionalPopulationTests.test_a_committed_wave_emits_one_bounded_boundary_event` | synthetic mechanism | …atomic — commit observability |
| `RegionalPopulationTests.test_a_stale_or_hand_built_plan_is_rejected_before_any_write` | synthetic mechanism | …atomic — protection and refusals (rejects stale plans) |
| `RegionalPopulationTests.test_initialization_runs_once_and_never_refills_on_reload_or_preparation` | synthetic mechanism | …individual state — initialization once |
| `RegionalPopulationTests.test_initialization_on_an_inactive_cell_creates_no_room` | synthetic mechanism | …individual state — no materialized room |
| `RegionalPopulationTests.test_named_refusals_are_distinct_from_blocked_space` | synthetic mechanism | …atomic — protection and refusals; Shared population seed — no implicit seed default |
| `RegionalPopulationTests.test_a_malformed_persisted_seed_refuses_instead_of_being_replaced` | synthetic mechanism | Shared population seed — no implicit seed default (a present unusable value is never replaced) |
| `RegionalPopulationTests.test_a_negative_world_seed_still_initializes_and_replays` | synthetic mechanism | …no implicit seed default and …individual state — initialization once (any integer seed) |
| `RegionalPopulationTests.test_a_malformed_state_envelope_refuses_before_any_write` | synthetic mechanism | …atomic — protection and refusals (malformed saved state refuses instead of reading as unset) |
| `RegionalPopulationTests.test_reads_create_nothing_and_emit_nothing` | synthetic mechanism | …atomic — commit observability (reads emit nothing) |
| `RegionalPopulationTests.test_explicit_registration_never_reads_birth_geometry_or_stamps_ownership` | synthetic mechanism | Shared population seed and explicit registrations are owner supplied — manual and quest actual registration |
| `RegionalPopulationTests.test_registration_target_reads_only_a_real_wilderness_room` | synthetic mechanism | …explicit registrations — manual and quest actual registration (valid surface only) |
| `RegionalPopulationTests.test_the_clock_contract_snapshots_the_population_surfaces` | synthetic mechanism | …atomic — protection and refusals (declared surface, pure read) |
| `RegionalPopulationTests.test_a_caller_owned_rollback_restores_registrations_and_room_contents` | representative integration control | …atomic — failure after real writes (enclosing rollback) |
| `ShippedZonePlanningTests.test_a_shipped_zone_plans_only_inside_its_real_eligible_birth_cells` | representative integration control | …ceilings — complete fitting groups, inside the published geometry |
| `MapConsoleWildernessSpawnTests.test_a_wilderness_spawn_registers_the_actual_individual_at_its_cell` | representative integration control | Shared population seed and explicit registrations — manual and quest actual registration |
| `MapConsoleWildernessSpawnTests.test_a_fault_after_registration_restores_every_surface` | representative integration control | …explicit registrations — complete post-registration rollback |
| `WildernessSceneMonsterPlacementTests.test_a_wilderness_scene_monster_is_registered_as_its_actual_identity` | representative integration control | …explicit registrations — manual and quest actual registration |
| `WildernessSceneMonsterPlacementTests.test_a_fault_after_registration_leaves_no_object_or_registration` | representative integration control | …explicit registrations — complete post-registration rollback |
| `WildernessBootstrapTests.test_fresh_wilderness_provisioning_saves_the_population_seed_once` | representative integration control | …no implicit seed default (fresh script writes once) |

Affected existing assertions (no new claim attached):

| Test | Change | Role |
| --- | --- | --- |
| `MapConsoleTests.test_spawn_authoritative_identity_and_placement_rollback` | unchanged; still the non-wilderness explicit path and its rollback | representative integration control |
| `PermanentPackageOccupantTests.*` | unchanged; their package may still place only in the instance layer or a permanent anchor room | representative integration control |

## Verification evidence (this change)

Run from the worktree root with the single-token environment file
(`/tmp/mud-population-test.env` containing `MUD_TEST_SETTINGS=1`):

| Command | Result |
| --- | --- |
| `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population` | `Ran 25 tests ... OK` |
| `… world.maps.tests.test_gm` | `Ran 8 tests ... OK` |
| `… world.maps.tests.test_bootstrap.WildernessBootstrapTests` | `Ran 15 tests ... OK` |
| `… world.quests.tests.test_permanent_occupants.WildernessSceneMonsterPlacementTests` | `Ran 2 tests ... OK` |
| `… world.quests.tests.test_scene_builder_offline` | `Ran 10 tests ... OK` |

A note for the archivist: `world.quests.tests.test_permanent_occupants` as a
whole module requires an already-published map world (a pre-existing shard
ordering assumption unrelated to this change), which is why only the new class
was run alone. CI shards and `tools.spec_traceability verify --evidence` remain
CI-owned and were not claimed locally.

# Regional monster population — developer notes

Developer document for the `combat-individual-identity` prerequisite of the
regional monster population work. It records the combat identity contract, the
caller dispositions of the cutover, and the evidence behind this change.

## Identity contract

`world/rules/combat_identity.py` is the single definition and has no Evennia or
domain imports, so it can be imported from `combat_beats` and inputfuncs
without an import-order cycle. `world.rules.combat.decision_scope` re-exports
it, and `world/rules/monster_ai/models.stable_identity` delegates to it.

- Persisted actor: `dbref:<positive integer pk>`.
- Nonpersistent actor: an explicit non-empty `combat_identity` string becomes
  `fixture:<identity>`. Internal spaces are allowed; leading/trailing
  whitespace, empty values, booleans and control characters raise
  `CombatIdentityError` before any mutation.
- Display labels are presentation only. No suffix is appended to a name, no
  identity is derived from a label, and no name-key fallback or second
  battlefield path exists.

`Battlefield` validates `key == stable_actor_id(entity)` for every roster
member and rejects duplicate participant identities. Membership, presence,
range, initiative order, tactical and taunt declarations, nonlethal key sets,
flee/knockout sets, action bookkeeping, session records and EventLog
participant references all use the stable identity. `EventEntry`/`EventLog`
carry `actor_id`/`target_id`/`target_ids` beside the readable labels, so prose
rendering is unchanged while attribution, credit and targeting never parse a
label.

Pure combat tests construct ordinary `Battlefield` instances with explicit
`combat_identity` fixtures. There is no synthetic-name identity.

## Caller dispositions

- `world/rules/combat/{battlefield,rounds,damage,healing,decision_scope}.py`,
  `combat_session/{battlefield,lifecycle,rounds,policies,scans,settlement,
  observations,records,ai_tuning}.py`, `combat_beats.py`, `targeting.py`,
  `disengage.py`, `overwhelm.py`, `monster_behaviour.py` and
  `monster_ai/{models,snapshot,candidates,legality,estimation,utility,
  manual_campaign}.py`: identity-based membership and bookkeeping; labels are
  kept only where prose is rendered.
- `world/rules/action/event_log.py`, `effects/gauge_transfer.py`,
  `world/rules/state_reactions.py`, `buffs/surface.py`,
  `defeat_aftermath/{aftermath,digest,violation}.py`: participant, nonlethal
  and buff-bookkeeping references resolved by identity; violation/digest
  outcome maps are keyed by identity while their wake lines still render the
  label.
- `world/quests/planner.py`, `world/narrative/action_adapters.py`
  (including the deleted `_unique_key_index` and label-key recipient
  discovery), `world/narrative/projector.py`, command/combat-result rendering
  and `web/webclient/presentation/{combat_panel,combat_beats,skill_use}.py`:
  defeat credit, delivery and presentation read identities; displayed labels
  and dbref-bound `a`/`e` tokens are preserved.
- Harmless display `.key` reads (titles, roster names, logs, status views) are
  intentionally unchanged; they are not identity decisions.

## Label review

Labels remain the human-facing text. `EventEntry.target` and `EventLog.targets`
stay labels so every authored template renders unchanged; a consumer that
attributes or credits reads the identity fields instead. `Battlefield` roster
keys are identities, so two individuals sharing a label are listed and
targeted independently, and renaming either cannot redirect an existing
selection because selections persist pks, not labels.

## Evidence and assertion roles

Focused commands (run from the worktree with the single-token environment
file described in the design):

```
uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb <LABELS>
```

Verified labels and results:

- `world.rules.tests.test_combat_session_targeting` — 11 pass, including the
  same-label acceptance cases: independent HP/resources/flee/effects and a
  durable saved selection that survives rename, a reload through the session
  owner, roster reorder and completion.
- `world.rules.tests.test_combat_session_targeting world.rules.tests.test_combat_beats world.rules.tests.test_defend_dodge world.rules.tests.test_disengage` — 48 pass.
- `world.rules.tests.test_disengage_integration world.rules.tests.test_upkeep_settlement` — 30 pass.
- `world.rules.tests.test_taunt_constraints world.rules.tests.test_monster_behaviour_integration world.rules.tests.test_monster_flee_decision world.rules.tests.test_positional_marker` — 57 pass.
- `world.rules.tests.test_combat_session_persistence` — 37 pass (includes the
  commit-failure round rollback).
- `world.rules.tests.test_combat_session_recovery world.rules.tests.test_combat_initiation` — 50 pass.
- `world.rules.tests.test_combat_party` — 65 pass.
- `world.rules.tests.test_combat_session_flow world.rules.tests.test_combat_session_sexual_coercion world.skills.tests.test_martial_arts_behavior` — 66 pass.
- `world.rules.tests.test_monster_ai_selection` — 58 pass;
  `test_monster_ai_snapshots test_monster_ai_tuning test_monster_ai_memory` — 85 pass;
  `test_monster_ai_candidates test_monster_ai_coordination` — 72 pass;
  `test_monster_ai_estimation.SpreadProjectionTests test_initiative_and_turn_loop test_lightning_turn_behavior test_turn_order_control` — 65 pass.
- `world.rules.tests.test_action_evidence test_on_hit_counter_damage` — 42 pass;
  `test_multi_strike_cap_widening test_unconditional_multi_strike test_monster_provisioning` — 35 pass;
  `test_cast_settlement test_cmd_cast test_climax_settlement test_erosion_leech` — 66 pass.
- `world.quests.tests.test_planner test_settlement` — 68 pass;
  `test_escort_lifecycle` — 38 pass (same-label defeat credit is exercised by
  `test_same_display_key_creates_no_false_failure` and the bound-objective
  dbref cases).
- `world.rules.tests.test_defeat_aftermath_digest world.rules.tests.test_defeat_aftermath_violation` — 81 pass.
- `world.rules.tests.test_item_combat_turn world.maps.tests.test_gm` — 22 pass.
- `web.webclient.actions.tests.test_skill_use_actions commands.tests.test_cast_member_suffix` — 47 pass; the former duplicate-label ambiguity case now asserts identity-addressed success.
- `world.narrative.tests.test_narrative_events` — pass with the escort run.
- `world.rules.tests.test_monster_ai_manual_reports.CampaignEncounterTests` — 9 pass,
  including the named encounter, the same-label opponent selection and the
  refusal batch.
- `world.rules.tests.test_conferral_cast world.rules.tests.test_divine_mystery_progression.PartyAudienceConferralTests` — 22 pass, including same-label
  sources and reconferral after rename.
- `world.rules.tests.test_stateful_spells` — 11 pass (contact-policy identity).
- `world.rules.tests.test_action_narrative_deeds` — 41 pass (committed-log
  identity, same-label resolution, fixture occurrence identity).
- `world.rules.tests.test_monster_ai_tuning.SessionAITuningTests` — 6 pass
  (rejected identity leaves the session table empty).

Assertion roles: the migrated assertions are synthetic-mechanism checks with
independently known outcomes (fixed rolls, explicit fixtures) or registry-
contract checks; none echoes shipped data or wording. No browser suite was run
locally. No new test module was added, so `.github/evennia-shards.json` is
unchanged.

## Requirement annotations

The apply slice added no `covers_requirement` annotation: the three
ADDED/MODIFIED deltas have no canonical IDs before archival. After the sync,
the archive step attached the generated ID
`player-combat-session::combat-state-preserves-individual-identity-across-repeated-labels`
(the only requirement the sync introduced) to the discoverable tests whose
assertions establish its clauses:

- `SameLabelIndividualTests.test_same_label_individuals_keep_independent_state`
  — participant, effect and outcome state: distinct identities and team
  membership, damage and resource loss on the selected twin only, and flee
  state that removes only its own range while the twin stays targetable.
- `SameLabelIndividualTests.test_rename_and_reorder_cannot_redirect_a_saved_selection`
  — selection and restoration: a saved pk selection survives rename, the
  owner's reload and roster reorder, and resolves only the chosen individual.
- `SameLabelIndividualTests.test_duplicate_identity_rejects_before_any_session_write`
  — identity uniqueness: the same entity supplied twice rejects before any
  session write.
- `ObservationMemoryTests.test_same_label_sources_keep_independent_memory`
  — AI state: two same-label sources keep independent observation memory.
- `QuestPlannerTests.test_two_individuals_with_one_display_key_count_separately`
  — outcome state: two same-label individuals each count their own defeat.

The remaining acceptance tests cited in the apply slice establish the delta
scenarios or extend requirements already covered by their own annotations, so
they were left unannotated here:

- `SameLabelIndividualTests.test_same_label_individuals_keep_independent_state`
  and `test_rename_and_reorder_cannot_redirect_a_saved_selection` also carry
  the delta scenarios "Independent removal and credit", "Repeated labels are
  independent" and "Independent selected recipient" as behavior evidence.
- `QuestPlannerTests.test_a_redelivered_defeat_entry_advances_once` supplies
  the duplicate-delivery half of "Independent removal and credit" under its
  own `monster-individual-construction` annotation.
- `SessionItemMultiTargetRollbackTests.test_same_label_recipients_keep_distinct_event_log_identities`
  → `player-combat-session` "Independent selected recipient" (item recipient
  identity population feeding observation memory).
- `CampaignEncounterTests.test_legal_opponent_addresses_same_label_monsters_by_identity`
  → same identity contract at the manual-campaign boundary.
- `ConferralCastPathTests.test_same_label_sources_keep_distinct_grants` and
  `test_reconferral_after_rename_keeps_one_source_identity` → same identity
  contract for grant sources.
- `SettledResultNormalizationTests.test_shared_display_keys_resolve_by_identity_only`
  and `test_fixture_occurrence_identity_is_not_the_display_label` → narrative
  occurrence/recipient attribution; `SettledEffectVocabularyTests.test_committed_log_form_states_the_same_settled_results`
  now supplies explicit identities and keeps the identity-less rejection.

Rollback disposition: the identity cutover adds no new durable write path, so
the existing verified rollback controls remain authoritative instead of a
duplicated synthetic failure test — `test_commit_failed_after_prior_actor_aborts_entire_selected_round`
(round HP/revision/draft), `test_receipt_failure_after_terminal_clock_and_clear_restores_round`
(terminal clock/receipt/clear), the item journal rollback cases
(`test_upkeep_fault_restores_actor_and_companion_surfaces`,
`test_terminal_settlement_failure_after_item_use_restores_everything`) and the
defeat-aftermath rollback/replay suite. They assert durable rows, live handler
caches and draft state against the pre-call baseline.

Nearest current anchors (from the design's generated list) whose scope these
behaviours extend; the existing annotations on them already cover those main
requirements, so no additional claim was added:

- `battlefield-action-context::is-present-checks-canonical-battlefield-roster-membership`
- `player-combat-session::startup-restores-valid-sessions-and-terminates-invalid-references-safely`
- `monster-individual-construction::kill-accounting-keys-on-persistent-individual-identity-and-dedupes-duplicate-defeat-events`

No retired, empty or skipped claim is retained.
