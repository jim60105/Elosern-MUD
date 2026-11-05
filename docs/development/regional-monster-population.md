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
    activity_key: str,   # ref("monster_activities", inverse="encounter_compositions")
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

### Content expansion habitats

The three weak species of the content expansion (泥膜史萊姆, 膠掌小鬼 and
蠟囊鼠) are placed only through the bounded zones below. Each rectangle is land
classified into its own parent region, and it stands clear of every published
settlement, harbor and authored site, so the shared validity rule and the
generic settlement ring leave the patch eligible without an explicit birth
policy. The declarations remain the only authority. No coordinate, density,
count or timing is repeated here.

| Zone keys | Dossier fact it serves | Terrain and scenario fit |
| --- | --- | --- |
| `eastern_mudbank_habitat`, `western_mudbank_habitat` | 泥膜史萊姆 keeps to damp banks, old irrigation side-channels and seepage mouths, and depends on standing film water. | Both patches sit in low plains and hill-valley ground that inland waterways cross, which is the damp, shaded low ground the dossier describes. |
| `western_quarry_habitat` | 膠掌小鬼 lives in hill scrub, disused quarry ground and under rock shelving. | Remote, dry, passable western hills, with no inland waterway cell inside the patch and no maintained settlement nearby. |
| `eastern_cache_habitat`, `western_cache_habitat` | 蠟囊鼠 works plains field margins, disused grain stores and hill transport ground. | A plains field margin and a hill transport patch, both remote from settlements and working facilities, so the authored cache stays a field cache and never a working granary or canal. |

**Movement and aggression.** The mudbank binding is `solitary_roaming`. Its
birth group disperses into independent single-member units that each roam the
whole patch, and its condition is `passive`, because the dossier describes a
creature that retreats from footsteps and answers after engagement. The goblin
group and each rat family are `cohesive_group` with a `defended_area` condition
bound to a small nest or cache sub-area inside their own grounds. They forage
over the patch and turn hostile in the defended area, which keeps their ordinary
foraging retreat-oriented. Every patch's grounds repeat its birth rectangle, so
movement and birth geometry stay aligned.

**No stronger variant in an ordinary pool.** Each of these pools holds the one
ordinary variant of its species. Stronger variants belong to manual sites and
boss sites, and none of them joins a pool. No pool names a variant the species
registry does not declare.

**Declared values.** These zones keep the shared sparse profile of the existing
zones, with the same density interval, the same delayed recovery and
replenishment timing, and the same home-owned per-cell ceiling wherever that
ceiling already fits the pool's largest group. The quarry patch and the cache
patches raise the per-cell capacity and the wave budget, because their single
composition can place a larger complete group than the earlier pools. The rule
that a complete composition fits one cell and one wave, together with the
recovery proof, is what moves those two values. The mudbank patches keep the
profile unchanged because their largest group already fit. Working canals,
granaries and settlement-adjacent conflicts stay outside automatic birth
geometry and require explicit manual or quest placement under the approved
exceptions.

**Accepted deviation, damp cells.** Design §4.1 limits the slime to explicitly
authored damp cells, while the zone model has no per-cell wetness predicate and
derives density from every eligible cell of a rectangle. The mudbank patches are
bounded rectangles inside the damp low ground instead of a set of individually
damp cells, and part of each rectangle lies immediately beside inland water. A
later change may shrink those rectangles onto the water cluster without a test
edit, because no test pins their geometry.

**Moving a rectangle later.** The birth registry and the activity registry are
validated independently, and no validator ties a zone's rectangle to its
grounds area. A reviewer who moves or shrinks any of these rectangles must apply
the same change to the matching grounds and, for the goblin nest and the two rat
caches, to the defended sub-area, and keep the sub-area strictly inside its
grounds.

**Verification.** Focused runs, each executed independently from the worktree
root with the single-token environment file `/tmp/mud-field-tests.env`
(`MUD_TEST_SETTINGS=1`):

| Command | Result |
| --- | --- |
| `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_placement` | OK |
| `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_activity` | OK |
| `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_population_geometry` | OK |
| `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_bootstrap` | OK |
| `uv run --locked --env-file=/tmp/mud-field-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_regional_population` | OK |
| `uv run --locked python -m tools.map_reference_context --check` | exit 0 |
| `openspec validate weak-species-habitats --strict` | valid |
| `uv run --locked python -m tools.contract_gate --change weak-species-habitats` | passed |

A disposable-database placement smoke observed the real births through the
deterministic owner. It published the authored map candidate, provisioned a
fresh wilderness, initialized every authored zone and read the committed
state. The mudbank patches produced only independent single-member groups under
their passive binding, each quarry and cache patch kept its members together
inside its own patch, every individual carried its authored species and
ordinary variant, and a fresh reload preserved identity, home zone, resources
and cell. The probe itself is not committed, because the retained production
smoke module belongs to the mixed-encounter change.

### Content expansion sites

`abandoned_transfer_station_encounter` is this batch's mixed manual site. Its
cell lies in remote western hill-valley ground on a hill transport route, far
from every maintained settlement and outside every authored ecology rectangle,
so the place reads as a disused station on an old route. The declarations stay
the only authority for the geometry and the counts; this section repeats none
of them.

**Co-location of independent animals.** The composition holds exactly two
`hanging_nest_forager` goblins and one `wax_cache_forager` rat. The goblin row
binds the cohesive station activity and the rat row binds the solitary stray
activity, so the site owner forms one pair and one independent individual. The
rat is an explicitly authored stray, distinct from its species' ordinary family
birth range. The site declares no activity override, so those row bindings
resolve for the whole composition.

**Defended sub-areas.** Both bindings roam the station grounds. The goblin pair
turns hostile only inside the nest sub-area and the rat only inside the cache
sub-area, which keeps an ordinary meeting elsewhere on the grounds
retreat-oriented.

**One cell only at the start.** All three are placed on the site's cell and
share it until their first independent decisions fall due. The goblin pair
decides on its cohesive interval and the rat on its solitary interval, so the
two movement groups may separate after that boundary. Whole-cell engagement
admitting all three is a property of the freshly populated site, and the smoke
engages before any decision is due.

**One-shot lifecycle.** The site is one-shot. Defeating its members leaves the
durable record cleared, and the clock settlement is the only writer of that
state. A committed reload, a later clock settlement, the map's own population
read and a clear-out quest acceptance all observe the same cleared site, and
none of them creates an individual. Future repeatable content must declare its
own lifecycle in its own declaration; quest acceptance or map observation never
restores a cleared site.

**Verification.** Focused runs, each executed independently from the worktree
root with the single-token environment file `/tmp/mud-transfer-station.env`
(`MUD_TEST_SETTINGS=1`):

| Command | Result |
| --- | --- |
| `uv run --locked --env-file=/tmp/mud-transfer-station.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_content_expansion_sites.TransferStationEncounterTests` | OK, 5 tests |
| `uv run --locked --env-file=/tmp/mud-transfer-station.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_placement` | OK |
| `uv run --locked --env-file=/tmp/mud-transfer-station.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_activity` | OK |
| `uv run --locked --env-file=/tmp/mud-transfer-station.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_sites` | OK |
| `uv run --locked --env-file=/tmp/mud-transfer-station.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_population_geometry` | OK |
| `uv run --locked --env-file=/tmp/mud-transfer-station.env evennia test --settings test_settings.py --keepdb world.rules.tests.test_field_contact_boundaries` | OK |
| `uv run --locked --env-file=/tmp/mud-transfer-station.env evennia test --settings test_settings.py --keepdb world.quests.tests.test_hunt_catalog_content` | OK |
| `uv run --locked python -m tools.map_reference_context --check` | exit 0 |
| `openspec validate abandoned-transfer-station-encounter --strict` | valid |
| `uv run --locked python -m tools.contract_gate --change abandoned-transfer-station-encounter` | passed |

The smoke module populates the shipped site through the real lifecycle owner
and observes three persisted identities, the movement groups its declarations
derive, one ordinary session admitting all three as distinct targets, one
defeat credit per actual individual with a redelivered event adding nothing,
and a cleared one-shot site that stays cleared across a committed reload, a
later clock settlement, the map read and a refused clear-out acceptance.

### High-tier boss sites

`reservoir_crocodile_boss_site` and `ember_bristle_boss_site` are this batch's
two one-shot high-tier bosses. The first holds one `reservoir_warden` (the local
name 閉灣者) in a remote southeast tidal backwater; the second holds one
`warm_den_boar` (赤背) in remote dry western rocky woodland. The declarations
remain the only authority for cells, extents and counts; this section repeats
none of them.

**Remoteness and geography.** The crocodile's backwater is southeast-coast land
immediately beside a cluster of inland-water cells, far from every maintained
settlement and outside every authored ecology rectangle, so the place reads as a
quiet tidal inlet rather than a working coast. The boar's ground is dry western
hill-valley woodland with no inland water inside it, which matches the species'
authored old-kiln and reused-den ecology, and it also stands clear of maintained
settlements and authored rectangles. Both positions are walkable wilderness
ground and neither is an anchor footprint.

**Territory and defended extents.** Each boss roams one bounded territory and
defends a smaller extent strictly inside it: the crocodile's deep bay inside the
backwater grounds, and the boar's den inside the woodland grounds. Roaming the
outer grounds stays retreat-oriented; entering the defended extent admits an
immediate hostile response. Each site declares one solitary individual, so the
composition's own territorial binding governs and no site override is needed.

**Names are not identity.** 閉灣者 and 赤背 are individual names
(`individual_name_zh`, stored as the individual's `individual_name`). Each
boss's identity remains its registered species/variant pair, and the site's
authority over the individual is its saved persistent identity, never the name.

**Escape and the crocodile trade-off.** The boar keeps its legacy `pack_hunter`
flee threshold, so a real session can drive it to a legal adjacent departure. The
living individual keeps its identity, its site ownership and its actual
remaining resources through the journey, re-entry and a committed reload, and a
later engagement starts with those same values; nothing resets them on exit. The
crocodile's utility binding never chooses a voluntary flee, so its fight is
decided by the party's own legal retreat. That trade-off is recorded here and
adds no mechanism. Neither high-tier variant joins an ecology pool: both
compositions are owned by these one-shot sites.

**One-shot lifecycle.** Defeating a boss leaves the site's durable record
cleared at the committed loss boundary, and no clock settlement, map read,
revisit or quest acceptance recreates it. The cleared record keeps the defeated
member identities as ownership history, so a later quest binding can never
count a replacement individual.

**Verification.** Focused runs, each executed independently from the worktree
root with the single-token environment file `/tmp/mud-boss-tests.env`
(`MUD_TEST_SETTINGS=1`):

| Command | Result |
| --- | --- |
| `uv run --locked --env-file=/tmp/mud-boss-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_content_expansion_sites` | OK, 8 tests |
| `uv run --locked --env-file=/tmp/mud-boss-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_placement` | OK |
| `uv run --locked --env-file=/tmp/mud-boss-tests.env evennia test --settings test_settings.py --keepdb world.lore.tests.test_monster_activity` | OK |
| `uv run --locked --env-file=/tmp/mud-boss-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_monster_sites` | OK |
| `uv run --locked --env-file=/tmp/mud-boss-tests.env evennia test --settings test_settings.py --keepdb world.maps.tests.test_population_geometry` | OK |
| `uv run --locked python -m tools.map_reference_context --check` | exit 0 |
| `openspec validate high-tier-boss-sites --strict` | valid |
| `uv run --locked python -m tools.contract_gate --change high-tier-boss-sites` | passed |

The smoke module populates both boss sites through the real lifecycle owner and
observes one labelled individual per site with its composition's variant and
territorial binding, no boss variant in any ecology pool, a defeated crocodile
whose cleared record survives a committed reload, a revisit, the map read and a
refused clear-out acceptance with no new individual, and an escaped boar that
departs through a real journey, keeps its persistent identity and site
ownership while absent, reloads with its actual departure HP/MP/SP, and is
re-engaged at its destination with those same values.

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

# Actual live population view

`world/maps/wilderness_population.population_view(wilderness, cells)` is the
single read projection every presence consumer shares (area map entities,
live-sight travel notices, the hostile interrupt comparison, GM placement
facts). Since `actual-live-population-view` it reports **only actually present
individuals**:

- The wilderness script's `db.itemcoordinates` is the one authoritative
  position surface. The view builds one index over it and projects each living
  `Monster` on a requested valid cell exactly once, under its persistent
  `object:<dbref>` identity, with its current coordinate and the tier/danger
  grade resolved from its species/variant record. Characters and NPCs keep
  their existing observations.
- Stored HP decides living (`world.rules.surfaces.persisted_hp`); no gauge is
  ticked and no `TraitHandler` is constructed. The read creates, reconciles,
  moves and deletes nothing and emits no event.
- Nothing prospective exists in the fact stream. An uninitialized, empty,
  blocked or due habitat, a composition declaration, a site's lifecycle state
  and an ecology zone's home ownership are never evidence of presence: a
  scheduled future birth is not a visible entity and never raises a sighting or
  an interruption. A dead individual is absent. A cleared site whose members
  are still alive keeps those members: physical presence is not filtered by
  the site owner's read verdict.
- Identity belongs to the individual. Renaming, activating the cell, recycling
  the room or reloading keeps the same key; a freshly born individual is a new
  ID, so two same-label individuals stay distinct.

The view no longer consumes `ambient_population_decision`, `ExpectedSlot`,
`ambient_observation_key`, the capital entry or slot matching. Those remain
the materializer's own machinery until `regional-population-runtime-cutover`.
No second view and no slot-projection alias exists.

## Habitat guidance versus entity facts

A regional hunt's authored hunting region or ecology zone is **habitat
guidance**, owned by `regional-hunt-supply-cutover` and presented as a
destination marker, never as a monster fact. Exact entity destinations and
hostile travel interruptions require an actual present individual from this
view; a marker for an undersupplied habitat stays a marker and never becomes an
entity annotation or an exact target.

## GM ownership versus current position

`web/gm/readers/monsters.py` reports the two independently:

- **Home ownership** — `home_zone_of` reads the individual's own
  `home_ecology_zone` marker (reported even when the authored row no longer
  resolves); `region_of` resolves the owning site's region or the home ecology
  zone's region. Variant membership of an ambient placement rule is never read
  as ownership. The GM `region` list filter selects by this ownership region.
- **Actual position** — `actual_cell_of` reads the owner's registered cell and
  `current_region_of` classifies that cell's terrain region. The placement
  section prints `歸屬生態領域`, `歸屬區域`, `目前區域` and `實際座標` as separate
  rows, so a moved individual no longer inherits its site's authored coordinate.

## Assertion roles and requirement hand-off

The delta removes
`wilderness-population-view::population-reads-share-materialization-decisions`
and `wilderness-population-view::observation-identities-survive-materialization`
and adds two requirements. Following
`docs/development/spec-test-traceability.md`, the IDs were generated from an
equivalent spec tree (the main specs with this delta applied) before archiving,
and the new tests were annotated with them **at the archive sync**, once the
CLI had written the requirements into the main spec:

- `wilderness-population-view::population-reads-report-actual-living-registrations`
  ← `test_a_configured_cell_reports_nothing_until_an_individual_exists`,
  `test_a_habitat_without_a_living_individual_reports_nothing`,
  `test_every_actual_living_owner_is_reported_once_with_canonical_facts`,
  `test_a_moved_individual_is_absent_from_its_former_cell`,
  `test_repeated_reads_change_nothing`,
  `test_population_view_does_not_construct_traits`,
  `test_a_species_cell_reports_exactly_its_living_members`,
  `test_a_protected_branch_migration_monster_stays_visible`,
  `test_supplementary_individuals_take_unique_slots_and_keep_them`.
- `wilderness-population-view::observation-identity-belongs-to-persistent-individuals`
  ← `test_identity_survives_activation_rename_and_reload`,
  `test_a_same_label_birth_gets_a_fresh_identity`,
  `test_a_same_label_replacement_gets_a_fresh_identity`.

The retired IDs are not re-pointed to any live requirement. This table is the
hand-off: each test, its role, and the delta requirement/scenario it
establishes.

| Test | Role | Delta requirement and scenario |
| --- | --- | --- |
| `WildernessPopulationViewTests.test_a_configured_cell_reports_nothing_until_an_individual_exists` | synthetic mechanism | Population reads report actual living registrations — no prospective entities |
| `WildernessPopulationViewTests.test_an_empty_cell_reports_no_monster` (configured habitat, covered by the test above) | synthetic mechanism | …no prospective entities (configured composition is not presence) |
| `WildernessPopulationViewTests.test_a_habitat_without_a_living_individual_reports_nothing` | representative integration control | …no prospective entities (uninitialized, cleared and due habitat) |
| `WildernessPopulationViewTests.test_every_actual_living_owner_is_reported_once_with_canonical_facts` | synthetic mechanism | …actual members of every owner (ambient, site, foreign, explicit; dead/absent excluded) |
| `WildernessPopulationViewTests.test_repeated_reads_change_nothing` | synthetic mechanism | …no read mutation |
| `WildernessPopulationViewTests.test_population_view_does_not_construct_traits` | synthetic mechanism | …no read mutation (no traits handler, no SQL write) |
| `WildernessPopulationViewTests.test_identity_survives_activation_rename_and_reload` | representative integration control | Observation identity belongs to persistent individuals — identity across room lifecycle |
| `WildernessPopulationViewTests.test_a_same_label_birth_gets_a_fresh_identity` | synthetic mechanism | …fresh birth and repeated labels |
| `WildernessPopulationViewTests.test_a_moved_individual_is_absent_from_its_former_cell` | synthetic mechanism | …actual members of every owner (current position wins) |
| `WildernessPopulationViewTests.test_a_hostile_interrupt_needs_an_actual_living_individual` | representative integration control | Wilderness steps report stateless committed interrupts — future birth is not an interruption |
| `AmbientSpeciesReconciliationTests.test_a_species_cell_reports_exactly_its_living_members` | synthetic mechanism | …actual members of every owner (dead member absent while protected) |
| `AmbientSpeciesReconciliationTests.test_a_same_label_replacement_gets_a_fresh_identity` | synthetic mechanism | …fresh birth and repeated labels |
| `AmbientSpeciesReconciliationTests.test_a_protected_branch_migration_monster_stays_visible` | synthetic mechanism | …actual members of every owner (branch classification is not presence) |
| `HuntProvisioningTests.test_supplementary_individuals_take_unique_slots_and_keep_them` | synthetic mechanism | …actual members of every owner (view reports the persistent IDs) |
| `BuildTravelEventsTests.test_a_recycled_room_keeps_the_same_identity_and_raises_no_notice` | synthetic mechanism | Wilderness steps … — identity and absent context |
| `BuildTravelEventsTests.test_a_new_live_identity_raises_the_hostile_notice` | synthetic mechanism | …transition/context table (new hostile) |
| `WildernessAreaTests.test_entity_annotations_are_actual_living_individuals_only` | representative integration control | Wilderness area maps … — entity presence is actual |
| `WildernessAreaTests.test_entities_carry_one_count_and_their_canonical_threat` | synthetic mechanism | …entity presence is actual (one count, canonical threat) |
| `MonsterReaderTests.test_placement_reports_home_ownership_and_actual_position_apart` | synthetic mechanism | GM inspection (delta task 2.1, no ambient-rule ownership guess) |
| `MonsterReaderTests.test_a_standing_position_is_read_from_the_actual_registration` | representative integration control | GM inspection reads the actual coordinate/region |
| `StateApiListFilterTests.test_monster_species_and_region_filters_select_the_individual` | representative integration control | GM region filter selects home ownership, not variant membership |

Affected assertions whose claim was retired rather than replaced:
`test_view_agrees_with_entry_and_observation_identity_is_stable`,
`test_species_view_agrees_with_materialization_and_session_protection`,
`test_a_survivor_keeps_its_identity_when_the_slot_before_it_dies`,
`test_a_protected_drifted_baseline_monster_stays_visible`,
`test_a_protected_monster_on_a_now_empty_cell_stays_visible`,
`test_protected_duplicate_baseline_monsters_are_both_visible`,
`test_a_prospective_slot_that_materializes_is_not_resighted` and
`test_a_slot_and_its_materialized_monster_state_one_threat` were deleted with
their prospective-slot subject; their live-presence substance moved to the
actual-owner and actual-annotation tests above. No annotation was re-pointed at
a different requirement to keep the local traceability gate green.

## Verification evidence (this change)

| Command | Result |
| --- | --- |
| `… world.maps.tests.test_wilderness_population.WildernessPopulationViewTests` | `Ran 10 tests ... OK` |
| `… world.maps.tests.test_wilderness_population_species.AmbientSpeciesReconciliationTests` | `Ran 12 tests ... OK` |
| `… world.maps.tests.test_monster_provisioning.HuntProvisioningTests` | `Ran 11 tests ... OK` |
| `… world.rules.tests.test_travel_events` | `Ran 35 tests ... OK` |
| `… web.webclient.presentation.tests.test_area_map.WildernessAreaTests` | `Ran 15 tests ... OK` |
| `… web.gm.tests.test_reader_monsters` | `Ran 12 tests ... OK` |
| `… web.gm.tests.test_state_api.StateApiListFilterTests` | `Ran 2 tests ... OK` |
| `uv run --locked python -m tools.spec_traceability --repo-root /tmp/omp-equiv-np8f_k9m list --json-output …/reqs.json` (equivalent tree outside Git: main specs + this delta, all test sources copied, new tests mounted to the generated IDs) | produced the two IDs quoted above |
| `uv run --locked python -m tools.spec_traceability --repo-root /tmp/omp-equiv-np8f_k9m check` | `2702 requirements, 12332 associations, 2702 covered, 0 uncovered, 0 errors` |
| `uv run --locked python -m tools.map_reference_context` | regenerated the source fingerprint after the `travel_interrupts` docstring change |
| `uv run --locked python -m tools.observability_lint check` | `scanned=823 frozen=0 violations=0 exemptions=376` |
| `uv run --locked python -m tools.contract_gate` | reference-context, observability, test-data, manifests and contracts pass; in the checkout, traceability reports the two requirements this delta REMOVES as uncovered with 0 errors until the archive sync replaces them — the expected pre-sync state, superseded by the equivalent-tree evidence above |

The temporary equivalent tree is a disposable directory outside the checkout,
not a branch or a worktree; it is deleted after the check and never committed.

No logging path changed (the touched modules only had docstrings updated); the
observability lint ran because they are facade-adopter files. CI shards, the
managed browser suite and `tools.spec_traceability verify --evidence` remain
CI-owned and were not claimed locally.

## Whole-cell field engagement

Ordinary field engagement and field-cast openings now share one encounter
roster and one recipient rule:

| Concern | Rule |
| --- | --- |
| Encounter roster | `field_enemy_roster(actor)` in `world/rules/combat_initiation.py`: every living, co-located `Monster`, sorted by integer pk, or `()` when the actor is unlocated. It reads no ownership, species or group marker. |
| Ordinary text/browser `engage` | Validates the named anchor with `engage_group()`'s own per-target gates, then calls `engage_group(actor, field_enemy_roster(actor))`. A dead, remote or non-monster anchor rejects instead of resolving a same-labeled bystander. |
| Explicitly staged combat | `engage_group(actor, targets)` keeps its declared participant set. Guild examinations build their session directly with the host as the only enemy; manual campaigns pass their own list. Neither consults the roster. |
| Opening recipients | `_prepare_opening` computes `enemies = field_enemy_roster(commander)` and `recipients = _opening_recipients(...)`: the anchor alone for SINGLE/NONE/SELF, every roster member for AREA. The candidate battlefield is built from `enemies`; only `recipients` are revalidated and preflighted. |
| Preview and commit | `FieldOpeningPreview.enemies` is the admitted roster; `FieldOpeningPreview.targets` stays the concrete recipients. The committed path calls `engage_group(..., preview.enemies)` and then `submit_opening_action(..., preview.targets)` inside the same transaction. `FieldChoice.line_up` remains the action's recipient line-up, so the browser protocol's SINGLE-opening shape is unchanged. |

All ordinary entry points reach the same rule: the text `engage` command and
the `explore.engage` browser adapter call `engage`; field `cast`, `cast ... 由
<成員>` and `explore.cast` route through `cast_in_field` / `cast_as_member` to
`initiate_field_combat`. No one-element `engage_group` bypass remains.
The `webclient-skillbook-casting` delta records the browser routing contract so
the main spec's opening-membership scenario matches this rule after the archive
sync.

### Assertion roles and requirement hand-off

After the archive sync, the whole-cell requirement the sync generated is
`field-combat-initiation::whole-cell-field-membership-is-independent-of-opening-recipients`,
and the retired single-target/AREA requirement no longer exists as an ID. Three
assertion-bearing `LineUpSelectionTests` methods carry that generated ID as
their `covers_requirement` claim, each because its assertions establish a
clause of it:
`test_area_opens_against_every_living_room_monster` (AREA membership admits
every living occupant and excludes the dead),
`test_single_open_admits_the_whole_room_but_targets_only_the_named_monster`
(membership in persistent-ID order plus exactly one opening recipient), and
`test_preview_roster_matches_the_committed_admission` (preview `enemies` equals
the persisted `enemy_ids` while `targets` stays the anchor). The other tests in
the table establish scenarios of the `player-combat-session` and
`webclient-skillbook-casting` requirements, whose own annotated tests already
carry those IDs.

| Test | Role | Requirement / scenario |
| --- | --- | --- |
| `LineUpSelectionTests.test_single_open_admits_the_whole_room_but_targets_only_the_named_monster` | synthetic mechanism: same-label roster, selected-recipient HP, dead and remote exclusion | `field-combat-initiation` "Whole-cell field membership is independent of opening recipients" / "Single recipient in mixed cell", "Dead and absent exclusion" |
| `LineUpSelectionTests.test_preview_roster_matches_the_committed_admission` | synthetic mechanism: preview `enemies` equals persisted `enemy_ids`, `targets` is the anchor | same / "Preview and companion parity" |
| `LineUpSelectionTests.test_area_opens_against_every_living_room_monster` | synthetic mechanism: AREA recipients and roster both exclude a dead occupant | same / "Area opening", "Dead and absent exclusion" |
| `LineUpSelectionTests.test_area_in_a_one_monster_room_takes_the_same_path` | synthetic mechanism: single-monster AREA path | same / "Area opening" |
| `EngageGroupTests.test_engage_admits_every_living_colocated_monster_in_persistent_id_order` | synthetic mechanism: ordinary A + A + B admission by identity | `player-combat-session` "engage creates one persistent local combat session" / "Whole-cell ordinary membership" |
| `EngageGroupTests.test_explicit_group_roster_stays_exact` | synthetic mechanism: staged `engage_group` does not sweep | same / designated/staged participants |
| `EngageGroupTests.test_engage_rejects_an_invalid_anchor_without_substituting_a_bystander` | synthetic mechanism: dead anchor refusal with a living same-label twin | same / "Remote or dead target is rejected", "Whole-cell ordinary membership" |
| `CombatActionsCommandTests.test_engage_command_admits_the_whole_cell_of_same_label_monsters` | real text owner: `CmdEngage` with `#dbref`, same-label A + A + B | same / "Whole-cell ordinary membership" |
| `ExplorationActionAdapterTests.test_engage_adapter_admits_every_living_monster_in_the_cell` | real browser adapter: authoritative `explore.engage` entry | same / "Whole-cell ordinary membership" |
| `ExplorationActionAdapterTests.test_engage_rejects_remote_or_dead_target_without_session` | real browser adapter: dead id with a living same-label twin is not substituted | same / "Remote or dead target is rejected" |
| `FieldCastActionTests.test_a_companion_opening_opens_the_commanders_encounter` | real browser companion cast: roster parity, commander-owned session, caster-owned draft | same / "Whole-cell ordinary membership" |
| `ExamStartTests.test_an_examination_roster_never_sweeps_a_co_located_monster` | real guild examination start: exact host-only enemy roster | same / designated examination participants |
| `PreviewFieldSkillTests.test_duplicate_display_labels_keep_individual_line_up_identities` | synthetic mechanism: preview discloses both same-label individuals instead of disabling | `field-combat-initiation` "Whole-cell field membership is independent of opening recipients" / "Single recipient in mixed cell" |
| `OpeningOrderPolicyTests.test_ordinary_entry_order_never_reorders_initiative` | synthetic mechanism: whole-cell admission keeps `opening_first_actor` empty and the initiator does not act first | `player-combat-session` "engage creates one persistent local combat session" / "Whole-cell ordinary membership" |
| `FieldCombatTargetTests.test_roster_is_empty_for_an_unlocated_actor` | synthetic mechanism: unlocated roster | `field-combat-initiation` / "Dead and absent exclusion" |
| `SkillPreviewActionTests.test_single_openings_keep_recipient_shape_in_a_mixed_cell` | real browser preview panel: every same-cell anchor is listed while each SINGLE row keeps one recipient | `webclient-skillbook-casting` "Field submissions revalidate and preserve deterministic routing" / "Anchor engagement follows the skill shape" |

### Verification evidence (this change)

Focused runs, each executed independently with the single-token environment
file:

| Command label | Result |
| --- | --- |
| `world.rules.tests.test_combat_initiation` | 32 tests, OK |
| `world.rules.tests.test_combat_session_flow.test_engage_group_flow` | 8 tests, OK |
| `commands.tests.test_combat_actions` | 36 tests, OK |
| `web.webclient.actions.tests.test_exploration_actions.test_party_and_engage` | 18 tests, OK |
| `world.rules.tests.test_field_cast` | 17 tests, OK |
| `world.rules.tests.test_companion_field_opening` | 16 tests, OK |
| `world.rules.tests.test_companion_field_cast` | 15 tests, OK |
| `world.rules.tests.test_combat_session_flow.test_opening_draft_seed` | 7 tests, OK |
| `commands.tests.test_cast_member_suffix` | 11 tests, OK |
| `world.rules.tests.test_combat_session_targeting` | 12 tests, OK |
| `world.rules.tests.test_combat_session_persistence` | 37 tests, OK |
| `world.rules.tests.test_combat_party` | 65 tests, OK |
| `web.webclient.actions.tests.test_skill_use_actions.FieldCastActionTests.test_a_companion_opening_opens_the_commanders_encounter` | 1 test, OK |
| `web.webclient.actions.tests.test_skill_use_actions.SkillPreviewActionTests` | 13 tests, OK |
| `world.rules.tests.test_guild_exams.ExamStartTests.test_an_examination_roster_never_sweeps_a_co_located_monster` | 1 test, OK |

The full `world.rules.tests.test_guild_exams` module also reproduces a
pre-existing failure in
`ExamSettlementRecoveryTests.test_incoherent_cold_start_fails_once_and_restores_the_host`
on unmodified `master`; it is unrelated to this change and was not modified
here. No browser suite beyond the listed authoritative action tests was run.
No new test module was added, so `.github/evennia-shards.json` is unchanged.

# Manual monster compositions

Developer document for the OpenSpec change `manual-monster-compositions`. Manual
sites no longer cycle `variant_keys` until `capacity`: a site names one complete
authored composition, owns exactly the individuals that composition places,
and resolves them by persistent identity rather than by standing on its cell.

## Declarations

`world/lore/monster_placement.MonsterSite` is
`(key, kind, region_key, coordinates, composition_key, capacity, one_shot,
recover_after_ticks=None)`; `kind` comes from
`camp | nest | boss_site | stray | encounter`. `capacity` is the ceiling every
legal outcome of the composition must fit, never an instruction to fill absent
rows. `validate_monster_placement_registry(..., compositions=...)` resolves the
named composition, checks every member variant against the variant and species
registries and the site's habitat, and rejects an empty, unknown, or
over-capacity reference before publication. `composition_variant_keys`
projects a composition's member keys for reporting and validation.

The three shipped sites keep their declared membership and lifecycle as three
new site-only composition rows (`ridge_burrow_nest_group`,
`cliff_echo_camp_group`, `tide_mouth_boss`); no composition is pooled into an
ecology zone unless a zone actually selects it.

## Durable site state and member identity

Each site's record on the wilderness script is

```text
{
  "state": "populated" | "cleared",
  "cleared_at_tick": int | None,
  "seed": int,                  # derived once, on first population
  "generation_sequence": int,   # 0 first, +1 per recovery
  "member_ids": list[int],      # authoritative persistent identities
}
```

`seed` derives deterministically from the world seed supplied by
`world.maps.regional_population.read_population_seed` and the site's own key.
The world seed is read only when a site needs its first population; a missing
or malformed seed raises the owner's `population_seed_uninitialized` refusal
before any construction, registration, or site write. There is no implicit
default.

`member_ids` is the site's authority. `monster_sites._members` resolves those
IDs through the database in persistent-ID order and keeps only rows whose
`db.site_key` still matches, so a member that moved away, lost its room, or was
detached is still the site's own living individual. A living absent member
therefore prevents a false clear. A row merely carrying the site marker without
being in `member_ids` is never adopted, counted, or deleted.

Clearing keeps the defeated IDs (ownership history); recovery replaces them
with fresh IDs at `generation_sequence + 1`, so an old quest binding can never
count a recovered individual. An existing record that cannot be interpreted
(missing seed/sequence/member IDs, or a non-integer ID list) raises
`MalformedPopulationState` before any write; the pure read answers the
`state_unreadable` verdict instead. Nothing repairs or converts such a save:
the documented development-save repair is an explicit GM reset/repair, never a
startup mutation.

### Interface for the successor slice

`site_state(site_key)` answers `SiteState(key, state, cleared_at_tick, seed,
generation_sequence, member_ids, readable)`; `site_living_members(site_key)`
answers `SiteLivingMembers(site_key, site, state, cleared_at_tick, members,
reason)`. Both are pure reads. The recovery slice consumes the record keys and
these reads; it must keep first population and matured recovery clock-owned.

## Selection and manual exceptions

`world.maps.regional_population.sample_composition_counts` is the shared pure
sampler: it enumerates the composition's inclusive count vectors inside a
budget and picks one through the existing SHA-256 draw stream under the distinct
`site_counts` purpose. A site occurrence is identified by its saved seed, site
key, and generation sequence only, so replaying the same occurrence reproduces
the same complete group after a retry at any in-game tick.

`monster_sites._populate` constructs every sampled row with its own identity
and stored resources and registers each through
`register_explicit_individual`, the population owner's explicit-placement
operation. That operation validates the shared wilderness surface while
applying no automatic settlement buffer, zone/cell density, or wave budget:
explicit manual placement is a lawful exception that ordinary maintenance
neither fills, caps, nor culls. A mixed group, a same-variant group, and a
solitary stray therefore all place exactly their authored rows.

## Assertion roles and requirement hand-off

The change's delta contains a REMOVED requirement
(`monster-site-placement::placement-honors-capacity-and-determinism`) and three
ADDED/MODIFIED requirements. The retired requirement's two annotations were
deleted rather than re-pointed, so the checkout-local
`tools.spec_traceability check` necessarily reports that removed requirement as
uncovered until the archive sync; it reports `0 errors` and no other gap. This
is the documented pre-sync state (`docs/development/spec-test-traceability.md`,
the `actual-live-population-view` precedent). No generated ID is fabricated.

New tests carry no `covers_requirement` annotation because the ADDED delta
requirement IDs exist only after the sync. Their hand-off:

| Test | Role / defect detected | Delta requirement and scenario |
| --- | --- | --- |
| `MonsterSiteLifecycleTests.test_a_mixed_composition_places_each_row_with_its_own_identity_and_resources` | synthetic mechanism: a mixed A+A+B group constructs three distinct IDs with independent stored HP and records them as the site's member IDs | `monster-site-placement` ADDED "Placement samples complete deterministic occurrences" / "Selection stays inside the authored variant set" |
| `MonsterSiteLifecycleTests.test_a_solitary_stray_places_exactly_one_individual` | synthetic mechanism: the `stray` kind places one authored row | ADDED / "Selection stays inside the authored variant set" |
| `MonsterSiteLifecycleTests.test_the_saved_occurrence_reproduces_its_group_and_ignores_the_retry_tick` | synthetic mechanism: the sampler reads its seed; an interrupted first population replays the same group at a later tick | ADDED / "Same saved occurrence, same composition" and "Selection uses persisted occurrence inputs" |
| `MonsterSiteLifecycleTests.test_a_living_absent_member_prevents_false_clearing` | synthetic mechanism: an unregistered, unlocated living member keeps the site populated | ADDED / "Missing presence is not clearing" |
| `MonsterSiteLifecycleTests.test_an_unchanged_site_pass_keeps_its_identities_and_resources` | synthetic mechanism: a repeat pass is a no-op | ADDED / "Capacity is a ceiling, not a reshuffle" |
| `MonsterSiteLifecycleTests.test_a_foreign_marked_individual_is_never_adopted_or_replaced` | synthetic mechanism: a marked row outside `member_ids` is untouched | MODIFIED "Every placed individual carries its owner marker..." / "All foreign owners are protected" |
| `MonsterSiteLifecycleTests.test_a_one_shot_site_is_never_refilled_by_a_regional_deficit_wave` | real owner integration: a genuine regional deficit wave births ambient individuals and leaves the cleared site empty | ADDED / "Manual exceptions"; existing "One-shot sites stay cleared..." |
| `MonsterSiteLifecycleTests.test_an_explicit_site_inside_a_settlement_ring_survives_maintenance` | real geometry + owner: an excluded-but-valid cell hosts the explicit site while ordinary birth geometry admits none; ambient reconciliation leaves it untouched | ADDED / "Manual exceptions" |
| `MonsterSiteLifecycleTests.test_manual_excess_counts_against_ordinary_ceilings_without_culling` | real owner: site individuals count locally and the wave is blocked without changes | ADDED / "Manual exceptions" and "Capacity is a ceiling, not a reshuffle" |
| `MonsterSiteLifecycleTests.test_an_unreadable_record_answers_a_named_verdict_and_refuses_work` | synthetic mechanism: corrupt member IDs answer `state_unreadable` and refuse lifecycle work without writes | ADDED / "Selection uses persisted occurrence inputs" (save integrity) |
| `MonsterSiteLifecycleTests.test_an_incomplete_saved_record_refuses_instead_of_repopulating` | synthetic mechanism: a pre-identity record refuses instead of being reinterpreted | ADDED / "Selection uses persisted occurrence inputs" |
| `MonsterSiteWithoutWorldSeedTests.test_first_population_refuses_without_an_explicit_world_seed` | synthetic mechanism: no implicit seed default | ADDED / "Selection uses persisted occurrence inputs" |
| `MonsterSiteLifecycleTests.test_a_direct_recovery_advances_the_sequence_with_fresh_identities` | real owner: a variable-range site recovers with new IDs at sequence + 1 and keeps its seed | existing "One-shot sites stay cleared..." / "A recoverable camp recovers at its in-game condition with fresh identities" |
| `MonsterSiteLifecycleTests.test_a_failed_direct_recovery_after_a_registration_restores_everything` | fault injection after a real registration: the direct recovery entry point restores state, coordinates and caches, emits no success, and its retry completes the group | ADDED / "Selection uses persisted occurrence inputs" (retry repeats the failed selection) |
| `MonsterSiteLifecycleTests.test_a_failed_state_write_restores_the_cleared_record` | fault injection after the state write: the cleared record and registrations are restored | ADDED / "Selection uses persisted occurrence inputs" |
| `MonsterSiteCandidatePublicationTests.test_an_unwalkable_site_surface_is_rejected_before_publication` / `…test_a_settlement_footprint_site_surface_is_rejected` / `…test_a_site_on_another_region_is_rejected` / `…test_a_lawful_manual_site_still_publishes` | candidate publication: site surfaces are validated against the candidate terrain and footprints, reject before publication, and a lawful site still publishes | MODIFIED "Ambient and site placement are frozen keyed lore data validated at construction" / "Sites are frozen values with the authored fields" |
| `SiteClearOutAcceptanceTests.test_a_binding_survives_the_site_clearing_without_generating_members` | real quest acceptance: the bound IDs survive the clear and later reads create nothing | existing "A site's living individuals are the quest layer's binding source..." / "A cleared site offers no targets and stays cleared" |
| `PlacementValidationTests.test_a_site_names_one_known_complete_composition` | registry contract: empty/unknown composition rejects at construction | MODIFIED "Ambient and site placement are frozen keyed lore data validated at construction" / "Sites are frozen values with the authored fields" |
| `PlacementValidationTests.test_every_legal_composition_outcome_must_fit_the_site_capacity` | registry contract: minimum fits, maximum exceeds, so capacity is the ceiling of every outcome | MODIFIED / "Sites are frozen values with the authored fields" |
| `PlacementValidationTests.test_explicit_site_kinds_admit_solitary_and_mixed_placements` | registry contract: `stray`/`encounter` accepted, `lair` rejected | MODIFIED / "Sites are frozen values with the authored fields" |

## Verification evidence (this change)

Run from the worktree root with the single-token environment file
(`/tmp/mud-population-test.env` containing `MUD_TEST_SETTINGS=1`):

| Command label | Result |
| --- | --- |
| `world.lore.tests.test_monster_placement world.lore.tests.test_registry_index_contract` | 64 tests, OK |
| `world.maps.tests.test_monster_sites` | 35 tests, OK |
| `world.maps.tests.test_geography_source` | 18 tests, OK |
| `world.quests.tests.test_site_clear_out_acceptance` | 20 tests, OK |
| `world.maps.tests.test_monster_provisioning` | 15 tests, OK |
| `world.quests.tests.test_definitions` | 46 tests, OK |
| `world.quests.tests.test_compile_registration.SiteClearOutPayloadTests` | 3 tests, OK |
| `world.quests.tests.test_hunt_catalog_content` | 22 tests, OK |
| `world.maps.tests.test_wilderness_population.WildernessPopulationViewTests` | 10 tests, OK |
| `world.tests.test_synthetic_data` | 27 tests, OK |
| `web.gm.tests.test_reader_monsters` | 12 tests, OK |

`python -m tools.observability_lint check` → `violations=0`. `openspec validate
manual-monster-compositions --strict` → valid. `content/map-reference-context.json`
was regenerated (`python -m tools.map_reference_context`) because the site
declaration shape changed, and its check reports up to date. `python -m
tools.contract_gate` passes reference-context, observability, test-data,
manifests, and the contract suite; its traceability gate reports the single
removed requirement described above and is expected to stay red until the
archive sync. The full `world.quests.tests.test_compile_registration` module was
also run: four pre-existing rollback tests
(`RegisterGeneratedQuestTests.test_conflicting_offer_rolls_back_the_definition_write`,
`…test_definition_new_plus_offer_conflicting_leaves_both_registries_unchanged`,
`SceneRequirementRegistryTests.test_conflicting_offer_rollback_leaves_no_requirement_entry`,
`PrivateCommissionRegistrationTests.test_a_conflicting_private_issuance_rolls_back_the_definition`)
reach the durable store through an unpatched rollback call in a module with no
database test class and fail with `no such table: django_content_type`; they do
not touch this change's code and are unrelated.

# Regional hunt supply cutover

Developer document for the OpenSpec change `regional-hunt-supply-cutover` of the
regional monster population programme. It records the supply contract, the
removed provisioning path, the habitat-guidance boundary, the assertion-role
ledger and the focused evidence for this slice.

## Supply contract

`world/quests/definitions.py` owns the read-only supply surface:

```python
HUNT_SUPPLY_ECOLOGY_ZONE = "ecology_zone"
HUNT_SUPPLY_MONSTER_SITE = "monster_site"

@dataclass(frozen=True, slots=True)
class HuntSupplySource:
    kind: str
    key: str
    region_key: str
    variant_keys: tuple[str, ...]

def hunt_supply_sources(
    region_key: str, species_key: str, countable_variant_keys: tuple[str, ...]
) -> tuple[HuntSupplySource, ...]
```

Sources are only the immutable ecology composition pools (`EcologyZone.pool` →
`EncounterComposition.members`) and the explicit monster-site compositions whose
parent region matches. A source qualifies when its authored compositions place
at least one requested, species-owned variant and that intersection includes an
ordinary baseline variant. The intersection becomes `variant_keys`; zones are
returned by key and then sites by key, so the order is deterministic. Current
living quantity, habitat tags, art keys and prose never participate.

`_validate_hunt_selector` rejects a definition when no source resolves, so a
hunt is never advertised for a species the region cannot lawfully supply.
Quantity is not compared with any cell, site or wave capacity: completion may
span encounters and recovery waves.

## Acceptance and the removed provisioning path

`world/quests/runtime.py::accept_quest` still owns issuance, rank-external
eligibility, duplicate-active refusal, deterministic `quest_id`, deadline
conversion and quest-log atomicity. It no longer snapshots, creates, moves or
restores population state for a regional hunt: an undersupplied hunt (including
zero living targets) commits a normal active record and writes nothing else.
`world/rules/guild_offers.py::accept_guild_offer` and
`world/rules/npc_intents.py::_apply_offer_quest` retain their quest-log and
relations cache compensation but no provisioning snapshot.

Deleted outright: `world/maps/monster_provisioning.py` (ensure/snapshot/restore
API and the `hunt_targets_provisioned` / `hunt_targets_unavailable` events), its
test module and shard label, and the runtime helpers `_stage_zero_hunt`,
`provisioning_snapshot_for`, `restore_provisioning` and
`_provision_hunt_targets`. `QuestTargetsUnavailable` now documents only the
bound-site refusal. `ordinary_countable_variant_keys` was removed with its last
caller; ordinary-variant validation remains inside `_validate_hunt_selector`.
`docs/superpowers/specs/2026-09-02-observability-logging-design.md` drops the two
provisioning event rows; the site binding events remain.

## Habitat guidance

`web/webclient/presentation/map_quest_destinations.py` adds the closed
`DestinationEvidence` vocabulary (`habitat`, `entity`, `location`) as a required
`QuestDestination.destination_kind`. ANCHOR, GRID, bound-instance and authored
site positions are `LOCATION`; a regional hunt is `HABITAT`. `ENTITY` is
reserved for a future destination whose position is supplied by surviving target
identities; no current family claims that evidence.

A regional hunt resolves to the nearest legal cell among its lawful sources,
using the shared `nearest_region_cell` order (squared distance, then x, then y)
and the union bounds of the source cells. Ecology-zone cells come from
`world.maps.population_geometry.eligible_birth_cells`, so parent-region,
wilderness-validity and inhabited-settlement-buffer exclusions are applied;
explicit site cells are lawful manual exceptions to those buffers. No living
monster is read and no topology is disclosed. The area and world maps keep their
existing quest-marker wire shape (`node` / `bearing`), so an empty habitat stays
a guidance marker and never becomes an entity observation. The browser payload
gains no field.

## Caller and contract dispositions

- `world/quests/catalog.py`: comments now describe source legality, no
  single-cell supply cap, and the introductory hunt's removal of any gate-local
  supply promise. Definition keys, objectives, ranks, prose and rewards are
  unchanged.
- `docs/game/commands.md` and `docs/game/command-reference.md`: `guild list`
  states that only legally unacceptable offers are omitted, that an undersupplied
  regional hunt stays listed, and that acceptance promises neither an immediate
  target nor completion before the deadline.
- `docs/superpowers/specs/2026-10-05-monster-data-model-design.md` §6 regional
  hunt text and §8 acceptance evidence were amended; the superseded
  proposal-delivery wording is marked historical.
- The capital hunting band in `world/maps/wilderness_population.py` and its
  main-spec requirement remain intentionally owned by
  `regional-population-runtime-cutover` (programme design §14), together with the
  legacy ambient-rule generation paths. This slice removes only the quest-side
  contracts that relied on a guaranteed immediate target.

## Assertion-role ledger

| Retired assertion | Prior role | Substantive replacement |
| --- | --- | --- |
| `test_hunt_catalog_content.RegionalHuntProvisionabilityTests.*` (ambient rule exists, quantity ≤ min(quantity, capacity), one hunt per placed species) | data contract for acceptance-time provisionability | `RegionalHuntSupplySourceTests` (lawful source resolves, sourced variants cover the selector, one advertisement per region/species) plus the synthetic wide-quantity registration test |
| `test_species_hunt_acceptance.test_a_shortfall_is_provisioned_and_the_record_commits` | provisioning creates the shortfall on acceptance | `test_an_undersupplied_hunt_accepts_without_creating_a_target` and `test_a_hunt_wider_than_one_cell_accepts_without_generating_members` |
| `…test_an_illegal_hunt_is_refused_with_no_partial_state` | acceptance-time named refusal | `test_a_species_with_no_authored_source_is_rejected_at_publication` (refusal moved to publication) |
| `…test_a_provisioned_target_waits_on_a_walkable_cell_of_the_region` | provisioning placement legality | `test_map_quest_destinations.test_habitat_guidance_skips_geometry_excluded_cells` (guidance legality) |
| `…test_a_post_provisioning_write_failure_rolls_back_everything` | rollback of provisioned individuals | `test_the_board_rolls_back_the_record_when_the_affinity_write_fails` and the retained cached-log restore test; no population surface is written to roll back |
| `world.maps.tests.test_monster_provisioning.*` | owner-level provisioning guarantee | acceptance/population-state assertions in `test_species_hunt_acceptance`; the module is deleted |

Delta requirements carry no canonical identifier until the archive sync puts
them into `openspec/specs/`; the tests below therefore ran unannotated during
the slice. The archive step attached the tool-generated post-sync identifiers
recorded here. Two judgments went beyond the hand-off list:
`test_each_region_species_pair_is_advertised_once` was left unannotated because
its single assertion (distinct region/species pairs) establishes no clause of
either replacement requirement, and `test_a_definition_that_is_not_a_clear_out_is_always_available`
lost its retired identifier without a replacement because it exercises only the
availability predicate and accepts nothing. Every other site was re-mounted
one by one onto the scenario its assertions establish:

| Test | Delta requirement and scenario |
| --- | --- |
| `world.quests.tests.test_species_hunt_acceptance.HuntAcceptanceTests.test_an_undersupplied_hunt_accepts_without_creating_a_target` | quest-lifecycle ADDED "Quest acceptance persists validated records without ordinary provisioning" — "Undersupplied hunt accepts without birth" |
| `…test_a_hunt_wider_than_one_cell_accepts_without_generating_members` | quest-lifecycle ADDED (same requirement) — "Undersupplied hunt accepts without birth"; quest-blueprint ADDED "Published regional hunts require lawful authored sources" — "Quantity spans encounters" |
| `…test_an_undersupplied_hunt_still_resolves_habitat_guidance` | no delta requirement: design-only "Guidance and introductory cutover" (owner-backed habitat guidance after an empty acceptance); its population-state assertions also support quest-lifecycle ADDED — "Undersupplied hunt accepts without birth" |
| `…test_a_species_with_no_authored_source_is_rejected_at_publication` | quest-blueprint ADDED — "No lawful source" |
| `…test_the_board_accepts_an_undersupplied_hunt_without_targets` | guild-quest-board MODIFIED "Board acceptance and abandonment delegate to quest lifecycle" — "Regional shortage is not a board refusal" |
| `…test_the_board_rolls_back_the_record_when_the_affinity_write_fails` | guild-quest-board MODIFIED — "A failed acceptance restores every surface" |
| `…test_no_provisioning_module_or_helper_survives` | quest-lifecycle ADDED — "Undersupplied hunt accepts without birth" (registration does not invoke provisioning) |
| `world.quests.tests.test_definitions.SpeciesHuntDefinitionTests.test_hunt_supply_sources_resolve_authored_zone_and_site_sources` | quest-blueprint ADDED — "No lawful source" |
| `…test_hunt_supply_sources_require_a_matching_region_and_ordinary_variant` | quest-blueprint ADDED — "No lawful source" |
| `…test_a_hunt_whose_species_has_no_authored_source_is_rejected` | quest-blueprint ADDED — "No lawful source" |
| `…test_a_hunt_wider_than_one_cell_still_registers` | quest-blueprint ADDED — "Quantity spans encounters" |
| `world.quests.tests.test_hunt_catalog_content.RegionalHuntSupplySourceTests.test_every_published_hunt_names_a_lawful_authored_source` | quest-blueprint ADDED — "No lawful source" |
| `…test_selected_variants_come_from_the_hunts_own_sources` | quest-blueprint ADDED — "No lawful source" |
| `…test_each_region_species_pair_is_advertised_once` | quest-blueprint ADDED — "No lawful source" (no duplicate advertisement) |
| `web.webclient.presentation.tests.test_map_quest_destinations.ResolveRecordDestinationTests.test_habitat_guidance_skips_geometry_excluded_cells` | no delta requirement: design-only "Guidance and introductory cutover" (habitat cells must be lawful authored habitat) |
| `web.webclient.presentation.tests.test_area_map.GridAreaTests.test_a_habitat_destination_is_guidance_not_an_entity` | no delta requirement: design-only "Guidance and introductory cutover" (habitat destination, not a live observation) |

## Verification evidence (this change)

Run from the worktree root with the single-token environment file
(`/tmp/mud-population-test.env` containing `MUD_TEST_SETTINGS=1`):

| Command label | Result |
| --- | --- |
| `world.quests.tests.test_definitions.SpeciesHuntDefinitionTests` | 14 tests, OK |
| `world.quests.tests.test_compile_registration.SpeciesHuntPayloadTests` | 2 tests, OK |
| `world.quests.tests.test_planner.SpeciesHuntPlannerTests` | 7 tests, OK |
| `commands.tests.test_guild_economy_commands.SpeciesHuntBoardCommandTests` | 2 tests, OK |
| `world.quests.tests.test_species_hunt_acceptance` | 8 tests, OK |
| `world.quests.tests.test_hunt_catalog_content` | 19 tests, OK |
| `web.webclient.presentation.tests.test_map_quest_destinations` | 19 tests, OK |
| `web.webclient.presentation.tests.test_area_map.GridAreaTests` | 6 tests, OK |
| `world.maps.tests.test_wilderness_geography_contract.BorderRiverContractTests.test_region_consumers_follow_the_amended_boundaries` | 1 test, OK |
| `world.rules.tests.test_npc_intents.test_offer_quest_intents` | 26 tests, OK |
| `tests.test_command_docs` | 33 tests, OK |

`python -m tools.observability_lint check` → `scanned=823 frozen=0
violations=0 exemptions=375`. `python -m tools.test_data_lint check` →
`violations=0`. `openspec validate regional-hunt-supply-cutover --strict` →
valid. `content/map-reference-context.json` was regenerated because the quest
module source hashes changed. `python -m tools.contract_gate` passes
reference-context, observability, test-data, manifests and the contract suite.
Its traceability step reports exactly one uncovered identifier with 0 errors —
`quest-blueprint::published-regional-species-hunts-are-legally-provisionable-in-their-authored-region`, which this delta removes — and stays red until the archive
sync, following the archived `manual-monster-compositions` precedent. No retired
or unrelated annotation was re-pointed.

# Delayed regional recovery and the merged population lifecycle

Developer document for the `regional-population-recovery` change. It extends the
persistent owner with the chronological presence evidence, delayed recovery
episodes, encounter protection and one merged clock coordinator. Zone and site
authored rows remain the balance authority; nothing here duplicates their
numbers, and tests use file-local synthetic zones.

## Durable shapes

`wilderness.db.population_timeline` is a whole-value JSON-safe mapping with
exactly `settled_through_tick`, `transitions` and `protection`. The explicit
seed initialization (`initialize_population_seed`) is the only creator of the
empty value; any other missing, unknown-keyed, or structurally incomplete value
is the owner's named `malformed_state` refusal, never a best-effort
reconstruction.

- `PopulationPosition(wilderness, x, y)` is the actual coordinate registration,
  never a pooled room identity.
- `PopulationPresence(alive, position, home_zone, site_key)` carries the
  complete fact. A dead individual has no position; a living unregistered one
  may have none. All four keys are required on read.
- `PopulationTransition(source_id, individual_id, occurred_tick, before,
  after)` is one committed presence change. `record_population_transition`
  deduplicates by `(source_id, individual_id)` while pending.
- `PopulationProtection(engagement_id, cell, start_tick, end_tick)` is an
  inclusive closed interval, or an open interval (`end_tick = None`) while the
  session is active. An end before its start refuses.

`record_population_transition` does nothing when the world has no explicit
population seed (the population system is not provisioned there); a seeded
world with a missing or malformed timeline refuses by name.

## Projection and accounting

`presence_at(wilderness, at_tick=…)` starts from the actual living state and
reverses every still-pending transition whose occurrence is later than `tick`,
in reverse chronological, stable source/individual order, using the complete
before facts. A deleted individual is restored for accounting only: no row is
recreated and no public presence is fabricated. `population_counts(…,
at_tick=…)` derives the local, home-owned and per-cell measures from that
projection, so a future loss never borrows headroom and a home-owned member
lost outside its zone still consumes its home ceiling.

`initialize_zone` already starts one wave loop; when it stops below the lower
bound it now establishes the zone's first delayed episode at its initialization
tick.

## Recovery episodes

`note_population_boundary(wilderness, zone, tick)` is the episode edge:

- below the lower bound with no due time → `due = tick + recovery_delay`;
- below with a pending due → unchanged (a further loss never restarts it);
- at or above the lower bound → the episode is cleared with no birth, draw or
  generation-sequence change.

`settle_recovery_due(wilderness, zone, tick)` acts only at or after the due
tick. It recomputes the living population first and cancels when the lower
bound is reached. Otherwise it commits exactly one planned complete composition
(the existing plan model: one composition, limited by local upper bound, home
upper bound, cell capacity and wave budget) and sets the next due to
`tick + replenishment_interval` while still deficient, or clears it. A lawful
blockage (no legal space, protected cells, home saturation) creates nothing,
leaves the generation sequence untouched, emits one bounded
`monster_population_recovery_blocked` reason event on the outer commit, and
retries at the next interval. Over-shooting the lower bound is lawful.

## Merged chronological coordinator

`world/maps/population_lifecycle.py` installs one coordinator under the existing
`monster_site_lifecycle` stage kind. Per selected boundary it:

1. establishes or cancels each zone's episode (zone-key order);
2. settles the site owner's create/clear/recover decisions (site-key order), so
   same-tick explicit site births precede ordinary births;
3. re-evaluates every zone's episode from the post-site counts, so a same-tick
   site birth cancels a pending due instead of leaving it to fire later;
4. settles each due regional wave (zone-key order);
5. consumes the applied transitions (`retain` keeps a deferred site clear's
   loss evidence) and retires passed protection.

Selected boundaries merge pending transitions, site boundaries, recovery due
times and closed-protection end ticks. The interval is processed through
`end_tick` (inclusive) and progress is persisted at the endpoint whether or not
a boundary fell there, so equal elapsed time leaves equal due/sequence state and
equal retirement. The pure `next_population_lifecycle_boundary` shares this
planning and also projects an episode the settlement would establish from a
loss already recorded at the interval start; it writes nothing and consumes no
randomness. Any transitions or boundaries created inside settlement are picked
up by the next boundary selection.

`next_site_boundary` / `settle_monster_sites_at` are the site owner's pure and
at-tick operations. A populated site's clear boundary is the committed loss
occurrence of its last own member (never the interval end and never mere
absence); while a persisted session still references the dead members the clear
is deferred and the loss evidence is retained so the later clear keeps the true
tick. An uninitialized site's creation boundary and a passed recovery due are
re-evaluated at the interval start. Site creation and recovery are deferred
while their coordinate is protected at the evaluated tick and retry on the
first unprotected tick. `settle_monster_sites(start, end)` remains only as the
site owner's chronological interval composition for its own tests; it is not
registered as a stage and has no production caller.

## Combat occurrence and protection

`CombatSessionRecord` stores required `started_tick` and `population_cell`
(`{wilderness, x, y}`, or `None` for staged nonwilderness combat); strict
storage refuses a record without them and there is no current-tick or
current-room fallback. Builders set them from the actual engagement: hostile
engagements from the player's real wilderness cell, guild exams from their own
start tick with no cell. Candidate previews carry the same fields and write
nothing else.

`_finalize_resolved_round` records each newly defeated enemy `Monster` inside
the round transaction at `started_tick + completed_round * round_seconds`
(six seconds per round from the combat rulebook), once per
engagement/round/individual. Knockouts, flees, absent members, simulated exams
and a replayed committed round record nothing.

Every lawful session clear — terminal settlement, operator deletion of a
participant, or startup restoration of a committed receipt — retains the
session's exact cell and closed interval before the record disappears
(`clear_session` owns the copy; the settlement's own call is deduplicated).
Map births consult the durable timeline plus currently active strict sessions;
an active session protects its cell from `started_tick`, and a closed interval
blocks births through its inclusive endpoint.

## Caller integrations

`world/maps/gm.py::delete_entity` captures the complete pre-removal presence
before deletion and records the removal with the actual tick, with the
population surfaces in its compensation. `world/rules/gm.py` records only a
real live/dead Monster HP crossing (explicit restoration included) and restores
the owner surfaces on failure. `world/rules/movement_settlement.py::
settle_relocation` records the exact old/new presence of a relocated Monster,
retaining its home ownership. Quest scene and site placements arrive through
`register_explicit_individual`, which records the arrival. An out-of-round
action/upkeep commit records a real crossing once at its current tick; a round
provenance owns its own occurrence and abstract encounters notify nothing.

## Deviations recorded for review

- A site's clear boundary uses the committed loss tick, not the interval end;
  existing tests were updated to that contract, and a raw HP edit without
  recorded evidence clears at the interval start it was observed at.
- Site births are recorded as timeline arrivals through the explicit-placement
  operation, so historical projection can tell that they did not stand earlier.
- The coordinator is implemented and exercised but its **production
  registration is intentionally deferred** to `regional-population-runtime-
  cutover`, per design.md. Startup therefore registers no population stage in
  this slice.

## Assertion roles and requirement hand-off

The archive sync assigned these canonical IDs. Every behavioural test below
carries `covers_requirement` for the requirement its own assertions establish;
the annotations were verified against the assertions, not the scenario names.

| Requirement | Canonical ID |
| --- | --- |
| Deficits recover only through delayed game-time episodes | `regional-population::deficits-recover-only-through-delayed-game-time-episodes` |
| Loss timing and encounter protection survive deferred combat settlement | `regional-population::loss-timing-and-encounter-protection-survive-deferred-combat-settlement` |
| Population lifecycle replays loss and site boundaries chronologically | `regional-population::population-lifecycle-replays-loss-and-site-boundaries-chronologically` |
| Historical population evidence preserves removed ownership and cell protection | `regional-population::historical-population-evidence-preserves-removed-ownership-and-cell-protection` |

All tests live in `world/maps/tests/test_regional_population_recovery.py`.
`D` = delayed episodes, `L` = loss timing and protection, `C` = chronological
lifecycle, `H` = historical evidence.

| Test | Requirement | Asserted mechanism |
| --- | --- | --- |
| `RecoveryLifecycleTests.test_a_loss_only_schedules_one_delayed_due_and_never_births_early` | D | one due at T+delay; no birth before it; the wave restores the band |
| `…test_consecutive_waves_keep_the_budget_and_recover_eventually` | D | budgeted waves at positive authored intervals until recovered |
| `…test_a_manual_restoration_cancels_without_a_birth_or_sequence_change` | D | cancellation leaves no birth, draw or sequence change |
| `…test_an_operator_hp_restoration_cancels_through_the_real_gm_route` | D | the real GM HP route restores density and clears the episode |
| `…test_equal_clock_advances_agree_under_any_partition` | D | equal elapsed time gives identical plans, sequence and due |
| `…test_settlement_progress_agrees_under_partition` | D | settled-through progress agrees under partition |
| `…test_the_pure_boundary_projects_an_unpersisted_episode` | D | the pending episode is projected without executing a writer |
| `…test_reads_re_entry_and_acceptance_never_birth` | D | reads, room preparation and hunt acceptance neither birth nor reset the due |
| `…test_a_later_combat_occurrence_is_never_earlier_birth_headroom` | L, H | the future loss is not headroom at 110; the 118 boundary starts due 128 and the removed member is still accounted |
| `…test_a_round_defeat_is_recorded_at_its_round_offset` | L | occurrence tick is start + completed rounds; replay adds nothing |
| `RealSessionRecoveryTests.test_a_real_session_persists_its_occurrence_and_protection` | L | a real session persists start/cell and protects its closed interval after the clear |
| `…test_a_late_terminal_failure_rolls_back_the_wave_and_keeps_the_session` | L | a later-stage failure rolls back clock, wave, due and session together |
| `…test_a_terminal_mapped_session_protects_its_closed_interval` | L, H | the closed interval is protected and survives a reload |
| `…test_a_lawful_clear_still_retains_the_closed_protection` | L | a lawful clear keeps the closed protection |
| `…test_a_protected_cell_blocks_the_due_wave_and_retries_next_interval` | L | a protected due births nothing and retries one positive interval later |
| `…test_a_protected_cell_defers_site_births_until_it_passes` | L | the site route honours the same protection |
| `…test_a_later_loss_after_a_restored_wave_starts_a_new_due` | C | a later loss after a restored wave creates its own due |
| `…test_a_same_tick_site_birth_cancels_the_pending_episode` | C | the same-tick site birth cancels the pending episode under any partition |
| `…test_a_later_site_recovery_never_consumes_the_earlier_wave` | C | the later site recovery cannot consume the earlier wave's headroom |
| `…test_a_deferred_site_clear_keeps_the_loss_occurrence` | H | the committed loss tick survives the deferred clear |
| `…test_a_deleted_home_member_still_counts_before_its_loss` | H | deleted home ownership still counts before its loss; distinct IDs stay separate |
| `…test_operator_spawn_and_delete_are_counted_presence_evidence` | H | a GM spawn/delete commits actual registration and a complete transition |
| `…test_an_operator_departure_keeps_home_ownership_and_schedules` | H | a lawful departure keeps home ownership and schedules the deficit |
| `…test_incomplete_timeline_evidence_refuses` | H | incomplete or inverted serialized evidence refuses |

Two dispositions from that audit:

- `…test_reads_re_entry_and_acceptance_never_birth` is annotated for `D` only.
  Its assertions establish "no read, view, re-entry or acceptance trigger";
  they say nothing about evidence retention, so the earlier draft hand-off that
  also named `H` there was dropped rather than kept for the gate.
- Loss timing's nondeath half (a flee, absence or knockout is not a defeat) is
  enforced by `_record_round_defeats`'s live-to-dead crossing test but has no
  dedicated assertion; the same apply-run gap covers the mapped action-commit
  route in `world/rules/action/transaction.py`, which no focused test drives.

## Verification evidence (this change)

Focused runs, each independently, from the worktree root with the single-token
environment file `/tmp/mud-population-test.env` (`MUD_TEST_SETTINGS=1`):

| Label | Result |
| --- | --- |
| `world.maps.tests.test_regional_population_recovery` | 24 tests, OK |
| `world.maps.tests.test_regional_population` | 25 tests, OK |
| `world.maps.tests.test_monster_sites` | 35 tests, OK |
| `world.maps.tests.test_monster_provisioning` | 15 tests, OK |
| `world.maps.tests.test_wilderness_population` | 33 tests, OK |
| `world.maps.tests.test_gm` | 8 tests, OK |
| `world.quests.tests.test_site_clear_out_acceptance` | 20 tests, OK |
| `world.rules.tests.test_movement_settlement` | 18 tests, OK |
| `world.rules.tests.test_combat_session_persistence` | 37 tests, OK |
| `world.rules.tests.test_art_view` | 15 tests, OK |
| `web.webclient.presentation.tests.test_creation_panel.test_presenter` | 14 tests, OK |

`python -m tools.observability_lint check` → `violations=0`. Three
`world.rules.tests.test_clock` errors/failure (unloaded settlement maps) and two
`test_action_pipeline_atomicity` errors reproduce identically on master and are
not caused by this change.

## Runtime cutover: activation, deletion boundary and operations

`server/conf/at_server_startstop.py` registers
`world.maps.population_lifecycle.register_regional_population()` as the
`monster_site_lifecycle` stage before `restore_persisted_sessions()`. The
coordinator merges exact-tick site lifecycle, pending presence transitions and
regional recovery due times; no wall timer owns a population boundary and no
second whole-interval regional stage exists.

`world/maps/bootstrap.py::sync_wilderness` distinguishes a genuinely new
wilderness script from a preexisting one:

- **Fresh world.** One compensated transaction creates the script, writes the
  configured `INITIAL_POPULATION_SEED` through `initialize_population_seed`,
  then calls `initialize_zone` for every authored zone in stable-key order.
  A later-zone failure restores earlier individuals and every owner/cache
  surface; retrying the same provisioning is safe.
- **Preexisting world.** The script is never re-seeded, rerolled, converted or
  reset. It must already carry the seed and a complete record for every
  authored zone. Missing or malformed state raises the named
  `population_state_uninitialized` operator refusal. Repeated startup, source
  reread, room preparation and player arrival create nothing and preserve
  living IDs and resources.

Incompatible development state is handled only by an explicit operator action:
save the world if it must be kept, then repair it through the GM console, or
delete the disposable development database and re-provision from scratch.
Startup never mutates, fills or converts an incompatible world.

### Deleted legacy path

`world/maps/wilderness_population.py` now contains only the actual read
projection (`population_view`, `PopulationFact`, `threat_label`, `_stored_hp`)
and the explicit population-marker departure primitive still used by
`defeat-aftermath-core`. Removed with every caller: `MonsterPopulation`,
`population_for_coordinates`, region tier/density tables, tier visual rows,
capital entry accessor, hunting band, coordinate hash/slot identity,
`ExpectedSlot`/`PopulationDecision`, `ambient_population_decision`,
`ambient_observation_key`, `ambient_slots_in_use`, `_population_key`, `_spawn`,
`_spawn_species_individual`, `ensure_population`, conformance helpers, the
`AmbientPlacementRule` registry/declarations/`ambient_rule`, the provider's
room-entry reconciliation, the synthetic-kit ambient fixtures, and the
test-only `settle_monster_sites(start, end)` interval replay.

`world.lore.monster_placement` keeps the species/variant, site, composition,
ecology-zone and settlement-policy registries. `settlement-stage-order`'s
stale provenance sentence is corrected by a MODIFIED delta in this change;
the `wilderness-monster-population` and `wilderness-population-view` Purpose
texts are amended in place during implementation.

### Assertion-role cutover ledger

Retired requirement IDs disappear at archive sync. Rows name the delta
requirement or, for ADDED contracts, the scenario; no canonical ID is
fabricated.

| Retired requirement | Retired test / role | Replacement or disposition |
| --- | --- | --- |
| `population_for_coordinates` is a pure, deterministic function over the bounded map | `test_wilderness_population.TerrainPopulationModelTests.*` — synthetic mechanism | Deleted with the model. No replacement: the coordinate-slot decision no longer exists. |
| A hunting band around the capital's north gate always hosts a low-tier monster | `TerrainPopulationModelTests.test_hunting_band_is_contiguous_low_tier` — synthetic mechanism | Deleted. The guarantee is retired; no replacement guarantee. |
| `ensure_population` idempotently places and respawns monsters at a coordinate | `WildernessPopulationSpawnTests.*` — representative integration | Deleted. Fresh-world constrained births are covered by `WildernessBootstrapTests.test_fresh_wilderness_provisioning_initializes_population_once` (bootstrap fresh/repeat) and the retained smoke (births + reload). |
| Ambient species reconciliation | `test_wilderness_population_species.AmbientSpeciesReconciliationTests.*` — synthetic mechanism | Module deleted. Actual-member projection is covered by `WildernessPopulationViewTests`; ordinary births/recovery by `test_regional_population*` and `test_monster_sites`. |
| `Population reconciliation never destroys an active-session participant` | `StartupSessionRestoreOrderTests.*` — representative integration | Contract replaced by `Active encounters retain protected individuals and cells`. Covered by `world.maps.tests.test_regional_population_recovery.RealSessionRecoveryTests` and the session-protection tests there. |
| Capital introductory hunt immediate supply | `OnboardingHuntIntegrationTests` — representative integration | Deleted. Undersupplied acceptance is owned by the quest slice; site acceptance remains covered by `world.quests.tests.test_site_clear_out_acceptance`. |
| Defeat departure followed by immediate respawn | `WildernessDepartureTests.test_population_winner_despawns_at_defeat_settlement` tail | Tail deleted; departure/registration assertions remain. Respawn is retired; delayed recovery is covered by the recovery module and the smoke. |
| Site and ambient owners never cross domains | `MonsterSiteLifecycleTests.test_the_two_owners_never_cross_domains` — synthetic mechanism | Reworked as `test_site_settlement_never_touches_a_foreign_individual` (same requirement, foreign-owner control). |

No new test carries a `covers_requirement` annotation for an ADDED delta
requirement; those IDs do not exist until archive sync. Hand-off list:

- `test_fresh_wilderness_provisioning_initializes_population_once` — ADDED
  `Runtime population uses authored regions without implicit fallback`,
  scenario `Fresh world and reuse`.
- `test_preexisting_world_without_population_state_refuses` — ADDED
  `Runtime population uses authored regions without implicit fallback`,
  scenario `Unconfigured and incompatible world`.
- `test_a_later_zone_failure_rolls_back_the_fresh_provisioning` — ADDED
  `Runtime population uses authored regions without implicit fallback`,
  scenario `Fresh world and reuse` (compensation half).
- `test_enter_wilderness_creates_no_population` and the round-trip module — MODIFIED
  `A registered wilderness monster survives room recycling`, scenario
  `Read and re-entry do not refill`.
- `world.maps.tests.test_regional_population_recovery.RealSessionRecoveryTests` —
  ADDED `Active encounters retain protected individuals and cells`.

### Real-world smoke evidence

The retained entrypoint is `tools/monster_population_smoke.py`, run through
`server/conf/monster_population_smoke_settings.py` against a disposable
database (the Evennia shell launcher's first-boot superuser check is bypassed
by the Django shell invocation):

```
MUD_SMOKE_DB=/tmp/mud-population-smoke.sqlite3 uv run --locked evennia migrate \
  --settings monster_population_smoke_settings --noinput
MUD_SMOKE_DB=/tmp/mud-population-smoke.sqlite3 \
  DJANGO_SETTINGS_MODULE=server.conf.monster_population_smoke_settings \
  uv run --locked python -m django shell \
  -c "import evennia; evennia._init(); from tools.monster_population_smoke import run; run()"
```

Observed output on the disposable database:

```json
{"seed": 0, "zone": "smoke_zone", "region": "western_hills_valleys", "birth_cells": 225, "coordinator_registered_once": true, "initial_pks": [2, 3, 4], "initial_state": {"generation_sequence": 3, "recovery_due_tick": null}, "view_initial_ids": [2, 3, 4], "defeat": {"pk": 2, "was_alive": true, "now_alive": false, "due_tick": 106}, "before_due_living": [3, 4], "before_exact_due_living": [3, 4], "at_due_living": [3, 4, 15], "delayed_wave_pks": [15], "state_after_due": {"generation_sequence": 4, "recovery_due_tick": null}, "view_due_ids": [3, 4, 15], "interrupt_hostile_ids": [3, 4, 15], "reload": {"id": 3, "hp": 40, "home_zone": "smoke_zone"}, "rollback": {"before_count": 4, "after_count": 4, "state": null, "retry_created": [17, 18, 19]}, "legacy_absent": {"ensure_population": true, "ambient_registry": true}, "species": "t_whisper_quail", "variant": "t_whisper_quail_ordinary"}
```

This proves the coordinator is registered once, a configured zone initializes
through the owner, births are actual registered individuals, one loss is
recorded by a real committed basic-attack combat round, no birth happens before
the due tick, the exact due tick produces a delayed wave, view and interrupt
surfaces show only living IDs, a fresh-object reload keeps
identity/resources/home, a post-construction fault leaves no state and a retry
succeeds, and no legacy generation symbol is importable. LLM and art services
are disabled in the smoke settings. Human review: the report names synthetic
species/content only; no shipped copy or balance value is asserted.

Disposition of the wider smoke contract: undersupplied hunt acceptance, GM
spawn/HP/delete, quest placement, manual excess, cleared one-shot sites and a
protected-battle restart are covered by their owning focused suites
(`test_regional_population*`, `test_monster_sites`, `test_site_clear_out_acceptance`,
`test_permanent_occupants`, GM/movement tests) rather than duplicated in this
runner. The runner deliberately exercises one real birth/defeat/recovery/reload
path plus the construction-fault retry.
