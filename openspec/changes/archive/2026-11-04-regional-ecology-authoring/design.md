# Design

## Context

`monster_placement.py` has frozen AmbientPlacementRule and MonsterSite plus injectable registry validation and reference metadata. Map geography is now YAML-backed through `world/maps/runtime.py` publication; `AnchorKind` distinguishes inhabited settlement categories from DUNGEON. `WILDERNESS_ENTRY_REGISTRY` supplies actual footprint cells; point anchors use `anchor_geography().cell`. `is_valid_wilderness_cell` is shared by provider and destinations.

## Goals / Non-Goals

Deliver this proposal's bounded regional-population prerequisite or cutover, using existing deterministic owners and real runnable operations. Do not implement adjacent field movement/aggression/escape or independent monster content. No compatibility paths or save conversion.

## Decisions

### Authoring contract
In `world/lore/monster_placement.py` add frozen slotted values:
```python
CompositionMember(variant_key: str, minimum: int, maximum: int)
EncounterComposition(key: str, members: tuple[CompositionMember, ...])
WeightedComposition(composition_key: str, weight: int)
EcologyZone(key: str, region_key: str, rectangles: tuple[tuple[int, int, int, int], ...],
            pool: tuple[WeightedComposition, ...], lower_density: int, upper_density: int,
            cell_capacity: int, recovery_delay: int, replenishment_interval: int,
            wave_budget: int)
SettlementBirthPolicy(anchor_key: str, buffer_cells: int)
```
Rectangle order is `(x_min, x_max, y_min, y_max)`, inclusive. References use existing `ref`/`ref_many` metadata, including nested composition members. Publish immutable keyed `ENCOUNTER_COMPOSITION_REGISTRY`, `ECOLOGY_ZONE_REGISTRY` and `SETTLEMENT_BIRTH_POLICY_REGISTRY` only after complete validation. Existing ambient rows remain solely until their explicit final cutover, with no aliases from old rows to zones.

### Candidate-world geometry contract
Add `world/maps/population_geometry.py` with pure `eligible_birth_cells(zone, *, geography, entries, policies) -> tuple[tuple[int, int], ...]` and `density_bounds(eligible_count: int, lower_density: int, upper_density: int) -> tuple[int, int]`. All inputs come from one candidate map bundle, never the previously published world. Deduplicate intersecting rectangles within a zone; intersect parent-region classification and map bounds/validity. Ordinary zones cannot share any parent-region geometry cell even if current terrain/exclusions make it unusable. Existing shared validity rules remain authoritative; no whole-world room scan/materialization.

Inhabited CAPITAL/CITY/TOWN/PORT/ELVEN_VILLAGE identities get at least a one-cell birth buffer. Explicit rows may enlarge it; reject unknown/nonsettlement identities and buffer below one. Use minimum Chebyshev distance to the complete footprint; use the anchor cell only for a point settlement. Dungeon anchors receive no automatic buffer. Geometry and density inspect the eligible cells after every exclusion. Do not apply these predicates to movement or explicit lawful placement.

`L=(E*lower_density+99)//100`, `U=(E*upper_density)//100`; integers excluding bool, `0<lower_density<=upper_density<100`, `E>0`, `1<=L<=U`. Empty enabled zones reject. All counts/weights/timings/capacities positive; `minimum<=maximum`; validate species ownership and habitat compatibility from variants. A complete outcome must fit cell capacity, wave budget and U. Reject a pool with no legal complete recovery path for any unobstructed sub-L population with lawful headroom, using reachable composition sizes and available cells rather than accepting only a fitting single example. Bounded dynamic programming over totals up to U proves recovery; never truncate groups or require exact L. Retain only fitting outcomes during runtime selection.

### Publication boundary and scope
Extend `world/maps/runtime.py::compose`/candidate validation and `world/maps/geography.py` joins to validate against the same candidate entries/terrain. Lore never mutates or reads a database. Author the following initial declarations in this change so supply-validation consumers have a lawful source before activation. These are authoring decisions, never test expected-value tables. Pure current-terrain inspection found each rectangle inside its named parent and over forty cells from every location anchor; implementation must still pass the shared candidate footprint/buffer validator.

| Zone key | Parent | Inclusive rectangle | Eligible variants |
| --- | --- | --- | --- |
| eastern_field_habitat | eastern_plains | (1520,1539,520,539) | grain_pecker, flock_leader, burrow_maker, nest_guard |
| highland_forest_habitat | northwest_highland_forest | (200,219,1320,1339) | wood_stalker, trail_hunter |
| southwest_shore_habitat | southwest_coast | (280,299,480,499) | shore_walker, reef_warden |
| western_rockland_habitat | western_hills_valleys | (200,219,760,779) | burrow_maker, nest_guard, cliff_stepper, pass_warden |

For each eligible variant author a solitary composition with count 1..1 and pool weight1. Additionally eastern_field_habitat gets a composition grain_pecker1 + burrow_maker1; western_rockland_habitat gets burrow_maker1 + cliff_stepper1, each weight1. Zone declarations initially use lower_density1, upper_density3, cell_capacity3, recovery_delay3600, replenishment_interval600, wave_budget3. These values live only in declarations; developer docs refer to the fields without copying an approval table. No new high-tier profile enters a pool. Enable the generic minimum-one-cell inhabited-settlement buffer, with no capital-specific exception. Old automatic creation remains scheduled for explicit removal at final cutover, with no translation from old rows to zones. Add a developer-document authoring section with formulas and registry signatures. Human review there assesses sparse local ecology and settlement-surroundings intent; tests do not pin production coordinates, density vectors, counts or prose.

## Risks / Trade-offs

The existing display-name, coordinate-slot and supply contracts have broad callers. Complete the named semantic caller cutover within this slice; do not add a parallel legacy path. Candidate-world validation and mutable Evennia cache restoration are part of correctness. Use synthetic independently known mechanism outcomes and real-owner integration controls instead of production data-echo tests.

## Verification and requirement traceability

During implementation, create an environment file outside tracked source containing `MUD_TEST_SETTINGS=1`. Focused command: `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb LABELS`. Replace LABELS with one affected focused method or class from the module inventory below, keeping the single-token env-file form; run independent focused invocations, never concatenate the whole inventory or exceed 100 discovered tests in one command. Use fixed synthetic inputs and independently known outputs. Production checks establish references, ownership/topology and profile obligations without copying shipped values or prose. New nonbrowser modules require exact ownership in `.github/evennia-shards.json`; browser methods, if added, require `.github/browser-shards.json` ownership. Run observability lint alongside focused tests when logging changes. Full managed browser and complete evidence verification remain CI-owned.

Before changing annotations, record each affected assertion's synthetic-mechanism, registry-contract or representative-smoke role and substantive replacement in `docs/development/regional-monster-population.md`. Canonical IDs below came from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/regional-population-requirements.json`. ADDED requirements have no current IDs; never fabricate one. Before archive, use the tool on an equivalent merged spec tree, then replace provisional nearest-current claims with generated IDs. Retain no retired, empty or skipped claims. Each delta scenario maps to tasks.md test modules and must assert behavior rather than echo data.

After the completed slice run `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. This gate does not establish coverage of unarchived deltas; the assertion-role ledger and focused evidence remain required. The runtime slice owns the cross-system real smoke; each earlier slice still owns real-owner integration and reload/fault controls.

## Deployment and rollback boundary

No migrations, legacy readers, aliases, implicit reset or compatibility setting are authorized. New ordinary runtime activates only at regional-population-runtime-cutover; earlier APIs are fully implemented and independently exercised through real owners. Operation failures restore durable and live surfaces through deterministic owner compensation. An incompatible development save requires documented explicit GM save/repair/reset procedures, never startup mutation. A source/code rollback requires its matching explicitly saved development state, with no incompatible-record reinterpretation.

### Nearest current canonical anchors

- `monster-site-placement::ambient-and-site-placement-are-frozen-keyed-lore-data-validated-at-construction`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.

### Focused implementation labels

`world.lore.tests.test_monster_placement world.maps.tests.test_population_geometry world.maps.tests.test_geography_source`
