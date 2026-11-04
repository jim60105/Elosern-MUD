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
