# Design

## Context

Species-backed construction is already authoritative in `construct_species_individual`. Wilderness position lives in `itemcoordinates`, independent of materialized room presence. Existing `monster_sites` and clock SurfaceSnapshot/rollback helpers demonstrate whole-value Attributes, registration and cache compensation; database rollback alone leaves mutable SaverDict and room surfaces stale.

## Goals / Non-Goals

Deliver this proposal's bounded regional-population prerequisite or cutover, using existing deterministic owners and real runnable operations. Do not implement adjacent field movement/aggression/escape or independent monster content. No compatibility paths or save conversion.

## Decisions

### Public owner contract
Create `world/maps/regional_population.py`; only this map owner writes `wilderness.db.regional_population`, a whole-value dictionary keyed by zone key. Each entry is JSON-safe:
```python
{"initialized": True, "seed": int, "generation_sequence": int,
 "recovery_due_tick": int | None, "settled_through_tick": int}
```
No missing record is inferred as a legacy-save conversion. New ordinary individuals carry `db.home_ecology_zone: str` separately from position, plus the existing species/variant identity. Persistent dbref is individual identity; no cell/slot key is assigned. Discover home-owned living objects by the ownership Attribute independently of the coordinate registry, so unlocated/detached objects count. Any future journey retains the same marker and ID without requiring a journey implementation now.

Implement frozen `PopulationCounts(local_ids: frozenset[int], home_ids: frozenset[int], cell_ids: Mapping[tuple[int,int], frozenset[int]])` and pure/read-only `population_counts(wilderness, zone_key: str) -> PopulationCounts`. Local means zone rectangles intersected with parent region, including excluded-buffer cells and all living ambient/manual/site/quest individuals physically there; it is NOT restricted to eligible birth cells. Home means every living ordinary ID bearing the home marker wherever it is. Use stored HP, not ticking gauges. Each set deduplicates IDs; cell capacity counts all living Monster occupants. A visitor counts locally without transfer. No count or planner repairs foreign entities.

Expose `initialize_zone(wilderness, zone_key: str, *, seed: int, tick: int) -> tuple[int, ...]`, `plan_population_wave(wilderness, zone_key: str, *, tick: int) -> PopulationWavePlan`, `commit_population_wave(wilderness, plan: PopulationWavePlan) -> tuple[int, ...]` and `snapshot_regional_population_surfaces(start_tick: int, end_tick: int) -> dict[int, SurfaceSnapshot]`. Plan is frozen and contains zone_key, tick, expected seed/sequence, ordered `(cell, tuple[(variant_key,count),...])` placements, and blocked reason or None. Commit revalidates state/counts/protection before writes and rejects stale plans. A blocked plan commits no births and does not increment sequence.

### Deterministic fitting selection
Sort cells lexicographically and composition keys lexicographically; choose weighted complete composition outcomes only among outcomes fitting BOTH `U-local_count` and `U-home_count`, remaining wave budget and remaining cell capacity. Select position, composition and inclusive counts with separate SHA-256 draw purposes over canonical `(seed, zone_key, generation_sequence, tick, placement_ordinal, purpose, draw_ordinal)` bytes; integer sampling uses rejection sampling, not Python hash or global RNG. The same retry at the same tick/state selects the same outcome. Distinct birth occurrences reselect and need not reproduce coordinate species. Stop once local count reaches L or no complete outcome fits; never split a group. One successful wave increments sequence once, regardless of group count. Returning living members or explicit overpopulation cannot authorize deletion, replacement, rescaling or resource refill.

### Atomic writes and initialization
One `transaction.atomic` owns every complete wave, construction through `construct_species_individual`, home marker, full `itemcoordinates` write, any active-room attachment and state update. Initialize once using repeated constrained waves at the initialization tick until reaching L or lawful blockage, recording initialization and all created individuals atomically. Normal recovery delay belongs to the next change; initialization never repeats because of restart, source reread or room activation. A preexisting initialized state keeps stored seed, sequence and resources. A missing wilderness is a named `world_unavailable`; unknown zone/malformed state rejects before writes, separate from temporary blocked space.

Snapshot all existing map Attributes, registrations, touched entity locations, room contents and owner/cache surfaces before mutation. Track newly constructed objects and flush rolled-back idmapper instances; restore live SaverDict and room/contents caches on ANY later failure, including state write or enclosing clock failure. Existing active-session cells are unavailable to births; neither session participants nor unrelated entities are changed. Committed births emit bounded `monster_population_wave` through named observability imports/on_commit with zone/region/ID/species/variant/cell/tick; no rolled-back birth event, read event or unchanged-reconcile event. A later caller-owned rollback invokes the same compensation through the existing clock surface contract, not merely on a local exception.

### Scope
Implement real callable owner operations and integration tests without enabling a second production scheduler/ambient branch. Do not touch provider preparation, old ambient helpers, hunt acceptance, activity or new content. `docs/development/regional-monster-population.md` records ownership and rollback API.

## Risks / Trade-offs

The existing display-name, coordinate-slot and supply contracts have broad callers. Complete the named semantic caller cutover within this slice; do not add a parallel legacy path. Candidate-world validation and mutable Evennia cache restoration are part of correctness. Use synthetic independently known mechanism outcomes and real-owner integration controls instead of production data-echo tests.

## Verification and requirement traceability

During implementation, create an environment file outside tracked source containing `MUD_TEST_SETTINGS=1`. Focused command: `uv run --locked --env-file=/tmp/mud-population-test.env evennia test --settings test_settings.py --keepdb LABELS`. Replace LABELS with this slice's labels below, keeping the single-token env-file form. Use fixed synthetic inputs and independently known outputs. Production checks establish references, ownership/topology and profile obligations without copying shipped values or prose. New nonbrowser modules require exact ownership in `.github/evennia-shards.json`; browser methods, if added, require `.github/browser-shards.json` ownership. Run observability lint alongside focused tests when logging changes. Full managed browser and complete evidence verification remain CI-owned.

Before changing annotations, record each affected assertion's synthetic-mechanism, registry-contract or representative-smoke role and substantive replacement in `docs/development/regional-monster-population.md`. Canonical IDs below came from `uv run --locked python -m tools.spec_traceability list --json-output /tmp/regional-population-requirements.json`. ADDED requirements have no current IDs; never fabricate one. Before archive, use the tool on an equivalent merged spec tree, then replace provisional nearest-current claims with generated IDs. Retain no retired, empty or skipped claims. Each delta scenario maps to tasks.md test modules and must assert behavior rather than echo data.

After the completed slice run `openspec validate <change> --strict` and `uv run --locked python -m tools.contract_gate`. This gate does not establish coverage of unarchived deltas; the assertion-role ledger and focused evidence remain required. The runtime slice owns the cross-system real smoke; each earlier slice still owns real-owner integration and reload/fault controls.

## Deployment and rollback boundary

No migrations, legacy readers, aliases, implicit reset or compatibility setting are authorized. New ordinary runtime activates only at regional-population-runtime-cutover; earlier APIs are fully implemented and independently exercised through real owners. Operation failures restore durable and live surfaces through deterministic owner compensation. An incompatible development save requires documented explicit GM save/repair/reset procedures, never startup mutation. A source/code rollback requires its matching explicitly saved development state, with no incompatible-record reinterpretation.

### Nearest current canonical anchors

- `wilderness-monster-population::a-registered-wilderness-monster-survives-room-recycling`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.
- `monster-site-placement::every-placed-individual-carries-its-owner-marker-and-reconciliation-stays-inside-the-owner-domain`: substantive current ownership/identity/lifecycle anchor; newly added behavior requires generated post-sync coverage, not an assertion-free extra decorator.

### Focused implementation labels

`world.maps.tests.test_regional_population`
